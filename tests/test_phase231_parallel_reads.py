"""Parallel reads use a trusted identity hint, retain all verification, and join cancellation."""

import asyncio
from uuid import uuid4

import httpx
import pytest
from test_phase23_preflight import MockRefundHTTP, synthetic_capture_order
from test_phase231_deadlines import prepare_refund
from test_preflight import token_response
from test_providers import CAPTURE, ORDER, REFUND, sandbox_settings

from refund_sentinel.integration import composition, provision
from refund_sentinel.paypal import ProviderError, SandboxPayPal


def test_parallel_reads_overlap_and_share_one_oauth():
    async def run():
        seen = set()
        both_started = asyncio.Event()
        oauth = 0
        capture, order = synthetic_capture_order()

        async def handle(request):
            nonlocal oauth
            if request.url.path == "/v1/oauth2/token":
                oauth += 1
                return httpx.Response(200, json=token_response())
            assert request.method == "GET" and request.url.host == "api-m.sandbox.paypal.com"
            seen.add(request.url.path)
            if len(seen) == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), 1)
            return httpx.Response(200, json=order if "/orders/" in request.url.path else capture)

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handle))
        facts = await client.capture(CAPTURE, expected_order_id=ORDER)
        assert facts.amount == "20.00" and facts.currency == "NZD"
        assert seen == {f"/v2/payments/captures/{CAPTURE}", f"/v2/checkout/orders/{ORDER}"}
        assert oauth == 1
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize("stop", ["provider_error", "caller_cancel"])
def test_parallel_read_children_are_joined_on_failure_or_cancellation(stop):
    async def run():
        started = asyncio.Event()
        finished = asyncio.Event()
        active = set()

        async def handle(request):
            path = request.url.path
            if path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            active.add(path)
            try:
                if "/orders/" in path:
                    started.set()
                    await asyncio.sleep(10)
                else:
                    await started.wait()
                    if stop == "provider_error":
                        return httpx.Response(503, json={})
                    await asyncio.sleep(10)
            finally:
                active.remove(path)
                if "/orders/" in path:
                    finished.set()

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handle))
        task = asyncio.create_task(client.capture(CAPTURE, expected_order_id=ORDER))
        await started.wait()
        if stop == "caller_cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(ProviderError, match="CAPTURE_READ_UNCERTAIN"):
                await task
        assert finished.is_set() and not active
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "change",
    ["related_order", "order_id", "merchant", "amount", "currency", "status", "refund"],
)
def test_parallel_execution_still_rejects_changed_payment_facts(tmp_path, change):
    async def run():
        settings = sandbox_settings()
        directory = tmp_path / "runtime"
        provision(directory, settings)
        network = MockRefundHTTP(tmp_path / "mock.sqlite3", "completed")
        client = SandboxPayPal(settings, transport=httpx.MockTransport(network.handle))
        with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            principal, command = await prepare_refund(
                runtime, store, client, model, settings, directory
            )
            if change == "related_order":
                network.capture["supplementary_data"]["related_ids"]["order_id"] = REFUND
            elif change == "order_id":
                network.order["id"] = REFUND
            elif change == "merchant":
                network.order["purchase_units"][0]["payee"]["merchant_id"] = "ZZZZ75W2GKDQE"
            elif change == "amount":
                network.capture["amount"]["value"] = "19.00"
            elif change == "currency":
                network.capture["amount"]["currency_code"] = "USD"
            elif change == "status":
                network.capture["status"] = "PENDING"
            else:
                network.order["purchase_units"][0]["payments"]["refunds"] = [
                    {
                        "id": REFUND,
                        "status": "COMPLETED",
                        "amount": {"value": "1.00", "currency_code": "NZD"},
                    }
                ]
            result = await runtime.gateway.execute(command, principal)
            assert result.action.state.value == "Failed"
            assert network.post_count() == len(network.effects()) == 0
        await client.close()

    asyncio.run(run())


def test_low_level_refund_cancellation_is_checked_without_an_attempt_context():
    async def run():
        posts = 0

        async def handle(request):
            nonlocal posts
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            posts += 1
            raise AssertionError("Cancelled refund must never reach the transport")

        async def cancel_on_prepare(request):
            if request.url.path.endswith("/refund"):
                asyncio.current_task().cancel()

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handle))
        client.http.event_hooks["request"] = [cancel_on_prepare]
        task = asyncio.create_task(client.refund(CAPTURE, "5.00", "NZD", str(uuid4())))
        with pytest.raises(asyncio.CancelledError):
            await task
        assert posts == 0
        await client.close()

    asyncio.run(run())
