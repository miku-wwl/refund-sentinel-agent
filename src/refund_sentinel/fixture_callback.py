"""Explicit loopback-only developer return receiver; never loads credentials or calls PayPal."""

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .models import Problem

CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8766
CALLBACK_ORIGIN = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}"
APPROVED_PATH = "/refund-sentinel-sandbox/approved"
CANCELLED_PATH = "/refund-sentinel-sandbox/cancelled"
HEALTH_PATH = "/refund-sentinel-sandbox/health"
CALLBACK_RETURN_URL = CALLBACK_ORIGIN + APPROVED_PATH
CALLBACK_CANCEL_URL = CALLBACK_ORIGIN + CANCELLED_PATH
CALLBACK_HEALTH = {"service": "refund-sentinel-fixture-callback", "mode": "return-only"}


def callback_app():
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    def page(event):
        # Do not echo/log/store query tokens or infer provider status from a browser redirect.
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Refund Sentinel Sandbox return</title></head><body>"
            f"<h1>{event}</h1><p>Read the existing order with Order GET to confirm its status.</p>"
            "<p>Capture requires separate explicit authorization.</p></body></html>",
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'none'; base-uri 'none'; form-action 'none'"
                ),
            },
        )

    @app.get(APPROVED_PATH)
    def approved_return():
        return page("Buyer checkout return received")

    @app.get(CANCELLED_PATH)
    def cancelled_return():
        return page("Cancellation return received")

    @app.get(HEALTH_PATH)
    def health():
        return CALLBACK_HEALTH

    return app


async def require_callback_ready(*, transport=None):
    """Bounded local readiness only; absent receiver must block future order creation."""
    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=1.0, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.get(CALLBACK_ORIGIN + HEALTH_PATH)
            if (
                response.status_code != 200
                or len(response.content) > 1024
                or response.json() != CALLBACK_HEALTH
            ):
                raise ValueError()
    except (httpx.HTTPError, ValueError):
        raise Problem("FIXTURE_CALLBACK_NOT_READY") from None


def main():
    # Fixed loopback/HTTP binding agrees with the URLs frozen into future fixture manifests.
    uvicorn.run(
        callback_app(),
        host=CALLBACK_HOST,
        port=CALLBACK_PORT,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
