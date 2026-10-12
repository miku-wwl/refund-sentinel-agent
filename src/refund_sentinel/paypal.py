import asyncio
import json
import re
import sqlite3
import time
from contextlib import closing
from copy import deepcopy
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import httpx
from pydantic import TypeAdapter

from .config import SANDBOX_URL
from .models import CaptureFacts, Money, Problem


class ProviderError(Problem):
    def __init__(self, code, *, no_effect=False):
        super().__init__(code, 502)
        self.no_effect = no_effect


EXECUTION_HTTP_TIMEOUT_SECONDS = 1.1
PREFLIGHT_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


class SandboxReadOnlyTransport(httpx.AsyncBaseTransport):
    """Preflight network boundary: allow OAuth and bounded reads, never payment mutations."""

    def __init__(self, inner=None):
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request):
        url = request.url
        safe_origin = (
            url.scheme == "https"
            and url.host == "api-m.sandbox.paypal.com"
            and url.port in {None, 443}
            and not url.userinfo
            and not url.query
        )
        safe_oauth = request.method == "POST" and url.path == "/v1/oauth2/token"
        safe_get = request.method == "GET" and re.fullmatch(
            r"/v2/(?:payments/(?:captures|refunds)|checkout/orders)/[A-Z0-9]{17}", url.path
        )
        if not safe_origin or not (safe_oauth or safe_get):
            raise Problem("PAYPAL_PREFLIGHT_REQUEST_FORBIDDEN")
        return await self.inner.handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


class PayPalClient(Protocol):
    async def capture(self, capture_id: str) -> CaptureFacts: ...
    async def refund(
        self, capture_id: str, amount: str, currency: str, request_id: str
    ) -> dict: ...
    async def lookup_refund(self, refund_id: str) -> dict: ...
    async def close(self) -> None: ...


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9]{17}", value):
        raise ProviderError("INVALID_PROVIDER_IDENTIFIER", no_effect=True)
    return value


def provider_money(data):
    """Normalize documented provider string money without rounding or accepting float inputs."""
    value, currency = data["value"], data["currency_code"]
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,2})?", value)
        or not isinstance(currency, str)
        or not re.fullmatch(r"[A-Z]{3}", currency)
    ):
        raise ValueError("Invalid provider money")
    return f"{Decimal(value):.2f}", currency


def verify_links(data, resource_path, *, refund_path=None):
    """Validate relevant links when returned; never follow provider-selected URLs."""
    if "links" not in data:
        return False
    links = data["links"]
    if not isinstance(links, list) or len(links) > 32:
        raise ValueError("Invalid provider links")
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Invalid provider link")
        if link.get("rel") == "self" and (
            link.get("href") != SANDBOX_URL + resource_path or link.get("method") != "GET"
        ):
            raise ValueError("Resource link mismatch")
        if (
            refund_path
            and link.get("rel") == "refund"
            and (link.get("href") != SANDBOX_URL + refund_path or link.get("method") != "POST")
        ):
            raise ValueError("Refund link mismatch")
    return any(link.get("rel") == "self" for link in links)


class SandboxPayPal:
    def __init__(
        self,
        settings,
        *,
        transport=None,
        read_only=False,
        http_timeout=EXECUTION_HTTP_TIMEOUT_SECONDS,
    ):
        if settings.environment != "sandbox" or settings.paypal_base_url != SANDBOX_URL:
            raise Problem("LIVE_PAYPAL_FORBIDDEN")
        if (
            not settings.client_id.get_secret_value()
            or not settings.client_secret.get_secret_value()
        ):
            raise Problem("PAYPAL_CREDENTIALS_MISSING")
        self.settings = settings
        self.read_only = read_only
        self.source = "MOCK" if isinstance(transport, httpx.MockTransport) else "REAL_SANDBOX"
        self.telemetry = []
        self.token_cache_hits = 0
        self.capture_checks = {}
        self.http = httpx.AsyncClient(
            base_url=SANDBOX_URL,
            timeout=http_timeout,
            follow_redirects=False,
            trust_env=False,
            transport=SandboxReadOnlyTransport(transport) if read_only else transport,
        )
        self._token, self._until = None, 0
        self._auth_lock = asyncio.Lock()

    async def _roundtrip(self, method, path, **kwargs):
        start = time.perf_counter()
        response_status = None
        operation = (
            "oauth"
            if path == "/v1/oauth2/token"
            else "order_get"
            if path.startswith("/v2/checkout/orders/")
            else "refund_post"
            if path.endswith("/refund")
            else "refund_get"
            if path.startswith("/v2/payments/refunds/")
            else "capture_get"
        )
        try:
            response = await self.http.request(method, path, **kwargs)
            response_status = response.status_code
            return response
        finally:
            # No URLs, identifiers, headers, credential values or provider bodies in diagnostics.
            self.telemetry.append(
                {
                    "operation": operation,
                    "method": method,
                    "http_status": response_status,
                    "elapsed_seconds": round(time.perf_counter() - start, 6),
                }
            )

    async def token(self):
        async with self._auth_lock:
            if self._token and time.monotonic() < self._until:
                self.token_cache_hits += 1
                return self._token
            try:
                response = await self._roundtrip(
                    "POST",
                    "/v1/oauth2/token",
                    auth=(
                        self.settings.client_id.get_secret_value(),
                        self.settings.client_secret.get_secret_value(),
                    ),
                    data={"grant_type": "client_credentials"},
                )
                if response.status_code in {401, 403}:
                    raise ProviderError("PAYPAL_AUTH_CREDENTIALS_REJECTED", no_effect=True)
                if response.status_code != 200:
                    raise ProviderError("PAYPAL_AUTH_HTTP_REJECTED", no_effect=True)
                if len(response.content) > 65536:
                    raise ValueError()
                data = response.json()
                if type(data) is not dict or data.get("token_type", "").lower() != "bearer":
                    raise ValueError()
                token, expiry = data["access_token"], data["expires_in"]
                if (
                    not isinstance(token, str)
                    or len(token) > 16000
                    or not re.fullmatch(r"[A-Za-z0-9._~+/-]{1,16000}=*", token)
                    or type(expiry) is not int
                    or expiry <= 0
                ):
                    raise ValueError()
                self._token = token
                self._until = time.monotonic() + max(0, expiry - 30)
                return token
            except httpx.TimeoutException:
                raise ProviderError("PAYPAL_AUTH_TIMEOUT", no_effect=True) from None
            except httpx.ConnectError:
                raise ProviderError("PAYPAL_AUTH_CONNECTION_FAILED", no_effect=True) from None
            except httpx.HTTPError:
                raise ProviderError("PAYPAL_AUTH_TRANSPORT_ERROR", no_effect=True) from None
            except (ValueError, KeyError, TypeError, AttributeError):
                raise ProviderError("PAYPAL_AUTH_INVALID_RESPONSE", no_effect=True) from None

    async def _request(self, method, path, *, body=None, request_id=None):
        if self.read_only and method != "GET":
            raise Problem("PAYPAL_MUTATION_FORBIDDEN")
        headers = {"Authorization": "Bearer " + await self.token()}
        if request_id:
            try:
                valid_key = str(UUID(request_id)) == request_id
            except (ValueError, TypeError, AttributeError):
                valid_key = False
            if not valid_key:
                raise ProviderError("INVALID_REQUEST_ID", no_effect=True)
            headers |= {"PayPal-Request-Id": request_id, "Prefer": "return=representation"}
        try:
            response = await self._roundtrip(method, path, headers=headers, json=body)
        except httpx.HTTPError:
            raise ProviderError("PAYPAL_TRANSPORT_UNCERTAIN", no_effect=method == "GET") from None
        if response.status_code not in ({200, 201} if method == "POST" else {200}):
            # Only documented definitive rejection responses constitute no-effect evidence.
            ambiguous_previous_request = False
            try:
                error = response.json()
                issues = {item.get("issue") for item in error.get("details", [])}
                ambiguous_previous_request = error.get("name") == "DUPLICATE_REQUEST_ID" or bool(
                    issues & {"DUPLICATE_REQUEST_ID", "PREVIOUS_REQUEST_IN_PROGRESS"}
                )
            except (ValueError, TypeError, AttributeError):
                pass
            raise ProviderError(
                "PAYPAL_HTTP_" + str(response.status_code),
                no_effect=response.status_code in {400, 401, 403, 404, 422}
                and not ambiguous_previous_request,
            )
        try:
            if len(response.content) > 262144:
                raise ValueError()
            data = response.json()
            if type(data) is not dict:
                raise ValueError()
            return data
        except ValueError:
            raise ProviderError("PAYPAL_INVALID_RESPONSE", no_effect=method == "GET") from None

    async def capture(self, capture_id):
        identifier(capture_id)
        if capture_id not in self.settings.capture_ids:
            raise Problem("CAPTURE_NOT_ALLOWED")
        capture = await self._request("GET", f"/v2/payments/captures/{capture_id}")
        try:
            if capture["id"] != capture_id:
                raise ValueError()
            capture_links = verify_links(
                capture,
                f"/v2/payments/captures/{capture_id}",
                refund_path=f"/v2/payments/captures/{capture_id}/refund",
            )
            order_id = identifier(capture["supplementary_data"]["related_ids"]["order_id"])
            order = await self._request("GET", f"/v2/checkout/orders/{order_id}")
            if order["id"] != order_id or order["status"] != "COMPLETED":
                raise ValueError()
            order_links = verify_links(order, f"/v2/checkout/orders/{order_id}")
            units = [
                unit
                for unit in order["purchase_units"]
                if any(
                    c.get("id") == capture_id for c in unit.get("payments", {}).get("captures", [])
                )
            ]
            if len(units) != 1:
                raise ValueError()
            unit = units[0]
            matches = [c for c in unit["payments"]["captures"] if c["id"] == capture_id]
            amount, currency = provider_money(capture["amount"])
            if len(matches) != 1 or provider_money(matches[0]["amount"]) != (amount, currency):
                raise ValueError()
            if matches[0]["status"] != capture["status"]:
                raise ValueError()
            merchant = unit["payee"]["merchant_id"]
            if capture.get("payee", {}).get("merchant_id", merchant) != merchant:
                raise ValueError()
            refunds = unit["payments"].get("refunds", [])
            if not isinstance(refunds, list):
                raise ValueError()
            for refund in refunds:
                identifier(refund["id"])
                if (
                    refund["status"] not in {"COMPLETED", "PENDING", "FAILED", "CANCELLED"}
                    or provider_money(refund["amount"])[1] != currency
                ):
                    raise ValueError()
            self.capture_checks = {
                "capture_order_identity": "MATCH",
                "capture_order_amount_currency": "MATCH",
                "merchant_matches_configuration": merchant == self.settings.merchant_id,
                "capture_self_link_present": capture_links,
                "order_self_link_present": order_links,
                "previous_refunds": "REPORTED" if refunds else "NONE_REPORTED",
            }
            return CaptureFacts(
                capture_id=capture_id,
                order_id=order_id,
                merchant_id=merchant,
                amount=amount,
                currency=currency,
                status=capture["status"],
                prior_refunds=bool(refunds),
                source="paypal-sandbox",
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderError("INSUFFICIENT_CAPTURE_EVIDENCE", no_effect=True) from None

    async def refund(self, capture_id, amount, currency, request_id):
        if self.read_only:
            raise Problem("PAYPAL_MUTATION_FORBIDDEN")
        identifier(capture_id)
        if capture_id not in self.settings.capture_ids:
            raise Problem("CAPTURE_NOT_ALLOWED")
        try:
            TypeAdapter(Money).validate_python(amount, strict=True)
            if (
                currency not in {"USD", "NZD"}
                or not (Decimal("0") < Decimal(amount) <= Decimal(self.settings.max_refund))
                or not request_id
            ):
                raise ValueError()
        except (ValueError, TypeError):
            raise ProviderError("INVALID_REFUND_INPUT", no_effect=True) from None
        # Endpoint never receives a full-refund empty body, credentials, or model-selected URL.
        return await self._request(
            "POST",
            f"/v2/payments/captures/{capture_id}/refund",
            body={"amount": {"value": amount, "currency_code": currency}},
            request_id=request_id,
        )

    async def lookup_refund(self, refund_id):
        return await self._request("GET", f"/v2/payments/refunds/{identifier(refund_id)}")

    async def close(self):
        await self.http.aclose()
        self._token = None


class FakePayPal:
    """Persisted simulated remote service, including real attempted-call records for tests."""

    def __init__(self, path, *, behavior="COMPLETED", delay=0):
        self.path, self.behavior, self.delay = path, behavior, delay

    @staticmethod
    def provision(path, settings):
        with closing(sqlite3.connect(path)) as db:
            db.executescript("""
                CREATE TABLE captures (id TEXT PRIMARY KEY, data TEXT NOT NULL) STRICT;
                CREATE TABLE calls (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                    capture_id TEXT NOT NULL, amount TEXT NOT NULL, currency TEXT NOT NULL) STRICT;
                CREATE TABLE refunds (request_id TEXT PRIMARY KEY, data TEXT NOT NULL) STRICT;
            """)
            for capture_id in settings.capture_ids:
                facts = CaptureFacts(
                    capture_id=capture_id,
                    order_id="DEMOORDER00000001",
                    merchant_id=settings.merchant_id,
                    amount="120.00",
                    currency="USD",
                    status="COMPLETED",
                    prior_refunds=False,
                    source="fake",
                )
                db.execute(
                    "INSERT INTO captures VALUES (?,?)", (capture_id, facts.model_dump_json())
                )
            db.commit()

    async def capture(self, capture_id):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT data FROM captures WHERE id=?", (capture_id,)).fetchone()
        if row is None:
            raise ProviderError("FAKE_CAPTURE_NOT_FOUND", no_effect=True)
        return CaptureFacts.model_validate_json(row[0])

    async def refund(self, capture_id, amount, currency, request_id):
        if self.delay:
            await asyncio.sleep(self.delay)
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO calls(request_id,capture_id,amount,currency) VALUES (?,?,?,?)",
                (request_id, capture_id, amount, currency),
            )
            row = db.execute(
                "SELECT data FROM refunds WHERE request_id=?", (request_id,)
            ).fetchone()
            if row:
                refund = json.loads(row[0])
                if refund["amount"] != {"value": amount, "currency_code": currency}:
                    db.commit()
                    raise ProviderError("FAKE_PAYLOAD_CONFLICT", no_effect=True)
            elif self.behavior == "REJECT":
                db.commit()
                raise ProviderError("PAYPAL_HTTP_422", no_effect=True)
            else:
                refund = {
                    "id": uuid4().hex[:17].upper(),
                    "status": (
                        "COMPLETED" if self.behavior == "TIMEOUT_AFTER_EFFECT" else self.behavior
                    ),
                    "amount": {"value": amount, "currency_code": currency},
                    "links": [
                        {
                            "rel": "up",
                            "href": f"{SANDBOX_URL}/v2/payments/captures/{capture_id}",
                            "method": "GET",
                        }
                    ],
                }
                db.execute("INSERT INTO refunds VALUES (?,?)", (request_id, json.dumps(refund)))
                facts = json.loads(
                    db.execute("SELECT data FROM captures WHERE id=?", (capture_id,)).fetchone()[0]
                )
                facts["prior_refunds"] = True
                facts["status"] = "PARTIALLY_REFUNDED"
                db.execute("UPDATE captures SET data=? WHERE id=?", (json.dumps(facts), capture_id))
            db.commit()
        if self.behavior == "TIMEOUT_AFTER_EFFECT":
            raise ProviderError("PAYPAL_TRANSPORT_UNCERTAIN")
        return deepcopy(refund)

    async def lookup_refund(self, refund_id):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute("SELECT data FROM refunds").fetchall()
        for row in rows:
            refund = json.loads(row[0])
            if refund["id"] == refund_id:
                return refund
        raise ProviderError("FAKE_REFUND_NOT_FOUND", no_effect=True)

    def recorded_calls(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM calls")]

    def persisted_refunds(self):
        with closing(sqlite3.connect(self.path)) as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM refunds")]

    async def close(self):
        pass


def verified_refund(data, args, *, expected_id=None):
    """Validate identity, exact Decimal amount/currency and capture relationship after GET."""
    try:
        refund_id = identifier(data["id"])
        value, currency = provider_money(data["amount"])
        if expected_id and refund_id != expected_id:
            raise ValueError()
        if (
            Decimal(value) != Decimal(args.amount)
            or currency != args.currency
            or not any(
                link.get("rel") == "up"
                and link.get("method") == "GET"
                and link.get("href") == f"{SANDBOX_URL}/v2/payments/captures/{args.capture_id}"
                for link in data["links"]
            )
        ):
            raise ValueError()
        status = data["status"]
        if status not in {"COMPLETED", "PENDING", "FAILED", "CANCELLED"}:
            raise ValueError()
        return {
            "refund_id": refund_id,
            "provider_status": status,
            "amount": args.amount,
            "currency": args.currency,
            "capture_id": args.capture_id,
        }
    except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
        raise ProviderError("REFUND_VERIFICATION_MISMATCH") from None
