"""Read-only PayPal diagnostics. Never open Runtime/state or return private provider bodies."""

import time

from .models import Problem, validate_capture_policy
from .paypal import PREFLIGHT_HTTP_TIMEOUT, SandboxPayPal


def blocked_report(check, code):
    report = {
        "check": check,
        "status": "BLOCKED",
        "code": code,
        "requests": [],
        "payment_mutation_requests": 0,
    }
    if check == "capture_order":
        report["checks"] = {
            "capture_get": "BLOCKED",
            "order_get": "BLOCKED",
            "refund_post": "NOT AUTHORIZED / NOT RUN",
        }
    return report


def readonly_client(settings):
    return SandboxPayPal(settings, read_only=True, http_timeout=PREFLIGHT_HTTP_TIMEOUT)


def mutation_count(client):
    return sum(
        item["method"] in {"POST", "PATCH", "PUT", "DELETE"} and item["operation"] != "oauth"
        for item in client.telemetry
    )


async def auth_report(settings, *, client=None):
    client = client if client is not None else readonly_client(settings)
    if not client.read_only:
        raise Problem("PREFLIGHT_READ_ONLY_CLIENT_REQUIRED")
    start = time.perf_counter()
    try:
        await client.token()
        # Demonstrates in-client cache reuse without an additional OAuth POST.
        await client.token()
        result = {
            "check": "oauth",
            "status": "PASS",
            "code": "BEARER_RESPONSE_VALID",
            "token_cache_reused": client.token_cache_hits >= 1,
        }
    except Problem as exc:
        result = {"check": "oauth", "status": "FAIL", "code": exc.code}
    finally:
        await client.close()
    return result | {
        "source": client.source,
        "environment": "sandbox",
        "elapsed_seconds": round(time.perf_counter() - start, 6),
        "requests": client.telemetry,
        "payment_mutation_requests": mutation_count(client),
    }


async def capture_report(settings, capture_id, *, client=None):
    client = client if client is not None else readonly_client(settings)
    if not client.read_only:
        raise Problem("PREFLIGHT_READ_ONLY_CLIENT_REQUIRED")
    start = time.perf_counter()
    checks = {
        "capture_get": "NOT RUN",
        "order_get": "NOT RUN",
        "refund_post": "NOT AUTHORIZED / NOT RUN",
    }
    try:
        facts = await client.capture(capture_id)
        validate_capture_policy(facts, settings)
        result = {
            "status": "PASS",
            "code": "CAPTURE_POLICY_ELIGIBLE",
            "validation": client.capture_checks,
        }
    except Problem as exc:
        result = {"status": "FAIL", "code": exc.code}
    finally:
        await client.close()
    for name, operation in [("capture_get", "capture_get"), ("order_get", "order_get")]:
        requests = [item for item in client.telemetry if item["operation"] == operation]
        if requests:
            checks[name] = "PASS" if requests[-1]["http_status"] == 200 else "FAIL"
    # HTTP-read success and validated eligibility are different pieces of evidence.
    return result | {
        "check": "capture_order",
        "source": client.source,
        "elapsed_seconds": round(time.perf_counter() - start, 6),
        "checks": checks,
        "requests": client.telemetry,
        "payment_mutation_requests": mutation_count(client),
    }
