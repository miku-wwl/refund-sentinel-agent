import os
import re
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator

from .models import CaptureId, Money, Problem, StrictModel

SANDBOX_URL = "https://api-m.sandbox.paypal.com"
PINNED_COMMIT = "fd742b783058a53400c465b4ab59c6e80715895a"
PAYPAL_ENV_FIELDS = {
    "payment_mode": "PAYMENT_MODE",
    "environment": "PAYPAL_ENVIRONMENT",
    "paypal_base_url": "PAYPAL_BASE_URL",
    "client_id": "PAYPAL_CLIENT_ID",
    "client_secret": "PAYPAL_CLIENT_SECRET",
}


def verify_python_version():
    if sys.version_info[:2] != (3, 13):
        raise Problem("PYTHON_313_REQUIRED", 503)


def env_fields(mapping):
    data = {key: os.environ[name] for key, name in mapping.items() if name in os.environ}
    for key in ("client_id", "client_secret", "llm_api_key"):
        if key in data:
            data[key] = SecretStr(data[key])
    return data


class SandboxOAuthSettings(StrictModel):
    """Auth-only configuration; normal Settings still requires merchant and capture evidence."""

    payment_mode: Literal["sandbox"]
    environment: Literal["sandbox"] = "sandbox"
    paypal_base_url: Literal["https://api-m.sandbox.paypal.com"] = SANDBOX_URL
    client_id: SecretStr
    client_secret: SecretStr

    @model_validator(mode="after")
    def credentials(self):
        if (
            not self.client_id.get_secret_value().strip()
            or not self.client_secret.get_secret_value()
        ):
            raise ValueError("Missing Sandbox OAuth credentials")
        return self

    @classmethod
    def from_env(cls):
        if os.environ.get("PAYMENT_MODE") != "sandbox":
            raise Problem("SANDBOX_CHECK_REQUIRES_SANDBOX_MODE")
        if not os.environ.get("PAYPAL_CLIENT_ID") or not os.environ.get("PAYPAL_CLIENT_SECRET"):
            raise Problem("BLOCKED_CREDENTIALS")
        return cls(**env_fields(PAYPAL_ENV_FIELDS))


class Settings(StrictModel):
    payment_mode: Literal["offline", "sandbox"] = "offline"
    ai_mode: Literal["deterministic", "real"] = "deterministic"
    environment: Literal["sandbox"] = "sandbox"
    paypal_base_url: Literal["https://api-m.sandbox.paypal.com"] = SANDBOX_URL
    merchant_id: str = Field(default="DEMO-MERCHANT", pattern=r"^[A-Za-z0-9-]{1,64}$")
    capture_ids: tuple[CaptureId, ...] = ("DEMO0000000000001",)
    max_refund: Money = "100.00"
    client_id: SecretStr = SecretStr("")
    client_secret: SecretStr = SecretStr("")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_format: Literal["json_object", "json_schema"] = "json_object"

    @field_validator("llm_base_url")
    @classmethod
    def safe_llm_url(cls, value):
        if not value:
            return value
        url = urlsplit(value)
        if (
            url.username
            or url.password
            or url.query
            or url.fragment
            or not url.hostname
            or (
                url.scheme != "https"
                and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
            )
        ):
            raise ValueError("LLM endpoint must use HTTPS or loopback HTTP without credentials")
        return value.rstrip("/")

    @model_validator(mode="after")
    def credentials(self):
        if not self.capture_ids:
            raise ValueError("Explicit capture allowlist is required")
        if self.payment_mode == "sandbox" and (
            not self.client_id.get_secret_value()
            or not self.client_secret.get_secret_value()
            or self.merchant_id == "DEMO-MERCHANT"
        ):
            raise ValueError("Missing PayPal Sandbox credentials or merchant identity")
        if self.payment_mode == "sandbox" and not re.fullmatch(r"[A-Z0-9]{13}", self.merchant_id):
            raise ValueError(
                "Sandbox merchant ID must be a merchant identity, not an email/app name"
            )
        if self.payment_mode == "sandbox" and any(x.startswith("DEMO") for x in self.capture_ids):
            raise ValueError("Offline capture fixtures are forbidden in Sandbox mode")
        if self.ai_mode == "real" and (not self.llm_base_url or not self.llm_model):
            raise ValueError("Missing real AI endpoint or model")
        return self

    def identity(self):
        return {
            key: getattr(self, key)
            for key in ("payment_mode", "ai_mode", "merchant_id", "max_refund")
        } | {"capture_ids": list(self.capture_ids)}

    @classmethod
    def from_env(cls):
        mapping = PAYPAL_ENV_FIELDS | {
            "ai_mode": "AI_MODE",
            "merchant_id": "PAYPAL_MERCHANT_ID",
            "max_refund": "MAX_REFUND",
            "llm_base_url": "LLM_BASE_URL",
            "llm_model": "LLM_MODEL",
            "llm_api_key": "LLM_API_KEY",
            "llm_format": "LLM_FORMAT",
        }
        data = env_fields(mapping)
        if "PAYPAL_CAPTURE_IDS" in os.environ:
            data["capture_ids"] = tuple(
                x.strip() for x in os.environ["PAYPAL_CAPTURE_IDS"].split(",") if x.strip()
            )
        elif data.get("payment_mode") == "sandbox":
            data["capture_ids"] = ()
        return cls(**data)


def read_env(path=Path(".env")):
    """Return private literal values to trusted code only; never use this mapping as diagnostics."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or name in values:
            raise ValueError("Invalid .env line")
        values[name] = value.strip().strip("\"'")
    return values


def load_env(path=Path(".env")):
    """Preserve private file/process values; reject conflicting inherited configuration."""
    values = read_env(path)
    conflicts = sorted(
        name for name, value in values.items() if name in os.environ and os.environ[name] != value
    )
    if conflicts:
        raise Problem("ENVIRONMENT_OVERRIDE_CONFLICT:" + ",".join(conflicts))
    for name, value in values.items():
        os.environ.setdefault(name, value)
