"""Architecture modeling only: no Gateway, Run, Plan, Action or genuine HTTP calls."""

import asyncio
import json
import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import (
    EXTERNAL_PAYLOAD_REVISION,
    AttemptContext,
    ExecutionSpec,
    Outcome,
    ToolBinding,
)
from test_phase23_preflight import MockRefundHTTP
from test_providers import CAPTURE, ORDER, sandbox_settings

from refund_sentinel.integration import RefundExecutor
from refund_sentinel.models import Recommendation
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.store import Store

PROFILES = {
    # budget, cold OAuth, OAuth delay, parallel read max, POST ACK, Refund GET, category, posts
    "warm_tail_5": (5, False, 0.9, 2.8, 2.2, 1.8, Outcome.UNKNOWN_OUTCOME, 1),
    "warm_tail_12": (12, False, 0.9, 2.8, 2.2, 1.8, Outcome.SUCCESS, 1),
    "warm_tail_15": (15, False, 0.9, 2.8, 2.2, 1.8, Outcome.SUCCESS, 1),
    "cold_slow_12": (12, True, 0.9, 3.2, 3.0, 2.4, Outcome.SUCCESS, 1),
    "cold_slow_15": (15, True, 0.9, 3.2, 3.0, 2.4, Outcome.SUCCESS, 1),
    "cold_tail_12": (12, True, 3.2, 3.5, 3.2, 3.2, Outcome.UNKNOWN_OUTCOME, 1),
    "cold_tail_15": (15, True, 3.2, 3.5, 3.2, 3.2, Outcome.SUCCESS, 1),
    "read_exceeds_phase": (15, False, 0.9, 4.2, 0.2, 0.2, Outcome.CONFIRMED_FAILURE, 0),
    "lost_post_ack": (12, False, 0.9, 2.3, 0.1, 0.2, Outcome.UNKNOWN_OUTCOME, 1),
    "cancel_before_dispatch": (15, False, 0.9, 1.8, 0.2, 0.2, Outcome.UNKNOWN_OUTCOME, 0),
    "expiry_after_persistence": (5, False, 0.9, 1.8, 0.2, 0.2, Outcome.UNKNOWN_OUTCOME, 0),
}


@pytest.mark.parametrize("name", PROFILES)
def test_model_full_consumer_path_without_gateway(tmp_path, name):
    async def run():
        budget, cold, oauth, reads, ack, lookup, expected, posts = PROFILES[name]
        settings = sandbox_settings()
        store = Store(tmp_path / "product.sqlite3")
        store.provision()  # Product facts only: no Runtime database or control-plane objects.
        network = MockRefundHTTP(tmp_path / "mock-provider.sqlite3", "completed")
        original_handle = network.handle
        phase_limits, persistence = [], []
        context = None

        def observe(*args, **kwargs):
            phase = kwargs["phase"]
            if phase == "REFUND_DISPATCH":
                if name == "cancel_before_dispatch":
                    context.cancelled.set()
                elif name == "expiry_after_persistence":
                    time.sleep(max(0, context.deadline - asyncio.get_running_loop().time()) + 0.02)
            start = time.perf_counter()
            try:
                return original_observe(*args, **kwargs)
            finally:
                persistence.append({"phase": phase, "seconds": time.perf_counter() - start})

        original_observe = store.observe
        store.observe = observe

        async def handler(request):
            if not network.executing:
                return await original_handle(request)
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
            delay = {
                "oauth": oauth,
                "capture_get": 1.3,
                "order_get": reads,
                "refund_post": ack,
                "refund_get": lookup,
            }[operation]
            limits = request.extensions["timeout"]
            phase_limits.append({"operation": operation, "limits": dict(limits)})
            response = await original_handle(request) if operation == "refund_post" else None
            if operation == "refund_post" and name == "lost_post_ack":
                raise httpx.ReadTimeout("SYNTHETIC_PRIVATE_MESSAGE", request=request)
            try:
                await asyncio.wait_for(asyncio.sleep(delay), timeout=limits["read"])
            except TimeoutError:
                raise httpx.ReadTimeout("SYNTHETIC_PRIVATE_MESSAGE", request=request) from None
            return response if response is not None else await original_handle(request)

        # A proposed four-second phase profile is MODEL ONLY, not enabled in production.
        client = SandboxPayPal(
            settings,
            transport=httpx.MockTransport(handler),
            http_timeout=httpx.Timeout(connect=1.1, read=4.0, write=1.1, pool=1.1),
        )
        facts = await client.capture(CAPTURE)
        incident = store.reserve(CAPTURE, "Synthetic NZD 5.00 request", {"payment": "mock"})
        args = {"incident_id": incident, "capture_id": CAPTURE, "amount": "5.00", "currency": "NZD"}
        recommendation = Recommendation(
            recommendation="REFUND",
            requested_amount="5.00",
            currency="NZD",
            explanation="Synthetic proposal for latency modeling only",
            reason_code="OTHER",
            uncertainty="LOW",
        )
        store.update(
            incident,
            capture=facts.model_dump(),
            recommendation=recommendation.model_dump(),
            refund_arguments=args,
        )
        binding = ToolBinding(
            "paypal_partial_refund",
            "1",
            "paypal-sandbox-adapter",
            "refund-binding-v1",
            "paypal-sandbox-refunds",
            str(uuid4()),
        )
        spec = ExecutionSpec(
            binding.tool_name,
            binding.tool_version,
            binding.target,
            args,
            binding.adapter_id,
            binding.binding_revision,
            binding.execution_scope,
            EXTERNAL_PAYLOAD_REVISION,
        )
        executor = RefundExecutor(store, binding, settings, client)
        if cold:
            client._until = 0
        network.executing = True
        start = time.perf_counter()
        network.started = start
        context = AttemptContext(
            str(uuid4()), asyncio.get_running_loop().time() + budget, asyncio.Event()
        )
        network.context_deadline = context.deadline
        telemetry_start = len(client.telemetry)
        try:
            # Mirrors timer shape only. Never instantiate, mutate or execute a Runtime Gateway.
            async with asyncio.timeout_at(context.deadline):
                outcome = await executor.execute(spec, str(uuid4()), context)
            category = outcome.category
        except TimeoutError:
            category = Outcome.UNKNOWN_OUTCOME
        finally:
            context.cancelled.set()
        wall = time.perf_counter() - start
        assert category == expected and network.post_count() == posts
        assert len(network.effects()) == posts and not network.dispatch_after_deadline
        assert not list(tmp_path.glob("gate.sqlite3*"))
        telemetry = client.telemetry[telemetry_start:]
        assert "SYNTHETIC_PRIVATE_MESSAGE" not in json.dumps(telemetry)
        if name in {"read_exceeds_phase", "lost_post_ack"}:
            assert any(row.get("exception_type") == "ReadTimeout" for row in telemetry)
        if name == "cold_tail_12":
            assert any(row["operation"] == "refund_get" for row in telemetry)
        evidence = {
            "source": "OFFLINE_EXECUTOR_MODEL_NOT_RUNTIME_QUALIFICATION",
            "profile": name,
            "modeled_seconds": budget,
            "executor_wall_seconds": round(wall, 6),
            "executor_category": category.name,
            "mock_posts": posts,
            "delay_assumptions": {
                "oauth": oauth,
                "capture": 1.3,
                "order": reads,
                "post_ack": ack,
                "refund_get": lookup,
            },
            "requests": telemetry,
            "phase_limits": phase_limits,
            "persistence": persistence,
            "gateway_executions": 0,
            "new_run_plan_action": False,
            "no_duplicate_or_late_dispatch": True,
            "actual_refund_latency_measured": False,
        }
        destination = (
            Path(os.getenv("SENTINEL_QA_OUTPUT_DIR", ".state-qa")) / "execution-budget-review/mock"
        )
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f"{name}.json").write_text(json.dumps(evidence, indent=2) + "\n", "utf-8")
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "error_class", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout]
)
def test_underlying_timeout_diagnostics_are_allowlisted(error_class):
    async def run():
        async def handler(request):
            raise error_class("SYNTHETIC_SECRET_AND_URL", request=request)

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(error_class):
            await client._roundtrip("GET", "/v2/payments/captures/74L756601X447022Y")
        assert client.telemetry[0]["exception_type"] == error_class.__name__
        assert "SYNTHETIC_SECRET_AND_URL" not in json.dumps(client.telemetry)
        await client.close()

    asyncio.run(run())


def test_existing_pilot_transport_rejects_duplicate_and_restart(tmp_path):
    # The distributable production fence keeps this check active in a fresh clone.
    from refund_sentinel.pilot_transport import PilotAuditTransport, PilotRequest

    async def run():
        calls = []

        async def handler(request):
            calls.append(request.method)
            return httpx.Response(201, json={"status": "COMPLETED"})

        context = AttemptContext(
            str(uuid4()), asyncio.get_running_loop().time() + 5, asyncio.Event()
        )
        identity = PilotRequest(str(uuid4()), str(uuid4()), CAPTURE, ORDER, "5.00", "NZD")

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

        first = PilotAuditTransport(tmp_path, identity, inner=httpx.MockTransport(handler))
        first.enabled, first.phase = True, "execution"
        await first.handle_async_request(request())
        with pytest.raises(Exception, match="PILOT_ONE_POST_ALREADY_ATTEMPTED"):
            await first.handle_async_request(request())
        await first.aclose()
        restarted = PilotAuditTransport(tmp_path, identity, inner=httpx.MockTransport(handler))
        restarted.enabled, restarted.phase = True, "execution"
        with pytest.raises(Exception, match="PILOT_ONE_POST_ALREADY_ATTEMPTED"):
            await restarted.handle_async_request(request())
        assert calls == ["POST"]
        await restarted.aclose()

    asyncio.run(run())
