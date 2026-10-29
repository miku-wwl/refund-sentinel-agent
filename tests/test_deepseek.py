"""Mocked cloud contracts only. Live qualification is separately budgeted and labeled."""

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from refund_sentinel import integration
from refund_sentinel.decision_lab import CASES
from refund_sentinel.deepseek import ENDPOINT, MODEL, DeepSeekProposal, configured_key
from refund_sentinel.models import Problem
from refund_sentinel.presentation import COOKIE, PROOF_SHA256, create_presentation_app

KEY = "test-only-deepseek-credential-123456"
FACTS = {
    "capture_id": "DEMO0000000000001",
    "merchant_id": "DEMO-MERCHANT",
    "source": "fake",
    "amount": "120.00",
    "currency": "USD",
    "status": "COMPLETED",
    "prior_refunds": False,
}
VALUE = {
    "recommendation": "REFUND",
    "requested_amount": "25.00",
    "currency": "USD",
    "explanation": "Mocked DeepSeek response for a synthetic request.",
    "reason_code": "DAMAGED_ITEM",
    "uncertainty": "LOW",
}


def envelope(output=None, *, model=MODEL, finish="stop", **msg):
    return {
        "model": model,
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(VALUE) if output is None else output,
                    **msg,
                },
            }
        ],
    }


@pytest.fixture(autouse=True)
def cloud_key(monkeypatch):
    monkeypatch.setenv("REFUND_SENTINEL_DEEPSEEK_API_KEY", KEY)


def infer(handler, *, message=None, facts=None, timeout=30):
    model = DeepSeekProposal(transport=httpx.MockTransport(handler), timeout=timeout)
    return model, model.analyze(message or CASES["valid_partial"].message, facts or FACTS)


def test_fixed_cloud_contract_and_minimal_synthetic_egress(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://attacker.invalid")
    monkeypatch.setenv("HTTPS_PROXY", "http://attacker.invalid")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://attacker.invalid")
    monkeypatch.setenv("LLM_MODEL", "untrusted")
    observed = []

    def handler(request):
        observed.append(request)
        assert str(request.url) == ENDPOINT and request.method == "POST"
        assert request.headers["authorization"] == "Bearer " + KEY
        assert request.headers["accept-encoding"] == "identity"
        body = json.loads(request.content)
        assert body["model"] == MODEL and body["stream"] is False
        assert body["thinking"] == {"type": "disabled"}
        assert body["response_format"] == {"type": "json_object"}
        assert body["max_tokens"] == 512 and "tools" not in body
        assert "Example JSON" in body["messages"][0]["content"]
        assert all(field in body["messages"][0]["content"] for field in VALUE)
        assert json.loads(body["messages"][1]["content"]) == {
            "customer_request": CASES["valid_partial"].message,
            "trusted_payment": {"amount": "120.00", "currency": "USD", "status": "COMPLETED"},
        }
        assert not any(
            s in request.content.decode()
            for s in (
                KEY,
                "execution_scope",
                "operator.capability",
                "1YA65594665951620",
                "DEMO-MERCHANT",
            )
        )
        return httpx.Response(200, json=envelope())

    model, call = infer(handler, facts=FACTS | {"private_record": "MUST_NOT_TRANSMIT"})
    assert asyncio.run(call).model_dump() == VALUE
    assert len(observed) == 1 and b"MUST_NOT_TRANSMIT" not in observed[0].content
    assert model.returned_model == MODEL and model.seconds >= 0 and model.http_status == 200
    assert model.model_output == json.dumps(VALUE) and not model.refused


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "DEEPSEEK_AUTHENTICATION_FAILED"),
        (403, "DEEPSEEK_AUTHENTICATION_FAILED"),
        (429, "DEEPSEEK_HTTP_ERROR"),
        (500, "DEEPSEEK_HTTP_ERROR"),
        (302, "DEEPSEEK_HTTP_ERROR"),
        (307, "DEEPSEEK_HTTP_ERROR"),
    ],
)
def test_http_and_redirect_errors_are_sanitized_one_attempt(status, code):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(status, headers={"Location": "https://attacker.invalid"}, text=KEY)

    model, call = infer(handler)
    with pytest.raises(Problem, match=code):
        asyncio.run(call)
    assert seen == [ENDPOINT] and model.model_output is None


@pytest.mark.parametrize(
    "data,code",
    [
        (b"", "INVALID_MODEL_RESPONSE"),
        (b'{"model":"deepseek-flash","model":"other"}', "INVALID_MODEL_RESPONSE"),
        ({}, "INVALID_MODEL_RESPONSE"),
        (envelope(""), "DEEPSEEK_EMPTY_RESPONSE"),
        (envelope("   "), "DEEPSEEK_EMPTY_RESPONSE"),
        (envelope("{}"), "INVALID_MODEL_RESPONSE"),
        (envelope('{"recommendation":"REFUND",'), "INVALID_MODEL_RESPONSE"),
        (
            envelope('{"recommendation":"REFUND","recommendation":"REFUND"}'),
            "INVALID_MODEL_RESPONSE",
        ),
        (envelope("[]"), "INVALID_MODEL_RESPONSE"),
        (envelope(json.dumps(VALUE), finish="length"), "DEEPSEEK_FINISH_REASON_REJECTED"),
        (envelope("refused", finish="content_filter"), "DEEPSEEK_REFUSED"),
        (envelope("refused", refusal="No"), "DEEPSEEK_REFUSED"),
        (envelope(finish="tool_calls"), "DEEPSEEK_FINISH_REASON_REJECTED"),
        (envelope(finish="unrecognized"), "DEEPSEEK_FINISH_REASON_REJECTED"),
        (envelope(model="unexpected-model"), "DEEPSEEK_MODEL_METADATA_REJECTED"),
        (envelope(model=None), "DEEPSEEK_MODEL_METADATA_REJECTED"),
        (envelope(role="tool"), "DEEPSEEK_FINISH_REASON_REJECTED"),
        (envelope(tool_calls=[{"name": "refund"}]), "DEEPSEEK_FINISH_REASON_REJECTED"),
        (envelope(json.dumps(VALUE | {"explanation": KEY})), "INVALID_MODEL_RESPONSE"),
        (envelope("x" * 16385), "INVALID_MODEL_RESPONSE"),
    ],
)
def test_invalid_envelopes_are_never_recommendations(data, code):
    response = (
        httpx.Response(200, content=data)
        if isinstance(data, bytes)
        else httpx.Response(200, json=data)
    )
    model, call = infer(lambda r: response)
    with pytest.raises(Problem, match=code):
        asyncio.run(call)
    assert KEY not in (model.model_output or "")
    if isinstance(data, dict) and data.get("choices"):
        finish = data["choices"][0]["finish_reason"]
        if finish == "length":
            assert model.output_truncated
        if finish == "content_filter":
            assert model.refused


@pytest.mark.parametrize("field", VALUE)
@pytest.mark.parametrize("mutation", ["missing", "type"])
def test_each_of_six_fields_is_strictly_required(field, mutation):
    value = dict(VALUE)
    if mutation == "missing":
        value.pop(field)
    else:
        value[field] = 123
    _, call = infer(lambda r: httpx.Response(200, json=envelope(json.dumps(value))))
    with pytest.raises(Problem, match="INVALID_MODEL_RESPONSE"):
        asyncio.run(call)


@pytest.mark.parametrize(
    "extra",
    [
        {"authorized": True},
        {"endpoint": "https://attacker.invalid"},
        {"execution_timeout_seconds": 15},
    ],
)
def test_extra_authority_fields_rejected(extra):
    _, call = infer(lambda r: httpx.Response(200, json=envelope(json.dumps(VALUE | extra))))
    with pytest.raises(Problem, match="INVALID_MODEL_RESPONSE"):
        asyncio.run(call)


def test_envelope_bound_and_transport_timeout():
    model, call = infer(lambda r: httpx.Response(200, content=b"x" * 65537))
    with pytest.raises(Problem, match="DEEPSEEK_OUTPUT_TOO_LARGE"):
        asyncio.run(call)
    assert model.output_truncated

    async def slow(request):
        await asyncio.sleep(1)

    model, call = infer(slow, timeout=0.01)
    with pytest.raises(Problem, match="DEEPSEEK_REQUEST_EXPIRED"):
        asyncio.run(call)
    assert model.seconds < 1

    def expired(request):
        raise httpx.ReadTimeout(KEY)

    _, call = infer(expired)
    with pytest.raises(Problem, match="DEEPSEEK_REQUEST_EXPIRED"):
        asyncio.run(call)


def test_no_proxy_inheritance_or_redirect_configuration(monkeypatch):
    original = httpx.AsyncClient
    configurations = []

    def client(**kwargs):
        configurations.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    _, call = infer(lambda r: httpx.Response(200, json=envelope()))
    asyncio.run(call)
    assert configurations[0]["trust_env"] is False
    assert configurations[0]["follow_redirects"] is False


def test_key_precedence_and_dotenv_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fallback-key-1234567890")
    assert configured_key().get_secret_value() == KEY
    monkeypatch.setenv("REFUND_SENTINEL_DEEPSEEK_API_KEY", "")
    with pytest.raises(Problem, match="DEEPSEEK_KEY_NOT_CONFIGURED"):
        configured_key()
    monkeypatch.delenv("REFUND_SENTINEL_DEEPSEEK_API_KEY")
    assert configured_key().get_secret_value() == "fallback-key-1234567890"
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=" + KEY)
    with pytest.raises(Problem, match="DEEPSEEK_KEY_NOT_CONFIGURED"):
        configured_key()


@pytest.mark.parametrize(
    "message,facts",
    [
        ("Real customer private message", FACTS),
        (CASES["valid_partial"].message, FACTS | {"source": "paypal-sandbox"}),
        (CASES["valid_partial"].message, FACTS | {"capture_id": "1YA65594665951620"}),
    ],
)
def test_non_synthetic_inputs_denied_before_dispatch(message, facts):
    model, call = infer(lambda r: pytest.fail("No dispatch"), message=message, facts=facts)
    with pytest.raises(Problem, match="DEEPSEEK_SYNTHETIC_INPUT_REQUIRED"):
        asyncio.run(call)
    assert not model.request_sent


def command(view, operation):
    entity = view["run" if operation == "approve" else "action"] or {}
    return {
        "operation": operation,
        "confirmed": True,
        "expected_version": entity.get("version", 1),
        "plan_digest": view["plan_sha256"] or "0" * 64,
        "idempotency_key": str(uuid4()),
    }


@pytest.mark.parametrize("case", ["valid_partial", "ambiguous", "excessive", "injection"])
def test_cloud_case_gates_persistence_and_no_real_paypal(tmp_path, monkeypatch, case):
    monkeypatch.setattr(integration, "SandboxPayPal", lambda *a, **k: pytest.fail("No real PayPal"))
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=envelope())

    def factory():
        return DeepSeekProposal(transport=httpx.MockTransport(handler))

    app = create_presentation_app(
        tmp_path / "lab",
        delay=0,
        cloud_proposal_factory=factory,
        proposal_factory=lambda: pytest.fail("No provider fallback"),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        proof = client.get("/presentation/proof").content
        body = {"scenario": case, "planning_mode": "deepseek"}
        assert client.post("/presentation/demo", json=body).status_code == 200
        view = client.post("/presentation/demo/generate", json=body).json()
        assert view["decision"]["provider"] == "deepseek"
        assert view["decision"]["source"] == "REAL_DEEPSEEK_API"
        assert view["model"] == view["decision"]["requested_model"] == MODEL
        assert view["decision"]["returned_model"] == MODEL
        assert view["action"] is None and view["simulated_dispatches"] == 0
        for op in ("authorize", "execute"):
            assert (
                client.post("/presentation/demo/command", json=command(view, op)).status_code == 409
            )
        if case in {"ambiguous", "excessive"}:
            assert view["run"] is None and view["executable_amount"] is None
            assert view["decision"]["policy_verdict"] == "BLOCKED"
        else:
            assert view["run"]["state"] == "AwaitingApproval"
            for op in ("approve", "authorize", "execute"):
                response = client.post("/presentation/demo/command", json=command(view, op))
                assert response.status_code == 200
                view = response.json()
                assert view["simulated_dispatches"] == (1 if op == "execute" else 0)
            assert view["receipt"]["persisted"] and view["action"]["state"] == "Succeeded"
        exported = client.get("/presentation/demo/export")
        assert exported.json() == view and KEY not in exported.text
        assert view["amount_semantics"] == "SIMULATION_DEFAULT_ONLY"
        assert view["requested_amount"] == CASES[case].requested_amount
        assert client.post("/presentation/demo/generate", json=body).status_code == 409
        assert len(seen) == 1
        assert client.get("/presentation/proof").content == proof
    with TestClient(
        create_presentation_app(tmp_path / "lab"), base_url="http://127.0.0.1"
    ) as client:
        client.cookies.set(COOKIE, view["session_id"])
        assert client.get("/presentation/demo").json()["decision"] == view["decision"]
        assert client.get("/presentation/demo").json()["receipt"] == view["receipt"]
    import hashlib

    from refund_sentinel.presentation import STATIC

    assert hashlib.sha256((STATIC / "qualified-case.json").read_bytes()).hexdigest() == PROOF_SHA256


def test_cloud_failure_stays_cloud_and_never_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("REFUND_SENTINEL_DEEPSEEK_API_KEY", "")
    app = create_presentation_app(
        tmp_path / "lab", proposal_factory=lambda: pytest.fail("No fallback")
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        body = {"scenario": "valid_partial", "planning_mode": "deepseek"}
        client.post("/presentation/demo", json=body)
        view = client.post("/presentation/demo/generate", json=body).json()
        assert view["decision"]["reason"] == "DEEPSEEK_KEY_NOT_CONFIGURED"
        assert view["decision"]["source"] == "NOT_GENERATED"
        assert view["decision"]["provider"] == "deepseek" and view["run"] is None
        assert view["simulated_dispatches"] == 0
        for override in (
            {"model": "other"},
            {"endpoint": "https://attacker.invalid"},
            {"api_key": KEY},
            {"provider_url": "https://attacker.invalid"},
        ):
            assert client.post("/presentation/demo", json=body | override).status_code == 422
        assert (
            client.post(
                "/presentation/demo",
                json={"scenario": "unknown_outcome", "planning_mode": "deepseek"},
            ).status_code
            == 422
        )
