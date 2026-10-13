"""Closed browser contracts. No raw Runtime rows or provider payloads cross this boundary."""

from typing import Annotated, Literal

from pydantic import Field

from .models import Recommendation, RefundInput, StrictModel

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class PlanStep(StrictModel):
    tool_name: Literal["paypal_partial_refund"]
    tool_version: Literal["1"]
    arguments: RefundInput


class PresentedPlan(StrictModel):
    goal: str = Field(max_length=500)
    target: Literal["paypal-sandbox-refunds"]
    steps: list[PlanStep] = Field(min_length=1, max_length=1)
    risk_class: Literal["SIDE_EFFECT"]


class ProofRuntime(StrictModel):
    version: Literal["0.2.0"]
    commit: Literal["7261fdd2f47d2b15fabe8faac527eeee37338eb1"]
    profile: Literal["paypal-sandbox-15s"]
    adapter_seconds: Literal[15]
    binding_revision: Literal["refund-binding-v2.exec-15s"]
    execution_scope: str


class ProofPayment(StrictModel):
    capture_id: Literal["1YA65594665951620"]
    order_id: Literal["3KT99923NY800615C"]
    merchant_id: Literal["EZL4XDY2TTLVW"]
    gross_amount: Literal["20.00"]
    currency: Literal["NZD"]
    buyer_identity: Literal["VERIFIED_INDEPENDENT_PRIVATE_REFERENCE"]
    refund_balance_ledger: Literal["NOT_AUTHORITATIVE_COMPLETE_LEDGER"]


class ProofAnalysis(StrictModel):
    source: Literal["REAL_LOCAL_OLLAMA"]
    model: Literal["phi4-mini:latest"]
    incident_description: str
    incident_is_synthetic: Literal[True]
    recommendation: Recommendation
    plan: PresentedPlan
    plan_review_sha256: Digest


class ProofExecution(StrictModel):
    run_id: str
    action_id: Literal["26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1"]
    action_state: Literal["Succeeded"]
    action_version: Literal[4]
    refund_id: Literal["1XN74010T5365280D"]
    refund_status: Literal["COMPLETED"]
    amount: Literal["5.00"]
    currency: Literal["NZD"]
    financial_post_count: Literal[1]
    gateway_seconds: float
    post_http_status: Literal[201]
    post_seconds: float
    verification_http_status: Literal[200]
    verification_seconds: float
    receipt_id: Literal["e1415750-0971-4347-a88d-a3704dbb79c8"]
    receipt_persisted: Literal[True]
    independent_new_process_verification: Literal[True]
    three_separate_human_gates_recorded: Literal[True]


class HistoricalFailure(StrictModel):
    action_id: Literal["5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5"]
    state: Literal["Failed"]
    version: Literal[4]
    financial_post_count: Literal[0]


class HistoricalProof(StrictModel):
    schema_version: Literal[1]
    evidence_kind: Literal["HISTORICAL_VERIFIED_PAYPAL_SANDBOX"]
    observed_at: str
    runtime: ProofRuntime
    payment: ProofPayment
    analysis: ProofAnalysis
    execution: ProofExecution
    historical_failed_case: HistoricalFailure
    limitations: list[str]


class NewDemo(StrictModel):
    scenario: Literal["completed", "unknown", "rejected"] = "completed"
    planning_mode: Literal["deterministic", "local_ai"] = "deterministic"


class DemoCommand(StrictModel):
    operation: Literal["approve", "admit", "authorize", "execute"]
    expected_version: int = Field(ge=1, le=10)
    plan_digest: Digest
    idempotency_key: str = Field(pattern=r"^[0-9a-f-]{36}$")
    confirmed: Literal[True]


class DemoRun(StrictModel):
    id: str
    state: str = Field(max_length=32)
    version: int


class DemoAction(StrictModel):
    id: str
    state: Literal["Pending", "Authorized", "Executing", "Succeeded", "Failed", "Unknown"]
    version: int
    effect_key: str
    binding_revision: str
    execution_scope: str
    authorized: bool
    tool: Literal["paypal_partial_refund@1"]


class DemoReceipt(StrictModel):
    id: str
    source: Literal["SIMULATED_PROVIDER"]
    phase: Literal["VERIFIED_REFUND"]
    refund_id: str
    status: Literal["COMPLETED"]
    amount: Literal["25.00"]
    currency: Literal["USD"]
    payload_digest: Digest
    persisted: Literal[True]


class DemoView(StrictModel):
    mode: Literal["DEMO MODE — SIMULATED"] = "DEMO MODE — SIMULATED"
    session_id: str
    scenario: Literal["completed", "unknown", "rejected"]
    capture_id: Literal["DEMO0000000000001"] = "DEMO0000000000001"
    merchant_id: Literal["DEMO-MERCHANT"] = "DEMO-MERCHANT"
    original_amount: Literal["120.00"] = "120.00"
    amount: Literal["25.00"] = "25.00"
    currency: Literal["USD"] = "USD"
    planning_mode: Literal["deterministic", "local_ai"] = "deterministic"
    analysis_source: Literal[
        "SIMULATED_DETERMINISTIC_FIXTURE", "NOT_GENERATED", "REAL_LOCAL_OLLAMA"
    ] = "SIMULATED_DETERMINISTIC_FIXTURE"
    model: Literal["phi4-mini:latest"] | None = None
    model_seconds: float | None = None
    incident_description: str
    recommendation: Recommendation | None = None
    plan: PresentedPlan | None = None
    plan_sha256: Digest | None = None
    run: DemoRun | None = None
    action: DemoAction | None = None
    receipt: DemoReceipt | None = None
    simulated_dispatches: int
    execution_seconds: float | None = None
    adapter_seconds: Literal[5] = 5
