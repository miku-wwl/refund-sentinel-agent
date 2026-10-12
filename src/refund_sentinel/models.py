import json
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

CaptureId = Annotated[str, Field(pattern=r"^[A-Z0-9]{17}$")]
Money = Annotated[str, Field(pattern=r"^[0-9]{1,7}\.[0-9]{2}$")]


class Problem(Exception):
    """Allowlisted diagnostic; never expose remote bodies or exception strings."""

    def __init__(self, code: str, status: int = 422):
        self.code, self.status = code, status
        super().__init__(code)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RequestInput(StrictModel):
    capture_id: CaptureId
    message: str = Field(min_length=5, max_length=2000)


class Recommendation(StrictModel):
    recommendation: Literal["REFUND", "REVIEW", "REJECT"]
    requested_amount: Money | None
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None
    explanation: str = Field(min_length=1, max_length=500)
    reason_code: Literal["DAMAGED_ITEM", "NOT_RECEIVED", "DUPLICATE", "OTHER", "UNCLEAR"]
    uncertainty: Literal["LOW", "MEDIUM", "HIGH"]


class CaptureFacts(StrictModel):
    capture_id: CaptureId
    order_id: CaptureId
    merchant_id: str = Field(min_length=1, max_length=64)
    amount: Money
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    status: str = Field(min_length=1, max_length=32)
    prior_refunds: bool
    source: Literal["fake", "paypal-sandbox"]


class RefundInput(StrictModel):
    incident_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    capture_id: CaptureId
    amount: Money
    currency: str = Field(pattern=r"^[A-Z]{3}$")


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 16384:
        raise ValueError("Response too large")
    return json.loads(raw, object_pairs_hook=pairs)


def validate_capture_policy(facts: CaptureFacts, settings):
    """Payment eligibility only; does not invent a recommendation or authorize a refund."""
    if facts.capture_id not in settings.capture_ids:
        raise Problem("CAPTURE_NOT_ALLOWED")
    if facts.source != ("fake" if settings.payment_mode == "offline" else "paypal-sandbox"):
        raise Problem("PROVIDER_MODE_MISMATCH")
    if facts.merchant_id != settings.merchant_id:
        raise Problem("MERCHANT_MISMATCH")
    if facts.status != "COMPLETED" or facts.prior_refunds:
        raise Problem("CAPTURE_NOT_ELIGIBLE")
    if facts.currency not in {"USD", "NZD"}:
        raise Problem("UNSUPPORTED_CURRENCY")
    if Decimal(facts.amount) <= Decimal("0.01") or Decimal(settings.max_refund) < Decimal("0.01"):
        raise Problem("AMOUNT_OUTSIDE_POLICY")


def validate_policy(facts: CaptureFacts, proposal: Recommendation, settings):
    validate_capture_policy(facts, settings)
    if proposal.recommendation != "REFUND" or proposal.uncertainty == "HIGH":
        raise Problem("MANUAL_REVIEW_REQUIRED")
    if proposal.currency != facts.currency or proposal.requested_amount is None:
        raise Problem("CURRENCY_OR_AMOUNT_MISMATCH")
    amount = Decimal(proposal.requested_amount)
    if not Decimal("0") < amount < Decimal(facts.amount) or amount > Decimal(settings.max_refund):
        raise Problem("AMOUNT_OUTSIDE_POLICY")
    return proposal.requested_amount
