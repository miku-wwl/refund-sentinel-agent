from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .integration import composition, verify_distribution
from .models import Problem, RequestInput, StrictModel
from .service import Sentinel


class PlanCommand(StrictModel):
    expected_version: int = Field(ge=1)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DecisionCommand(PlanCommand):
    decision: Literal["approve", "reject"]


class ExecutionCommand(PlanCommand):
    idempotency_key: str = Field(pattern=r"^[0-9a-f-]{36}$")


def create_app(directory, settings, *, predecessor_stopped=False, paypal=None, analyst=None):
    @asynccontextmanager
    async def lifespan(app):
        with composition(
            directory,
            settings,
            paypal=paypal,
            analyst=analyst,
            predecessor_stopped=predecessor_stopped,
        ) as resources:
            runtime, store, client, model, _ = resources
            app.state.sentinel = Sentinel(runtime, store, client, model, settings)
            try:
                yield
            finally:
                await client.close()
                await model.close()

    app = FastAPI(title="Refund Sentinel", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def safe_browser(request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method != "GET"
            and origin
            and (
                urlsplit(origin).netloc != request.headers.get("host")
                or urlsplit(origin).scheme != request.url.scheme
            )
        ):
            return JSONResponse({"error": "CROSS_ORIGIN_REQUEST_REJECTED"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(Problem)
    async def problem_handler(request, exc):
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    @app.exception_handler(Exception)
    async def safe_error(request, exc):
        # Core exceptions deliberately expose safe enumerated codes only, never internal traces.
        code = getattr(getattr(exc, "code", None), "value", None)
        allowed = {
            "AUTHENTICATION_REQUIRED",
            "ACTION_NOT_AUTHORIZED",
            "STALE_RUN_VERSION",
            "INVALID_RUN_TRANSITION",
            "STALE_ACTION_VERSION",
            "ACTION_NOT_EXECUTABLE",
            "EXECUTION_ALREADY_STARTED",
            "IDEMPOTENCY_CONFLICT",
            "RUN_NOT_ACTION_ELIGIBLE",
            "TOOL_NOT_BOUND",
            "PLAN_NOT_EXECUTABLE",
            "INVALID_ACTION_REQUEST",
            "ACTION_NOT_FOUND",
        }
        status = (
            401
            if code == "AUTHENTICATION_REQUIRED"
            else (403 if code == "ACTION_NOT_AUTHORIZED" else 409)
        )
        return JSONResponse(
            {"error": code if code in allowed else "INTERNAL_ERROR"},
            status_code=status if code in allowed else 500,
        )

    def service(request: Request):
        return request.app.state.sentinel

    def principal(request: Request, sentinel=Depends(service)):
        value = sentinel.runtime.verifier.verify(request.headers.get("authorization"))
        sentinel.runtime.gateway.require(value, "read")
        return value

    @app.get("/api/config")
    def config():
        return {
            "payment_mode": settings.payment_mode,
            "ai_mode": settings.ai_mode,
            "environment": "sandbox",
            "capture_ids": settings.capture_ids,
            "max_refund": settings.max_refund,
            "runtime": verify_distribution(),
        }

    @app.get("/api/incidents")
    def incidents(sentinel=Depends(service), operator=Depends(principal)):
        return [
            {
                "id": row["id"],
                "capture_id": row["capture_id"],
                "analysis_state": row["analysis_state"],
            }
            for row in sentinel.store.list()
        ]

    @app.post("/api/incidents")
    async def analyze(body: RequestInput, sentinel=Depends(service), operator=Depends(principal)):
        result = await sentinel.analyze(body)
        return sentinel.view(result["id"], operator)

    @app.get("/api/incidents/{incident_id}")
    def inspect_incident(incident_id: str, sentinel=Depends(service), operator=Depends(principal)):
        return sentinel.view(incident_id, operator)

    @app.post("/api/incidents/{incident_id}/decision")
    def decision(
        incident_id: str,
        body: DecisionCommand,
        sentinel=Depends(service),
        operator=Depends(principal),
    ):
        return sentinel.decide(incident_id, body, operator)

    @app.post("/api/incidents/{incident_id}/admit")
    def admit(
        incident_id: str,
        body: ExecutionCommand,
        sentinel=Depends(service),
        operator=Depends(principal),
    ):
        return sentinel.admit(incident_id, body, operator)

    @app.post("/api/incidents/{incident_id}/authorize")
    def authorize(
        incident_id: str,
        body: ExecutionCommand,
        sentinel=Depends(service),
        operator=Depends(principal),
    ):
        return sentinel.authorize(incident_id, body, operator)

    @app.post("/api/incidents/{incident_id}/execute")
    async def execute(
        incident_id: str,
        body: ExecutionCommand,
        sentinel=Depends(service),
        operator=Depends(principal),
    ):
        return await sentinel.execute(incident_id, body, operator)

    @app.post("/api/incidents/{incident_id}/verify")
    async def verify(incident_id: str, sentinel=Depends(service), operator=Depends(principal)):
        return await sentinel.verify(incident_id, operator)

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app
