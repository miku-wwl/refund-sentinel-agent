"""Consumer-specific one-POST pilot audit, additional to public Runtime claiming."""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import httpx
from agentic_intent_gate.runtime import AttemptContext

from .models import Problem
from .paypal import identifier, refund_budget_checkpoint


def durable_json(path, data, *, exclusive=False):
    with path.open("xb" if exclusive else "wb") as file:
        file.write((json.dumps(data, indent=2) + "\n").encode("utf-8"))
        file.flush()
        os.fsync(file.fileno())


@dataclass(frozen=True)
class PilotRequest:
    action_id: str
    effect_key: str
    capture_id: str
    order_id: str
    amount: str
    currency: str

    def __post_init__(self):
        for value in (self.action_id, self.effect_key):
            if str(UUID(value, version=4)) != value:
                raise Problem("PILOT_IDENTITY_INVALID")
        identifier(self.capture_id)
        identifier(self.order_id)
        if self.amount != "5.00" or self.currency != "NZD":
            raise Problem("PILOT_EXACT_AMOUNT_REQUIRED")


async def retain_attempt_context(request):
    if "refund_attempt_context" in request.extensions:
        request.extensions["sentinel_pilot_context"] = request.extensions["refund_attempt_context"]


class PilotAuditTransport(httpx.AsyncBaseTransport):
    def __init__(self, directory, request, *, inner=None):
        self.directory, self.request = directory, request
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)
        self.is_mock = isinstance(inner, httpx.MockTransport)
        self.posts, self.events, self.refund_id = 0, [], None
        self.enabled, self.phase = False, "preflight"
        self.marker = directory / "refund-post.transport-attempt.json"

    async def observe_response(self, response):
        if response.request.url.path == f"/v2/payments/captures/{self.request.capture_id}/refund":
            await response.aread()
            if len(response.content) <= 262144:
                try:
                    self.refund_id = identifier(response.json()["id"])
                except (ValueError, KeyError, TypeError, Problem):
                    pass

    async def handle_async_request(self, request):
        context = request.extensions.pop("sentinel_pilot_context", None)
        url, approved = request.url, self.request
        if (
            url.scheme != "https"
            or url.host != "api-m.sandbox.paypal.com"
            or url.port not in {None, 443}
            or url.userinfo
            or url.query
            or url.fragment
        ):
            raise Problem("PILOT_ORIGIN_REJECTED")
        path = url.path
        if request.method == "POST" and path == "/v1/oauth2/token":
            operation = "oauth"
        elif request.method == "GET" and path == f"/v2/payments/captures/{approved.capture_id}":
            operation = "capture_get"
        elif request.method == "GET" and path == f"/v2/checkout/orders/{approved.order_id}":
            operation = "order_get"
        elif (
            request.method == "GET"
            and self.refund_id
            and path == f"/v2/payments/refunds/{self.refund_id}"
            and self.posts == 1
        ):
            operation = "refund_get"
        elif (
            request.method == "POST"
            and path == f"/v2/payments/captures/{approved.capture_id}/refund"
        ):
            if not self.enabled or self.phase != "execution" or type(context) is not AttemptContext:
                raise Problem("PILOT_FINANCIAL_NOT_ENABLED")
            if self.posts or self.marker.exists():
                raise Problem("PILOT_ONE_POST_ALREADY_ATTEMPTED")
            if (
                request.headers.get("PayPal-Request-Id") != approved.effect_key
                or request.headers.get("Prefer") != "return=representation"
                or json.loads(request.content)
                != {"amount": {"value": approved.amount, "currency_code": approved.currency}}
            ):
                raise Problem("PILOT_EXACT_REQUEST_MISMATCH")
            await refund_budget_checkpoint(context)
            durable_json(
                self.marker,
                {
                    "action_id": approved.action_id,
                    "effect_key": approved.effect_key,
                    "attempt_id": context.attempt_id,
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "meaning": "Exclusive dispatch reservation, not proof of provider receipt",
                },
                exclusive=True,
            )
            await refund_budget_checkpoint(context)
            self.posts += 1
            operation = "refund_post"
        else:
            raise Problem("PILOT_EXTRA_OPERATION_REJECTED")
        row = {"phase": self.phase, "operation": operation, "http_status": None}
        self.events.append(row)
        start = time.perf_counter()
        try:
            response = await self.inner.handle_async_request(request)
            row["http_status"] = response.status_code
            return response
        except asyncio.CancelledError:
            row["exception_type"] = "CancelledError"
            raise
        except httpx.HTTPError as exc:
            row["exception_type"] = (
                type(exc).__name__
                if type(exc)
                in {
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                    httpx.ConnectError,
                    httpx.ReadError,
                    httpx.WriteError,
                    httpx.RemoteProtocolError,
                }
                else "HTTPError"
            )
            raise
        finally:
            row["header_seconds"] = round(time.perf_counter() - start, 6)
            durable_json(
                self.directory / "transport-evidence.json",
                {"posts": self.posts, "requests": self.events},
            )

    async def aclose(self):
        await self.inner.aclose()
