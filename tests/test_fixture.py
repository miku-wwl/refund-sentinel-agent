import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from refund_sentinel.fixture import (
    ALLOWLIST_CONSENT,
    CAPTURE_CONSENT,
    CREATE_CONSENT,
    FixtureClient,
    FixtureSettings,
    FixtureStore,
    SandboxFixtureTransport,
    approval_link,
    configure_allowlist,
    operate,
    summary,
    verification_settings,
    verify_capture,
)
from refund_sentinel.models import Problem
from refund_sentinel.paypal import SandboxPayPal, SandboxReadOnlyTransport

ORDER = "5O190127TN364715T"
CAPTURE = "3C679366HH908993F"
MERCHANT = "MMMMMMMMMMMMM"
BUYER = "BBBBBBBBBBBBB"
ORIGIN = "https://api-m.sandbox.paypal.com"
APPROVAL = "https://www.sandbox.paypal.com/checkoutnow?token=" + ORDER


def settings():
    return FixtureSettings(
        payment_mode="sandbox",
        client_id=SecretStr("synthetic-fixture-client"),
        client_secret=SecretStr("synthetic-fixture-secret"),
        merchant_id=MERCHANT,
    )


class SandboxServer:
    def __init__(self, state):
        self.state = state
        self.status = "PAYER_ACTION_REQUIRED"
        self.calls = []
        self.mutation_error = None
        self.change_order = lambda data: data
        self.change_ack = lambda data: data

    def order(self):
        unit = {
            "reference_id": self.state.create_request_id,
            "payee": {"merchant_id": MERCHANT},
            "amount": {"value": "20", "currency_code": "NZD"},
        }
        if self.status == "COMPLETED":
            unit["payments"] = {"captures": [self.capture()]}
        data = {
            "id": ORDER,
            "intent": "CAPTURE",
            "status": self.status,
            "purchase_units": [unit],
            "links": [
                {"rel": "self", "method": "GET", "href": ORIGIN + "/v2/checkout/orders/" + ORDER}
            ],
        }
        if self.status in {"APPROVED", "COMPLETED"}:
            data["payment_source"] = {"paypal": {"account_id": BUYER}}
        return self.change_order(copy.deepcopy(data))

    def capture(self):
        return {
            "id": CAPTURE,
            "status": "COMPLETED",
            "amount": {"value": "20.00", "currency_code": "NZD"},
            "supplementary_data": {"related_ids": {"order_id": ORDER}},
            "links": [
                {
                    "rel": "self",
                    "method": "GET",
                    "href": ORIGIN + "/v2/payments/captures/" + CAPTURE,
                }
            ],
        }

    def __call__(self, request):
        self.calls.append(request)
        assert request.url.host == "api-m.sandbox.paypal.com"
        path = request.url.path
        if path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "synthetic-fixture-token",
                    "token_type": "Bearer",
                    "expires_in": 300,
                },
            )
        assert request.headers["Authorization"] == "Bearer synthetic-fixture-token"
        if request.method == "POST":
            assert request.headers["Prefer"] == "return=representation"
            if self.mutation_error:
                return self.mutation_error(request)
        if path == "/v2/checkout/orders":
            assert request.method == "POST"
            body = json.loads(request.content)
            assert body["intent"] == "CAPTURE" and len(body["purchase_units"]) == 1
            assert body["purchase_units"][0]["payee"] == {"merchant_id": MERCHANT}
            assert body["purchase_units"][0]["amount"] == {"value": "20.00", "currency_code": "NZD"}
            assert (
                "payer" not in body
            )  # Buyer credentials/information are never submitted by this tool.
            assert request.headers["PayPal-Request-Id"] == self.state.create_request_id
            return httpx.Response(
                201,
                json={
                    "id": ORDER,
                    "status": self.status,
                    "links": [{"rel": "payer-action", "method": "GET", "href": APPROVAL}],
                },
            )
        if path == f"/v2/checkout/orders/{ORDER}/capture":
            assert request.method == "POST" and json.loads(request.content) == {}
            assert request.headers["PayPal-Request-Id"] == self.state.capture_request_id
            self.status = "COMPLETED"
            ack = {
                "id": ORDER,
                "status": "COMPLETED",
                "purchase_units": [{"payments": {"captures": [self.capture()]}}],
            }
            return httpx.Response(201, json=self.change_ack(ack))
        if path == f"/v2/checkout/orders/{ORDER}":
            return httpx.Response(200, json=self.order())
        if path == f"/v2/payments/captures/{CAPTURE}":
            return httpx.Response(200, json=self.capture())
        raise AssertionError("Unexpected request, including refunds")


@pytest.fixture
def fixture(tmp_path):
    config = settings()
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(config, source="MOCK")
    return store, config, SandboxServer(state)


def perform(fixture, operation, *, authorized=True, **kwargs):
    store, config, server = fixture
    state = store.load(config, "MOCK")
    defaults = (
        {
            "authorization": CREATE_CONSENT if operation == "create" else CAPTURE_CONSENT,
            "review_digest": state.review_digest(),
            "accounts_confirmed": True,
        }
        if authorized
        else {}
    )
    return asyncio.run(
        operate(
            store,
            config,
            operation,
            client=FixtureClient(config, transport=httpx.MockTransport(server)),
            **(defaults | kwargs),
        )
    )


def created(fixture):
    return perform(fixture, "create")


def approved(fixture):
    created(fixture)
    fixture[2].status = "APPROVED"
    return perform(fixture, "status")


def test_fixture_happy_path_persists_actual_capture_and_independent_gets(fixture):
    store, config, server = fixture
    prepared = store.load(config, "MOCK")
    assert prepared.create_request_id != prepared.capture_request_id
    before_ids = (prepared.create_request_id, prepared.capture_request_id)
    report = created(fixture)
    assert report["phase"] == "AWAITING_BUYER" and report["source"] == "MOCK"
    assert store.load(config, "MOCK").approval_url == APPROVAL
    server.status = "APPROVED"
    assert perform(fixture, "status")["phase"] == "APPROVED"
    assert perform(fixture, "capture")["phase"] == "CAPTURED"
    state = store.load(config, "MOCK")
    assert (
        state.order_id == ORDER
        and state.capture_id == CAPTURE
        and state.order_id != state.capture_id
    )
    assert (state.create_request_id, state.capture_request_id) == before_ids
    client = SandboxPayPal(
        verification_settings(config, state), read_only=True, transport=httpx.MockTransport(server)
    )
    verified = asyncio.run(verify_capture(store, config, client=client))
    assert (
        verified["phase"] == "VERIFIED" and verified["validation"]["merchant_matches_configuration"]
    )
    assert [r["operation"] for r in verified["requests"]] == ["oauth", "capture_get", "order_get"]
    assert all(r["elapsed_seconds"] >= 0 for r in verified["requests"])
    assert sum(r.method == "POST" and r.url.path != "/v1/oauth2/token" for r in server.calls) == 2
    assert store.directory.joinpath("create.attempt.json").exists()
    assert store.directory.joinpath("capture.attempt.json").exists()
    serialized = json.dumps(report) + json.dumps(verified) + store.path.read_text()
    assert (
        "synthetic-fixture-secret" not in serialized and "synthetic-fixture-token" not in serialized
    )
    assert ORDER not in json.dumps(verified) and CAPTURE not in json.dumps(verified)
    assert not any("refund" in r.url.path for r in server.calls)


@pytest.mark.parametrize(
    "changes",
    [
        {"authorization": None},
        {"authorization": CAPTURE_CONSENT},
        {"review_digest": "0" * 64},
        {"accounts_confirmed": False},
    ],
)
def test_creation_requires_exact_explicit_consent_before_network(fixture, changes):
    with pytest.raises(Problem, match="EXPLICIT_OPERATION_AUTHORIZATION_REQUIRED"):
        perform(fixture, "create", **changes)
    assert fixture[2].calls == []
    assert not (fixture[0].directory / "create.attempt.json").exists()


def test_capture_requires_its_own_authorization(fixture):
    approved(fixture)
    before = len(fixture[2].calls)
    with pytest.raises(Problem, match="EXPLICIT_OPERATION_AUTHORIZATION_REQUIRED"):
        perform(fixture, "capture", authorization=CREATE_CONSENT)
    assert len(fixture[2].calls) == before


def test_missing_buyer_approval_cannot_capture(fixture):
    created(fixture)
    with pytest.raises(Problem, match="BUYER_APPROVAL_REQUIRED"):
        perform(fixture, "capture")
    assert not (fixture[0].directory / "capture.attempt.json").exists()


def test_approval_rechecked_fresh_before_capture(fixture):
    approved(fixture)
    fixture[2].status = "PAYER_ACTION_REQUIRED"
    with pytest.raises(Problem, match="BUYER_APPROVAL_REQUIRED"):
        perform(fixture, "capture")
    assert not (fixture[0].directory / "capture.attempt.json").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://www.sandbox.paypal.com/checkoutnow?token=" + ORDER,
        "https://www.paypal.com/checkoutnow?token=" + ORDER,
        "https://www.sandbox.paypal.com.evil.test/checkoutnow?token=" + ORDER,
        "https://user@www.sandbox.paypal.com/checkoutnow?token=" + ORDER,
        "https://www.sandbox.paypal.com:444/checkoutnow?token=" + ORDER,
        APPROVAL + "#private",
        APPROVAL + "&token=" + ORDER,
        APPROVAL + "&redirect=https://evil.test",
        APPROVAL.replace(ORDER, CAPTURE),
        "https://www.sandbox.paypal.com/other?token=" + ORDER,
    ],
)
def test_approval_url_rejects_wrong_origin_path_identity_or_ambiguity(url):
    with pytest.raises(Problem, match="APPROVAL_LINK_INVALID"):
        approval_link({"links": [{"rel": "payer-action", "method": "GET", "href": url}]}, ORDER)


@pytest.mark.parametrize(
    "links",
    [
        [],
        None,
        [{"rel": "approve", "method": "POST", "href": APPROVAL}],
        [{"rel": "approve", "method": "GET", "href": APPROVAL}] * 2,
    ],
)
def test_missing_or_ambiguous_approval_link(links):
    with pytest.raises(Problem, match="APPROVAL_LINK_INVALID"):
        approval_link({"links": links}, ORDER)


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda o: o["purchase_units"][0]["payee"].update(merchant_id=BUYER), "MERCHANT_MISMATCH"),
        (
            lambda o: o["purchase_units"][0]["amount"].update(value="21.00"),
            "AMOUNT_OR_CURRENCY_MISMATCH",
        ),
        (
            lambda o: o["purchase_units"][0]["amount"].update(currency_code="USD"),
            "AMOUNT_OR_CURRENCY_MISMATCH",
        ),
        (lambda o: o.update(id=CAPTURE), "ORDER_EVIDENCE_INVALID"),
        (lambda o: o.update(intent="AUTHORIZE"), "ORDER_EVIDENCE_INVALID"),
        (
            lambda o: o["purchase_units"].append(copy.deepcopy(o["purchase_units"][0])),
            "ORDER_EVIDENCE_INVALID",
        ),
    ],
)
def test_creation_post_then_mismatching_get_is_unknown_and_never_repeated(fixture, change, code):
    server = fixture[2]

    def mutate(data):
        change(data)
        return data

    server.change_order = mutate
    with pytest.raises(Problem, match=code):
        created(fixture)
    assert fixture[0].load(fixture[1], "MOCK").phase == "UNKNOWN_CREATE"
    before = len(server.calls)
    with pytest.raises(Problem, match="NO_RETRY"):
        created(fixture)
    assert len(server.calls) == before


@pytest.mark.parametrize("buyer", [MERCHANT, None, "not-an-account"])
def test_separate_buyer_evidence_required(fixture, buyer):
    created(fixture)
    server = fixture[2]
    server.status = "APPROVED"

    def mutate(data):
        data["payment_source"]["paypal"]["account_id"] = buyer
        return data

    server.change_order = mutate
    with pytest.raises(Problem, match="SEPARATE_BUYER_EVIDENCE_REQUIRED"):
        perform(fixture, "status")
    assert not (fixture[0].directory / "capture.attempt.json").exists()


@pytest.mark.parametrize("operation", ["create", "capture"])
@pytest.mark.parametrize("error", ["timeout", "connection", "500", "duplicate", "malformed"])
def test_ambiguous_mutation_retains_stable_ids_and_no_retry(fixture, operation, error):
    if operation == "capture":
        approved(fixture)
    store, config, server = fixture
    original = store.load(config, "MOCK")

    def fail(request):
        if error == "timeout":
            raise httpx.ReadTimeout("PRIVATE_ERROR_WITH_SECRET", request=request)
        if error == "connection":
            raise httpx.ConnectError("PRIVATE_ERROR_WITH_SECRET", request=request)
        if error == "500":
            return httpx.Response(500, text="PRIVATE_RESPONSE_WITH_SECRET")
        if error == "duplicate":
            return httpx.Response(422, json={"name": "DUPLICATE_REQUEST_ID"})
        return httpx.Response(201, text="PRIVATE_RESPONSE_WITH_SECRET")

    server.mutation_error = fail
    with pytest.raises(Problem) as result:
        perform(fixture, operation)
    assert "PRIVATE" not in str(result.value)
    state = FixtureStore(store.directory).load(
        config, "MOCK"
    )  # Restart uses existing private identity.
    assert state.phase == "UNKNOWN_" + operation.upper()
    assert state.create_request_id == original.create_request_id
    assert state.capture_request_id == original.capture_request_id
    before = len(server.calls)
    with pytest.raises(Problem):
        perform(fixture, operation)
    assert len(server.calls) == before


@pytest.mark.parametrize(
    "change",
    [
        lambda ack: ack["purchase_units"][0]["payments"]["captures"][0].update(id=ORDER),
        lambda ack: ack["purchase_units"][0]["payments"]["captures"][0].update(status="PENDING"),
        lambda ack: ack["purchase_units"][0]["payments"]["captures"].clear(),
        lambda ack: ack["purchase_units"][0]["payments"]["captures"].append(
            copy.deepcopy(ack["purchase_units"][0]["payments"]["captures"][0])
        ),
        lambda ack: ack["purchase_units"][0]["payments"]["captures"][0]["amount"].update(
            value="19.00"
        ),
        lambda ack: ack["purchase_units"][0]["payments"]["captures"][0]["amount"].update(
            currency_code="USD"
        ),
    ],
)
def test_invalid_or_noncompleted_capture_ack_is_unknown(fixture, change):
    approved(fixture)

    def mutate(ack):
        change(ack)
        return ack

    fixture[2].change_ack = mutate
    with pytest.raises(Problem, match="CAPTURE_EVIDENCE_INVALID"):
        perform(fixture, "capture")
    assert fixture[0].load(fixture[1], "MOCK").phase == "UNKNOWN_CAPTURE"


def test_capture_post_then_get_failure_preserves_known_capture_but_unknown(fixture):
    approved(fixture)

    def mutate(order):
        if order["status"] == "COMPLETED":
            order["purchase_units"][0]["payee"]["merchant_id"] = BUYER
        return order

    fixture[2].change_order = mutate
    with pytest.raises(Problem, match="MERCHANT_MISMATCH"):
        perform(fixture, "capture")
    state = fixture[0].load(fixture[1], "MOCK")
    assert state.phase == "UNKNOWN_CAPTURE" and state.capture_id == CAPTURE
    assert not any("refund" in request.url.path for request in fixture[2].calls)


def test_successful_mutations_cannot_be_sent_twice(fixture):
    approved(fixture)
    with pytest.raises(Problem, match="NO_RETRY"):
        created(fixture)
    perform(fixture, "capture")
    with pytest.raises(Problem):
        perform(fixture, "capture")
    assert sum(r.url.path.endswith("/capture") for r in fixture[2].calls) == 1


def test_unknown_status_read_cannot_reconcile_or_enable_another_post(fixture):
    approved(fixture)
    store, config, server = fixture

    def timeout_after_effect(request):
        server.status = "COMPLETED"
        raise httpx.ReadTimeout("Lost acknowledgment", request=request)

    server.mutation_error = timeout_after_effect
    with pytest.raises(Problem, match="TRANSPORT_UNCERTAIN"):
        perform(fixture, "capture")
    server.mutation_error = None
    report = perform(fixture, "status")
    assert report["order_status"] == "COMPLETED" and report["phase"] == "UNKNOWN_CAPTURE"
    assert report["code"] == "FIXTURE_UNCERTAIN_MANUAL_REVIEW_REQUIRED"
    assert store.load(config, "MOCK").capture_id is None
    before = len(server.calls)
    with pytest.raises(Problem, match="NO_RETRY"):
        perform(fixture, "capture")
    assert len(server.calls) == before


def test_cancellation_after_dispatch_preserves_claim_and_unknown(fixture):
    approved(fixture)
    store, config, server = fixture

    async def handler(request):
        if request.url.path.endswith("/capture"):
            server.calls.append(request)
            server.status = "COMPLETED"
            raise asyncio.CancelledError()
        return server(request)

    state = store.load(config, "MOCK")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            operate(
                store,
                config,
                "capture",
                client=FixtureClient(config, transport=httpx.MockTransport(handler)),
                authorization=CAPTURE_CONSENT,
                review_digest=state.review_digest(),
                accounts_confirmed=True,
            )
        )
    assert store.load(config, "MOCK").phase == "UNKNOWN_CAPTURE"
    assert (store.directory / "capture.attempt.json").exists()
    assert not (store.directory / "operation.lock").exists()
    with pytest.raises(Problem, match="NO_RETRY"):
        perform(fixture, "capture")


def test_existing_refund_blocks_independent_verification(fixture):
    approved(fixture)
    perform(fixture, "capture")
    store, config, server = fixture
    state = store.load(config, "MOCK")

    def add_refund(order):
        order["purchase_units"][0]["payments"]["refunds"] = [
            {
                "id": "1JU08902781691411",
                "status": "COMPLETED",
                "amount": {"value": "5.00", "currency_code": "NZD"},
            }
        ]
        return order

    server.change_order = add_refund
    client = SandboxPayPal(
        verification_settings(config, state), read_only=True, transport=httpx.MockTransport(server)
    )
    with pytest.raises(Problem, match="CAPTURE_NOT_ELIGIBLE"):
        asyncio.run(verify_capture(store, config, client=client))
    assert store.load(config, "MOCK").phase == "CAPTURED"
    assert not any("refund" in r.url.path for r in server.calls)


def test_claim_and_lock_survive_interrupted_state_and_concurrent_dispatch(fixture):
    store, config, server = fixture
    state = store.load(config, "MOCK")
    store.claim("create", state.create_request_id)  # Crash after marker, before JSON update/POST.
    with pytest.raises(Problem, match="NO_RETRY"):
        created(fixture)
    assert not any(r.url.path == "/v2/checkout/orders" for r in server.calls)
    with store.lock(), pytest.raises(Problem, match="BUSY_OR_INTERRUPTED"):
        created(fixture)
    assert not any(r.url.path == "/v2/checkout/orders" for r in server.calls)


def test_mock_real_or_changed_account_cannot_reuse_fixture(fixture):
    store, config, _ = fixture
    with pytest.raises(Problem, match="ACCOUNT_OR_SOURCE_CHANGED"):
        store.load(config, "REAL_SANDBOX")
    with pytest.raises(Problem, match="ACCOUNT_OR_SOURCE_CHANGED"):
        store.load(config.model_copy(update={"merchant_id": BUYER}), "MOCK")
    with pytest.raises(Problem, match="ACCOUNT_OR_SOURCE_CHANGED"):
        store.load(config.model_copy(update={"client_id": SecretStr("other-client")}), "MOCK")
    with pytest.raises(Problem, match="ALREADY_EXISTS"):
        store.prepare(config, source="MOCK")


@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", ORIGIN + f"/v2/payments/captures/{CAPTURE}/refund"),
        ("POST", "https://api-m.paypal.com/v2/checkout/orders"),
        ("POST", "http://api-m.sandbox.paypal.com/v2/checkout/orders"),
        ("POST", ORIGIN + "/v2/checkout/orders?x=1"),
        ("POST", ORIGIN + "/v2/checkout/orders#private"),
        ("POST", ORIGIN + f"/v2/checkout/orders/{ORDER}/authorize"),
        ("PATCH", ORIGIN + f"/v2/checkout/orders/{ORDER}"),
        ("GET", "https://www.sandbox.paypal.com/checkoutnow?token=" + ORDER),
    ],
)
def test_fixture_transport_forbids_refunds_live_origins_and_buyer_automation(method, url):
    async def scenario():
        calls = []
        transport = SandboxFixtureTransport(httpx.MockTransport(lambda r: calls.append(r)))
        with pytest.raises(Problem, match="FIXTURE_REQUEST_FORBIDDEN"):
            await transport.handle_async_request(httpx.Request(method, url))
        assert calls == []
        await transport.aclose()

    asyncio.run(scenario())


def test_original_readonly_transport_still_blocks_order_creation():
    async def scenario():
        transport = SandboxReadOnlyTransport(
            httpx.MockTransport(lambda r: pytest.fail("Dispatched"))
        )
        with pytest.raises(Problem, match="PREFLIGHT_REQUEST_FORBIDDEN"):
            await transport.handle_async_request(
                httpx.Request("POST", ORIGIN + "/v2/checkout/orders")
            )
        await transport.aclose()

    asyncio.run(scenario())


def test_normal_pytest_cannot_open_real_http(fixture):
    async def scenario():
        client = FixtureClient(fixture[1])
        try:
            with pytest.raises(AssertionError, match="Offline regression"):
                await client.auth.token()
        finally:
            await client.close()

    asyncio.run(scenario())


def test_allowlist_requires_verified_real_fixture_and_explicit_edit_consent(tmp_path):
    config = settings()
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(config)
    state.order_id, state.capture_id, state.phase = ORDER, CAPTURE, "VERIFIED"
    store.save(state)
    env = tmp_path / ".env"
    before = (
        "# Private test only\r\nPAYMENT_MODE=sandbox\r\nPAYPAL_ENVIRONMENT=sandbox\r\n"
        f"PAYPAL_BASE_URL={ORIGIN}\r\n"
        f"PAYPAL_CLIENT_ID=synthetic-fixture-client\r\nPAYPAL_CLIENT_SECRET=synthetic-fixture-secret\r\n"
        f"PAYPAL_MERCHANT_ID={MERCHANT}\r\nPAYPAL_CAPTURE_IDS=\r\nUNRELATED=value\r\n"
    ).encode()
    env.write_bytes(before)
    with pytest.raises(Problem, match="ALLOWLIST_AUTHORIZATION_REQUIRED"):
        configure_allowlist(store, config, None, env_path=env)
    assert env.read_bytes() == before
    configure_allowlist(store, config, ALLOWLIST_CONSENT, env_path=env)
    assert env.read_bytes() == before.replace(
        b"PAYPAL_CAPTURE_IDS=", b"PAYPAL_CAPTURE_IDS=" + CAPTURE.encode()
    )
    configure_allowlist(store, config, ALLOWLIST_CONSENT, env_path=env)
    assert env.read_bytes().count(CAPTURE.encode()) == 1
    state.phase = "CAPTURED"
    store.save(state)
    with pytest.raises(Problem, match="VERIFIED_CAPTURE_REQUIRED"):
        configure_allowlist(store, config, ALLOWLIST_CONSENT, env_path=env)


def test_fixture_settings_no_capture_or_ai_required_but_live_forbidden(monkeypatch):
    for key in tuple(__import__("os").environ):
        if key.startswith(("PAYPAL_", "LLM_")) or key in {"PAYMENT_MODE", "MAX_REFUND"}:
            monkeypatch.delenv(key)
    for key, value in {
        "PAYMENT_MODE": "sandbox",
        "PAYPAL_CLIENT_ID": "synthetic-fixture-client",
        "PAYPAL_CLIENT_SECRET": "synthetic-fixture-secret",
        "PAYPAL_MERCHANT_ID": MERCHANT,
        "PAYPAL_CAPTURE_IDS": "",
    }.items():
        monkeypatch.setenv(key, value)
    assert FixtureSettings.from_env().merchant_id == MERCHANT
    monkeypatch.setenv("PAYPAL_BASE_URL", "https://api-m.paypal.com")
    with pytest.raises(ValidationError):
        FixtureSettings.from_env()


def test_summary_does_not_publish_private_account_or_payment_identifiers(fixture):
    store, config, _ = fixture
    state = store.load(config, "MOCK")
    state.order_id, state.capture_id = ORDER, CAPTURE
    output = json.dumps(summary(state))
    assert all(
        value not in output
        for value in (ORDER, CAPTURE, MERCHANT, config.client_id.get_secret_value())
    )
    assert Path(".env").name not in output
