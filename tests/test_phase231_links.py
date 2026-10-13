"""Strict Sandbox response-link contracts; every identifier here is synthetic."""

from copy import deepcopy
from uuid import uuid4

import pytest
from test_providers import CAPTURE, ORDER, REFUND, refund_data

from refund_sentinel.models import RefundInput
from refund_sentinel.paypal import ProviderError, verified_refund, verify_links


def arguments():
    return RefundInput(incident_id=str(uuid4()), capture_id=CAPTURE, amount="25.00", currency="USD")


@pytest.mark.parametrize("host", ["api-m.sandbox.paypal.com", "api.sandbox.paypal.com"])
@pytest.mark.parametrize("port", ["", ":443"])
def test_refund_sandbox_aliases_keep_exact_self_and_capture_identity(host, port):
    data = refund_data()
    origin = f"https://{host}{port}"
    data["links"] = [
        {"rel": "self", "method": "GET", "href": f"{origin}/v2/payments/refunds/{REFUND}"},
        {"rel": "up", "method": "GET", "href": f"{origin}/v2/payments/captures/{CAPTURE}"},
    ]
    assert verified_refund(data, arguments(), expected_id=REFUND)["provider_status"] == "COMPLETED"


BAD_URLS = [
    f"http://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
    f"//api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://api.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://api-m.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com.evil.test/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com@evil.test/v2/payments/captures/{CAPTURE}",
    f"https://evil.test@api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://user:password@api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com:444/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com:443.evil/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com:65536/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com:/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com./v2/payments/captures/{CAPTURE}",
    f"https://API.SANDBOX.PAYPAL.COM/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbоx.paypal.com/v2/payments/captures/{CAPTURE}",  # Cyrillic o.
    f"https://api.sandbox.paypal.com/v2/payments/captures/{ORDER}",
    f"https://api.sandbox.paypal.com/v2/payments/refunds/{CAPTURE}",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}/refund",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}/",
    f"https://api.sandbox.paypal.com/v2/payments/captures/../captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com/v2/payments/captures/%37{CAPTURE[1:]}",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}?",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}?x=1",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}#",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}#fragment",
    f" https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}\n",
    f"https://api.sandbox.paypal.com/v2/payments/captures/{CAPTURE}\x00",
    f"https://api.sandbox.paypal.com\\evil.test/v2/payments/captures/{CAPTURE}",
    f"https://[api.sandbox.paypal.com]/v2/payments/captures/{CAPTURE}",
    "/v2/payments/captures/" + CAPTURE,
    123,
    None,
]


@pytest.mark.parametrize("href", BAD_URLS)
def test_bad_refund_relationship_urls_fail_closed(href):
    data = refund_data()
    data["links"][0]["href"] = href
    with pytest.raises(ProviderError, match="REFUND_VERIFICATION_MISMATCH"):
        verified_refund(data, arguments(), expected_id=REFUND)


@pytest.mark.parametrize(
    "change",
    ["method", "relation", "missing", "not_list", "invalid_item", "duplicate", "bad_self", "id"],
)
def test_refund_link_shape_and_conflicting_identity_fail_closed(change):
    data = refund_data()
    if change == "method":
        data["links"][0]["method"] = "POST"
    elif change == "relation":
        data["links"][0]["rel"] = "self"
    elif change == "missing":
        data.pop("links")
    elif change == "not_list":
        data["links"] = {}
    elif change == "invalid_item":
        data["links"] = [None]
    elif change == "duplicate":
        data["links"].append(deepcopy(data["links"][0]))
    elif change == "id":
        data["id"] = ORDER
    else:
        data["links"].append(
            {
                "rel": "self",
                "method": "GET",
                "href": f"https://api.sandbox.paypal.com/v2/payments/refunds/{ORDER}",
            }
        )
    with pytest.raises(ProviderError, match="REFUND_VERIFICATION_MISMATCH"):
        verified_refund(data, arguments(), expected_id=REFUND)


@pytest.mark.parametrize("host", ["api-m.sandbox.paypal.com", "api.sandbox.paypal.com"])
def test_capture_links_use_the_same_bounded_metadata_policy(host):
    path = f"/v2/payments/captures/{CAPTURE}"
    data = {
        "links": [
            {"rel": "self", "method": "GET", "href": f"https://{host}:443{path}"},
            {"rel": "refund", "method": "POST", "href": f"https://{host}{path}/refund"},
        ]
    }
    assert verify_links(data, path, refund_path=path + "/refund")
    data["links"][1]["method"] = "GET"
    with pytest.raises(ValueError):
        verify_links(data, path, refund_path=path + "/refund")
