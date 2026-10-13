import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_fixture import settings

from refund_sentinel import fixture, fixture_callback
from refund_sentinel.fixture import (
    CREATE_CONSENT,
    LEGACY_CANCEL_URL,
    LEGACY_RETURN_URL,
    FixtureClient,
    FixtureState,
    FixtureStore,
    operate,
    order_body,
    validate_order,
)
from refund_sentinel.fixture_callback import (
    APPROVED_PATH,
    CALLBACK_CANCEL_URL,
    CALLBACK_HEALTH,
    CALLBACK_ORIGIN,
    CALLBACK_RETURN_URL,
    CANCELLED_PATH,
    HEALTH_PATH,
    callback_app,
    require_callback_ready,
)
from refund_sentinel.models import Problem


def test_future_fixture_freezes_working_return_and_cancel_urls_in_private_request(tmp_path):
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(settings(), source="MOCK")
    assert state.return_url == CALLBACK_RETURN_URL and state.cancel_url == CALLBACK_CANCEL_URL
    body = json.loads((store.directory / "create-order.private.json").read_text("utf-8"))
    context = body["payment_source"]["paypal"]["experience_context"]
    assert context["return_url"] == "http://127.0.0.1:8766/refund-sentinel-sandbox/approved"
    assert context["cancel_url"] == "http://127.0.0.1:8766/refund-sentinel-sandbox/cancelled"
    assert body == order_body(store.load(settings(), "MOCK"))


def test_legacy_fixture_without_url_fields_preserves_original_body_digest_and_bytes(tmp_path):
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(settings(), source="MOCK")
    state.return_url, state.cancel_url = LEGACY_RETURN_URL, LEGACY_CANCEL_URL
    state.phase, state.order_id = "UNKNOWN_CREATE", "5O190127TN364715T"
    payload = state.model_dump(exclude={"return_url", "cancel_url"})
    store.path.write_text(json.dumps(payload), encoding="utf-8")
    expected_body = order_body(state)
    expected_digest = state.review_digest()
    before = store.path.read_bytes()
    loaded = store.load(settings(), "MOCK")
    assert loaded.return_url == LEGACY_RETURN_URL and loaded.cancel_url == LEGACY_CANCEL_URL
    assert order_body(loaded) == expected_body and loaded.review_digest() == expected_digest
    assert store.path.read_bytes() == before and loaded.phase == "UNKNOWN_CREATE"


@pytest.mark.parametrize(
    "urls",
    [
        ("https://evil.test/approved", CALLBACK_CANCEL_URL),
        (CALLBACK_RETURN_URL, "https://evil.test/cancelled"),
        (LEGACY_RETURN_URL, CALLBACK_CANCEL_URL),
        (CALLBACK_RETURN_URL, LEGACY_CANCEL_URL),
        (CALLBACK_RETURN_URL + "?token=private", CALLBACK_CANCEL_URL),
    ],
)
def test_callback_configuration_rejects_arbitrary_or_mixed_pairs(tmp_path, urls):
    state = FixtureStore(tmp_path / ".state-fixture").prepare(settings(), source="MOCK")
    payload = state.model_dump() | {"return_url": urls[0], "cancel_url": urls[1]}
    with pytest.raises(ValidationError):
        FixtureState.model_validate(payload)


@pytest.mark.parametrize("path", [APPROVED_PATH, CANCELLED_PATH])
def test_callback_get_neither_confirms_provider_status_nor_echoes_private_query(path):
    with TestClient(callback_app()) as client:
        response = client.get(
            path + "?token=PRIVATE_ORDER_ID&PayerID=PRIVATE_BUYER_ID&extra=%3Cscript%3E"
        )
        assert response.status_code == 200
        assert "Order GET" in response.text and "separate explicit authorization" in response.text
        assert "PRIVATE" not in response.text and "<script>" not in response.text
        assert "APPROVED" not in response.text and "COMPLETED" not in response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "default-src 'none'" in response.headers["content-security-policy"]
        assert client.post(path).status_code == 405
        assert client.post("/capture").status_code == 404
        assert client.post("/refund").status_code == 404


def test_callback_health_is_local_receiver_liveness_only():
    with TestClient(callback_app()) as client:
        response = client.get(HEALTH_PATH)
        assert response.json() == CALLBACK_HEALTH
        assert client.get("/docs").status_code == 404


def test_callback_server_entrypoint_is_explicit_loopback_http_without_access_logs(monkeypatch):
    calls = []
    monkeypatch.setattr(fixture_callback.uvicorn, "run", lambda app, **kw: calls.append(kw))
    fixture_callback.main()
    assert calls == [
        {"host": "127.0.0.1", "port": 8766, "access_log": False, "log_level": "warning"}
    ]
    assert "ssl_keyfile" not in calls[0]


def test_readiness_uses_only_fixed_loopback_health_without_credentials():
    def handler(request):
        assert str(request.url) == CALLBACK_ORIGIN + HEALTH_PATH and request.method == "GET"
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=CALLBACK_HEALTH)

    asyncio.run(require_callback_ready(transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize(
    "failure", ["connection", "timeout", "redirect", "wrong_service", "malformed"]
)
def test_callback_readiness_fails_closed_without_retry(failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "connection":
            raise httpx.ConnectError("PRIVATE_FAILURE", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE_FAILURE", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://evil.test"})
        if failure == "wrong_service":
            return httpx.Response(200, json={"service": "unrelated-local-service"})
        return httpx.Response(200, text="PRIVATE_FAILURE")

    with pytest.raises(Problem, match="FIXTURE_CALLBACK_NOT_READY"):
        asyncio.run(require_callback_ready(transport=httpx.MockTransport(handler)))
    assert len(calls) == 1


def test_unready_callback_blocks_future_create_before_oauth_or_payment_attempt(
    tmp_path, monkeypatch
):
    async def scenario():
        config = settings()
        store = FixtureStore(tmp_path / ".state-fixture")
        state = store.prepare(config)
        calls = []
        client = FixtureClient(config, transport=httpx.MockTransport(lambda r: calls.append(r)))
        client.source = "REAL_SANDBOX"  # Exercise real composition's local readiness admission.

        async def unavailable():
            raise Problem("FIXTURE_CALLBACK_NOT_READY")

        monkeypatch.setattr(fixture, "require_callback_ready", unavailable)
        with pytest.raises(Problem, match="FIXTURE_CALLBACK_NOT_READY"):
            await operate(
                store,
                config,
                "create",
                client=client,
                authorization=CREATE_CONSENT,
                review_digest=state.review_digest(),
                accounts_confirmed=True,
            )
        assert calls == []
        assert not (store.directory / "create.attempt.json").exists()
        assert store.load(config, "REAL_SANDBOX").phase == "PREPARED"

    asyncio.run(scenario())


def test_missing_create_authorization_precedes_even_callback_health_query(tmp_path, monkeypatch):
    async def forbidden():
        pytest.fail("Missing payment authorization must not trigger callback readiness or PayPal")

    monkeypatch.setattr(fixture, "require_callback_ready", forbidden)
    config = settings()
    store = FixtureStore(tmp_path / ".state-fixture")
    store.prepare(config)
    client = FixtureClient(config, transport=httpx.MockTransport(lambda r: pytest.fail("PayPal")))
    client.source = "REAL_SANDBOX"
    with pytest.raises(Problem, match="EXPLICIT_OPERATION_AUTHORIZATION_REQUIRED"):
        asyncio.run(operate(store, config, "create", client=client))


def test_sanitized_genuine_approved_order_validates_without_promoting_original_fixture(tmp_path):
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(settings(), source="MOCK")
    state.order_id = "5O190127TN364715T"
    state.create_request_id = "11111111-1111-4111-8111-111111111111"
    state.phase = "UNKNOWN_CREATE"
    store.save(state)
    before = store.path.read_bytes()
    data = json.loads(
        (Path(__file__).parent / "fixtures/paypal-order-approved.sanitized.json").read_text("utf-8")
    )
    assert validate_order(data, state, approved=True) == "APPROVED"
    assert store.path.read_bytes() == before and state.phase == "UNKNOWN_CREATE"


def test_buyer_redirect_page_cannot_reconcile_unknown_or_authorize_capture(tmp_path):
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(settings(), source="MOCK")
    state.order_id, state.phase = "5O190127TN364715T", "UNKNOWN_CREATE"
    store.save(state)
    before = {p.name: p.read_bytes() for p in store.directory.iterdir()}
    with TestClient(callback_app()) as client:
        assert client.get(APPROVED_PATH + "?token=5O190127TN364715T").status_code == 200
    assert {p.name: p.read_bytes() for p in store.directory.iterdir()} == before
    assert store.load(settings(), "MOCK").phase == "UNKNOWN_CREATE"
    assert not (store.directory / "capture.attempt.json").exists()
