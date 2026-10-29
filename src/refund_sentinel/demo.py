"""Isolated synthetic consumer, using the unchanged public Runtime and fake provider only."""

import asyncio
import json
import time
from contextlib import ExitStack
from pathlib import Path
from uuid import UUID, uuid4

from agentic_intent_gate.runtime import ExecutionSpec

from .decision_lab import CASES, fixture, load_decision, save_decision, verify_case
from .demo_ai import LocalProposal, PreparedAnalyst, demo_settings
from .execution_guard import probe_owner_lock
from .integration import composition, provision
from .llm import DeterministicAnalyst
from .models import Problem, RequestInput, validate_policy
from .paypal import FakePayPal
from .presentation_models import DemoView
from .service import Sentinel
from .web import DecisionCommand, ExecutionCommand

MARKER = "refund-sentinel-presentation-simulation-v1"
SAMPLE = "Synthetic customer: my item arrived damaged. Please refund USD 25.00."
SCENARIOS = {"completed": "COMPLETED", "unknown": "TIMEOUT_AFTER_EFFECT", "rejected": "REJECT"}
SCENARIOS.update({name: case.behavior for name, case in CASES.items()})


def canonical_id(value):
    try:
        if str(UUID(value, version=4)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise Problem("DEMO_SESSION_INVALID", 404)


class DemoSession:
    def __init__(self, directory, scenario, stack, *, delay, planning_mode, proposal_factory):
        self.directory, self.scenario = directory, scenario
        self.planning_mode, self.proposal_factory = planning_mode, proposal_factory
        # Never from_env/load_env, never any genuine Sandbox identity or credential.
        self.settings = demo_settings(planning_mode)
        self.analyst = (
            PreparedAnalyst()
            if planning_mode == "local_ai" or scenario in CASES
            else DeterministicAnalyst()
        )
        self.fake = FakePayPal(
            directory / "fake-paypal.sqlite3", behavior=SCENARIOS[scenario], delay=delay
        )
        gate = directory / "gate.sqlite3"
        if gate.exists():
            # The fake executor has no helper processes/background tasks. Existing case owners
            # must release the original OS fence before resume; open_runtime reacquires it.
            probe_owner_lock(gate)
        resources = stack.enter_context(
            composition(
                directory,
                self.settings,
                paypal=self.fake,
                analyst=self.analyst,
                predecessor_stopped=True,
            )
        )
        self.runtime, self.store, _, _, _ = resources
        self.sentinel = Sentinel(*resources[:4], self.settings)
        self.principal = self.runtime.verifier.verify(
            "Bearer " + (directory / "operator.capability").read_text("ascii")
        )
        self.lock = asyncio.Lock()
        self.execution_seconds = None

    def incident(self):
        rows = self.store.list()
        if len(rows) > 1:
            raise Problem("DEMO_STATE_INCONSISTENT", 409)
        return self.store.get(rows[0]["id"]) if rows else None

    def view(self):
        incident = self.incident()
        data = {
            "session_id": self.directory.name,
            "scenario": self.scenario,
            "incident_description": CASES[self.scenario].message
            if self.scenario in CASES
            else SAMPLE,
            "simulated_dispatches": len(self.fake.recorded_calls()),
            "execution_seconds": self.execution_seconds,
            "planning_mode": self.planning_mode,
            "analysis_source": "NOT_GENERATED"
            if self.planning_mode == "local_ai"
            else "SIMULATED_DETERMINISTIC_FIXTURE",
        }
        decision = load_decision(self.directory) if self.scenario in CASES else None
        if decision:
            data.update(
                decision=decision,
                recommendation=decision.recommendation,
                analysis_source=decision.source,
                model="phi4-mini:latest" if decision.source == "REAL_LOCAL_OLLAMA" else None,
                model_seconds=decision.model_seconds,
            )
        if incident:
            detail = self.sentinel.view(incident["id"], self.principal)
            run = detail.get("run")
            data["recommendation"] = detail.get("recommendation")
            if self.planning_mode == "local_ai" and detail.get("recommendation"):
                evidence = json.loads((self.directory / "proposal.json").read_text("utf-8"))
                data.update(
                    analysis_source="REAL_LOCAL_OLLAMA",
                    model="phi4-mini:latest",
                    model_seconds=evidence["seconds"],
                )
            if run:
                data.update(
                    plan=run.get("plan"),
                    plan_sha256=detail.get("plan_digest"),
                    run={"id": run["run_id"], "state": run["state"], "version": run["version"]},
                )
            if detail.get("action"):
                action = self.sentinel.action(incident["id"], self.principal)
                data["action"] = {
                    "id": action.action_id,
                    "state": action.state.value,
                    "version": action.version,
                    "effect_key": action.effect_key,
                    "binding_revision": action.spec.binding_revision,
                    "execution_scope": action.spec.execution_scope,
                    "authorized": bool(action.authorization),
                    "tool": "paypal_partial_refund@1",
                }
                # Financial receipt, rather than command receipts or unfiltered observations.
                for row in detail["evidence"]:
                    fact = row["data"]
                    if (
                        action.state.value == "Succeeded"
                        and row["id"] == (action.result or {}).get("receipt_reference")
                        and row["payload_digest"]
                        == ExecutionSpec.from_compiled(action.spec).payload_digest()
                        and fact.get("phase") == "VERIFIED_REFUND"
                        and fact.get("provider_status") == "COMPLETED"
                    ):
                        data["receipt"] = {
                            "id": row["id"],
                            "source": "SIMULATED_PROVIDER",
                            "phase": "VERIFIED_REFUND",
                            "refund_id": fact["refund_id"],
                            "status": "COMPLETED",
                            "amount": fact["amount"],
                            "currency": fact["currency"],
                            "payload_digest": row["payload_digest"],
                            "persisted": True,
                        }
        return DemoView.model_validate(data)

    async def generate(self):
        async with self.lock:
            if self.scenario in CASES:
                return await self.generate_lab()
            if self.incident():
                raise Problem("DEMO_PLAN_ALREADY_EXISTS", 409)
            if self.planning_mode == "local_ai":
                # No incident/Run/Approval/Action is written until model and policy pass.
                facts = await self.fake.capture("DEMO0000000000001")
                local = self.proposal_factory()
                proposal = await local.analyze(SAMPLE, facts.model_dump())
                amount = validate_policy(facts, proposal, self.settings)
                if amount != "25.00" or proposal.currency != "USD":
                    raise Problem("DEMO_PROPOSAL_AMOUNT_MISMATCH", 409)
                self.analyst.value = proposal
                (self.directory / "proposal.json").write_text(
                    json.dumps(
                        {
                            "source": "REAL_LOCAL_OLLAMA",
                            "model": "phi4-mini:latest",
                            "seconds": local.seconds,
                        }
                    ),
                    "utf-8",
                )
            await self.sentinel.analyze(
                RequestInput(capture_id="DEMO0000000000001", message=SAMPLE)
            )
            return self.view()

    async def generate_lab(self):
        # Evidence is not a gate/grant ledger. Never retry an interrupted or blocked decision;
        # a new synthetic case is required. All execution still uses Sentinel and public Runtime.
        if self.incident() or load_decision(self.directory):
            raise Problem("DEMO_DECISION_ALREADY_EXISTS", 409)
        case = CASES[self.scenario]
        evidence = {
            "source": "NOT_GENERATED",
            "reason": "ANALYSIS_INTERRUPTED",
            "facts": {"requested_amount": case.requested_amount},
        }
        save_decision(self.directory, evidence)
        local = None
        try:
            facts = await self.fake.capture("DEMO0000000000001")
            if self.planning_mode == "local_ai":
                local = self.proposal_factory()
                proposal = await local.analyze(case.message, facts.model_dump())
                evidence["source"] = "REAL_LOCAL_OLLAMA"
            else:
                proposal = fixture(self.scenario)
                evidence.update(
                    source="SIMULATED_DETERMINISTIC_FIXTURE",
                    model_output=proposal.model_dump_json(),
                )
            evidence.update(schema_verdict="PASS", recommendation=proposal.model_dump())
            verify_case(self.scenario, facts, proposal, self.settings)
            evidence.update(policy_verdict="PASS", reason="REQUEST_SUPPORTED_POLICY_PASS")
            self.analyst.value = proposal
            if local:
                (self.directory / "proposal.json").write_text(
                    json.dumps({"seconds": local.seconds}), "utf-8"
                )
            await self.sentinel.analyze(
                RequestInput(capture_id="DEMO0000000000001", message=case.message)
            )
        except Problem as exc:
            evidence.update(policy_verdict="BLOCKED", reason=exc.code)
            if exc.code == "INVALID_MODEL_RESPONSE":
                evidence["schema_verdict"] = "REJECTED"
        finally:
            if local:
                evidence.update(
                    model_output=local.model_output,
                    output_truncated=local.output_truncated,
                    model_seconds=local.seconds,
                )
                if local.model_output is not None:
                    evidence["source"] = "REAL_LOCAL_OLLAMA"
            save_decision(self.directory, evidence)
        return self.view()

    async def command(self, command):
        # Consumer serializes commands; CAS, grant/claim and effect protection remain in Runtime.
        async with self.lock:
            incident = self.incident()
            if not incident:
                raise Problem("DEMO_PLAN_REQUIRED", 409)
            self.sentinel.confirm_plan(incident["id"], command.plan_digest)
            view = self.view()
            operation = command.operation
            if operation == "approve":
                if view.run.state != "AwaitingApproval" or view.action:
                    raise Problem("DEMO_APPROVAL_NOT_PENDING", 409)
                self.sentinel.decide(
                    incident["id"],
                    DecisionCommand(
                        expected_version=command.expected_version,
                        plan_digest=command.plan_digest,
                        decision="approve",
                    ),
                    self.principal,
                )
                version = self.view().run.version
                self.sentinel.admit(
                    incident["id"],
                    ExecutionCommand(
                        expected_version=version,
                        plan_digest=command.plan_digest,
                        idempotency_key=command.idempotency_key,
                    ),
                    self.principal,
                )
            elif operation == "admit":
                if view.run.state != "Approved" or view.action:
                    raise Problem("DEMO_ADMISSION_NOT_PENDING", 409)
                self.sentinel.admit(
                    incident["id"],
                    ExecutionCommand(**command.model_dump(exclude={"operation", "confirmed"})),
                    self.principal,
                )
            elif operation == "authorize":
                if not view.action or view.action.state != "Pending":
                    raise Problem("DEMO_AUTHORIZATION_NOT_PENDING", 409)
                self.sentinel.authorize(
                    incident["id"],
                    ExecutionCommand(**command.model_dump(exclude={"operation", "confirmed"})),
                    self.principal,
                )
            else:
                if not view.action or view.action.state != "Authorized":
                    raise Problem("DEMO_ACTION_NOT_EXECUTABLE", 409)
                started = time.perf_counter()
                try:
                    await self.sentinel.execute(
                        incident["id"],
                        ExecutionCommand(**command.model_dump(exclude={"operation", "confirmed"})),
                        self.principal,
                    )
                finally:
                    self.execution_seconds = round(time.perf_counter() - started, 6)
            return self.view()


class DemoController:
    def __init__(self, root, *, delay=0.8, proposal_factory=LocalProposal):
        self.root = Path(root).absolute()
        if self.root.is_symlink():
            raise Problem("DEMO_ROOT_UNSAFE", 503)
        marker = self.root / "simulation.marker"
        if self.root.exists() and any(self.root.iterdir()):
            if not marker.is_file() or marker.read_text("ascii") != MARKER:
                raise Problem("DEMO_ROOT_UNSAFE", 503)
        else:
            self.root.mkdir(parents=True, exist_ok=True)
            marker.write_text(MARKER, "ascii")
        self.stack, self.sessions, self.delay = ExitStack(), {}, delay
        self.proposal_factory = proposal_factory

    def new(self, scenario, planning_mode="deterministic"):
        if scenario not in SCENARIOS:
            raise Problem("DEMO_SCENARIO_INVALID")
        if planning_mode not in {"deterministic", "local_ai"}:
            raise Problem("DEMO_PLANNING_MODE_INVALID")
        if len(list(self.root.iterdir())) >= 65:
            raise Problem("DEMO_SESSION_LIMIT", 429)
        directory = self.root / str(uuid4())
        provision(directory, demo_settings(planning_mode))
        (directory / "simulation.json").write_text(
            json.dumps({"marker": MARKER, "scenario": scenario, "planning_mode": planning_mode}),
            "utf-8",
        )
        return self.get(directory.name)

    def get(self, session_id):
        session_id = canonical_id(session_id)
        directory = self.root / session_id
        if (
            directory.is_symlink()
            or directory.resolve() != directory.absolute()
            or not (directory / "simulation.json").is_file()
        ):
            raise Problem("DEMO_SESSION_NOT_FOUND", 404)
        if any(p.is_symlink() for p in directory.iterdir()):
            raise Problem("DEMO_SESSION_INVALID", 409)
        metadata = json.loads((directory / "simulation.json").read_text("utf-8"))
        if (
            set(metadata) not in ({"marker", "scenario"}, {"marker", "scenario", "planning_mode"})
            or metadata["marker"] != MARKER
            or metadata["scenario"] not in SCENARIOS
            or metadata.get("planning_mode", "deterministic") not in {"deterministic", "local_ai"}
        ):
            raise Problem("DEMO_SESSION_INVALID", 409)
        if session_id not in self.sessions:
            self.sessions[session_id] = DemoSession(
                directory,
                metadata["scenario"],
                self.stack,
                delay=self.delay,
                planning_mode=metadata.get("planning_mode", "deterministic"),
                proposal_factory=self.proposal_factory,
            )
        return self.sessions[session_id]

    def close(self):
        self.stack.close()
