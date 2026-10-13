"""Loopback presentation server, deliberately separate from the financial-capable web app."""

import argparse
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .demo import DemoController
from .demo_ai import LocalProposal
from .integration import verify_distribution
from .models import Problem
from .presentation_models import DemoCommand, DemoView, HistoricalProof, NewDemo

STATIC = Path(__file__).parent / "static"
PROOF_SHA256 = "1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853"
COOKIE = "sentinel_simulation"


def archived_proof():
    body = (STATIC / "qualified-case.json").read_bytes()
    if hashlib.sha256(body).hexdigest() != PROOF_SHA256:
        raise Problem("ARCHIVED_PROOF_INTEGRITY_FAILURE", 503)
    return HistoricalProof.model_validate_json(body)


def create_presentation_app(root=None, *, delay=0.8, proposal_factory=LocalProposal):
    @asynccontextmanager
    async def lifespan(app):
        verify_distribution()
        app.state.proof = archived_proof()
        controller = DemoController(
            root or Path.cwd() / ".state-presentation-demo",
            delay=delay,
            proposal_factory=proposal_factory,
        )
        app.state.demo = controller
        try:
            yield
        finally:
            controller.close()

    app = FastAPI(
        title="Refund Sentinel • Presentation", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def browser_boundary(request, call_next):
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            if request.headers.get("x-sentinel-demo") != "simulation" or (
                origin
                and (
                    urlsplit(origin).netloc != request.headers.get("host")
                    or urlsplit(origin).scheme != request.url.scheme
                )
            ):
                return JSONResponse({"error": "SIMULATION_ORIGIN_REQUIRED"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        return JSONResponse({"error": "INVALID_SIMULATION_INPUT"}, status_code=422)

    @app.exception_handler(Exception)
    async def closed_error(request, exc):
        code = getattr(getattr(exc, "code", None), "value", None)
        safe = {
            "STALE_RUN_VERSION",
            "STALE_ACTION_VERSION",
            "PLAN_CONFIRMATION_MISMATCH",
            "ACTION_NOT_AUTHORIZED",
            "IDEMPOTENCY_CONFLICT",
            "ACTION_NOT_EXECUTABLE",
        }
        return JSONResponse(
            {"error": code if code in safe else "PRESENTATION_UNAVAILABLE"},
            status_code=409 if code in safe else 503,
        )

    def session(request):
        value = request.cookies.get(COOKIE)
        if not value:
            raise Problem("DEMO_SESSION_REQUIRED", 409)
        return request.app.state.demo.get(value)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "console.html")

    # Fixed asset names: no filesystem path input and no operational app JS/routes.
    for name, media in {
        "console-icon.svg": "image/svg+xml",
        "console.js": "text/javascript",
        "console-state.mjs": "text/javascript",
        "console.css": "text/css",
    }.items():

        def asset_factory(filename, media_type):
            def asset():
                return FileResponse(STATIC / filename, media_type=media_type)

            return asset

        app.add_api_route("/assets/" + name, asset_factory(name, media), methods=["GET"])

    @app.get("/presentation/proof", response_model=HistoricalProof)
    def proof(request: Request):
        return request.app.state.proof

    @app.get("/presentation/demo", response_model=DemoView | None)
    def current_demo(request: Request):
        return session(request).view() if request.cookies.get(COOKIE) else None

    @app.post("/presentation/demo", response_model=DemoView)
    def new_demo(body: NewDemo, request: Request, response: Response):
        value = request.app.state.demo.new(body.scenario, body.planning_mode)
        response.set_cookie(
            COOKIE,
            value.directory.name,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=86400,
        )
        return value.view()

    @app.post("/presentation/demo/generate", response_model=DemoView)
    async def generate(body: NewDemo, request: Request):
        value = session(request)
        if body.scenario != value.scenario:
            raise Problem("DEMO_SCENARIO_MISMATCH", 409)
        if body.planning_mode != value.planning_mode:
            raise Problem("DEMO_PLANNING_MODE_MISMATCH", 409)
        return await value.generate()

    @app.post("/presentation/demo/command", response_model=DemoView)
    async def command(body: DemoCommand, request: Request):
        return await session(request).command(body)

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Read-only archived proof + isolated synthetic demo"
    )
    parser.add_argument("--port", type=int, default=8880)
    args = parser.parse_args()
    uvicorn.run(create_presentation_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
