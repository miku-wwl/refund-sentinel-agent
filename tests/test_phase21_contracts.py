import asyncio
import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from agentic_intent_gate.runtime import (
    ActionCommand,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
)
from test_preflight import token_response
from test_providers import (
    CAPTURE,
    ORDER,
    REFUND,
    capture_data,
    order_data,
    refund_data,
    sandbox_settings,
)

from refund_sentinel.config import Settings
from refund_sentinel.integration import composition, provision
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import FakePayPal, ProviderError, SandboxPayPal, verified_refund
from refund_sentinel.preflight import capture_report
from refund_sentinel.service import Sentinel


async def authorized_action(runtime, sentinel, settings):
    principal = runtime.verifier.verify(
        "Bearer " + (sentinel.store.path.parent / "operator.capability").read_text("ascii")
    )
    result = await sentinel.analyze(
        RequestInput(
            capture_id=settings.capture_ids[0], message="Synthetic damaged item. Refund USD 25.00."
        )
    )
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


@pytest.mark.parametrize(
    "post_status,lookup_status,expected",
    [
        (200, "COMPLETED", "Succeeded"),
        (201, "COMPLETED", "Succeeded"),
        (200, "PENDING", "Unknown"),
        (201, "PENDING", "Unknown"),
        (201, "FAILED", "Unknown"),
        (201, "MISSING_AMOUNT", "Unknown"),
        (201, "LOST_ID", "Unknown"),
    ],
)
def test_mock_refund_minimal_ack_requires_verified_lookup(
    tmp_path, post_status, lookup_status, expected
):
    async def scenario():
        settings = sandbox_settings()
        provision(tmp_path, settings)
        effects_path = tmp_path / "mock-provider.sqlite3"
        with sqlite3.connect(effects_path) as db:
            db.execute("CREATE TABLE effects(request_id TEXT PRIMARY KEY, payload TEXT)")
        calls = []

        def handler(request):
            calls.append((request.method, request.url.path))
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            if request.url.path == f"/v2/payments/captures/{CAPTURE}":
                return httpx.Response(200, json=capture_data())
            if request.url.path == f"/v2/checkout/orders/{ORDER}":
                return httpx.Response(200, json=order_data())
            if request.url.path.endswith("/refund"):
                key = request.headers["PayPal-Request-Id"]
                assert str(__import__("uuid").UUID(key)) == key
                assert request.headers["Authorization"] == "Bearer fixture-access-token"
                assert request.headers["Prefer"] == "return=representation"
                assert json.loads(request.content) == {
                    "amount": {"value": "25.00", "currency_code": "USD"}
                }
                with sqlite3.connect(effects_path) as db:
                    db.execute("INSERT INTO effects VALUES (?,?)", (key, request.content.decode()))
                return httpx.Response(
                    post_status,
                    json=(
                        {"status": "COMPLETED"}
                        if lookup_status == "LOST_ID"
                        else {"id": REFUND, "status": "PENDING"}
                    ),
                )
            assert request.url.path == f"/v2/payments/refunds/{REFUND}"
            data = refund_data("COMPLETED" if lookup_status == "MISSING_AMOUNT" else lookup_status)
            if lookup_status == "MISSING_AMOUNT":
                data.pop("amount")
            return httpx.Response(200, json=data)

        client = SandboxPayPal(settings, transport=httpx.MockTransport(handler))
        assert client.source == "MOCK"
        with composition(tmp_path, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, analyst, _ = resources
            sentinel = Sentinel(runtime, store, client, analyst, settings)
            principal, command = await authorized_action(runtime, sentinel, settings)
            result = await runtime.gateway.execute(command, principal)
            assert result.action.state.value == expected
            assert runtime.actions.get(result.action.action_id).state.value == expected
            assert sum(path.endswith("/refund") for _, path in calls) == 1
            assert (await runtime.gateway.execute(command, principal)).replayed
            assert sum(path.endswith("/refund") for _, path in calls) == 1
            with sqlite3.connect(effects_path) as db:
                assert db.execute("SELECT count(*) FROM effects").fetchone()[0] == 1
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("shape", ["missing_capture_payee", "equivalent_money", "valid_links"])
def test_documented_capture_variations_preserve_identity(shape):
    async def scenario():
        capture, order = capture_data(), order_data()
        if shape == "missing_capture_payee":
            capture.pop("payee")  # Associated order still supplies the exact trusted merchant.
        elif shape == "equivalent_money":
            capture["amount"]["value"] = "100"
            order["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"] = "100.0"
        else:
            capture["links"] = [
                {
                    "rel": "self",
                    "method": "GET",
                    "href": f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
                }
            ]
            order["links"] = [
                {
                    "rel": "self",
                    "method": "GET",
                    "href": f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{ORDER}",
                }
            ]

        def handler(request):
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            return httpx.Response(200, json=order if "orders" in request.url.path else capture)

        settings = sandbox_settings()
        client = SandboxPayPal(settings, read_only=True, transport=httpx.MockTransport(handler))
        report = await capture_report(settings, CAPTURE, client=client)
        assert report["status"] == "PASS"
        assert report["validation"]["merchant_matches_configuration"]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "shape",
    [
        "float_money",
        "excess_precision",
        "links_not_list",
        "foreign_self_link",
        "foreign_refund_link",
        "refunds_not_list",
        "malformed_refund",
        "pending_refund",
        "no_purchase_units",
        "foreign_order_capture",
    ],
)
def test_unexpected_capture_evidence_fails_closed(shape):
    async def scenario():
        capture, order = capture_data(), order_data()
        if shape == "float_money":
            capture["amount"]["value"] = 100.0
        elif shape == "excess_precision":
            capture["amount"]["value"] = "100.001"
        elif shape == "links_not_list":
            capture["links"] = {}
        elif shape in {"foreign_self_link", "foreign_refund_link"}:
            capture["links"] = [
                {
                    "rel": "self" if shape == "foreign_self_link" else "refund",
                    "method": "GET" if shape == "foreign_self_link" else "POST",
                    "href": f"https://api-m.paypal.com/v2/payments/captures/{CAPTURE}",
                }
            ]
        elif shape == "refunds_not_list":
            order["purchase_units"][0]["payments"]["refunds"] = {}
        elif shape == "malformed_refund":
            order["purchase_units"][0]["payments"]["refunds"] = [{}]
        elif shape == "pending_refund":
            order["purchase_units"][0]["payments"]["refunds"] = [refund_data("PENDING")]
        elif shape == "no_purchase_units":
            order.pop("purchase_units")
        else:
            order["purchase_units"][0]["payments"]["captures"][0]["id"] = ORDER
        calls = []

        def handler(request):
            calls.append((request.method, request.url.path))
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            return httpx.Response(200, json=order if "orders" in request.url.path else capture)

        settings = sandbox_settings()
        report = await capture_report(
            settings,
            CAPTURE,
            client=SandboxPayPal(settings, read_only=True, transport=httpx.MockTransport(handler)),
        )
        assert report["status"] == "FAIL"
        assert all(method == "GET" or path == "/v1/oauth2/token" for method, path in calls)

    asyncio.run(scenario())


@pytest.mark.parametrize("value", ["25", "25.0", "25.00"])
def test_refund_provider_string_money_is_exact_decimal(value):
    from refund_sentinel.models import RefundInput

    data = refund_data()
    data["amount"]["value"] = value
    args = RefundInput(incident_id=str(uuid4()), capture_id=CAPTURE, amount="25.00", currency="USD")
    assert verified_refund(data, args, expected_id=REFUND)["amount"] == "25.00"


def test_duplicate_provider_error_is_not_no_effect_proof():
    async def scenario():
        def handler(request):
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            return httpx.Response(
                422, json={"name": "DUPLICATE_REQUEST_ID", "message": "PRIVATE_PROVIDER_DETAILS"}
            )

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError) as error:
            await client.refund(CAPTURE, "25.00", "USD", str(uuid4()))
        assert not error.value.no_effect and "PRIVATE_" not in str(error.value)
        await client.close()

    asyncio.run(scenario())


def test_later_gateway_deadline_cannot_extend_five_seconds(tmp_path):
    async def scenario():
        class SlowAcknowledgement(FakePayPal):
            async def refund(self, *args, **kwargs):
                response = await super().refund(*args, **kwargs)
                await asyncio.sleep(15)
                return response

        settings = Settings()
        provision(tmp_path, settings)
        fake = SlowAcknowledgement(tmp_path / "fake-paypal.sqlite3")
        with composition(tmp_path, settings, paypal=fake, predecessor_stopped=True) as resources:
            runtime, store, _, model, _ = resources
            principal, command = await authorized_action(
                runtime, Sentinel(runtime, store, fake, model, settings), settings
            )
            start = time.perf_counter()
            result = await runtime.gateway.execute(
                command, principal, deadline=asyncio.get_running_loop().time() + 30
            )
            elapsed = time.perf_counter() - start
            assert runtime.gateway.tool_timeout_seconds == 5
            assert 4.8 <= elapsed < 10 and result.action.state.value == "Unknown"
            assert len(fake.persisted_refunds()) == len(fake.recorded_calls()) == 1
            assert (await runtime.gateway.execute(command, principal)).replayed
            Path("evidence/phase-2.1").mkdir(exist_ok=True)
            Path("evidence/phase-2.1/deadline-mock.json").write_text(
                json.dumps(
                    {
                        "source": "ISOLATED_FAKE_PROVIDER",
                        "requested_gateway_deadline_seconds": 30,
                        "actual_runtime_limit_seconds": 5,
                        "elapsed_seconds": round(elapsed, 6),
                        "durable_action_state": result.action.state.value,
                        "committed_fake_refunds": len(fake.persisted_refunds()),
                        "provider_attempts_after_replay": len(fake.recorded_calls()),
                    },
                    indent=2,
                )
            )

    asyncio.run(scenario())
