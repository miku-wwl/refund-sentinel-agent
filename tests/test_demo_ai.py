"""Offline model contracts use MockTransport; none qualify genuine inference."""

import asyncio
import hashlib
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from refund_sentinel import integration
from refund_sentinel.demo_ai import OLLAMA_URL, BoundedOllamaTransport, LocalProposal
from refund_sentinel.presentation import create_presentation_app


def recommendation(**overrides):
    return dict(
        recommendation="REFUND",
        requested_amount="25.00",
        currency="USD",
        explanation="Synthetic model response for an offline test.",
        reason_code="DAMAGED_ITEM",
        uncertainty="LOW",
        **overrides,
    )


def envelope(content=None, **overrides):
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": content or json.dumps(recommendation()),
                    **overrides,
                },
            }
        ]
    }


@pytest.fixture
def ai_console(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real payments are forbidden even with a real AI mode")

    monkeypatch.setattr(integration, "SandboxPayPal", forbidden)
    observed = []

    def handler(request):
        observed.append(request)
        return httpx.Response(200, json=envelope())

    def factory():
        return LocalProposal(transport=httpx.MockTransport(handler))

    app = create_presentation_app(tmp_path / "demo", delay=0, proposal_factory=factory)
    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        yield client, app, observed


def new_ai(client):
    response = client.post("/presentation/demo", json={"planning_mode": "local_ai"})
    assert response.status_code == 200, response.text
    return response.json()


def generate(client):
    return client.post("/presentation/demo/generate", json={"planning_mode": "local_ai"})


def advance(client, view, operation, **extra):
    return client.post(
        "/presentation/demo/command",
        json={
            "operation": operation,
            "confirmed": True,
            "expected_version": view["run" if operation == "approve" else "action"]["version"],
            "plan_digest": view["plan_sha256"],
            "idempotency_key": str(uuid4()),
            **extra,
        },
    )


def test_mock_local_ai_pipeline_with_genuine_runtime_and_fake_effect(ai_console):
    client, app, requests = ai_console
    empty = new_ai(client)
    assert empty["analysis_source"] == "NOT_GENERATED" and empty["model"] is None
    assert not requests
    view = generate(client).json()
    assert view["analysis_source"] == "REAL_LOCAL_OLLAMA"
    assert view["model"] == "phi4-mini:latest" and view["model_seconds"] >= 0
    assert view["run"]["state"] == "AwaitingApproval" and view["action"] is None
    assert view["simulated_dispatches"] == 0
    assert view["plan"]["steps"][0]["arguments"]["capture_id"] == "DEMO0000000000001"
    request = requests[0]
    body = json.loads(request.content)
    assert str(request.url) == OLLAMA_URL + "/chat/completions"
    assert request.headers.get("authorization") is None
    assert body["model"] == "phi4-mini:latest" and body["max_tokens"] == 384
    assert body["temperature"] == 0 and body["stream"] is False
    assert body["response_format"]["type"] == "json_schema"
    assert not any(
        word in request.content.decode()
        for word in (
            "1YA65594665951620",
            "EZL4XDY2TTLVW",
            "operator.capability",
            "execution_scope",
        )
    )
    for operation in ("approve", "authorize", "execute"):
        response = advance(client, view, operation)
        assert response.status_code == 200, response.text
        view = response.json()
    assert view["action"]["state"] == "Succeeded" and view["receipt"]["persisted"]
    assert view["simulated_dispatches"] == 1 and len(requests) == 1
    assert advance(client, view, "execute").status_code == 409
    assert len(requests) == 1
    session = app.state.demo.get(view["session_id"])
    assert session.settings.payment_mode == "offline" and session.settings.ai_mode == "real"
    assert session.settings.client_id.get_secret_value() == ""
    assert session.settings.client_secret.get_secret_value() == ""
    assert view["adapter_seconds"] == 5


@pytest.mark.parametrize(
    "content,error",
    [
        ("not JSON", "INVALID_MODEL_RESPONSE"),
        ('{"recommendation":"REFUND","recommendation":"REFUND"}', "INVALID_MODEL_RESPONSE"),
        (json.dumps(recommendation() | {"tool_name": "arbitrary_tool"}), "INVALID_MODEL_RESPONSE"),
        (
            json.dumps(recommendation() | {"execution_scope": str(uuid4())}),
            "INVALID_MODEL_RESPONSE",
        ),
        (
            json.dumps(recommendation() | {"execution_timeout_seconds": 15}),
            "INVALID_MODEL_RESPONSE",
        ),
        (json.dumps(recommendation() | {"payment_mode": "sandbox"}), "INVALID_MODEL_RESPONSE"),
        (json.dumps(recommendation() | {"authorized": True}), "INVALID_MODEL_RESPONSE"),
        (
            json.dumps(recommendation() | {"requested_amount": "26.00"}),
            "DEMO_PROPOSAL_AMOUNT_MISMATCH",
        ),
        (json.dumps(recommendation() | {"requested_amount": "125.00"}), "AMOUNT_OUTSIDE_POLICY"),
        (json.dumps(recommendation() | {"currency": "NZD"}), "CURRENCY_OR_AMOUNT_MISMATCH"),
        (json.dumps(recommendation() | {"uncertainty": "HIGH"}), "MANUAL_REVIEW_REQUIRED"),
        (json.dumps(recommendation() | {"recommendation": "REVIEW"}), "MANUAL_REVIEW_REQUIRED"),
        (json.dumps(recommendation() | {"requested_amount": "-5.00"}), "INVALID_MODEL_RESPONSE"),
        (json.dumps(recommendation() | {"explanation": "x" * 501}), "INVALID_MODEL_RESPONSE"),
    ],
)
def test_rejected_proposal_preserves_safe_state_and_manual_fallback(ai_console, content, error):
    client, app, _ = ai_console
    empty = new_ai(client)
    session = app.state.demo.get(empty["session_id"])
    identity = hashlib.sha256((session.directory / "identity.json").read_bytes()).hexdigest()
    session.proposal_factory = lambda: LocalProposal(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=envelope(content)))
    )
    response = generate(client)
    assert response.status_code >= 400 and response.json()["error"] == error
    current = client.get("/presentation/demo").json()
    assert current == empty and session.incident() is None
    assert not (session.directory / "proposal.json").exists()
    assert (
        hashlib.sha256((session.directory / "identity.json").read_bytes()).hexdigest() == identity
    )
    assert client.post("/presentation/demo", json={}).status_code == 200
    fallback = client.post("/presentation/demo/generate", json={}).json()
    assert fallback["session_id"] != empty["session_id"]
    assert fallback["analysis_source"] == "SIMULATED_DETERMINISTIC_FIXTURE"
    assert session.directory.exists() and session.incident() is None


@pytest.mark.parametrize(
    "case,error",
    [
        ("unavailable", "MODEL_UNAVAILABLE"),
        ("http_error", "MODEL_UNAVAILABLE"),
        ("expired", "LOCAL_AI_REQUEST_EXPIRED"),
        ("oversized", "LOCAL_AI_OUTPUT_TOO_LARGE"),
        ("refusal", "INVALID_MODEL_RESPONSE"),
        ("truncated", "INVALID_MODEL_RESPONSE"),
    ],
)
def test_bounded_failure_without_durable_plan(ai_console, case, error):
    client, app, _ = ai_console
    empty = new_ai(client)

    async def handler(request):
        if case == "unavailable":
            raise httpx.ConnectError("private details must not escape", request=request)
        if case == "http_error":
            return httpx.Response(503, text="private backend error")
        if case == "expired":
            await asyncio.sleep(0.1)
        if case == "oversized":
            return httpx.Response(200, content=b"x" * 65537)
        if case == "refusal":
            return httpx.Response(200, json=envelope(refusal="refused"))
        result = envelope()
        if case == "truncated":
            result["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=result)

    session = app.state.demo.get(empty["session_id"])
    session.proposal_factory = lambda: LocalProposal(
        transport=httpx.MockTransport(handler), timeout=0.02 if case == "expired" else 45
    )
    response = generate(client)
    assert response.status_code >= 400 and response.json() == {"error": error}
    assert client.get("/presentation/demo").json() == empty
    assert session.incident() is None and session.fake.recorded_calls() == []


def test_ai_mode_is_bound_to_original_identity_and_not_browser_configurable(ai_console):
    client, app, requests = ai_console
    empty = new_ai(client)
    assert client.post("/presentation/demo/generate", json={}).status_code == 409
    for override in (
        {"model": "another"},
        {"llm_base_url": "https://evil.test"},
        {"capture_id": "1YA65594665951620"},
        {"budget": 15},
    ):
        assert (
            client.post(
                "/presentation/demo", json={"planning_mode": "local_ai", **override}
            ).status_code
            == 422
        )
    assert not requests and client.get("/presentation/demo").json() == empty


def test_mock_ai_receipt_resume_does_not_call_model_or_replay(ai_console):
    client, app, requests = ai_console
    new_ai(client)
    view = generate(client).json()
    for operation in ("approve", "authorize", "execute"):
        view = advance(client, view, operation).json()
    root = app.state.demo.root
    app.state.demo.close()
    from refund_sentinel.demo import DemoController

    restored = DemoController(root, proposal_factory=lambda: pytest.fail("No model on resume"))
    try:
        resumed = restored.get(view["session_id"]).view().model_dump()
        assert resumed["receipt"] == view["receipt"]
        assert resumed["analysis_source"] == "REAL_LOCAL_OLLAMA"
        assert resumed["model_seconds"] == view["model_seconds"]
        assert resumed["simulated_dispatches"] == 1 and len(requests) == 1
    finally:
        restored.close()


@pytest.mark.parametrize(
    "url,auth",
    [
        ("https://evil.test/v1/chat/completions", None),
        (OLLAMA_URL + "/chat/completions?redirect=evil", None),
        (OLLAMA_URL + "/chat/completions", "Bearer forbidden"),
    ],
)
def test_model_transport_fail_closed_endpoint_identity(url, auth):
    async def run():
        transport = BoundedOllamaTransport(
            httpx.MockTransport(lambda r: pytest.fail("Must not send"))
        )
        request = httpx.Request(
            "POST",
            url,
            json={"model": "phi4-mini:latest"},
            headers={"Authorization": auth} if auth else {},
        )
        with pytest.raises(Exception, match="LOCAL_AI_ENDPOINT_REJECTED"):
            await transport.handle_async_request(request)
        await transport.aclose()

    asyncio.run(run())


def test_cancellation_during_model_does_not_create_plan_or_effect(tmp_path):
    from refund_sentinel.demo import DemoController

    async def run():
        started = asyncio.Event()

        async def handler(request):
            started.set()
            await asyncio.sleep(10)
            return httpx.Response(200, json=envelope())

        controller = DemoController(
            tmp_path / "demo",
            delay=0,
            proposal_factory=lambda: LocalProposal(transport=httpx.MockTransport(handler)),
        )
        try:
            session = controller.new("completed", "local_ai")
            before = session.view()
            task = asyncio.create_task(session.generate())
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert session.view() == before and session.incident() is None
            assert session.fake.recorded_calls() == []
            assert not (session.directory / "proposal.json").exists()
        finally:
            controller.close()

    asyncio.run(run())


def test_underlying_model_read_timeout_is_sanitized_and_classified(ai_console):
    client, app, _ = ai_console
    empty = new_ai(client)

    def handler(request):
        raise httpx.ReadTimeout("private traceback", request=request)

    app.state.demo.get(empty["session_id"]).proposal_factory = lambda: LocalProposal(
        transport=httpx.MockTransport(handler)
    )
    response = generate(client)
    assert response.status_code == 504
    assert response.json() == {"error": "LOCAL_AI_REQUEST_EXPIRED"}
    assert client.get("/presentation/demo").json() == empty
