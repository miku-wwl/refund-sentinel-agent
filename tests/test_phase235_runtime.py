"""Actual installed v0.2.0 Gateway, synthetic provider and isolated state only."""

import asyncio
import json
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import (
    ActionCommand,
    ActionError,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
    ToolBinding,
    execution_budget_binding,
)
from pydantic import ValidationError
from test_phase23_preflight import MockRefundHTTP
from test_phase231_deadlines import prepare_refund
from test_providers import CAPTURE, sandbox_settings

from refund_sentinel.integration import composition, provision
from refund_sentinel.models import Problem, RequestInput
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.profiles import SANDBOX_15_PROFILE
from refund_sentinel.web import ExecutionCommand


def extended(tmp_path):
    settings = sandbox_settings()
    provision(tmp_path, settings, profile=SANDBOX_15_PROFILE)
    identity = json.loads((tmp_path / "identity.json").read_text("utf-8"))
    return settings, identity


def test_default_extended_identity_and_readonly_configuration(tmp_path):
    legacy = tmp_path / "legacy"
    provision(legacy, sandbox_settings())
    identity = json.loads((legacy / "identity.json").read_text("utf-8"))
    assert (
        "execution_profile" not in identity
        and identity["binding"]["binding_revision"] == "refund-binding-v1"
    )
    fresh = tmp_path / "extended"
    settings, identity = extended(fresh)
    assert UUID(identity["binding"]["execution_scope"]).version == 4
    assert (
        identity["binding"]["execution_scope"]
        != json.loads((legacy / "identity.json").read_text("utf-8"))["binding"]["execution_scope"]
    )
    assert identity["binding"]["binding_revision"] == "refund-binding-v2.exec-15s"
    assert identity["execution_profile"] == asdict(SANDBOX_15_PROFILE)
    with composition(fresh, settings, predecessor_stopped=True) as resources:
        runtime, store, client, model, executor = resources
        assert runtime.gateway.tool_timeout_seconds == 15
        assert client.http.timeout.read == 4 and client.http.timeout.connect == 1.1
        assert executor.binding.binding_revision == identity["binding"]["binding_revision"]
        with pytest.raises((AttributeError, TypeError)):
            runtime.gateway.tool_timeout_seconds = 30
        store.check_identity()
        asyncio.run(client.close())
        asyncio.run(model.close())
    with pytest.raises(Problem, match="PERSISTED_EXECUTION_PROFILE_MISMATCH"):
        with composition(legacy, settings, profile=SANDBOX_15_PROFILE, predecessor_stopped=True):
            pass


@pytest.mark.parametrize("value", [True, False, None, "15", float("nan"), float("inf"), -1, 0, 16])
def test_invalid_public_budget_rejected(value):
    binding = ToolBinding(
        "paypal_partial_refund",
        "1",
        "paypal-sandbox-adapter",
        "reviewed-v2",
        "paypal-sandbox-refunds",
        str(uuid4()),
    )
    with pytest.raises((ValueError, TypeError)):
        execution_budget_binding(binding, value)


def test_untrusted_budget_and_unreviewed_profile_rejected(tmp_path):
    with pytest.raises(ValidationError):
        RequestInput(capture_id=CAPTURE, message="Synthetic NZD 5.00", execution_timeout_seconds=15)
    with pytest.raises(ValidationError):
        ExecutionCommand(
            expected_version=2,
            plan_digest="0" * 64,
            idempotency_key=str(uuid4()),
            execution_timeout_seconds=15,
        )
    with pytest.raises(Problem, match="UNREVIEWED_EXECUTION_PROFILE"):
        provision(
            tmp_path / "bad", sandbox_settings(), profile=replace(SANDBOX_15_PROFILE, seconds=16)
        )
    with pytest.raises(Problem, match="EXTENDED_PROFILE_REQUIRES_SANDBOX"):
        from refund_sentinel.config import Settings

        provision(tmp_path / "offline", Settings(), profile=SANDBOX_15_PROFILE)
    with pytest.raises(ValidationError):
        sandbox_settings(environment="live")


@pytest.mark.parametrize("tamper", ["profile", "binding", "store"])
def test_persisted_identity_mismatch_stops_before_network(tmp_path, tamper):
    settings, identity = extended(tmp_path)
    if tamper == "profile":
        identity["execution_profile"]["seconds"] = 5
    elif tamper == "binding":
        identity["binding"]["execution_scope"] = str(uuid4())
    else:
        with sqlite3.connect(tmp_path / "application.sqlite3") as db:
            db.execute("UPDATE store_identity SET identity='{}'")
    if tamper != "store":
        (tmp_path / "identity.json").write_text(json.dumps(identity), "utf-8")
    with pytest.raises(Problem):
        with composition(tmp_path, settings, predecessor_stopped=True):
            pytest.fail("Tampered identity entered Runtime")


CASES = {
    "warm": "Succeeded",
    "cold": "Succeeded",
    "read_timeout": "Failed",
    "lost_ack": "Unknown",
    "pending": "Unknown",
    "slow_get": "Unknown",
    "reserve": "Failed",
    "short_caller": "Unknown",
    "cancel": "Unknown",
    "expiry_commit": "Unknown",
    "late_receipt": "Unknown",
    "direct_over_10": "Succeeded",
    "wrong_capture": "Failed",
    "wrong_merchant": "Failed",
}


@pytest.mark.parametrize("case", CASES)
def test_extended_actual_gateway_financial_path(tmp_path, monkeypatch, case):
    async def run():
        settings, identity = extended(tmp_path)
        network = MockRefundHTTP(
            tmp_path / "mock.sqlite3", "pending" if case == "pending" else "completed"
        )
        base = network.handle
        context = None
        delays = {
            "oauth": 0.7,
            "capture_get": 0.05,
            "order_get": 0.08,
            "refund_post": 0.1,
            "refund_get": 0.1,
        }
        if case in {"warm", "cold"}:
            delays.update(capture_get=1.1, order_get=1.8, refund_post=0.7, refund_get=0.7)
        if case == "read_timeout":
            delays["order_get"] = 4.2
        if case == "slow_get":
            delays["refund_get"] = 4.2
        if case == "direct_over_10":
            delays.update(order_get=1.8, refund_post=3.4, refund_get=3.4)

        async def handle(request):
            if not network.executing:
                return await base(request)
            path = request.url.path
            operation = (
                "oauth"
                if path.endswith("/token")
                else "refund_post"
                if path.endswith("/refund")
                else "refund_get"
                if "/refunds/" in path
                else "order_get"
                if "/orders/" in path
                else "capture_get"
            )
            response = await base(request) if operation == "refund_post" else None
            if case == "lost_ack" and operation == "refund_post":
                raise httpx.ReadTimeout("Synthetic lost acknowledgment", request=request)
            try:
                await asyncio.wait_for(
                    asyncio.sleep(delays[operation]), timeout=request.extensions["timeout"]["read"]
                )
            except TimeoutError:
                raise httpx.ReadTimeout("Synthetic read expiry", request=request) from None
            return response if response is not None else await base(request)

        client = SandboxPayPal(
            settings,
            transport=httpx.MockTransport(handle),
            http_timeout=SANDBOX_15_PROFILE.http_timeout(),
        )
        with composition(tmp_path, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, executor = resources
            principal, command = await prepare_refund(
                runtime, store, client, model, settings, tmp_path
            )
            action = runtime.gateway.get(command.action_id, principal)
            assert "action-compiler-v3" in json.dumps(action.spec.to_dict())
            assert action.spec.binding_revision == "refund-binding-v2.exec-15s"
            assert action.effect_key != command.idempotency_key
            original_execute = executor._execute

            async def capture_context(spec, key, attempt):
                nonlocal context
                context = attempt
                network.context_deadline = attempt.deadline
                return await original_execute(spec, key, attempt)

            executor._execute = (
                capture_context  # Consumer executor observation, not a Runtime patch.
            )
            original_observe = store.observe

            def observe(*args, **kwargs):
                if kwargs["phase"] == "REFUND_DISPATCH":
                    if case == "cancel":
                        context.cancelled.set()
                    if case == "expiry_commit":
                        time.sleep(
                            max(0, context.deadline - asyncio.get_running_loop().time()) + 0.02
                        )
                if kwargs["phase"] == "VERIFIED_REFUND":
                    if case == "late_receipt":
                        time.sleep(15)
                    if case == "direct_over_10":
                        time.sleep(2)
                return original_observe(*args, **kwargs)

            monkeypatch.setattr(store, "observe", observe)
            if case == "wrong_capture":
                network.capture["id"] = "8" * 17
            if case == "wrong_merchant":
                network.capture["payee"]["merchant_id"] = "X" * 13
            if case == "cold":
                client._until = 0
            network.executing = True
            start = time.perf_counter()
            network.started = start
            caller = (
                asyncio.get_running_loop().time() + 0.04
                if case == "short_caller"
                else asyncio.get_running_loop().time() + 4
                if case == "reserve"
                else None
            )
            result = await runtime.gateway.execute(command, principal, deadline=caller)
            wall = time.perf_counter() - start
            expected_posts = (
                0
                if case
                in {
                    "read_timeout",
                    "reserve",
                    "short_caller",
                    "cancel",
                    "expiry_commit",
                    "wrong_capture",
                    "wrong_merchant",
                }
                else 1
            )
            assert result.action.state.value == CASES[case]
            assert network.post_count() == expected_posts and not network.dispatch_after_deadline
            if case == "direct_over_10":
                assert 10 < wall < 15
            if caller is not None and context is not None:
                assert context.deadline <= caller
            if case == "short_caller":
                assert network.post_count() == 0
            assert (await runtime.gateway.execute(command, principal)).replayed
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(command.action_id, result.action.version, str(uuid4())), principal
                )
            assert network.post_count() == expected_posts
            if result.action.state.value == "Succeeded":
                receipt = result.action.snapshot()["result"]["receipt_reference"]
                assert any(
                    r["id"] == receipt and r["data"]["phase"] == "VERIFIED_REFUND"
                    for r in store.observations(action.effect_key)
                )
            evidence = {
                "source": "ISOLATED_MOCK_REAL_RUNTIME_V020_GATEWAY",
                "case": case,
                "action_state": result.action.state.value,
                "gateway_seconds": round(wall, 6),
                "adapter_limit": runtime.gateway.tool_timeout_seconds,
                "posts": network.post_count(),
                "requests": client.telemetry,
                "binding_revision": action.spec.binding_revision,
            }
            destination = Path("evidence/phase-2.3.5/mock")
            destination.mkdir(parents=True, exist_ok=True)
            (destination / f"{case}.json").write_text(
                json.dumps(evidence, indent=2) + "\n", "utf-8"
            )
        with composition(tmp_path, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (tmp_path / "operator.capability").read_text("ascii")
            )
            assert (await runtime.gateway.execute(command, principal)).replayed
            assert network.post_count() == expected_posts
        await client.close()

    asyncio.run(run())


def test_approval_authorization_scope_and_concurrent_commands(tmp_path):
    async def run():
        settings, _ = extended(tmp_path)
        network = MockRefundHTTP(tmp_path / "mock.sqlite3", "completed")
        client = SandboxPayPal(
            settings,
            transport=httpx.MockTransport(network.handle),
            http_timeout=SANDBOX_15_PROFILE.http_timeout(),
        )
        with composition(tmp_path, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            from agentic_intent_gate.runtime import CapabilityVerifier

            from refund_sentinel.service import Sentinel

            service = Sentinel(runtime, store, client, model, settings)
            item = await service.analyze(
                RequestInput(capture_id=CAPTURE, message="Synthetic refund NZD 5.00")
            )
            principal = runtime.verifier.verify(
                "Bearer " + (tmp_path / "operator.capability").read_text("ascii")
            )
            with pytest.raises(Problem, match="PLAN_CONFIRMATION_MISMATCH"):
                service.confirm_plan(item["id"], "0" * 64)
            with pytest.raises(ActionError):
                runtime.gateway.admit(
                    AdmissionCommand(item["run"]["run_id"], 4, principal.subject_id, str(uuid4())),
                    principal,
                )
            approved = runtime.run_service.decide(
                item["run"]["run_id"], ApprovalDecisionRequest(ApprovalChoice.APPROVE, 4)
            )
            with pytest.raises(Exception) as stale:
                runtime.gateway.admit(
                    AdmissionCommand(approved.run_id, 4, principal.subject_id, str(uuid4())),
                    principal,
                )
            assert stale.value.code.value == "STALE_RUN_VERSION"
            assert runtime.gateway.list_for_run(approved.run_id, principal) == ()
            action = runtime.gateway.admit(
                AdmissionCommand(approved.run_id, 5, principal.subject_id, str(uuid4())), principal
            ).action
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(action.action_id, 1, str(uuid4())), principal
                )
            foreign = CapabilityVerifier(
                "a" * 64,
                subject_id="merchant-operator",
                binding=replace(resources[4].binding, execution_scope=str(uuid4())),
                operations=("read", "authorize", "execute"),
            )
            with pytest.raises(ActionError):
                runtime.gateway.authorize(
                    ActionCommand(action.action_id, 1, str(uuid4())),
                    foreign.verify("Bearer " + "a" * 64),
                )
            action = runtime.gateway.authorize(
                ActionCommand(action.action_id, 1, str(uuid4())), principal
            ).action
            command = ActionCommand(action.action_id, 2, str(uuid4()))
            network.executing = True
            network.context_deadline = asyncio.get_running_loop().time() + 15
            results = await asyncio.gather(
                runtime.gateway.execute(command, principal),
                runtime.gateway.execute(command, principal),
                return_exceptions=True,
            )
            assert (
                sum(
                    not isinstance(r, Exception) and r.action.state.value == "Succeeded"
                    for r in results
                )
                >= 1
            )
            assert network.post_count() == 1
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize("lose_ack", [False, True])
def test_real_process_restart_preserves_terminal_without_second_post(tmp_path, lose_ack):
    async def prepare():
        settings, _ = extended(tmp_path)
        network = MockRefundHTTP(tmp_path / "setup-provider.sqlite3", "completed")
        client = SandboxPayPal(
            settings,
            transport=httpx.MockTransport(network.handle),
            http_timeout=SANDBOX_15_PROFILE.http_timeout(),
        )
        with composition(tmp_path, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            _, command = await prepare_refund(runtime, store, client, model, settings, tmp_path)
            (tmp_path / "worker.json").write_text(
                json.dumps({"lose_ack": lose_ack, "command": asdict(command)}), "utf-8"
            )
        await client.close()

    asyncio.run(prepare())
    worker = Path(__file__).with_name("phase235_worker.py")
    results = []
    for _ in range(2):
        process = subprocess.run(
            [sys.executable, str(worker), str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        assert process.returncode == 0, process.stderr
        results.append(json.loads(process.stdout))
    expected = "Unknown" if lose_ack else "Succeeded"
    assert [r["state"] for r in results] == [expected, expected]
    assert [r["replayed"] for r in results] == [False, True]
    assert all(r["posts"] == r["effects"] == 1 and r["budget"] == 15 for r in results)


def test_old_default_action_denied_in_extended_scope(tmp_path):
    async def run():
        settings = sandbox_settings()
        old = tmp_path / "old"
        provision(old, settings)
        old_network = MockRefundHTTP(old / "mock.sqlite3", "completed")
        old_client = SandboxPayPal(settings, transport=httpx.MockTransport(old_network.handle))
        with composition(old, settings, paypal=old_client, predecessor_stopped=True) as resources:
            old_runtime, store, _, model, _ = resources
            _, old_command = await prepare_refund(
                old_runtime, store, old_client, model, settings, old
            )
            assert old_runtime.gateway.tool_timeout_seconds == 5
        fresh = tmp_path / "new"
        extended(fresh)
        with composition(fresh, settings, paypal=old_client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (fresh / "operator.capability").read_text("ascii")
            )
            with pytest.raises(ActionError):
                await runtime.gateway.execute(old_command, principal)
            assert old_network.post_count() == 0
        with pytest.raises(Problem, match="PERSISTED_EXECUTION_PROFILE_MISMATCH"):
            with composition(old, settings, profile=SANDBOX_15_PROFILE, predecessor_stopped=True):
                pass
        await old_client.close()

    asyncio.run(run())


def test_parameterized_pilot_fence_context_reserve_and_restart(tmp_path):
    async def run():
        from agentic_intent_gate.runtime import AttemptContext
        from test_providers import ORDER, refund_data

        from refund_sentinel.paypal import paypal_http_attempt
        from refund_sentinel.pilot_transport import (
            PilotAuditTransport,
            PilotRequest,
        )

        calls = []

        async def handle(request):
            calls.append(request.method)
            return httpx.Response(201, json=refund_data())

        identity = PilotRequest(str(uuid4()), str(uuid4()), CAPTURE, ORDER, "5.00", "NZD")
        audit = PilotAuditTransport(tmp_path, identity, inner=httpx.MockTransport(handle))
        context = AttemptContext(
            str(uuid4()), asyncio.get_running_loop().time() + 15, asyncio.Event()
        )

        def request():
            return httpx.Request(
                "POST",
                f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}/refund",
                json={"amount": {"value": "5.00", "currency_code": "NZD"}},
                headers={
                    "PayPal-Request-Id": identity.effect_key,
                    "Prefer": "return=representation",
                },
                extensions={"sentinel_pilot_context": context},
            )

        with pytest.raises(Problem, match="PILOT_FINANCIAL_NOT_ENABLED"):
            await audit.handle_async_request(request())
        audit.enabled = True
        audit.phase = "execution"
        with paypal_http_attempt(context, dispatch_reserve_seconds=9):
            await audit.handle_async_request(request())
        with pytest.raises(Problem, match="PILOT_ONE_POST_ALREADY_ATTEMPTED"):
            await audit.handle_async_request(request())
        await audit.aclose()
        restarted = PilotAuditTransport(tmp_path, identity, inner=httpx.MockTransport(handle))
        restarted.enabled = True
        restarted.phase = "execution"
        with pytest.raises(Problem, match="PILOT_ONE_POST_ALREADY_ATTEMPTED"):
            await restarted.handle_async_request(request())
        assert calls == ["POST"]
        await restarted.aclose()

    asyncio.run(run())


def test_pilot_sync_audit_cannot_spend_dispatch_reserve(tmp_path, monkeypatch):
    async def run():
        from agentic_intent_gate.runtime import AttemptContext
        from test_providers import ORDER

        from refund_sentinel import pilot_transport
        from refund_sentinel.paypal import ProviderError, paypal_http_attempt

        calls = []

        async def handle(request):
            calls.append(request.method)
            return httpx.Response(201, json={})

        approved = pilot_transport.PilotRequest(
            str(uuid4()), str(uuid4()), CAPTURE, ORDER, "5.00", "NZD"
        )
        audit = pilot_transport.PilotAuditTransport(
            tmp_path, approved, inner=httpx.MockTransport(handle)
        )
        audit.enabled = True
        audit.phase = "execution"
        context = AttemptContext(
            str(uuid4()), asyncio.get_running_loop().time() + 10.0, asyncio.Event()
        )
        original = pilot_transport.durable_json

        def delayed(path, data, **kwargs):
            original(path, data, **kwargs)
            if path == audit.marker:
                time.sleep(1.2)

        monkeypatch.setattr(pilot_transport, "durable_json", delayed)
        request = httpx.Request(
            "POST",
            f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}/refund",
            json={"amount": {"value": "5.00", "currency_code": "NZD"}},
            headers={"PayPal-Request-Id": approved.effect_key, "Prefer": "return=representation"},
            extensions={"sentinel_pilot_context": context},
        )
        with (
            paypal_http_attempt(context, dispatch_reserve_seconds=9),
            pytest.raises(ProviderError, match="REFUND_BUDGET_RESERVE_INSUFFICIENT"),
        ):
            await audit.handle_async_request(request)
        assert audit.marker.exists() and audit.posts == 0 and calls == []
        await audit.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("change", ["host", "capture", "amount", "request_id", "method"])
def test_pilot_exact_wire_contract_rejects_before_inner_transport(tmp_path, change):
    async def run():
        from agentic_intent_gate.runtime import AttemptContext
        from test_providers import ORDER

        from refund_sentinel.pilot_transport import PilotAuditTransport, PilotRequest

        calls = []
        approved = PilotRequest(str(uuid4()), str(uuid4()), CAPTURE, ORDER, "5.00", "NZD")

        def inner(request):
            calls.append(request)
            return httpx.Response(201, json={})

        audit = PilotAuditTransport(tmp_path, approved, inner=httpx.MockTransport(inner))
        audit.enabled, audit.phase = True, "execution"
        host = "api-m.paypal.com" if change == "host" else "api-m.sandbox.paypal.com"
        capture = "8" * 17 if change == "capture" else CAPTURE
        request = httpx.Request(
            "PATCH" if change == "method" else "POST",
            f"https://{host}/v2/payments/captures/{capture}/refund",
            json={
                "amount": {
                    "value": "6.00" if change == "amount" else "5.00",
                    "currency_code": "NZD",
                }
            },
            headers={
                "PayPal-Request-Id": str(uuid4())
                if change == "request_id"
                else approved.effect_key,
                "Prefer": "return=representation",
            },
            extensions={
                "sentinel_pilot_context": AttemptContext(
                    str(uuid4()), asyncio.get_running_loop().time() + 15, asyncio.Event()
                )
            },
        )
        with pytest.raises(Problem):
            await audit.handle_async_request(request)
        assert audit.posts == 0 and calls == [] and not audit.marker.exists()
        await audit.aclose()

    asyncio.run(run())


def test_pilot_context_survives_httpx_hooks_and_refund_get_is_observed(tmp_path):
    async def run():
        from agentic_intent_gate.runtime import AttemptContext
        from test_providers import ORDER, REFUND, refund_data

        from refund_sentinel.paypal import paypal_http_attempt
        from refund_sentinel.pilot_transport import (
            PilotAuditTransport,
            PilotRequest,
            retain_attempt_context,
        )

        approved = PilotRequest(str(uuid4()), str(uuid4()), CAPTURE, ORDER, "5.00", "NZD")
        calls = []

        def inner(request):
            calls.append(request.url.path)
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            data = refund_data()
            data["amount"] = {"value": "5.00", "currency_code": "NZD"}
            return httpx.Response(201 if request.method == "POST" else 200, json=data)

        audit = PilotAuditTransport(tmp_path, approved, inner=httpx.MockTransport(inner))
        client = SandboxPayPal(
            sandbox_settings(), transport=audit, http_timeout=SANDBOX_15_PROFILE.http_timeout()
        )
        client.http.event_hooks["request"].append(retain_attempt_context)
        client.http.event_hooks["response"].append(audit.observe_response)
        assert client.source == "MOCK"
        audit.enabled, audit.phase = True, "execution"
        context = AttemptContext(
            str(uuid4()), asyncio.get_running_loop().time() + 15, asyncio.Event()
        )
        with paypal_http_attempt(context, dispatch_reserve_seconds=9):
            assert (
                await client.refund(CAPTURE, "5.00", "NZD", approved.effect_key, context=context)
            )["id"] == REFUND
            assert (await client.lookup_refund(REFUND))["status"] == "COMPLETED"
            with pytest.raises(Problem, match="PILOT_ONE_POST_ALREADY_ATTEMPTED"):
                await client.refund(CAPTURE, "5.00", "NZD", approved.effect_key, context=context)
        assert audit.posts == 1 and len(calls) == 3
        assert [r["operation"] for r in audit.events] == ["oauth", "refund_post", "refund_get"]
        await client.close()

    asyncio.run(run())
