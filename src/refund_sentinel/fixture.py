"""Developer-only, one-order Sandbox fixture. Not registered with the application Runtime."""

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
from pydantic import Field, model_validator

from .config import (
    SANDBOX_URL,
    SandboxOAuthSettings,
    Settings,
    load_env,
    read_env,
    verify_python_version,
)
from .fixture_callback import CALLBACK_CANCEL_URL, CALLBACK_RETURN_URL, require_callback_ready
from .models import CaptureId, Money, Problem, StrictModel, validate_capture_policy
from .paypal import PREFLIGHT_HTTP_TIMEOUT, SandboxPayPal, identifier, provider_money, verify_links

PRIVATE_DIRECTORY = Path(".state-paypal-fixture")
CREATE_CONSENT = "CREATE SANDBOX NZD 20.00"
CAPTURE_CONSENT = "CAPTURE SANDBOX NZD 20.00"
ALLOWLIST_CONSENT = "ALLOWLIST VERIFIED SANDBOX CAPTURE"
LEGACY_RETURN_URL = "https://localhost/refund-sentinel-sandbox/approved"
LEGACY_CANCEL_URL = "https://localhost/refund-sentinel-sandbox/cancelled"


class FixtureSettings(SandboxOAuthSettings):
    merchant_id: str = Field(pattern=r"^[A-Z0-9]{13}$")
    max_refund: Money = "100.00"

    @classmethod
    def from_env(cls):
        auth = SandboxOAuthSettings.from_env()
        return cls(
            **auth.model_dump(),
            merchant_id=os.environ.get("PAYPAL_MERCHANT_ID", ""),
            max_refund=os.environ.get("MAX_REFUND", "100.00"),
        )


class FixtureState(StrictModel):
    revision: Literal[1] = 1
    environment: Literal["sandbox"] = "sandbox"
    amount: Literal["20.00"] = "20.00"
    currency: Literal["NZD"] = "NZD"
    source: Literal["MOCK", "REAL_SANDBOX"]
    merchant_id: str = Field(pattern=r"^[A-Z0-9]{13}$")
    client_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    create_request_id: str = Field(pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    capture_request_id: str = Field(pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    phase: Literal[
        "PREPARED",
        "AWAITING_BUYER",
        "APPROVED",
        "CAPTURED",
        "VERIFIED",
        "UNKNOWN_CREATE",
        "UNKNOWN_CAPTURE",
    ] = "PREPARED"
    order_id: CaptureId | None = None
    capture_id: CaptureId | None = None
    approval_url: str | None = None
    order_status: str | None = None
    last_code: str = "LOCAL_PREPARATION_ONLY"
    requests: list[dict] = Field(default_factory=list)
    # Preserve old manifests' exact request/digest; only new preparation selects working URLs.
    return_url: str = LEGACY_RETURN_URL
    cancel_url: str = LEGACY_CANCEL_URL

    @model_validator(mode="after")
    def callback_pair(self):
        if (self.return_url, self.cancel_url) not in {
            (LEGACY_RETURN_URL, LEGACY_CANCEL_URL),
            (CALLBACK_RETURN_URL, CALLBACK_CANCEL_URL),
        }:
            raise ValueError("Unsupported fixture callback pair")
        return self

    def review_digest(self):
        fields = self.model_dump(
            include={
                "revision",
                "environment",
                "source",
                "amount",
                "currency",
                "merchant_id",
                "client_fingerprint",
                "create_request_id",
                "capture_request_id",
                "order_id",
            }
        )
        fields["create_body"] = order_body(self)
        return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def fingerprint(settings):
    return hashlib.sha256(settings.client_id.get_secret_value().encode()).hexdigest()


def durable_write(path, data, *, exclusive=False):
    with path.open("xb" if exclusive else "wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


class FixtureStore:
    """Private fixture manifest and permanent POST markers; no retry/reset operation exists."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "fixture.json"

    def prepare(self, settings, *, source="REAL_SANDBOX"):
        self.directory.mkdir(exist_ok=True)
        if any(self.directory.iterdir()):
            raise Problem("FIXTURE_ALREADY_EXISTS_OR_DIRECTORY_NOT_EMPTY")
        state = FixtureState(
            source=source,
            merchant_id=settings.merchant_id,
            client_fingerprint=fingerprint(settings),
            create_request_id=str(uuid4()),
            capture_request_id=str(uuid4()),
            return_url=CALLBACK_RETURN_URL,
            cancel_url=CALLBACK_CANCEL_URL,
        )
        durable_write(self.path, state.model_dump_json(indent=2).encode(), exclusive=True)
        durable_write(
            self.directory / "create-order.private.json",
            json.dumps(order_body(state), indent=2).encode(),
            exclusive=True,
        )
        return state

    def load(self, settings, source):
        state = FixtureState.model_validate_json(self.path.read_bytes())
        if (
            state.merchant_id != settings.merchant_id
            or state.client_fingerprint != fingerprint(settings)
            or state.source != source
        ):
            raise Problem("FIXTURE_ACCOUNT_OR_SOURCE_CHANGED")
        if state.create_request_id == state.capture_request_id:
            raise Problem("FIXTURE_REQUEST_ID_CONFLICT")
        return state

    def save(self, state):
        temporary = self.directory / (".fixture-" + str(uuid4()) + ".tmp")
        durable_write(temporary, state.model_dump_json(indent=2).encode(), exclusive=True)
        os.replace(temporary, self.path)

    @contextmanager
    def lock(self):
        path = self.directory / "operation.lock"
        try:
            durable_write(
                path,
                b"An operation owns this fixture. Never clear after an uncertain POST.",
                exclusive=True,
            )
        except FileExistsError:
            raise Problem("FIXTURE_BUSY_OR_INTERRUPTED_REVIEW_REQUIRED") from None
        try:
            yield
        finally:
            path.unlink()

    def claim(self, operation, request_id):
        try:
            durable_write(
                self.directory / (operation + ".attempt.json"),
                json.dumps({"request_id": request_id}).encode(),
                exclusive=True,
            )
        except FileExistsError:
            raise Problem("FIXTURE_POST_ALREADY_ATTEMPTED_NO_RETRY") from None


class SandboxFixtureTransport(httpx.AsyncBaseTransport):
    """Separate fixture boundary: order create/capture/GET only; no refund or buyer automation."""

    def __init__(self, inner=None):
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request):
        url = request.url
        safe = (
            url.scheme == "https"
            and url.host == "api-m.sandbox.paypal.com"
            and url.port in {None, 443}
            and not url.userinfo
            and not url.query
            and not url.fragment
            and url.raw_path == url.path.encode("ascii")
        )
        allowed = (
            (request.method == "POST" and url.path == "/v2/checkout/orders")
            or (
                request.method == "GET"
                and re.fullmatch(r"/v2/checkout/orders/[A-Z0-9]{17}", url.path)
            )
            or (
                request.method == "POST"
                and re.fullmatch(r"/v2/checkout/orders/[A-Z0-9]{17}/capture", url.path)
            )
        )
        if not safe or not allowed:
            raise Problem("FIXTURE_REQUEST_FORBIDDEN")
        return await self.inner.handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


class FixtureClient:
    def __init__(self, settings, *, transport=None):
        self.auth = SandboxPayPal(
            settings, read_only=True, transport=transport, http_timeout=PREFLIGHT_HTTP_TIMEOUT
        )
        self.source = self.auth.source
        self.requests = []
        self.http = httpx.AsyncClient(
            base_url=SANDBOX_URL,
            follow_redirects=False,
            trust_env=False,
            timeout=PREFLIGHT_HTTP_TIMEOUT,
            transport=SandboxFixtureTransport(transport),
        )

    @property
    def telemetry(self):
        return self.auth.telemetry + self.requests

    async def request(self, method, path, operation, *, body=None, request_id=None):
        headers = {
            "Authorization": "Bearer " + await self.auth.token(),
            "Prefer": "return=representation",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        start, status = time.perf_counter(), None
        try:
            response = await self.http.request(method, path, json=body, headers=headers)
            status = response.status_code
            if status not in ({200, 201} if method == "POST" else {200}):
                raise Problem("FIXTURE_HTTP_" + str(status))
            if len(response.content) > 262144:
                raise ValueError()
            data = response.json()
            if type(data) is not dict:
                raise ValueError()
            return data
        except httpx.HTTPError:
            raise Problem(
                "FIXTURE_TRANSPORT_UNCERTAIN"
                if method == "POST"
                else "FIXTURE_READ_TRANSPORT_FAILED"
            ) from None
        except (ValueError, TypeError):
            raise Problem("FIXTURE_INVALID_RESPONSE") from None
        finally:
            self.requests.append(
                {
                    "operation": operation,
                    "method": method,
                    "http_status": status,
                    "elapsed_seconds": round(time.perf_counter() - start, 6),
                }
            )

    async def order(self, order_id):
        return await self.request("GET", f"/v2/checkout/orders/{identifier(order_id)}", "order_get")

    async def close(self):
        await self.http.aclose()
        await self.auth.close()


def order_body(state):
    return {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": state.create_request_id,
                "description": "Refund Sentinel synthetic Sandbox fixture; no real goods",
                "amount": {"currency_code": state.currency, "value": state.amount},
                "payee": {"merchant_id": state.merchant_id},
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "landing_page": "LOGIN",
                    "shipping_preference": "NO_SHIPPING",
                    "user_action": "PAY_NOW",
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "return_url": state.return_url,
                    "cancel_url": state.cancel_url,
                }
            }
        },
    }


def approval_link(data, order_id):
    try:
        links = [link for link in data["links"] if link.get("rel") in {"approve", "payer-action"}]
        if len(links) != 1 or links[0].get("method") != "GET":
            raise ValueError()
        href = links[0]["href"]
        url = urlsplit(href)
        if (
            url.scheme != "https"
            or url.hostname != "www.sandbox.paypal.com"
            or url.port not in {None, 443}
            or url.username
            or url.password
            or url.fragment
            or url.path != "/checkoutnow"
            or parse_qs(url.query, strict_parsing=True) != {"token": [order_id]}
        ):
            raise ValueError()
        return href  # Return the original genuine URL; never synthesize or follow it.
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Problem("FIXTURE_APPROVAL_LINK_INVALID") from None


def validate_order(data, state, *, approved=False):
    try:
        if data["id"] != state.order_id or data["intent"] != "CAPTURE":
            raise ValueError()
        try:
            verify_links(data, f"/v2/checkout/orders/{state.order_id}")
        except ValueError:
            raise Problem("FIXTURE_ORDER_RESOURCE_LINK_INVALID") from None
        if len(data["purchase_units"]) != 1:
            raise ValueError()
        unit = data["purchase_units"][0]
        if unit["payee"]["merchant_id"] != state.merchant_id:
            raise Problem("FIXTURE_MERCHANT_MISMATCH")
        if provider_money(unit["amount"]) != (state.amount, state.currency):
            raise Problem("FIXTURE_AMOUNT_OR_CURRENCY_MISMATCH")
        if unit["reference_id"] != state.create_request_id:
            raise ValueError()
        if data["status"] not in {"CREATED", "PAYER_ACTION_REQUIRED", "APPROVED", "COMPLETED"}:
            raise ValueError()
        if approved:
            if data["status"] != "APPROVED":
                raise Problem("FIXTURE_BUYER_APPROVAL_REQUIRED")
            validate_buyer(data, state)
            payments = unit.get("payments", {})
            if (
                payments.get("captures")
                or payments.get("authorizations")
                or payments.get("refunds")
            ):
                raise Problem("FIXTURE_UNEXPECTED_EXISTING_PAYMENT")
        return data["status"]
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Problem("FIXTURE_ORDER_EVIDENCE_INVALID") from None


def validate_buyer(data, state):
    try:
        payer = data.get("payer", {}).get("payer_id")
        wallet = data.get("payment_source", {}).get("paypal", {}).get("account_id")
        buyer = wallet or payer
        if (
            not isinstance(buyer, str)
            or not re.fullmatch(r"[A-Z0-9]{13}", buyer)
            or buyer == state.merchant_id
            or (payer and wallet and payer != wallet)
        ):
            raise ValueError()
    except (TypeError, ValueError, AttributeError):
        raise Problem("FIXTURE_SEPARATE_BUYER_EVIDENCE_REQUIRED") from None


def captured_id(data, state):
    try:
        if data["id"] != state.order_id or data["status"] != "COMPLETED":
            raise ValueError()
        if len(data["purchase_units"]) != 1:
            raise ValueError()
        payments = data["purchase_units"][0]["payments"]
        captures = payments["captures"]
        if len(captures) != 1 or payments.get("refunds") or payments.get("authorizations"):
            raise ValueError()
        capture = captures[0]
        result = identifier(capture["id"])
        if result == state.order_id or capture["status"] != "COMPLETED":
            raise ValueError()
        if provider_money(capture["amount"]) != (state.amount, state.currency):
            raise ValueError()
        verify_links(
            capture,
            f"/v2/payments/captures/{result}",
            refund_path=f"/v2/payments/captures/{result}/refund",
        )
        return result
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Problem("FIXTURE_CAPTURE_EVIDENCE_INVALID") from None


def consent(state, supplied, expected, review_digest, accounts_confirmed):
    if supplied != expected or review_digest != state.review_digest() or not accounts_confirmed:
        raise Problem("FIXTURE_EXPLICIT_OPERATION_AUTHORIZATION_REQUIRED")


def summary(state, *, telemetry=()):
    return {
        "source": state.source,
        "environment": "sandbox",
        "phase": state.phase,
        "amount": state.amount,
        "currency": state.currency,
        "intent": "CAPTURE",
        "purchase_units": 1,
        "merchant": "existing privately configured Sandbox Business account",
        "order_status": state.order_status,
        "order_id_recorded_privately": bool(state.order_id),
        "capture_id_recorded_privately": bool(state.capture_id),
        "review_digest": state.review_digest(),
        "code": state.last_code,
        "requests": list(telemetry),
        "refund_requests": 0,
    }


async def operate(
    store,
    settings,
    operation,
    *,
    client=None,
    authorization=None,
    review_digest=None,
    accounts_confirmed=False,
    reconcile_approved_creation=False,
):
    client = client if client is not None else FixtureClient(settings)
    try:
        with store.lock():
            state = store.load(settings, client.source)
            try:
                if operation == "create":
                    consent(state, authorization, CREATE_CONSENT, review_digest, accounts_confirmed)
                    if state.phase != "PREPARED":
                        raise Problem("FIXTURE_POST_ALREADY_ATTEMPTED_NO_RETRY")
                    if client.source == "REAL_SANDBOX" and state.return_url == CALLBACK_RETURN_URL:
                        await require_callback_ready()
                    # Authentication failure cannot claim a payment attempt.
                    await client.auth.token()
                    store.claim("create", state.create_request_id)
                    state.phase = "UNKNOWN_CREATE"
                    # Durable uncertainty before dispatch; survives crash/cancellation.
                    store.save(state)
                    data = await client.request(
                        "POST",
                        "/v2/checkout/orders",
                        "order_create",
                        body=order_body(state),
                        request_id=state.create_request_id,
                    )
                    state.order_id = identifier(data.get("id"))
                    store.save(state)
                    state.approval_url = approval_link(data, state.order_id)
                    order = await client.order(state.order_id)
                    state.order_status = validate_order(order, state)
                    if state.order_status not in {"CREATED", "PAYER_ACTION_REQUIRED"}:
                        raise Problem("FIXTURE_UNEXPECTED_ORDER_STATUS")
                    state.phase, state.last_code = (
                        "AWAITING_BUYER",
                        "SANDBOX_BUYER_CHECKOUT_REQUIRED",
                    )
                elif operation == "status":
                    if not state.order_id:
                        raise Problem("FIXTURE_NO_KNOWN_ORDER_ID")
                    order = await client.order(state.order_id)
                    state.order_status = validate_order(order, state)
                    if state.phase in {"UNKNOWN_CREATE", "UNKNOWN_CAPTURE"}:
                        state.last_code = "FIXTURE_UNCERTAIN_MANUAL_REVIEW_REQUIRED"
                    elif state.order_status == "APPROVED" and state.phase in {
                        "AWAITING_BUYER",
                        "APPROVED",
                    }:
                        validate_order(order, state, approved=True)
                        state.phase, state.last_code = (
                            "APPROVED",
                            "READY_FOR_SEPARATE_CAPTURE_AUTHORIZATION",
                        )
                    elif state.order_status == "COMPLETED":
                        if not state.capture_id or captured_id(order, state) != state.capture_id:
                            raise Problem("FIXTURE_UNEXPECTED_ORDER_COMPLETION")
                        validate_buyer(order, state)
                        state.last_code = "COMPLETED_ORDER_READ_ONLY_OBSERVATION"
                    else:
                        state.last_code = "SANDBOX_BUYER_CHECKOUT_REQUIRED"
                elif operation == "capture":
                    consent(
                        state, authorization, CAPTURE_CONSENT, review_digest, accounts_confirmed
                    )
                    if (store.directory / "capture.attempt.json").exists():
                        raise Problem("FIXTURE_POST_ALREADY_ATTEMPTED_NO_RETRY")
                    reconcile_creation = (
                        reconcile_approved_creation and state.phase == "UNKNOWN_CREATE"
                    )
                    if (state.phase != "APPROVED" and not reconcile_creation) or not state.order_id:
                        raise Problem("FIXTURE_BUYER_APPROVAL_REQUIRED")
                    if reconcile_creation:
                        marker = json.loads((store.directory / "create.attempt.json").read_bytes())
                        if marker != {"request_id": state.create_request_id}:
                            raise Problem("FIXTURE_CREATE_ATTEMPT_IDENTITY_MISMATCH")
                    order = await client.order(state.order_id)  # Fresh verification before POST.
                    validate_order(order, state, approved=True)
                    if reconcile_creation:
                        # Explicit continuation of this approved order. Never retry creation.
                        durable_write(
                            store.directory / "pre-capture.fixture.json",
                            store.path.read_bytes(),
                            exclusive=True,
                        )
                        state.phase, state.order_status = "APPROVED", "APPROVED"
                        state.last_code = "CREATE_OBSERVATION_RECONCILED_FOR_AUTHORIZED_CAPTURE"
                        store.save(state)
                    store.claim("capture", state.capture_request_id)
                    state.phase = "UNKNOWN_CAPTURE"
                    store.save(state)
                    data = await client.request(
                        "POST",
                        f"/v2/checkout/orders/{state.order_id}/capture",
                        "order_capture",
                        body={},
                        request_id=state.capture_request_id,
                    )
                    state.capture_id = captured_id(data, state)
                    store.save(state)
                    order = await client.order(state.order_id)
                    if (
                        validate_order(order, state) != "COMPLETED"
                        or captured_id(order, state) != state.capture_id
                    ):
                        raise Problem("FIXTURE_CAPTURE_EVIDENCE_INVALID")
                    validate_buyer(order, state)
                    state.phase, state.order_status = "CAPTURED", "COMPLETED"
                    state.last_code = "CAPTURED_REQUIRES_INDEPENDENT_CAPTURE_GET"
                else:
                    raise Problem("FIXTURE_OPERATION_INVALID")
            except Problem as exc:
                state.last_code = exc.code
                raise
            finally:
                state.requests.extend(client.telemetry)
                store.save(state)
            return summary(state, telemetry=client.telemetry)
    finally:
        await client.close()


def verification_settings(settings, state):
    return Settings(
        **settings.model_dump(), capture_ids=(state.capture_id,), ai_mode="deterministic"
    )


async def verify_capture(store, settings, *, client=None):
    with store.lock():
        source = client.source if client is not None else "REAL_SANDBOX"
        state = store.load(settings, source)
        if state.phase not in {"CAPTURED", "VERIFIED"} or not state.capture_id:
            raise Problem("FIXTURE_COMPLETED_CAPTURE_REQUIRED")
        config = verification_settings(settings, state)
        client = (
            client
            if client is not None
            else SandboxPayPal(config, read_only=True, http_timeout=PREFLIGHT_HTTP_TIMEOUT)
        )
        if not client.read_only:
            raise Problem("PREFLIGHT_READ_ONLY_CLIENT_REQUIRED")
        try:
            facts = await client.capture(state.capture_id)
            validate_capture_policy(facts, config)
            if (
                facts.order_id != state.order_id
                or facts.amount != state.amount
                or facts.currency != state.currency
            ):
                raise Problem("FIXTURE_CAPTURE_ORDER_OR_MONEY_MISMATCH")
            state.phase, state.last_code = "VERIFIED", "CAPTURE_POLICY_ELIGIBLE"
            return summary(state, telemetry=client.telemetry) | {
                "validation": client.capture_checks
            }
        except Problem as exc:
            state.phase, state.last_code = "CAPTURED", exc.code
            raise
        finally:
            state.requests.extend(client.telemetry)
            store.save(state)
            await client.close()


def configure_allowlist(store, settings, authorization, *, env_path=Path(".env")):
    if authorization != ALLOWLIST_CONSENT:
        raise Problem("FIXTURE_EXPLICIT_ALLOWLIST_AUTHORIZATION_REQUIRED")
    with store.lock():
        state = store.load(settings, "REAL_SANDBOX")
        if state.phase != "VERIFIED" or not state.capture_id:
            raise Problem("FIXTURE_VERIFIED_CAPTURE_REQUIRED")
        values = read_env(env_path)
        if (
            values.get("PAYPAL_MERCHANT_ID") != settings.merchant_id
            or values.get("PAYPAL_CLIENT_ID") != settings.client_id.get_secret_value()
            or values.get("PAYPAL_CLIENT_SECRET") != settings.client_secret.get_secret_value()
            or values.get("PAYMENT_MODE") != "sandbox"
            or values.get("PAYPAL_ENVIRONMENT") != "sandbox"
            or values.get("PAYPAL_BASE_URL") != SANDBOX_URL
        ):
            raise Problem("FIXTURE_ENVIRONMENT_CHANGED")
        captures = [x.strip() for x in values.get("PAYPAL_CAPTURE_IDS", "").split(",") if x.strip()]
        if state.capture_id not in captures:
            captures.append(state.capture_id)
        original = env_path.read_bytes()
        pattern = rb"(?m)^(PAYPAL_CAPTURE_IDS=)[^\r\n]*"
        if len(re.findall(pattern, original)) != 1:
            raise Problem("FIXTURE_ALLOWLIST_LINE_REQUIRED")
        updated = re.sub(pattern, lambda match: match[1] + ",".join(captures).encode(), original)
        for capture_id in captures:
            identifier(capture_id)
        temporary = env_path.with_name(".env.fixture-" + str(uuid4()))
        durable_write(temporary, updated, exclusive=True)
        if env_path.read_bytes() != original:
            raise Problem("FIXTURE_ENVIRONMENT_CHANGED")
        os.replace(temporary, env_path)
        return {"status": "PASS", "code": "VERIFIED_CAPTURE_ALLOWLISTED", "refund_requests": 0}


def ignored_private_directory():
    root = Path.cwd().resolve()
    path = PRIVATE_DIRECTORY.resolve()
    if path.parent != root or PRIVATE_DIRECTORY.is_symlink():
        raise Problem("FIXTURE_PRIVATE_DIRECTORY_INVALID")
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(PRIVATE_DIRECTORY / "fixture.json")],
        capture_output=True,
    )
    if result.returncode != 0:
        raise Problem("FIXTURE_PRIVATE_DIRECTORY_MUST_BE_GIT_IGNORED")
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Developer-only Sandbox NZD 20.00 fixture; never refunds"
    )
    parser.add_argument(
        "command",
        choices=["prepare", "create", "status", "approval-link", "capture", "verify", "allowlist"],
    )
    parser.add_argument("--authorize-create")
    parser.add_argument("--authorize-capture")
    parser.add_argument("--authorize-allowlist")
    parser.add_argument("--review-digest")
    parser.add_argument(
        "--reconcile-approved-creation",
        action="store_true",
        help=(
            "Reconcile UNKNOWN_CREATE after fresh approved-order verification; never retries a POST"
        ),
    )
    parser.add_argument(
        "--accounts-confirmed",
        action="store_true",
        help="Human verified Sandbox Business NZD receiving and separate synthetic Personal buyer",
    )
    args = parser.parse_args()
    store = settings = None
    try:
        verify_python_version()
        load_env()
        settings = FixtureSettings.from_env()
        store = FixtureStore(ignored_private_directory())
        if args.command == "prepare":
            report = summary(store.prepare(settings))
        elif args.command == "approval-link":
            state = store.load(settings, "REAL_SANDBOX")
            if state.phase not in {"AWAITING_BUYER", "APPROVED"}:
                raise Problem("FIXTURE_BUYER_LINK_NOT_READY")
            print(
                approval_link(
                    {"links": [{"rel": "approve", "method": "GET", "href": state.approval_url}]},
                    state.order_id,
                )
            )
            return  # Intentionally private handoff URL. Do not copy it to public evidence.
        elif args.command == "verify":
            report = asyncio.run(verify_capture(store, settings))
        elif args.command == "allowlist":
            if args.authorize_allowlist != ALLOWLIST_CONSENT:
                raise Problem("FIXTURE_EXPLICIT_ALLOWLIST_AUTHORIZATION_REQUIRED")
            asyncio.run(verify_capture(store, settings))  # Fresh reads before the authorized edit.
            report = configure_allowlist(store, settings, args.authorize_allowlist)
        else:
            report = asyncio.run(
                operate(
                    store,
                    settings,
                    args.command,
                    authorization=args.authorize_create
                    if args.command == "create"
                    else args.authorize_capture,
                    review_digest=args.review_digest,
                    accounts_confirmed=args.accounts_confirmed,
                    reconcile_approved_creation=args.reconcile_approved_creation,
                )
            )
        print(json.dumps(report, indent=2))
    except (Problem, ValueError, OSError) as exc:
        code = exc.code if isinstance(exc, Problem) else "FIXTURE_CONFIGURATION_OR_STATE_INVALID"
        report = {"status": "BLOCKED", "code": code, "refund_requests": 0}
        if store is not None and settings is not None:
            try:
                state = store.load(settings, "REAL_SANDBOX")
                report |= {"phase": state.phase, "request_history": state.requests}
            except (Problem, ValueError, OSError):
                pass
        print(json.dumps(report, indent=2))
        parser.exit(2)


if __name__ == "__main__":
    main()
