"""Reviewed startup profiles, never selected by Plans or request bodies."""

from dataclasses import asdict, dataclass

import httpx

from .config import SANDBOX_URL
from .models import Problem


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    seconds: int
    base_revision: str
    read_seconds: float
    dispatch_reserve_seconds: float

    def http_timeout(self):
        return httpx.Timeout(connect=1.1, read=self.read_seconds, write=1.1, pool=1.1)


LEGACY_PROFILE = ExecutionProfile("legacy-5s", 5, "refund-binding-v1", 2.0, 0.0)
SANDBOX_15_PROFILE = ExecutionProfile("paypal-sandbox-15s", 15, "refund-binding-v2", 4.0, 9.0)


def validate_profile(profile, settings):
    if type(profile) is not ExecutionProfile or profile not in (LEGACY_PROFILE, SANDBOX_15_PROFILE):
        raise Problem("UNREVIEWED_EXECUTION_PROFILE")
    if profile == SANDBOX_15_PROFILE and (
        settings.payment_mode != "sandbox"
        or settings.environment != "sandbox"
        or settings.paypal_base_url != SANDBOX_URL
    ):
        raise Problem("EXTENDED_PROFILE_REQUIRES_SANDBOX")
    return profile


def persisted_profile(identity, settings):
    value = identity.get("execution_profile")
    if value is None:
        return LEGACY_PROFILE
    if value != asdict(SANDBOX_15_PROFILE):
        raise Problem("PERSISTED_EXECUTION_PROFILE_MISMATCH")
    return validate_profile(SANDBOX_15_PROFILE, settings)
