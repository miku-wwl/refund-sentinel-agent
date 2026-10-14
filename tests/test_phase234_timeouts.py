"""HTTP phase-delay simulations, not measurements of genuine PayPal refund latency."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import ActionCommand, ActionError, AttemptContext
from test_phase23_preflight import MockRefundHTTP
from test_phase231_deadlines import prepare_refund
from test_providers import sandbox_settings

from refund_sentinel import integration
from refund_sentinel.integration import RefundExecutor, composition, provision
from refund_sentinel.paypal import EXECUTION_HTTP_TIMEOUT, SandboxPayPal

CASES = {
    "warm_09_11": (0.9, 1.1, 0.2, 0.2, False, "Succeeded", 1),
    "warm_13_18": (1.3, 1.8, 0.35, 0.35, False, "Succeeded", 1),
    "read_exceeds_2": (0.9, 2.2, 0.1, 0.1, False, "Failed", 0),
    "cold_slow": (1.3, 1.8, 0.4, 0.4, True, "Succeeded", 1),
    "cancel_before_dispatch": (0.02, 0.02, 0.1, 0.1, False, "Unknown", 0),
    "expire_before_post": (0.02, 0.02, 0.1, 0.1, False, "Unknown", 0),
    "lost_ack": (0.02, 0.02, 0.1, 0.1, False, "Unknown", 1),
    "refund_get_remaining": (1.2, 1.7, 1.6, 1.95, True, "Unknown", 1),
}


@pytest.mark.parametrize("case", CASES)
def test_full_gateway_timeout_and_failure_safety(tmp_path, monkeypatch, case):
    async def run():
        capture, order, post, get, cold, expected, count = CASES[case]
        settings = sandbox_settings()
        directory = tmp_path / "runtime"
        provision(directory, settings)
        delays = {
            "oauth": 0.65,
            "capture_get": capture,
            "order_get": order,
            "refund_post": post,
            "refund_get": get,
        }
        network = MockRefundHTTP(tmp_path / "provider.sqlite3", "completed")
        measurements, adapter = [], {}
        original_handle = network.handle
        context = None
        original_observe = integration.Store.observe

        def observe(store, *args, **kwargs):
            if kwargs["phase"] == "REFUND_DISPATCH":
                if case == "cancel_before_dispatch":
                    context.cancelled.set()
                elif case == "expire_before_post":
                    # Deliberately cross the real immutable five-second deadline in a sync commit.
                    time.sleep(max(0, context.deadline - asyncio.get_running_loop().time()) + 0.02)
            return original_observe(store, *args, **kwargs)

        monkeypatch.setattr(integration.Store, "observe", observe)

        class TimedExecutor(RefundExecutor):
            async def execute(self, spec, effect_key, attempt):
                nonlocal context
                context = attempt
                network.context_deadline = attempt.deadline
                adapter["remaining_at_entry"] = attempt.deadline - asyncio.get_running_loop().time()
                start = time.perf_counter()
                try:
                    return await super().execute(spec, effect_key, attempt)
                finally:
                    adapter["seconds"] = time.perf_counter() - start

        monkeypatch.setattr(integration, "RefundExecutor", TimedExecutor)

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
            limits = dict(request.extensions["timeout"])
            measurements.append({"operation": operation, "phase_limits": limits})
            assert 0 < limits["read"] <= 2.0
            assert all(0 < limits[p] <= 1.1 for p in ("connect", "write", "pool"))
            delay = delays[operation]
            if operation == "refund_post":
                # Commit the synthetic remote effect before the delayed/lost acknowledgment.
                response = await original_handle(request)
                if case == "lost_ack":
                    raise httpx.ReadTimeout("Synthetic acknowledgment lost", request=request)
            else:
                response = None
            try:
                await asyncio.wait_for(asyncio.sleep(delay), timeout=limits["read"])
            except TimeoutError:
                raise httpx.ReadTimeout(
                    "Synthetic HTTPX read phase expiry", request=request
                ) from None
            return response if response is not None else await original_handle(request)

        client = SandboxPayPal(settings, transport=httpx.MockTransport(handler))
        assert client.http.timeout.as_dict() == EXECUTION_HTTP_TIMEOUT.as_dict()
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            principal, command = await prepare_refund(
                runtime, store, client, model, settings, directory
            )
            if cold:
                client._until = 0
            network.executing = True
            network.started = time.perf_counter()
            local_timings, frame_starts = [], {}

            def profile(frame, event, arg):
                if not (
                    frame.f_code.co_filename.endswith("sqlite_action_execution.py")
                    and frame.f_code.co_name in {"claim", "finish"}
                ):
                    return
                if event == "call":
                    frame_starts[id(frame)] = time.perf_counter()
                elif event == "return":
                    local_timings.append(
                        {
                            "operation": frame.f_code.co_name,
                            "seconds": time.perf_counter() - frame_starts.pop(id(frame)),
                        }
                    )

            previous_profile = sys.getprofile()
            try:
                sys.setprofile(profile)  # Observation only; never modify the pinned Runtime.
                result = await runtime.gateway.execute(command, principal)
            finally:
                sys.setprofile(previous_profile)
            wall = time.perf_counter() - network.started
            assert runtime.gateway.tool_timeout_seconds == 5
            assert result.action.state.value == expected
            assert network.post_count() == count and len(network.effects()) == count
            assert not network.dispatch_after_deadline
            observations = store.observations(result.action.effect_key)
            if expected == "Succeeded":
                assert any(r["data"]["phase"] == "VERIFIED_REFUND" for r in observations)
            if case == "refund_get_remaining":
                lookup = next(r for r in measurements if r["operation"] == "refund_get")
                assert lookup["phase_limits"]["read"] < 1.95
            snapshot = result.action.snapshot()
            # Local command replay is tested in synthetic state only; never retry the real pilot.
            assert (await runtime.gateway.execute(command, principal)).replayed
            with pytest.raises(ActionError):
                await runtime.gateway.execute(
                    ActionCommand(command.action_id, result.action.version, str(uuid4())), principal
                )
            if expected == "Failed":
                assert result.action.version == 4
                with pytest.raises(ActionError):
                    runtime.gateway.authorize(
                        ActionCommand(command.action_id, 4, str(uuid4())), principal
                    )
            assert runtime.gateway.get(command.action_id, principal).snapshot() == snapshot
            scope = principal.execution_scope
        # Reopen only synthetic state. No new financial call is permitted by terminal receipts.
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (directory / "operator.capability").read_text("ascii")
            )
            assert principal.execution_scope == scope
            assert (await runtime.gateway.execute(command, principal)).replayed
            assert network.post_count() == count
        await client.close()
        evidence = {
            "source": "ISOLATED_MOCK_HTTP_PHASE_SIMULATION",
            "case": case,
            "delay_assumptions": delays,
            "phase_limits": measurements,
            "state": expected,
            "refund_posts": count,
            "gateway_seconds": round(wall, 6),
            "adapter_seconds": round(adapter["seconds"], 6),
            "claim_finish_and_gateway_seconds": round(wall - adapter["seconds"], 6),
            "local_claim_finish_timings": local_timings,
            "runtime_deadline_seconds": 5,
            "no_duplicate_or_late_dispatch": True,
            "real_refund_latency_measured": False,
        }
        destination = Path(os.getenv("SENTINEL_QA_OUTPUT_DIR", ".state-qa")) / "phase-2.3.4/mock"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f"{case}.json").write_text(json.dumps(evidence, indent=2) + "\n", "utf-8")

    asyncio.run(run())


def test_request_context_isolation_and_remaining_budget():
    from refund_sentinel.paypal import paypal_http_attempt

    async def run():
        requests = []

        async def handler(request):
            requests.append(dict(request.extensions["timeout"]))
            return httpx.Response(200, json={})

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        loop = asyncio.get_running_loop()
        context = AttemptContext(str(uuid4()), loop.time() + 0.3, asyncio.Event())
        with paypal_http_attempt(context):
            await client._roundtrip("GET", "/v2/payments/captures/74L756601X447022Y")
        await client._roundtrip("GET", "/v2/payments/captures/74L756601X447022Y")
        assert all(0 < value <= 0.3 for value in requests[0].values())
        assert requests[1] == EXECUTION_HTTP_TIMEOUT.as_dict()
        await client.close()

    asyncio.run(run())
