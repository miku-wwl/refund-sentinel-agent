"""Phase 2.3 qualification: real consumer/Runtime, isolated HTTP and synthetic identities."""

import asyncio
import json
import sqlite3
import sys
import time
from uuid import UUID, uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import (
    ActionCommand,
    ActionError,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
)
from test_preflight import token_response
from test_providers import CAPTURE, ORDER, REFUND, capture_data, order_data, sandbox_settings

from refund_sentinel import integration
from refund_sentinel.integration import RefundExecutor, composition, provision
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.service import Sentinel
from refund_sentinel.store import Store

SCENARIOS = {
    "completed": "Succeeded",
    "cold_oauth": "Succeeded",
    "lost_post_response": "Unknown",
    "pending": "Unknown",
    "lost_refund_id": "Unknown",
    "lookup_timeout": "Unknown",
    "foreign_capture": "Unknown",
    "legacy_sandbox_link": "Succeeded",
    "cumulative_delay": "Succeeded",
    "cumulative_delay_cold": "Succeeded",
    "lost_ack_at_deadline": "Unknown",
    "slow_dispatch_persistence": "Unknown",
}


def synthetic_capture_order():
    capture, order = capture_data(), order_data()
    capture["amount"] = {"value": "20.00", "currency_code": "NZD"}
    order["intent"] = "CAPTURE"
    order["purchase_units"][0]["amount"] = capture["amount"].copy()
    order["purchase_units"][0]["payments"]["captures"] = [capture]
    return capture, order


class MockRefundHTTP:
    """Effects commit independently before an acknowledgment can be lost or cancelled."""

    def __init__(self, path, scenario, *, delays=None):
        self.path, self.scenario = path, scenario
        self.delays = delays
        self.executing = False
        self.started = 0
        self.calls, self.commit_times = [], []
        self.provider_commits = []
        self.context_deadline = None
        self.dispatch_after_deadline = False
        self.capture, self.order = synthetic_capture_order()
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE effects(request_id TEXT PRIMARY KEY, payload TEXT, status TEXT)"
            )

    async def handle(self, request):
        assert request.url.host == "api-m.sandbox.paypal.com"
        assert not request.url.query and request.url.scheme == "https"
        path = request.url.path
        self.calls.append((request.method, path))
        if self.executing:
            delay = 0.025
            if self.delays is not None:
                operation = (
                    "oauth"
                    if path == "/v1/oauth2/token"
                    else "refund_post"
                    if path.endswith("/refund")
                    else "refund_get"
                    if "/refunds/" in path
                    else "order_get"
                    if "/orders/" in path
                    else "capture_get"
                )
                delay = self.delays[operation]
            elif self.scenario == "cumulative_delay":
                delay = 1.35  # Composite request latency; not an HTTPX per-phase timeout test.
            elif self.scenario == "cumulative_delay_cold":
                delay = 1.1
            elif self.scenario == "slow_dispatch_persistence":
                delay = 1.8 if request.method == "GET" and "refunds" not in path else 0
            elif self.scenario == "lost_ack_at_deadline":
                delay = 0
            if delay and not path.endswith("/refund"):
                await asyncio.sleep(delay)
        if path == "/v1/oauth2/token":
            return httpx.Response(200, json=token_response())
        assert request.headers["Authorization"] == "Bearer fixture-access-token"
        if path == f"/v2/payments/captures/{CAPTURE}":
            assert request.method == "GET"
            return httpx.Response(200, json=self.capture)
        if path == f"/v2/checkout/orders/{ORDER}":
            assert request.method == "GET"
            return httpx.Response(200, json=self.order)
        if path == f"/v2/payments/captures/{CAPTURE}/refund":
            assert self.executing and request.method == "POST"
            self.dispatch_after_deadline = (
                asyncio.get_running_loop().time() >= self.context_deadline
            )
            key = request.headers["PayPal-Request-Id"]
            assert str(UUID(key)) == key
            assert request.headers["Prefer"] == "return=representation"
            body = json.loads(request.content)
            assert body == {"amount": {"value": "5.00", "currency_code": "NZD"}}
            status = "PENDING" if self.scenario == "pending" else "COMPLETED"
            start = time.perf_counter()
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO effects VALUES (?,?,?)", (key, json.dumps(body), status))
            self.provider_commits.append(time.perf_counter() - start)
            self.commit_times.append(time.perf_counter() - self.started)
            if self.delays is not None:
                await asyncio.sleep(self.delays["refund_post"])
            if self.scenario == "lost_post_response":
                raise httpx.ReadTimeout("Synthetic lost acknowledgment", request=request)
            if self.scenario == "lost_ack_at_deadline":
                await asyncio.sleep(10)
            if self.scenario == "cumulative_delay":
                await asyncio.sleep(1.35)
            elif self.scenario == "cumulative_delay_cold":
                await asyncio.sleep(1.1)
            if self.scenario == "lost_refund_id":
                return httpx.Response(201, json={"status": status})
            return httpx.Response(201, json={"id": REFUND, "status": status})
        assert path == f"/v2/payments/refunds/{REFUND}" and request.method == "GET"
        if self.scenario == "lookup_timeout":
            raise httpx.ReadTimeout("Synthetic read timeout", request=request)
        origin = "https://api-m.sandbox.paypal.com"
        if self.scenario == "legacy_sandbox_link":
            origin = "https://api.sandbox.paypal.com"
        related = ORDER if self.scenario == "foreign_capture" else CAPTURE
        return httpx.Response(
            200,
            json={
                "id": REFUND,
                "status": "PENDING" if self.scenario == "pending" else "COMPLETED",
                "amount": {"value": "5.00", "currency_code": "NZD"},
                "links": [
                    {
                        "rel": "up",
                        "method": "GET",
                        "href": f"{origin}/v2/payments/captures/{related}",
                    }
                ],
            },
        )

    def effects(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT request_id, status FROM effects").fetchall()

    def post_count(self):
        return sum(method == "POST" and path.endswith("/refund") for method, path in self.calls)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_http_mock_qualification(tmp_path, monkeypatch, scenario):
    async def run():
        persistence = []
        store_reads = []
        network = MockRefundHTTP(tmp_path / "mock-provider.sqlite3", scenario)

        class MeasuredStore(Store):
            def get(self, *args):
                start = time.perf_counter()
                try:
                    return super().get(*args)
                finally:
                    store_reads.append(time.perf_counter() - start)

            def observe(self, *args, **kwargs):
                start = time.perf_counter()
                if scenario == "slow_dispatch_persistence" and kwargs["phase"] == "REFUND_DISPATCH":
                    time.sleep(1.6)  # Model a wait below Store's 2s busy timeout.
                try:
                    return super().observe(*args, **kwargs)
                finally:
                    persistence.append(
                        {"phase": kwargs["phase"], "seconds": time.perf_counter() - start}
                    )

        class MeasuredExecutor(RefundExecutor):
            async def execute(self, spec, effect_key, context):
                network.context_deadline = context.deadline
                return await super().execute(spec, effect_key, context)

        class ReadReferenceClient(SandboxPayPal):
            async def capture(self, capture_id, *, expected_order_id=None):
                # Preserve the former 5s expiry reproduction while current reads run concurrently.
                hint = None if scenario == "slow_dispatch_persistence" else expected_order_id
                return await super().capture(capture_id, expected_order_id=hint)

        # Instrument consumer storage only. The installed Runtime is not patched or replaced.
        monkeypatch.setattr(integration, "Store", MeasuredStore)
        monkeypatch.setattr(integration, "RefundExecutor", MeasuredExecutor)
        settings = sandbox_settings()
        provision(tmp_path / "runtime", settings)
        directory = tmp_path / "runtime"
        client = ReadReferenceClient(settings, transport=httpx.MockTransport(network.handle))
        core_persistence, profile_starts = [], {}

        def profile(frame, event, arg):
            code = frame.f_code
            if code.co_filename.endswith("sqlite_action_execution.py") and code.co_name in {
                "claim",
                "finish",
            }:
                if event == "call":
                    profile_starts[id(frame)] = time.perf_counter()
                elif event == "return":
                    core_persistence.append(
                        {
                            "operation": code.co_name,
                            "seconds": time.perf_counter() - profile_starts.pop(id(frame)),
                        }
                    )

        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            principal = runtime.verifier.verify(
                "Bearer " + (directory / "operator.capability").read_text("ascii")
            )
            sentinel = Sentinel(runtime, store, client, model, settings)
            result = await sentinel.analyze(
                RequestInput(capture_id=CAPTURE, message="Synthetic damage. Refund NZD 5.00.")
            )
            assert result["run"]["state"] == "AwaitingApproval" and network.post_count() == 0
            assert not runtime.gateway.list_for_run(result["run"]["run_id"], principal)
            run = runtime.run_service.decide(
                result["run"]["run_id"],
                ApprovalDecisionRequest(ApprovalChoice.APPROVE, result["run"]["version"]),
            )
            assert network.post_count() == 0
            action = runtime.gateway.admit(
                AdmissionCommand(run.run_id, run.version, principal.subject_id, str(uuid4())),
                principal,
            ).action
            # Approval and admission do not grant execution authorization.
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(action.action_id, action.version, str(uuid4())), principal
                )
            assert network.post_count() == 0
            action = runtime.gateway.authorize(
                ActionCommand(action.action_id, action.version, str(uuid4())), principal
            ).action
            assert network.post_count() == 0
            command = ActionCommand(action.action_id, action.version, str(uuid4()))
            if scenario in {"cold_oauth", "cumulative_delay_cold"}:
                client._until = 0  # Isolated Mock client only, exercising documented token refresh.
            assert runtime.gateway.tool_timeout_seconds == 5
            network.executing = True
            telemetry_start = len(client.telemetry)
            store_reads.clear()
            previous_profile = sys.getprofile()
            network.started = time.perf_counter()
            try:
                sys.setprofile(profile)  # Observational timings; no change to core dispatch/claim.
                outcome = await runtime.gateway.execute(
                    command, principal, deadline=asyncio.get_running_loop().time() + 30
                )
            finally:
                sys.setprofile(previous_profile)
            elapsed = time.perf_counter() - network.started
            execution_reads = store_reads.copy()
            expected_posts = 0 if scenario == "slow_dispatch_persistence" else 1
            assert outcome.action.state.value == SCENARIOS[scenario]
            assert runtime.actions.get(action.action_id).state.value == SCENARIOS[scenario]
            assert network.post_count() == len(network.effects()) == expected_posts
            if expected_posts:
                assert network.effects()[0][0] == action.effect_key
            assert (await runtime.gateway.execute(command, principal)).replayed
            current = runtime.actions.get(action.action_id)
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(current.action_id, current.version, str(uuid4())), principal
                )
            assert network.post_count() == expected_posts
            observations = store.observations(action.effect_key)
            phases = [row["data"]["phase"] for row in observations]
            if SCENARIOS[scenario] == "Succeeded":
                assert phases == ["REFUND_DISPATCH", "REFUND_RESPONSE", "VERIFIED_REFUND"]
            if scenario == "lost_ack_at_deadline":
                assert 4.8 <= elapsed < 7
            if scenario in {"cumulative_delay", "cumulative_delay_cold"}:
                assert "VERIFIED_REFUND" in phases
            if scenario == "slow_dispatch_persistence":
                assert elapsed > 5 and "REFUND_DISPATCH" in phases
            assert not network.dispatch_after_deadline
            evidence = {
                "source": "ISOLATED_HTTP_MOCK_WITH_PINNED_RUNTIME",
                "scenario": scenario,
                "serial_read_reference": scenario == "slow_dispatch_persistence",
                "action_state": SCENARIOS[scenario],
                "runtime_limit_seconds": 5,
                "requested_deadline_seconds": 30,
                "gateway_elapsed_seconds": round(elapsed, 6),
                "requests_during_execute": client.telemetry[telemetry_start:],
                "consumer_observation_commits": persistence,
                "consumer_incident_read_seconds": execution_reads,
                "runtime_persistence": core_persistence,
                "mock_provider_commit_seconds": network.provider_commits,
                "effect_commit_elapsed_seconds": network.commit_times,
                "mock_post_started_after_actual_context_deadline": network.dispatch_after_deadline,
                "mock_effect_status": network.effects()[0][1] if expected_posts else "NONE",
                "refund_posts_after_replay": network.post_count(),
                "persisted_mock_effects": len(network.effects()),
                "stable_effect_key_used_as_request_id": bool(expected_posts),
                "approval_without_authorization_rejected": True,
                "observation_phases": phases,
            }
        # Reload the same isolated identity/history. Unknown must stay terminal after restart.
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (directory / "operator.capability").read_text("ascii")
            )
            assert (await runtime.gateway.execute(command, principal)).replayed
            assert runtime.actions.get(action.action_id).state.value == SCENARIOS[scenario]
            assert network.post_count() == expected_posts
            evidence["same_command_after_restart_replayed_without_dispatch"] = True
        await client.close()
        (tmp_path / "qualification.json").write_text(json.dumps(evidence, indent=2), "utf-8")

    asyncio.run(run())
