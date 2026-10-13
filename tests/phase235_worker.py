"""Process restart fixture: hard network denial, synthetic HTTP only."""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import httpx
from agentic_intent_gate.runtime import ActionCommand
from pydantic import SecretStr

from refund_sentinel.config import SANDBOX_URL, Settings
from refund_sentinel.integration import composition
from refund_sentinel.paypal import SandboxPayPal
from refund_sentinel.profiles import SANDBOX_15_PROFILE


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("SYNTHETIC_WORKER_NETWORK_FORBIDDEN")


directory = Path(sys.argv[1])
data = json.loads((directory / "worker.json").read_text("utf-8"))
settings = Settings(
    payment_mode="sandbox",
    merchant_id="YXZY75W2GKDQE",
    capture_ids=("74L756601X447022Y",),
    client_id=SecretStr("synthetic-client"),
    client_secret=SecretStr("synthetic-secret"),
)
capture = {
    "id": "74L756601X447022Y",
    "status": "COMPLETED",
    "amount": {"value": "20.00", "currency_code": "NZD"},
    "payee": {"merchant_id": settings.merchant_id},
    "supplementary_data": {"related_ids": {"order_id": "25M43554V9523650M"}},
}
order = {
    "id": "25M43554V9523650M",
    "status": "COMPLETED",
    "intent": "CAPTURE",
    "purchase_units": [
        {
            "payee": capture["payee"],
            "amount": capture["amount"],
            "payments": {"captures": [capture]},
        }
    ],
}
refund = {
    "id": "1JU08902781691411",
    "status": "COMPLETED",
    "amount": {"value": "5.00", "currency_code": "NZD"},
    "links": [
        {
            "rel": "up",
            "method": "GET",
            "href": SANDBOX_URL + "/v2/payments/captures/" + capture["id"],
        }
    ],
}


async def handle(request):
    with sqlite3.connect(directory / "process-provider.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS calls(method TEXT,path TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS effects(request_id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO calls VALUES (?,?)", (request.method, request.url.path))
        if request.url.path.endswith("/refund"):
            db.execute("INSERT INTO effects VALUES (?)", (request.headers["PayPal-Request-Id"],))
    if request.url.path.endswith("/token"):
        return httpx.Response(
            200, json={"access_token": "synthetic-token", "token_type": "Bearer", "expires_in": 300}
        )
    if "/captures/" in request.url.path and request.method == "GET":
        return httpx.Response(200, json=capture)
    if "/orders/" in request.url.path:
        return httpx.Response(200, json=order)
    if request.method == "POST" and data["lose_ack"]:
        raise httpx.ReadTimeout("Synthetic committed effect acknowledgment lost", request=request)
    return httpx.Response(201 if request.method == "POST" else 200, json=refund)


async def main():
    client = SandboxPayPal(
        settings,
        transport=httpx.MockTransport(handle),
        http_timeout=SANDBOX_15_PROFILE.http_timeout(),
    )
    with composition(directory, settings, paypal=client, predecessor_stopped=True) as resources:
        runtime = resources[0]
        principal = runtime.verifier.verify(
            "Bearer " + (directory / "operator.capability").read_text("ascii")
        )
        result = await runtime.gateway.execute(ActionCommand(**data["command"]), principal)
        with sqlite3.connect(directory / "process-provider.sqlite3") as db:
            count = db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
            posts = db.execute(
                "SELECT COUNT(*) FROM calls WHERE method='POST' AND path LIKE '%/refund'"
            ).fetchone()[0]
        print(
            json.dumps(
                {
                    "state": result.action.state.value,
                    "version": result.action.version,
                    "replayed": result.replayed,
                    "effects": count,
                    "posts": posts,
                    "budget": runtime.gateway.tool_timeout_seconds,
                }
            ),
            flush=True,
        )
    await client.close()


with asyncio.Runner() as runner:
    # Windows creates its internal socketpair while initializing the event loop.
    # Install the fence afterwards, before any provider/client execution.
    sys.addaudithook(deny_network)
    runner.run(main())
