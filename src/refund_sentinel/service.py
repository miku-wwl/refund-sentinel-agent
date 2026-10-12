import hashlib
import json

from agentic_intent_gate.runtime import (
    ActionCommand,
    AdmissionCommand,
    ApprovalChoice,
    ApprovalDecisionRequest,
    Intent,
)

from .models import Problem, RefundInput, validate_policy
from .paypal import verified_refund


def plan_digest(plan):
    # Browser confirmation fingerprint; Runtime independently binds its exact persisted Plan.
    return hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class Sentinel:
    def __init__(self, runtime, store, paypal, analyst, settings):
        self.runtime, self.store, self.paypal = runtime, store, paypal
        self.analyst, self.settings = analyst, settings

    async def analyze(self, request):
        if request.capture_id not in self.settings.capture_ids:
            raise Problem("CAPTURE_NOT_ALLOWED")
        incident_id = self.store.reserve(
            request.capture_id,
            request.message,
            {"payment": self.settings.payment_mode, "ai": self.settings.ai_mode},
        )
        try:
            facts = await self.paypal.capture(request.capture_id)
            self.store.update(incident_id, capture=facts.model_dump())
            proposal = await self.analyst.analyze(request.message, facts.model_dump())
            self.store.update(incident_id, recommendation=proposal.model_dump())
            amount = validate_policy(facts, proposal, self.settings)
            args = RefundInput(
                incident_id=incident_id,
                capture_id=request.capture_id,
                amount=amount,
                currency=facts.currency,
            )
            self.store.update(incident_id, refund_arguments=args.model_dump(), policy="PASS")
            run = await self.runtime.run_service.create(
                Intent(json.dumps({"incident_id": incident_id}))
            )
            self.store.update(incident_id, run_id=run.run_id, analysis_state="READY")
        except Problem as exc:
            self.store.update(incident_id, analysis_state="BLOCKED", policy=exc.code)
        return self.view(incident_id)

    def view(self, incident_id, principal=None):
        incident = self.store.get(incident_id)
        if incident.get("run_id"):
            run = self.runtime.run_service.get(incident["run_id"])
            incident["run"] = run.to_dict()
            incident["plan_digest"] = plan_digest(run.plan.to_dict()) if run.plan else None
            # Supported public gateway read includes principal scope enforcement.
            actions = self.runtime.gateway.list_for_run(run.run_id, principal) if principal else []
            if actions:
                action = actions[0]
                incident["action"] = action.snapshot() | {"effect_key": action.effect_key}
                incident["evidence"] = self.store.observations(action.effect_key)
        return incident

    def confirm_plan(self, incident_id, digest):
        incident = self.store.get(incident_id)
        if not incident.get("run_id"):
            raise Problem("NO_EXECUTABLE_PLAN", 409)
        run = self.runtime.run_service.get(incident["run_id"])
        if not run.plan or digest != plan_digest(run.plan.to_dict()):
            raise Problem("PLAN_CONFIRMATION_MISMATCH", 409)
        return run

    def decide(self, incident_id, command, principal):
        run = self.confirm_plan(incident_id, command.plan_digest)
        self.runtime.run_service.decide(
            run.run_id,
            ApprovalDecisionRequest(
                ApprovalChoice.APPROVE if command.decision == "approve" else ApprovalChoice.REJECT,
                command.expected_version,
                "Merchant declined this proposed refund" if command.decision == "reject" else None,
            ),
        )
        return self.view(incident_id, principal)

    def admit(self, incident_id, command, principal):
        run = self.confirm_plan(incident_id, command.plan_digest)
        self.runtime.gateway.admit(
            AdmissionCommand(
                run.run_id, command.expected_version, principal.subject_id, command.idempotency_key
            ),
            principal,
        )
        return self.view(incident_id, principal)

    def action(self, incident_id, principal):
        incident = self.store.get(incident_id)
        if not incident.get("run_id"):
            raise Problem("NO_ACTION", 409)
        actions = self.runtime.gateway.list_for_run(incident["run_id"], principal)
        if len(actions) != 1:
            raise Problem("NO_ACTION", 409)
        return actions[0]

    def authorize(self, incident_id, command, principal):
        self.confirm_plan(incident_id, command.plan_digest)
        action = self.action(incident_id, principal)
        self.runtime.gateway.authorize(
            ActionCommand(action.action_id, command.expected_version, command.idempotency_key),
            principal,
        )
        return self.view(incident_id, principal)

    async def execute(self, incident_id, command, principal):
        self.confirm_plan(incident_id, command.plan_digest)
        action = self.action(incident_id, principal)
        await self.runtime.gateway.execute(
            ActionCommand(action.action_id, command.expected_version, command.idempotency_key),
            principal,
        )
        return self.view(incident_id, principal)

    async def verify(self, incident_id, principal):
        action = self.action(incident_id, principal)
        observations = self.store.observations(action.effect_key)
        refund_ids = [
            row["data"]["refund_id"] for row in observations if row["data"].get("refund_id")
        ]
        if not refund_ids:
            raise Problem("NO_REFUND_ID_AVAILABLE", 409)
        args = RefundInput.model_validate(dict(action.spec.normalized_arguments))
        result = verified_refund(
            await self.paypal.lookup_refund(refund_ids[-1]), args, expected_id=refund_ids[-1]
        )
        self.store.observe(
            action.effect_key,
            observations[0]["payload_digest"],
            phase="MANUAL_READ_ONLY_CHECK",
            source="fake" if self.settings.payment_mode == "offline" else "paypal-sandbox",
            **result,
        )
        # A read-only provider observation never changes an Unknown/Pending Runtime Action.
        return self.view(incident_id, principal)
