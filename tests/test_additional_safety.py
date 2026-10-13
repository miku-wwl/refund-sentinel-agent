import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from conftest import command, ready, step
from fastapi.testclient import TestClient
from test_providers import CAPTURE, sandbox_settings

from refund_sentinel.paypal import FakePayPal, ProviderError, SandboxPayPal
from refund_sentinel.web import create_app


@pytest.mark.parametrize(
    "amount,currency,key",
    [
        ("NaN", "USD", str(uuid4())),
        (25.0, "USD", str(uuid4())),
        ("0.00", "USD", str(uuid4())),
        ("101.00", "USD", str(uuid4())),
        ("25.001", "USD", str(uuid4())),
        ("25.00", "JPY", str(uuid4())),
        ("25.00", "USD", ""),
        ("25.00", "USD", "not-a-uuid"),
    ],
)
def test_real_client_invalid_money_and_idempotency_never_posts(amount, currency, key):
    async def scenario():
        calls = []

        def handler(request):
            calls.append(request)
            assert request.url.path == "/v1/oauth2/token"
            return httpx.Response(
                200,
                json={"access_token": "synthetic-token", "token_type": "Bearer", "expires_in": 300},
            )

        client = SandboxPayPal(sandbox_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError):
            await client.refund(CAPTURE, amount, currency, key)
        assert not any("/refund" in r.url.path for r in calls)
        await client.close()

    asyncio.run(scenario())


def test_concurrent_incident_reservation(browser):
    client, fake, _ = browser

    def submit(_):
        return client.post(
            "/api/incidents",
            json={"capture_id": "DEMO0000000000001", "message": "Please refund USD 25.00."},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert fake.recorded_calls() == []


def test_actual_runtime_deadline_after_committed_fake_effect(environment):
    class SlowAcknowledgement(FakePayPal):
        async def refund(self, *args, **kwargs):
            response = await super().refund(*args, **kwargs)
            await asyncio.sleep(10)  # The unmodified Runtime cancels after its real 5-second limit.
            return response

    path, settings = environment
    fake = SlowAcknowledgement(path / "fake-paypal.sqlite3")
    with TestClient(
        create_app(path, settings, paypal=fake, predecessor_stopped=True),
        base_url="http://127.0.0.1",
        raise_server_exceptions=False,
    ) as client:
        client.headers["Authorization"] = "Bearer " + (path / "operator.capability").read_text()
        data, _ = step(client, ready(client), "execute")
        assert data["action"]["state"] == "Unknown"
        assert len(fake.recorded_calls()) == len(fake.persisted_refunds()) == 1
    # Restart cannot turn that ambiguous effect into another dispatch.
    with TestClient(
        create_app(path, settings, predecessor_stopped=True),
        base_url="http://127.0.0.1",
        raise_server_exceptions=False,
    ) as client:
        client.headers["Authorization"] = "Bearer " + (path / "operator.capability").read_text()
        observed = client.get(f"/api/incidents/{data['id']}").json()
        assert observed["action"]["state"] == "Unknown"
        response = client.post(
            f"/api/incidents/{data['id']}/execute",
            json=command(observed, action=True, idempotency_key=str(uuid4())),
        )
        assert response.status_code == 409 and len(fake.recorded_calls()) == 1
        with sqlite3.connect(path / "fake-paypal.sqlite3") as db:
            assert db.execute("SELECT count(*) FROM refunds").fetchone()[0] == 1
