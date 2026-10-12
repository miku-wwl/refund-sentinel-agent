import argparse
import asyncio
import os
from pathlib import Path

import uvicorn

from .config import Settings, load_env
from .integration import provision
from .models import Problem
from .paypal import SandboxPayPal
from .web import create_app


async def check_capture(settings, capture_id):
    if settings.payment_mode != "sandbox":
        raise Problem("SANDBOX_CHECK_REQUIRES_SANDBOX_MODE")
    client = SandboxPayPal(settings)
    try:
        facts = await client.capture(capture_id)
        print(facts.model_dump_json(indent=2))
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(description="Refund Sentinel: local sandbox-only MVP")
    parser.add_argument("command", choices=["init", "serve", "check-capture"])
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
        load_env()
        settings = Settings.from_env()
        directory = args.state or Path(os.getenv("SENTINEL_STATE_DIR", ".state-offline"))
        if args.command == "init":
            provision(directory, settings)
            print("Provisioned " + str(directory.resolve()))
            print("Private operator capability created. Keep it out of shared evidence.")
        elif args.command == "check-capture":
            if not args.capture_id:
                raise Problem("CAPTURE_ID_REQUIRED")
            asyncio.run(check_capture(settings, args.capture_id))
        else:
            if not args.predecessor_stopped:
                raise Problem("PREDECESSOR_STOP_CONFIRMATION_REQUIRED")
            app = create_app(directory, settings, predecessor_stopped=True)
            uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    except (ValueError, OSError, Problem) as exc:
        # Pydantic validation exceptions may contain input values. Never print them.
        parser.exit(
            2, (exc.code if isinstance(exc, Problem) else "CONFIGURATION_OR_STATE_INVALID") + "\n"
        )


if __name__ == "__main__":
    main()
