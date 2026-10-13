"""Run outside the checkout: installed consumer wheel + installed public Runtime, mocks only."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx
from agentic_intent_gate.runtime import (
    ActionCommand,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
)
from pydantic import SecretStr

import refund_sentinel
from refund_sentinel.config import Settings
from refund_sentinel.integration import composition, provision, verify_distribution
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.profiles import LEGACY_PROFILE, SANDBOX_15_PROFILE
from refund_sentinel.service import Sentinel

CAPTURE, ORDER, REFUND, MERCHANT = "1" * 17, "2" * 17, "3" * 17, "S" * 13


async def qualify(profile):
    settings = Settings(
        payment_mode="sandbox",
        capture_ids=(CAPTURE,),
        merchant_id=MERCHANT,
        client_id=SecretStr("synthetic-client"),
        client_secret=SecretStr("synthetic-secret"),
    )
    posts = 0
    capture = {
        "id": CAPTURE,
        "status": "COMPLETED",
        "amount": {"value": "20.00", "currency_code": "NZD"},
        "payee": {"merchant_id": MERCHANT},
        "supplementary_data": {"related_ids": {"order_id": ORDER}},
    }
    refund = {
        "id": REFUND,
        "status": "COMPLETED",
        "amount": {"value": "5.00", "currency_code": "NZD"},
        "links": [
            {
                "rel": "up",
                "method": "GET",
                "href": f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}",
            }
        ],
    }

    def handle(request):
        nonlocal posts
        path = request.url.path
        if path == "/v1/oauth2/token":
            data = {"access_token": "synthetic-token", "token_type": "Bearer", "expires_in": 300}
        elif path == f"/v2/payments/captures/{CAPTURE}":
            data = capture
        elif path == f"/v2/checkout/orders/{ORDER}":
            data = {
                "id": ORDER,
                "status": "COMPLETED",
                "purchase_units": [
                    {"payee": {"merchant_id": MERCHANT}, "payments": {"captures": [capture]}}
                ],
            }
        elif path == f"/v2/payments/captures/{CAPTURE}/refund":
            posts += 1
            assert posts == 1 and request.headers["PayPal-Request-Id"] == action.effect_key
            data = refund
        else:
            assert path == f"/v2/payments/refunds/{REFUND}" and request.method == "GET"
            data = refund
        return httpx.Response(201 if path.endswith("/refund") else 200, json=data)

    with tempfile.TemporaryDirectory(prefix="wheel-profile-") as temporary:
        state = Path(temporary)
        provision(state, settings, profile=profile)
        client = SandboxPayPal(
            settings, transport=httpx.MockTransport(handle), http_timeout=profile.http_timeout()
        )
        with composition(state, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime, store, _, model, executor = resources
            service = Sentinel(runtime, store, client, model, settings)
            item = await service.analyze(
                RequestInput(
                    capture_id=CAPTURE, message="Synthetic damaged item partial refund NZD 5.00"
                )
            )
            principal = runtime.verifier.verify(
                "Bearer " + (state / "operator.capability").read_text("ascii")
            )
            approved = runtime.run_service.decide(
                item["run"]["run_id"], ApprovalDecisionRequest(ApprovalChoice.APPROVE, 4)
            )
            action = runtime.gateway.admit(
                AdmissionCommand(approved.run_id, 5, principal.subject_id, str(uuid4())), principal
            ).action
            action = runtime.gateway.authorize(
                ActionCommand(action.action_id, 1, str(uuid4())), principal
            ).action
            command = ActionCommand(action.action_id, 2, str(uuid4()))
            result = await runtime.gateway.execute(command, principal)
            assert result.action.state.value == "Succeeded" and posts == 1
            assert runtime.gateway.tool_timeout_seconds == profile.seconds
            receipt = result.action.snapshot()["result"]["receipt_reference"]
            assert any(
                row["id"] == receipt and row["data"]["phase"] == "VERIFIED_REFUND"
                for row in store.observations(action.effect_key)
            )
        with composition(state, settings, paypal=client, predecessor_stopped=True) as resources:
            runtime = resources[0]
            principal = runtime.verifier.verify(
                "Bearer " + (state / "operator.capability").read_text("ascii")
            )
            assert (await runtime.gateway.execute(command, principal)).replayed and posts == 1
        await client.close()
        return {
            "profile": profile.name,
            "budget": profile.seconds,
            "binding_revision": executor.binding.binding_revision,
            "state": "Succeeded",
            "mock_posts": posts,
            "durable_receipt": True,
            "restart_duplicate_posts": 0,
        }


async def main():
    package = Path(refund_sentinel.__file__).resolve()
    expected = Path(sys.argv[1]).resolve()
    assert package.is_relative_to(expected)
    rows = [await qualify(profile) for profile in (LEGACY_PROFILE, SANDBOX_15_PROFILE)]
    print(
        json.dumps(
            {
                "source": "INSTALLED_WHEEL_OFFLINE",
                "runtime": verify_distribution(),
                "consumer_import": str(package),
                "profiles": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    with asyncio.Runner() as runner:

        def deny_network(event, args):
            if event == "socket.connect":
                raise RuntimeError("OUTSIDE_WHEEL_NETWORK_FORBIDDEN")

        sys.addaudithook(deny_network)
        runner.run(main())
