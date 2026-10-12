import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from conftest import analyze, ready, step, synthetic_recommendation
from pydantic import SecretStr, ValidationError

from refund_sentinel.config import SANDBOX_URL, Settings
from refund_sentinel.integration import composition
from refund_sentinel.llm import ChatCompletionsAnalyst
from refund_sentinel.models import (
    CaptureFacts,
    Problem,
    Recommendation,
    RefundInput,
    validate_policy,
)
from refund_sentinel.paypal import ProviderError, SandboxPayPal, verified_refund

CAPTURE = "74L756601X447022Y"
ORDER = "25M43554V9523650M"
REFUND = "1JU08902781691411"


def sandbox_settings(**overrides):
    return Settings(
        payment_mode="sandbox",
        merchant_id="YXZY75W2GKDQE",
        capture_ids=(CAPTURE,),
        client_id=SecretStr("synthetic-client"),
        client_secret=SecretStr("synthetic-secret"),
        **overrides,
    )


def capture_data():
    return {
        "id": CAPTURE,
        "status": "COMPLETED",
        "amount": {"value": "100.00", "currency_code": "USD"},
        "payee": {"merchant_id": "YXZY75W2GKDQE"},
        "supplementary_data": {"related_ids": {"order_id": ORDER}},
    }


def order_data():
    return {
        "id": ORDER,
        "status": "COMPLETED",
        "purchase_units": [
            {"payee": {"merchant_id": "YXZY75W2GKDQE"}, "payments": {"captures": [capture_data()]}}
        ],
    }


def refund_data(status="COMPLETED"):
    return {
        "id": REFUND,
        "status": status,
        "amount": {"value": "25.00", "currency_code": "USD"},
        "links": [
            {"rel": "up", "method": "GET", "href": f"{SANDBOX_URL}/v2/payments/captures/{CAPTURE}"}
        ],
    }


def test_real_client_wire_contract_mock_transport():
    async def scenario():
        calls = []
        request_id = str(uuid4())

        def handler(request):
            assert request.url.host == "api-m.sandbox.paypal.com"
            calls.append(request)
            if request.url.path == "/v1/oauth2/token":
                assert request.headers["Authorization"].startswith("Basic ")
                assert request.content == b"grant_type=client_credentials"
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            assert request.headers["Authorization"] == "Bearer synthetic-token"
            if request.url.path == f"/v2/payments/captures/{CAPTURE}":
                return httpx.Response(200, json=capture_data())
            if request.url.path == f"/v2/checkout/orders/{ORDER}":
                return httpx.Response(200, json=order_data())
            if request.url.path.endswith("/refund"):
                assert request.method == "POST"
                assert request.headers["PayPal-Request-Id"] == request_id
                assert request.headers["Prefer"] == "return=representation"
                assert json.loads(request.content) == {
                    "amount": {"value": "25.00", "currency_code": "USD"}
                }
                return httpx.Response(201, json=refund_data())
            assert request.url.path == f"/v2/payments/refunds/{REFUND}"
            return httpx.Response(200, json=refund_data())

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        facts = await client.capture(CAPTURE)
        assert facts.source == "paypal-sandbox" and facts.merchant_id == "YXZY75W2GKDQE"
        assert (await client.refund(CAPTURE, "25.00", "USD", request_id))["id"] == REFUND
        assert (await client.lookup_refund(REFUND))["status"] == "COMPLETED"
        assert len(calls) == 5 and sum(c.url.path == "/v1/oauth2/token" for c in calls) == 1
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "status,definitive",
    [
        (400, True),
        (401, True),
        (403, True),
        (404, True),
        (422, True),
        (409, False),
        (429, False),
        (500, False),
        (503, False),
        (302, False),
    ],
)
def test_provider_errors_redacted_and_classified(status, definitive):
    async def scenario():
        calls = []

        def handler(request):
            calls.append(request)
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            return httpx.Response(status, json={"details": "DO_NOT_LEAK_SECRET"})

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError) as error:
            await client.refund(CAPTURE, "25.00", "USD", str(uuid4()))
        assert error.value.no_effect is definitive and "DO_NOT_LEAK" not in str(error.value)
        assert len(calls) == 2  # No retry, including redirects and 5xx.
        await client.close()

    asyncio.run(scenario())


def test_real_refund_timeout_no_retry():
    async def scenario():
        count = 0

        def handler(request):
            nonlocal count
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            count += 1
            raise httpx.ReadTimeout("secret and provider payload must stay private")

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError) as error:
            await client.refund(CAPTURE, "25.00", "USD", str(uuid4()))
        assert not error.value.no_effect and count == 1
        assert str(error.value) == "PAYPAL_TRANSPORT_UNCERTAIN"
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_capture",
        "no_order",
        "wrong_order",
        "wrong_merchant",
        "capture_amount_mismatch",
        "capture_status_mismatch",
    ],
)
def test_capture_evidence_requires_consistency(mutation):
    async def scenario():
        capture, order = capture_data(), order_data()
        if mutation == "wrong_capture":
            capture["id"] = ORDER
        elif mutation == "no_order":
            capture.pop("supplementary_data")
        elif mutation == "wrong_order":
            order["id"] = CAPTURE
        elif mutation == "wrong_merchant":
            order["purchase_units"][0]["payee"]["merchant_id"] = "SOMEOTHERID"
        elif mutation == "capture_amount_mismatch":
            order["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"] = "110.00"
        else:
            order["purchase_units"][0]["payments"]["captures"][0]["status"] = "PENDING"

        def handler(request):
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            return httpx.Response(200, json=order if "orders" in request.url.path else capture)

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError, match="INSUFFICIENT_CAPTURE_EVIDENCE"):
            await client.capture(CAPTURE)
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "changes",
    [
        {"environment": "live"},
        {"paypal_base_url": "https://api-m.paypal.com"},
        {"paypal_base_url": "https://api-m.sandbox.paypal.com.attacker.example"},
        {"payment_mode": "sandbox"},
        {"ai_mode": "real"},
        {"capture_ids": ()},
        {"llm_base_url": "http://remote.example/v1"},
        {"llm_base_url": "https://secret@example.com/v1"},
    ],
)
def test_configuration_fails_closed(changes):
    with pytest.raises(ValidationError):
        Settings(**changes)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("merchant_id", "other-merchant", "MERCHANT_MISMATCH"),
        ("currency", "JPY", "UNSUPPORTED_CURRENCY"),
        ("prior_refunds", True, "CAPTURE_NOT_ELIGIBLE"),
        ("status", "PENDING", "CAPTURE_NOT_ELIGIBLE"),
    ],
)
def test_payment_policy_rejects_untrusted_facts(field, value, code):
    facts = CaptureFacts(
        capture_id="DEMO0000000000001",
        order_id=ORDER,
        merchant_id="DEMO-MERCHANT",
        amount="120.00",
        currency="USD",
        status="COMPLETED",
        prior_refunds=False,
        source="fake",
    )
    data = facts.model_dump() | {field: value}
    with pytest.raises(Problem, match=code):
        validate_policy(
            CaptureFacts.model_validate(data),
            Recommendation.model_validate_json(synthetic_recommendation()),
            Settings(),
        )


@pytest.mark.parametrize("status", ["COMPLETED", "PENDING", "FAILED", "CANCELLED"])
def test_refund_verification_statuses(status):
    args = RefundInput(incident_id=str(uuid4()), capture_id=CAPTURE, amount="25.00", currency="USD")
    assert (
        verified_refund(refund_data(status), args, expected_id=REFUND)["provider_status"] == status
    )


@pytest.mark.parametrize("mutation", ["amount", "currency", "capture", "id", "status", "missing"])
def test_refund_verification_rejects_mismatch(mutation):
    args = RefundInput(incident_id=str(uuid4()), capture_id=CAPTURE, amount="25.00", currency="USD")
    data = refund_data()
    if mutation == "amount":
        data["amount"]["value"] = "26.00"
    elif mutation == "currency":
        data["amount"]["currency_code"] = "NZD"
    elif mutation == "capture":
        data["links"][0]["href"] = f"{SANDBOX_URL}/v2/payments/captures/{ORDER}"
    elif mutation == "id":
        data["id"] = CAPTURE
    elif mutation == "status":
        data["status"] = "MAGIC_SUCCESS"
    else:
        data.pop("amount")
    with pytest.raises(Problem):
        verified_refund(data, args, expected_id=REFUND)


def test_real_ai_contract_mock_transport():
    async def scenario():
        def handler(request):
            assert str(request.url) == "https://model.example/v1/chat/completions"
            body = json.loads(request.content)
            assert body["model"] == "configured-model" and "tools" not in body
            assert body["response_format"] == {"type": "json_object"}
            assert "DEMO-MERCHANT" not in json.dumps(body)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": synthetic_recommendation()},
                        }
                    ]
                },
            )

        settings = Settings(
            ai_mode="real",
            llm_base_url="https://model.example/v1",
            llm_model="configured-model",
            llm_api_key=SecretStr("synthetic-key"),
        )
        client = ChatCompletionsAnalyst(settings, transport=httpx.MockTransport(handler))
        result = await client.analyze(
            "Synthetic damaged item, USD 25.00.",
            {
                "amount": "120.00",
                "currency": "USD",
                "status": "COMPLETED",
                "merchant_id": "DEMO-MERCHANT",
            },
        )
        assert result.requested_amount == "25.00"
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "data",
    [
        {
            "choices": [
                {"finish_reason": "length", "message": {"content": synthetic_recommendation()}}
            ]
        },
        {
            "choices": [
                {"finish_reason": "stop", "message": {"refusal": "Cannot comply", "content": None}}
            ]
        },
        {"choices": [{"finish_reason": "stop", "message": {"content": "invalid"}}]},
        {"choices": []},
    ],
)
def test_real_ai_rejects_invalid_or_refused_response(data):
    async def scenario():
        client = ChatCompletionsAnalyst(
            Settings(
                ai_mode="real", llm_base_url="https://model.example/v1", llm_model="test-model"
            ),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)),
        )
        with pytest.raises(Problem, match="INVALID_MODEL_RESPONSE"):
            await client.analyze(
                "Synthetic USD 25.00",
                {"amount": "120.00", "currency": "USD", "status": "COMPLETED"},
            )
        await client.close()

    asyncio.run(scenario())


def test_latest_facts_changed_prevents_refund(browser):
    client, fake, _ = browser
    data = ready(client)
    with __import__("sqlite3").connect(fake.path) as db:
        row = json.loads(db.execute("SELECT data FROM captures").fetchone()[0])
        row["prior_refunds"] = True
        db.execute("UPDATE captures SET data=?", (json.dumps(row),))
    result, _ = step(client, data, "execute")
    assert result["action"]["state"] == "Failed" and fake.recorded_calls() == []


def test_persisted_environment_cannot_switch(environment):
    path, settings = environment
    with (
        pytest.raises(Problem, match="PERSISTED_CONFIGURATION_MISMATCH"),
        composition(
            path, settings.model_copy(update={"merchant_id": "OTHER"}), predecessor_stopped=True
        ),
    ):
        pass


def test_unapproved_plan_and_foreign_scope_denied(browser):
    client, fake, app = browser
    data = analyze(client)
    runtime = app.state.sentinel.runtime
    principal = runtime.verifier.verify(client.headers["Authorization"])
    from agentic_intent_gate.runtime import AdmissionCommand

    with pytest.raises(Exception) as error:  # noqa: B017 -- error type not a public export
        runtime.gateway.admit(
            AdmissionCommand(
                data["run"]["run_id"], data["run"]["version"], principal.subject_id, str(uuid4())
            ),
            principal,
        )
    assert error.value.code.value == "RUN_NOT_ACTION_ELIGIBLE"
    data = client.post(
        f"/api/incidents/{data['id']}/decision",
        json={
            "decision": "approve",
            "expected_version": data["run"]["version"],
            "plan_digest": data["plan_digest"],
        },
    ).json()
    data, _ = step(client, data, "admit")
    action = runtime.actions.get(data["action"]["action_id"])
    for spec in [
        replace(action.spec, execution_scope=str(uuid4())),
        replace(action.spec, target="other-target"),
    ]:
        with pytest.raises(Exception) as denied:  # noqa: B017 -- error type not a public export
            runtime.gateway.policy.permit(principal, "authorize", spec)
        assert denied.value.code.value == "ACTION_NOT_AUTHORIZED"
    assert fake.recorded_calls() == []
