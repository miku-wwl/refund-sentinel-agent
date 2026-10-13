"""Sanitized genuine pre-approval GET shape; every request below uses MockTransport."""

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from test_fixture import CAPTURE, MERCHANT, ORDER, settings

from refund_sentinel.fixture import (
    FixtureState,
    FixtureStore,
    approval_link,
    validate_order,
)
from refund_sentinel.models import Problem
from refund_sentinel.paypal import SandboxPayPal, SandboxReadOnlyTransport, verify_links

REFERENCE = "11111111-1111-4111-8111-111111111111"


def observed_order():
    # All keys/list structure retained; IDs/reference/time substituted, no real account values.
    return json.loads(
        (
            Path(__file__).parent / "fixtures/paypal-order-payer-action-required.sanitized.json"
        ).read_text("utf-8")
    )


def expected_state():
    return FixtureState(
        source="MOCK",
        merchant_id=MERCHANT,
        client_fingerprint="0" * 64,
        create_request_id=REFERENCE,
        capture_request_id="22222222-2222-4222-8222-222222222222",
        phase="UNKNOWN_CREATE",
        order_id=ORDER,
    )


@pytest.mark.parametrize(
    "origin", ["https://api.sandbox.paypal.com", "https://api-m.sandbox.paypal.com"]
)
def test_genuine_payer_action_required_structure_validates_both_documented_self_origins(origin):
    data = observed_order()
    state = expected_state()
    data["links"][0]["href"] = origin + f"/v2/checkout/orders/{ORDER}"
    original = copy.deepcopy(data)
    state_before = state.model_dump_json()
    assert validate_order(data, state) == "PAYER_ACTION_REQUIRED"
    assert approval_link(data, ORDER) == f"https://www.sandbox.paypal.com/checkoutnow?token={ORDER}"
    assert data == original and state.model_dump_json() == state_before
    assert state.phase == "UNKNOWN_CREATE" and state.capture_id is None
    assert data["payment_source"] == {"paypal": {}}  # Buyer absent before checkout is legitimate.


@pytest.mark.parametrize(
    "href",
    [
        f"https://api-m.paypal.com/v2/checkout/orders/{ORDER}",
        f"https://api.paypal.com/v2/checkout/orders/{ORDER}",
        f"http://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}",
        f"https://api.sandbox.paypal.com.evil.test/v2/checkout/orders/{ORDER}",
        f"https://user@api.sandbox.paypal.com/v2/checkout/orders/{ORDER}",
        f"https://api.sandbox.paypal.com@evil.test/v2/checkout/orders/{ORDER}",
        f"https://api.sandbox.paypal.com:444/v2/checkout/orders/{ORDER}",
        f"https://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}?extra=1",
        f"https://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}#fragment",
        f"https://api.sandbox.paypal.com/v2/checkout/orders/{CAPTURE}",
        f"https://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}/capture",
        f"https://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}/",
        f"https://api.sandbox.paypal.com/v2/checkout%2Forders/{ORDER}",
        None,
        [],
        {},
    ],
)
def test_response_alias_does_not_relax_resource_origin_path_identity_or_url_shape(href):
    data = observed_order()
    data["links"][0]["href"] = href
    with pytest.raises(Problem, match="FIXTURE_ORDER_RESOURCE_LINK_INVALID"):
        validate_order(data, expected_state())


def test_self_method_must_still_be_get():
    data = observed_order()
    data["links"][0]["method"] = "POST"
    with pytest.raises(Problem, match="FIXTURE_ORDER_RESOURCE_LINK_INVALID"):
        validate_order(data, expected_state())


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda d: d.update(id=CAPTURE), "ORDER_EVIDENCE_INVALID"),
        (lambda d: d.update(intent="AUTHORIZE"), "ORDER_EVIDENCE_INVALID"),
        (lambda d: d.pop("intent"), "ORDER_EVIDENCE_INVALID"),
        (lambda d: d.update(status="UNKNOWN_STATUS"), "ORDER_EVIDENCE_INVALID"),
        (lambda d: d["purchase_units"].clear(), "ORDER_EVIDENCE_INVALID"),
        (
            lambda d: d["purchase_units"].append(copy.deepcopy(d["purchase_units"][0])),
            "ORDER_EVIDENCE_INVALID",
        ),
        (
            lambda d: d["purchase_units"][0].update(reference_id="different-reference"),
            "ORDER_EVIDENCE_INVALID",
        ),
        (
            lambda d: d["purchase_units"][0]["payee"].update(merchant_id="BBBBBBBBBBBBB"),
            "MERCHANT_MISMATCH",
        ),
        (lambda d: d["purchase_units"][0]["payee"].pop("merchant_id"), "ORDER_EVIDENCE_INVALID"),
        (
            lambda d: d["purchase_units"][0]["amount"].update(value="19.00"),
            "AMOUNT_OR_CURRENCY_MISMATCH",
        ),
        (
            lambda d: d["purchase_units"][0]["amount"].update(currency_code="USD"),
            "AMOUNT_OR_CURRENCY_MISMATCH",
        ),
        (lambda d: d["purchase_units"][0]["amount"].update(value=20.00), "ORDER_EVIDENCE_INVALID"),
        (
            lambda d: d["purchase_units"][0]["amount"].update(value="20.001"),
            "ORDER_EVIDENCE_INVALID",
        ),
    ],
)
def test_alias_acceptance_preserves_all_identity_amount_intent_and_unit_checks(mutation, code):
    data = observed_order()
    mutation(data)
    with pytest.raises(Problem, match=code):
        validate_order(data, expected_state())


def test_payer_action_required_is_not_buyer_approval_or_capture_authorization():
    with pytest.raises(Problem, match="FIXTURE_BUYER_APPROVAL_REQUIRED"):
        validate_order(observed_order(), expected_state(), approved=True)


@pytest.mark.parametrize(
    "origin", ["https://api.sandbox.paypal.com", "https://api-m.sandbox.paypal.com"]
)
def test_capture_resource_metadata_alias_keeps_exact_refund_resource_and_method(origin):
    path = f"/v2/payments/captures/{CAPTURE}"
    data = {
        "links": [
            {"rel": "self", "method": "GET", "href": origin + path},
            {"rel": "refund", "method": "POST", "href": origin + path + "/refund"},
        ]
    }
    assert verify_links(data, path, refund_path=path + "/refund")
    data["links"][1]["href"] = origin + f"/v2/payments/captures/{ORDER}/refund"
    with pytest.raises(ValueError, match="Refund link mismatch"):
        verify_links(data, path, refund_path=path + "/refund")
    data["links"][1]["href"] = origin + path + "/refund"
    data["links"][1]["method"] = "GET"
    with pytest.raises(ValueError, match="Refund link mismatch"):
        verify_links(data, path, refund_path=path + "/refund")


def test_metadata_alias_never_becomes_an_allowed_network_destination():
    async def scenario():
        calls = []
        transport = SandboxReadOnlyTransport(
            httpx.MockTransport(lambda request: calls.append(request))
        )
        with pytest.raises(Problem, match="PAYPAL_PREFLIGHT_REQUEST_FORBIDDEN"):
            await transport.handle_async_request(
                httpx.Request(
                    "GET",
                    f"https://api.sandbox.paypal.com/v2/checkout/orders/{ORDER}",
                )
            )
        assert calls == []
        await transport.aclose()

    asyncio.run(scenario())


def test_mock_readonly_query_with_legacy_metadata_uses_fixed_host_and_preserves_fixture_bytes(
    tmp_path,
):
    async def scenario():
        config = settings()
        store = FixtureStore(tmp_path / ".state-fixture")
        state = store.prepare(config, source="MOCK")
        state.order_id, state.create_request_id, state.phase = ORDER, REFERENCE, "UNKNOWN_CREATE"
        store.save(state)
        before = {p.name: p.read_bytes() for p in store.directory.iterdir()}
        calls = []

        def handler(request):
            calls.append((request.method, request.url.host, request.url.path))
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 300,
                    },
                )
            assert request.method == "GET" and request.url.path == f"/v2/checkout/orders/{ORDER}"
            return httpx.Response(200, json=observed_order())

        client = SandboxPayPal(config, read_only=True, transport=httpx.MockTransport(handler))
        try:
            data = await client._request("GET", f"/v2/checkout/orders/{ORDER}")
            assert validate_order(data, state) == "PAYER_ACTION_REQUIRED"
        finally:
            await client.close()
        assert calls == [
            ("POST", "api-m.sandbox.paypal.com", "/v1/oauth2/token"),
            ("GET", "api-m.sandbox.paypal.com", f"/v2/checkout/orders/{ORDER}"),
        ]
        assert {p.name: p.read_bytes() for p in store.directory.iterdir()} == before

    asyncio.run(scenario())
