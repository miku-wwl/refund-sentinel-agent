"""Financial dispatch guards with actual SQLite waits and the unmodified Runtime."""

import asyncio
import json
import sqlite3
import threading
import time
from uuid import uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import (
    ActionCommand,
    ActionError,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
)
from test_phase23_preflight import MockRefundHTTP
from test_providers import CAPTURE, sandbox_settings

from refund_sentinel import integration
from refund_sentinel.integration import RefundExecutor, composition, provision
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.service import Sentinel
from refund_sentinel.store import Store


async def prepare_refund(runtime, store, client, model, settings, directory):
    principal = runtime.verifier.verify(
        "Bearer " + (directory / "operator.capability").read_text("ascii")
    )
    result = await Sentinel(runtime, store, client, model, settings).analyze(
        RequestInput(capture_id=CAPTURE, message="Synthetic damage. Refund NZD 5.00.")
    )
    assert result["run"]["state"] == "AwaitingApproval"
    run = runtime.run_service.decide(
        result["run"]["run_id"],
        ApprovalDecisionRequest(ApprovalChoice.APPROVE, result["run"]["version"]),
    )
    action = runtime.gateway.admit(
        AdmissionCommand(run.run_id, run.version, principal.subject_id, str(uuid4())), principal
    ).action
    action = runtime.gateway.authorize(
        ActionCommand(action.action_id, action.version, str(uuid4())), principal
    ).action
    return principal, ActionCommand(action.action_id, action.version, str(uuid4()))


FAULTS = {
    "already_expired": 0,
    "incident_read_wait": 0,
    "incident_read_cancel": 0,
    "dispatch_commit_wait": 0,
    "dispatch_commit_error": 0,
    "dispatch_task_cancel": 0,
    "dispatch_context_cancel": 0,
    "oauth_expiry": 0,
    "oauth_cancel": 0,
    "httpx_preparation_expiry": 0,
    "httpx_preparation_cancel": 0,
    "response_commit_wait": 1,
    "response_commit_error": 1,
    "receipt_commit_wait": 1,
    "receipt_commit_error": 1,
    "lost_post_response": 1,
    "pending": 1,
}


@pytest.mark.parametrize("fault", FAULTS)
def test_pre_dispatch_stop_and_post_dispatch_unknown(tmp_path, monkeypatch, fault):
    async def run():
        context = None
        faulted = False
        releases = []
        sqlite_waits = []

        def delay_sqlite(path, *, reading=False):
            connection = sqlite3.connect(path, check_same_thread=False)
            connection.execute("BEGIN EXCLUSIVE" if reading else "BEGIN IMMEDIATE")

            def release():
                connection.commit()
                connection.close()

            timer = threading.Timer(0.45, release)
            timer.start()
            releases.append(timer)

        class FaultStore(Store):
            def get(self, *args):
                nonlocal faulted
                if context is not None and not faulted and fault.startswith("incident_read"):
                    faulted = True
                    if fault.endswith("cancel"):
                        asyncio.current_task().cancel()
                    else:
                        delay_sqlite(self.path, reading=True)
                start = time.perf_counter()
                try:
                    return super().get(*args)
                finally:
                    if fault == "incident_read_wait" and context is not None:
                        sqlite_waits.append(time.perf_counter() - start)

            def observe(self, *args, **kwargs):
                nonlocal faulted
                phase = kwargs["phase"]
                selected = {
                    "dispatch": "REFUND_DISPATCH",
                    "response": "REFUND_RESPONSE",
                    "receipt": "VERIFIED_REFUND",
                }.get(fault.split("_")[0])
                if phase == selected and not faulted:
                    faulted = True
                    if fault.endswith("wait"):
                        delay_sqlite(self.path)
                    elif fault.endswith("error"):
                        raise sqlite3.OperationalError("Synthetic commit uncertainty")
                    elif fault == "dispatch_task_cancel":
                        asyncio.current_task().cancel()
                    elif fault == "dispatch_context_cancel":
                        context.cancelled.set()
                start = time.perf_counter()
                try:
                    return super().observe(*args, **kwargs)
                finally:
                    if phase == selected and fault.endswith("wait"):
                        sqlite_waits.append(time.perf_counter() - start)

        class ObservedExecutor(RefundExecutor):
            async def execute(self, spec, effect_key, attempt):
                nonlocal context
                context = attempt
                network.context_deadline = attempt.deadline
                return await super().execute(spec, effect_key, attempt)

        class FaultHTTP(MockRefundHTTP):
            async def handle(self, request):
                if self.executing and request.url.path == "/v1/oauth2/token":
                    if fault == "oauth_expiry":
                        time.sleep(0.45)  # Expiry during synchronous provider response processing.
                    elif fault == "oauth_cancel":
                        asyncio.current_task().cancel()
                return await super().handle(request)

        scenario = fault if fault in {"lost_post_response", "pending"} else "completed"
        network = FaultHTTP(tmp_path / "provider.sqlite3", scenario)
        monkeypatch.setattr(integration, "Store", FaultStore)
        monkeypatch.setattr(integration, "RefundExecutor", ObservedExecutor)
        settings = sandbox_settings()
        directory = tmp_path / "runtime"
        provision(directory, settings)
        client = SandboxPayPal(settings, transport=httpx.MockTransport(network.handle))

        async def prepare_hook(request):
            if request.method == "POST" and request.url.path.endswith("/refund"):
                if fault == "httpx_preparation_expiry":
                    time.sleep(0.45)
                elif fault == "httpx_preparation_cancel":
                    asyncio.current_task().cancel()

        client.http.event_hooks["request"] = [prepare_hook]
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            principal, command = await prepare_refund(
                runtime, store, client, model, settings, directory
            )
            assert network.post_count() == 0
            if fault.startswith("oauth"):
                client._until = 0
            network.executing = True
            telemetry_start = len(client.telemetry)
            network.started = time.perf_counter()
            deadline = asyncio.get_running_loop().time() + (
                -1 if fault == "already_expired" else 0.35
            )
            task = asyncio.create_task(
                runtime.gateway.execute(command, principal, deadline=deadline)
            )
            cancelled = False
            try:
                result = await task
                assert result.action.state.value == "Unknown"
            except asyncio.CancelledError:
                cancelled = True
                assert "cancel" in fault
            elapsed = time.perf_counter() - network.started
            assert runtime.actions.get(command.action_id).state.value == "Unknown"
            assert network.post_count() == len(network.effects()) == FAULTS[fault]
            assert not network.dispatch_after_deadline
            assert (await runtime.gateway.execute(command, principal)).replayed
            current = runtime.actions.get(command.action_id)
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(current.action_id, current.version, str(uuid4())), principal
                )
            phases = [r["data"]["phase"] for r in store.observations(current.effect_key)]
            if fault == "response_commit_wait":
                assert "REFUND_RESPONSE" in phases
                assert not any(x[1].startswith("/v2/payments/refunds/") for x in network.calls)
            if fault == "receipt_commit_wait":
                assert "VERIFIED_REFUND" in phases
            if fault.endswith("wait"):
                assert max(sqlite_waits) >= 0.35
            evidence = {
                "source": "ISOLATED_HTTP_MOCK_AND_REAL_SQLITE_WAIT",
                "fault": fault,
                "public_caller_deadline_seconds": -1 if fault == "already_expired" else 0.35,
                "immutable_runtime_limit_seconds": runtime.gateway.tool_timeout_seconds,
                "gateway_elapsed_seconds": round(elapsed, 6),
                "durable_action_state": "Unknown",
                "caller_observed_cancellation": cancelled,
                "refund_post_count": network.post_count(),
                "mock_post_after_deadline": network.dispatch_after_deadline,
                "requests": client.telemetry[telemetry_start:],
                "real_sqlite_wait_seconds": sqlite_waits,
                "observation_phases": phases,
            }
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (directory / "operator.capability").read_text("ascii")
            )
            assert (await runtime.gateway.execute(command, principal)).replayed
            assert runtime.actions.get(command.action_id).state.value == "Unknown"
            assert network.post_count() == FAULTS[fault]
        for timer in releases:
            timer.join(timeout=2)
            assert not timer.is_alive()
        await client.close()
        evidence["restart_replay_without_post"] = True
        (tmp_path / "deadline-evidence.json").write_text(json.dumps(evidence, indent=2), "utf-8")

    asyncio.run(run())
