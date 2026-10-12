import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator

from .models import CaptureId, Money, StrictModel

SANDBOX_URL = "https://api-m.sandbox.paypal.com"
PINNED_COMMIT = "fd742b783058a53400c465b4ab59c6e80715895a"


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
        mapping = {
            "payment_mode": "PAYMENT_MODE",
            "ai_mode": "AI_MODE",
            "environment": "PAYPAL_ENVIRONMENT",
            "paypal_base_url": "PAYPAL_BASE_URL",
            "merchant_id": "PAYPAL_MERCHANT_ID",
            "max_refund": "MAX_REFUND",
            "client_id": "PAYPAL_CLIENT_ID",
            "client_secret": "PAYPAL_CLIENT_SECRET",
            "llm_base_url": "LLM_BASE_URL",
            "llm_model": "LLM_MODEL",
            "llm_api_key": "LLM_API_KEY",
            "llm_format": "LLM_FORMAT",
        }
        data = {key: os.environ[name] for key, name in mapping.items() if name in os.environ}
        for key in ("client_id", "client_secret", "llm_api_key"):
            if key in data:
                data[key] = SecretStr(data[key])
        if "PAYPAL_CAPTURE_IDS" in os.environ:
            data["capture_ids"] = tuple(
                x.strip() for x in os.environ["PAYPAL_CAPTURE_IDS"].split(",") if x.strip()
            )
        return cls(**data)


def load_env(path=Path(".env")):
    """Small literal dotenv reader; no expansion, execution, or implicit environment override."""
    if not path.exists():
        return
    for line in path.read_text("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or not name.replace("_", "").isalnum():
            raise ValueError("Invalid .env line")
        os.environ.setdefault(name, value.strip().strip("\"'"))
