import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from refund_sentinel.config import Settings
from refund_sentinel.integration import provision
from refund_sentinel.paypal import FakePayPal
from refund_sentinel.web import create_app


@pytest.fixture(autouse=True)
def forbid_real_http_in_regression_tests(monkeypatch):
    """Every regression uses ASGI, fake provider or MockTransport; fail before any real socket."""

    async def forbidden_async(*args, **kwargs):
        raise AssertionError("Offline regression tests cannot use a real HTTP transport")

    def forbidden_sync(*args, **kwargs):
        raise AssertionError("Offline regression tests cannot use a real HTTP transport")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden_sync)


@pytest.fixture
def environment(tmp_path):
    settings = Settings()
    provision(tmp_path, settings)
    return tmp_path, settings


@pytest.fixture
def browser(environment):
    directory, settings = environment
    fake = FakePayPal(directory / "fake-paypal.sqlite3")
    app = create_app(directory, settings, predecessor_stopped=True, paypal=fake)
    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        client.headers["Authorization"] = "Bearer " + (directory / "operator.capability").read_text(
            "ascii"
        )
        yield client, fake, app


def analyze(client, message="The item arrived damaged. Please refund USD 25.00."):
    response = client.post(
        "/api/incidents", json={"capture_id": "DEMO0000000000001", "message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()


def command(data, *, action=False, **extra):
    return {
        "expected_version": data["action" if action else "run"]["version"],
        "plan_digest": data["plan_digest"],
        **extra,
    }


def step(client, data, operation, *, key=None):
    body = command(
        data, action=operation in {"authorize", "execute"}, idempotency_key=key or str(uuid4())
    )
    response = client.post(f"/api/incidents/{data['id']}/{operation}", json=body)
    assert response.status_code == 200, response.text
    return response.json(), body


def approved(client, data):
    response = client.post(
        f"/api/incidents/{data['id']}/decision", json=command(data, decision="approve")
    )
    assert response.status_code == 200, response.text
    return response.json()


def ready(client):
    data = approved(client, analyze(client))
    data, _ = step(client, data, "admit")
    data, _ = step(client, data, "authorize")
    return data


def synthetic_recommendation(**overrides):
    return json.dumps(
        {
            "recommendation": "REFUND",
            "requested_amount": "25.00",
            "currency": "USD",
            "explanation": "Synthetic test",
            "reason_code": "OTHER",
            "uncertainty": "LOW",
            **overrides,
        }
    )
