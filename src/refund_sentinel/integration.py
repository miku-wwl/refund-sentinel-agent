import importlib.metadata
import json
from contextlib import contextmanager
from dataclasses import asdict
from uuid import UUID, uuid4

from agentic_intent_gate.runtime import (
    EXTERNAL_PAYLOAD_REVISION,
    BoundCapabilityAuthorization,
    CapabilityVerifier,
    ExecutableRegistry,
    Outcome,
    ToolBinding,
    ToolCapability,
    ToolOutcome,
    execution_budget_binding,
    open_runtime,
    provision_capability,
)

from .config import PINNED_COMMIT, verify_python_version
from .llm import ChatCompletionsAnalyst, DeterministicAnalyst
from .models import CaptureFacts, Problem, Recommendation, RefundInput, validate_policy
from .paypal import (
    FakePayPal,
    ProviderError,
    SandboxPayPal,
    execution_stopped,
    identifier,
    paypal_http_attempt,
    refund_budget_checkpoint,
    verified_refund,
)
from .profiles import LEGACY_PROFILE, SANDBOX_15_PROFILE, persisted_profile, validate_profile
from .store import Store

ARGUMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["incident_id", "capture_id", "amount", "currency"],
    "properties": {
        "incident_id": {
            "type": "string",
            "minLength": 36,
            "maxLength": 36,
            "pattern": "^[0-9a-f-]{36}$",
        },
        "capture_id": {
            "type": "string",
            "minLength": 17,
            "maxLength": 17,
            "pattern": "^[A-Z0-9]{17}$",
        },
        "amount": {
            "type": "string",
            "minLength": 4,
            "maxLength": 10,
            "pattern": "^[0-9]{1,7}\\.[0-9]{2}$",
        },
        "currency": {"type": "string", "minLength": 3, "maxLength": 3, "pattern": "^(USD|NZD)$"},
    },
}


def verify_distribution():
    verify_python_version()
    dist = importlib.metadata.distribution("agentic-intent-gate")
    direct = json.loads(dist.read_text("direct_url.json") or "{}")
    if dist.version != "0.2.0" or direct.get("vcs_info", {}).get("commit_id") != PINNED_COMMIT:
        raise Problem("RUNTIME_PIN_MISMATCH", 503)
    return {"version": dist.version, "commit": PINNED_COMMIT}


def provision(directory, settings, *, profile=LEGACY_PROFILE):
    verify_distribution()
    validate_profile(profile, settings)
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise Problem("PROVISION_REQUIRES_EMPTY_DIRECTORY")
    binding = ToolBinding(
        "paypal_partial_refund",
        "1",
        "paypal-sandbox-adapter",
        profile.base_revision,
        "paypal-sandbox-refunds",
        str(uuid4()),
    )
    binding = execution_budget_binding(binding, profile.seconds)
    provision_capability(directory / "operator.capability")
    (directory / "identity.json").write_text(
        json.dumps(
            {"binding": asdict(binding), "configuration": settings.identity()}
            | ({"execution_profile": asdict(profile)} if profile != LEGACY_PROFILE else {}),
            indent=2,
        ),
        "utf-8",
    )
    Store(
        directory / "application.sqlite3",
        binding=binding if profile != LEGACY_PROFILE else None,
        profile=profile if profile != LEGACY_PROFILE else None,
    ).provision()
    if settings.payment_mode == "offline":
        FakePayPal.provision(directory / "fake-paypal.sqlite3", settings)


class IncidentPlanProvider:
    """Compile a validated model recommendation with trusted host identities; no model tools."""

    def __init__(self, store, binding):
        self.store, self.binding = store, binding

    async def generate_plan(self, intent, **kwargs):
        incident = self.store.get(json.loads(intent.text)["incident_id"])
        return json.dumps(
            {
                "goal": "Issue one reviewed partial refund for this incident",
                "target": self.binding.target,
                "steps": [
                    {
                        "tool_name": self.binding.tool_name,
                        "tool_version": self.binding.tool_version,
                        "arguments": incident["refund_arguments"],
                    }
                ],
                "risk_class": "SIDE_EFFECT",
            }
        )


class RefundExecutor:
    def __init__(self, store, binding, settings, paypal, *, profile=LEGACY_PROFILE):
        self.store, self.binding, self.settings, self.paypal = store, binding, settings, paypal
        self.profile = validate_profile(profile, settings)

    def validate_arguments(self, arguments):
        args = RefundInput.model_validate(dict(arguments))
        if str(UUID(args.incident_id)) != args.incident_id:
            raise Problem("INVALID_INCIDENT_ID")
        incident = self.store.get(args.incident_id)
        if args.model_dump() != incident.get("refund_arguments"):
            raise Problem("PLAN_ARGUMENTS_MISMATCH")
        validate_policy(
            CaptureFacts.model_validate(incident["capture"]),
            Recommendation.model_validate(incident["recommendation"]),
            self.settings,
        )
        return args, incident

    async def execute(self, spec, effect_key, context):
        with paypal_http_attempt(
            context, dispatch_reserve_seconds=self.profile.dispatch_reserve_seconds
        ):
            return await self._execute(spec, effect_key, context)

    async def _execute(self, spec, effect_key, context):
        def outcome(category, receipt=None, reason=None):
            return ToolOutcome(
                category,
                effect_key,
                spec.execution_scope,
                spec.target,
                digest,
                receipt,
                reason,
            )

        digest = spec.payload_digest()
        if execution_stopped(context):
            return outcome(Outcome.UNKNOWN_OUTCOME)
        try:
            if (
                not self.binding.matches(spec)
                or spec.identity_revision != EXTERNAL_PAYLOAD_REVISION
            ):
                raise Problem("BINDING_MISMATCH")
            if (
                str(UUID(effect_key)) != effect_key
                or str(UUID(context.attempt_id)) != context.attempt_id
            ):
                raise Problem("INVALID_EFFECT_ID")
            args, incident = self.validate_arguments(spec.arguments)
            if execution_stopped(context):
                return outcome(Outcome.UNKNOWN_OUTCOME)
            latest = await self.paypal.capture(
                args.capture_id, expected_order_id=incident["capture"]["order_id"]
            )
            if execution_stopped(context):
                return outcome(Outcome.UNKNOWN_OUTCOME)
            validate_policy(
                latest, Recommendation.model_validate(incident["recommendation"]), self.settings
            )
            if latest.model_dump() != incident["capture"]:
                raise Problem("PAYMENT_FACTS_CHANGED")
            if self.profile.dispatch_reserve_seconds:
                await refund_budget_checkpoint(context)
        except (Problem, ValueError, TypeError) as exc:
            self.store.observe(
                effect_key,
                digest,
                phase="PRECHECK_REJECTED",
                error=exc.code if isinstance(exc, Problem) else "INPUT_REJECTED",
            )
            if execution_stopped(context):
                return outcome(Outcome.UNKNOWN_OUTCOME)
            return outcome(Outcome.CONFIRMED_FAILURE, reason="INPUT_REJECTED")
        if execution_stopped(context):
            return outcome(Outcome.UNKNOWN_OUTCOME)
        # Observations are evidence, never authorization or a replacement for durable claiming.
        self.store.observe(
            effect_key,
            digest,
            phase="REFUND_DISPATCH",
            source=latest.source,
            request_id=effect_key,
            capture_id=args.capture_id,
            amount=args.amount,
            currency=args.currency,
        )
        try:
            # This must follow the synchronous dispatch commit. The client rechecks after OAuth
            # and HTTPX preparation, using this same public Runtime attempt context.
            await refund_budget_checkpoint(context)
            response = await self.paypal.refund(
                args.capture_id, args.amount, args.currency, effect_key, context=context
            )
        except ProviderError as exc:
            self.store.observe(
                effect_key,
                digest,
                phase="REFUND_ERROR",
                error=exc.code,
                definitive_no_effect=exc.no_effect,
            )
            if execution_stopped(context):
                return outcome(Outcome.UNKNOWN_OUTCOME)
            return outcome(
                Outcome.CONFIRMED_FAILURE if exc.no_effect else Outcome.UNKNOWN_OUTCOME,
                reason="INPUT_REJECTED" if exc.no_effect else None,
            )
        try:
            refund_id = identifier(response["id"])
            # Save available safe evidence before the extra GET (which can time out).
            self.store.observe(
                effect_key,
                digest,
                phase="REFUND_RESPONSE",
                refund_id=refund_id,
                source=latest.source,
                provider_status=(
                    response.get("status")
                    if response.get("status") in {"COMPLETED", "PENDING", "FAILED", "CANCELLED"}
                    else "UNRECOGNIZED"
                ),
            )
            if execution_stopped(context):
                return outcome(Outcome.UNKNOWN_OUTCOME)
            verified = verified_refund(
                await self.paypal.lookup_refund(refund_id), args, expected_id=refund_id
            )
            receipt = self.store.observe(
                effect_key, digest, phase="VERIFIED_REFUND", source=latest.source, **verified
            )
            if execution_stopped(context) or verified["provider_status"] != "COMPLETED":
                return outcome(Outcome.UNKNOWN_OUTCOME)
            return outcome(Outcome.SUCCESS, receipt=receipt)
        except (Problem, ValueError, KeyError, TypeError):
            self.store.observe(effect_key, digest, phase="VERIFICATION_UNCERTAIN")
            return outcome(Outcome.UNKNOWN_OUTCOME)


@contextmanager
def composition(
    directory,
    settings,
    *,
    paypal=None,
    analyst=None,
    provider=None,
    predecessor_stopped=False,
    profile=None,
):
    verify_distribution()
    directory = directory.resolve()
    identity = json.loads((directory / "identity.json").read_text("utf-8"))
    stored_profile = persisted_profile(identity, settings)
    if profile is not None and validate_profile(profile, settings) != stored_profile:
        raise Problem("PERSISTED_EXECUTION_PROFILE_MISMATCH")
    profile = stored_profile
    if identity["configuration"] != settings.identity():
        raise Problem("PERSISTED_CONFIGURATION_MISMATCH", 503)
    binding = ToolBinding(**identity["binding"])
    if profile == SANDBOX_15_PROFILE and binding.binding_revision != "refund-binding-v2.exec-15s":
        raise Problem("PERSISTED_EXECUTION_PROFILE_MISMATCH")
    store = Store(
        directory / "application.sqlite3",
        binding=binding if profile != LEGACY_PROFILE else None,
        profile=profile if profile != LEGACY_PROFILE else None,
    )
    if profile != LEGACY_PROFILE:
        store.check_identity()
    paypal = paypal or (
        FakePayPal(directory / "fake-paypal.sqlite3")
        if settings.payment_mode == "offline"
        else SandboxPayPal(settings, http_timeout=profile.http_timeout())
    )
    analyst = analyst or (
        DeterministicAnalyst()
        if settings.ai_mode == "deterministic"
        else ChatCompletionsAnalyst(settings)
    )
    executor = RefundExecutor(store, binding, settings, paypal, profile=profile)

    def semantics(arguments, target):
        try:
            executor.validate_arguments(arguments)
        except (Problem, ValueError, TypeError):
            return "REFUND_POLICY_REJECTED"
        return None

    capability = ToolCapability(
        binding,
        "Issue one approved Sandbox partial refund",
        ARGUMENT_SCHEMA,
        semantic_rule=semantics,
    )
    verifier = CapabilityVerifier(
        (directory / "operator.capability").read_text("ascii"),
        subject_id="merchant-operator",
        binding=binding,
        operations=("read", "admit", "authorize", "execute"),
    )
    registry = ExecutableRegistry(executor, binding=binding)
    with open_runtime(
        gate_path=directory / "gate.sqlite3",
        provider=provider or IncidentPlanProvider(store, binding),
        capability=capability,
        registry=registry,
        verifier=verifier,
        policy=BoundCapabilityAuthorization(verifier, policy_revision="refund-policy-v1"),
        predecessor_stopped=predecessor_stopped,
        execution_timeout_seconds=profile.seconds,
    ) as runtime:
        yield runtime, store, paypal, analyst, executor
