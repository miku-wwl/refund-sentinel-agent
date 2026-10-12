"""Explicit evidence collection. Fake payments only; real-AI option never executes refunds."""

import argparse
import asyncio
import inspect
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from agentic_intent_gate.runtime import (
    ActionCommand,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
    Runtime,
    ToolBinding,
    ToolCapability,
    open_runtime,
)

from refund_sentinel.config import Settings
from refund_sentinel.integration import composition, provision, verify_distribution
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import FakePayPal
from refund_sentinel.service import Sentinel

MESSAGE = "Synthetic customer: One item arrived damaged. Please refund USD 25.00."


async def offline_case(directory, behavior):
    settings = Settings()
    provision(directory, settings)
    fake = FakePayPal(directory / "fake-paypal.sqlite3", behavior=behavior)
    with composition(directory, settings, paypal=fake, predecessor_stopped=True) as resources:
        runtime, store, client, model, executor = resources
        principal = runtime.verifier.verify(
            "Bearer " + (directory / "operator.capability").read_text("ascii")
        )
        app = Sentinel(runtime, store, client, model, settings)
        incident = await app.analyze(
            RequestInput(capture_id=settings.capture_ids[0], message=MESSAGE)
        )
        run_id = incident["run"]["run_id"]
        approved = runtime.run_service.decide(
            run_id, ApprovalDecisionRequest(ApprovalChoice.APPROVE, incident["run"]["version"])
        )
        action = runtime.gateway.admit(
            AdmissionCommand(run_id, approved.version, principal.subject_id, str(uuid4())),
            principal,
        ).action
        authorized = runtime.gateway.authorize(
            ActionCommand(action.action_id, action.version, str(uuid4())), principal
        ).action
        assert client.recorded_calls() == []
        execute_command = ActionCommand(authorized.action_id, authorized.version, str(uuid4()))
        result = await runtime.gateway.execute(execute_command, principal)
        replay = await runtime.gateway.execute(execute_command, principal)
        assert replay.replayed and len(client.recorded_calls()) == 1
        report = {
            "label": "SIMULATED PAYMENTS + DETERMINISTIC TEST PROVIDER",
            "behavior": behavior,
            "binding": asdict(executor.binding),
            "incident": app.view(incident["id"], principal),
            "recorded_provider_calls": client.recorded_calls(),
            "persisted_provider_refunds": client.persisted_refunds(),
            "command_replayed": replay.replayed,
        }
        assert result.action.state.value == ("Succeeded" if behavior == "COMPLETED" else "Unknown")
    with composition(directory, settings, predecessor_stopped=True) as resources:
        runtime = resources[0]
        persisted = runtime.actions.get(result.action.action_id)
        assert persisted.snapshot() == result.action.snapshot()
        report["restart_persisted_state"] = persisted.state.value
    return report


async def real_ai_case(directory, base_url, model_name):
    settings = Settings(
        ai_mode="real", llm_base_url=base_url, llm_model=model_name, llm_format="json_schema"
    )
    provision(directory, settings)
    start = time.monotonic()
    with composition(directory, settings, predecessor_stopped=True) as resources:
        runtime, store, client, model, _ = resources
        result = await Sentinel(runtime, store, client, model, settings).analyze(
            RequestInput(capture_id=settings.capture_ids[0], message=MESSAGE)
        )
        await model.close()
        return {
            "label": "GENUINE MODEL + FAKE PAYMENT FACTS; NO REFUND EXECUTED",
            "model": model_name,
            "response_format": "json_schema",
            "elapsed_seconds": round(time.monotonic() - start, 2),
            "result": result,
            "provider_refund_calls": client.recorded_calls(),
        }


async def collect(args):
    output = Path("evidence")
    output.mkdir(exist_ok=True)
    signatures = {
        name: str(inspect.signature(obj))
        for name, obj in {
            "ToolBinding": ToolBinding,
            "ToolCapability": ToolCapability,
            "open_runtime": open_runtime,
            "RunService.create": Runtime.__annotations__["run_service"].create,
            "RunService.decide": Runtime.__annotations__["run_service"].decide,
            "Gateway.admit": Runtime.__annotations__["gateway"].admit,
            "Gateway.authorize": Runtime.__annotations__["gateway"].authorize,
            "Gateway.execute": Runtime.__annotations__["gateway"].execute,
        }.items()
    }
    (output / "runtime-api.json").write_text(
        json.dumps({"installed": verify_distribution(), "public_signatures": signatures}, indent=2),
        "utf-8",
    )
    with tempfile.TemporaryDirectory(prefix="refund-sentinel-evidence-") as temporary:
        root = Path(temporary)
        if args.real_ai:
            result = await real_ai_case(root / "ai", args.base_url, args.model)
            path = output / "real-ai-collected.json"
        else:
            result = {
                "completed": await offline_case(root / "completed", "COMPLETED"),
                "ambiguous": await offline_case(root / "unknown", "TIMEOUT_AFTER_EFFECT"),
            }
            path = output / "offline-workflows.json"
    path.write_text(json.dumps(result, indent=2), "utf-8")
    print("Evidence saved: " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-ai", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--model", default="phi4-mini:latest")
    asyncio.run(collect(parser.parse_args()))


if __name__ == "__main__":
    main()
