import argparse
import asyncio
import json
import os
from pathlib import Path

import uvicorn

from .config import SandboxOAuthSettings, Settings, load_env, verify_python_version
from .integration import provision
from .models import Problem
from .preflight import auth_report, blocked_report, capture_report
from .web import create_app


async def check_capture(settings, capture_id):
    if settings.payment_mode != "sandbox":
        raise Problem("SANDBOX_CHECK_REQUIRES_SANDBOX_MODE")
    return await capture_report(settings, capture_id)


def main():
    parser = argparse.ArgumentParser(description="Refund Sentinel: local sandbox-only MVP")
    parser.add_argument("command", choices=["init", "serve", "check-auth", "check-capture"])
    parser.add_argument("--state", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--capture-id")
    parser.add_argument(
        "--predecessor-stopped",
        action="store_true",
        help="Confirm that the previous process using this state directory stopped",
    )
    args = parser.parse_args()
    try:
        verify_python_version()
        load_env()
        if args.command == "check-auth":
            report = asyncio.run(auth_report(SandboxOAuthSettings.from_env()))
            print(json.dumps(report, indent=2))
            parser.exit(0 if report["status"] == "PASS" else 1)
        if args.command == "check-capture" and os.environ.get("PAYMENT_MODE") != "sandbox":
            raise Problem("SANDBOX_CHECK_REQUIRES_SANDBOX_MODE")
        if args.command == "check-capture" and not os.environ.get("PAYPAL_CAPTURE_IDS", "").strip():
            print(json.dumps(blocked_report("capture_order", "BLOCKED_NO_CAPTURE_ID"), indent=2))
            parser.exit(2)
        settings = Settings.from_env()
        directory = args.state or Path(os.getenv("SENTINEL_STATE_DIR", ".state-offline"))
        if args.command == "init":
            provision(directory, settings)
            print("Provisioned " + str(directory.resolve()))
            print("Private operator capability created. Keep it out of shared evidence.")
        elif args.command == "check-capture":
            if not args.capture_id:
                raise Problem("CAPTURE_ID_REQUIRED")
            report = asyncio.run(check_capture(settings, args.capture_id))
            print(json.dumps(report, indent=2))
            parser.exit(0 if report["status"] == "PASS" else 1)
        else:
            if not args.predecessor_stopped:
                raise Problem("PREDECESSOR_STOP_CONFIRMATION_REQUIRED")
            app = create_app(directory, settings, predecessor_stopped=True)
            uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    except (ValueError, OSError, Problem) as exc:
        # Pydantic validation exceptions may contain input values. Never print them.
        code = exc.code if isinstance(exc, Problem) else "CONFIGURATION_OR_STATE_INVALID"
        if args.command in {"check-auth", "check-capture"}:
            print(
                json.dumps(
                    blocked_report(
                        "oauth" if args.command == "check-auth" else "capture_order", code
                    ),
                    indent=2,
                )
            )
            parser.exit(2)
        parser.exit(2, code + "\n")


if __name__ == "__main__":
    main()
