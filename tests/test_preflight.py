import asyncio
import json
import sys
import tomllib
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from test_providers import CAPTURE, ORDER, capture_data, order_data, sandbox_settings

from refund_sentinel import cli
from refund_sentinel.config import SandboxOAuthSettings, Settings, load_env, verify_python_version
from refund_sentinel.models import Problem
from refund_sentinel.paypal import SandboxPayPal, SandboxReadOnlyTransport
from refund_sentinel.preflight import auth_report, capture_report


def auth_settings():
    return SandboxOAuthSettings(
        payment_mode="sandbox",
        client_id=SecretStr("fixture-client-id"),
        client_secret=SecretStr("fixture-client-secret"),
    )


def token_response():
    return {"access_token": "fixture-access-token", "token_type": "Bearer", "expires_in": 300}


def test_auth_only_validates_cache_and_redacts():
    async def scenario():
        requests = []

        def handler(request):
            requests.append((request.method, request.url.path))
            assert request.url.host == "api-m.sandbox.paypal.com"
            return httpx.Response(200, json=token_response())

        client = SandboxPayPal(
            auth_settings(), read_only=True, transport=httpx.MockTransport(handler)
        )
        report = await auth_report(auth_settings(), client=client)
        assert report["status"] == "PASS" and report["source"] == "MOCK"
        assert report["token_cache_reused"] and report["elapsed_seconds"] >= 0
        assert requests == [("POST", "/v1/oauth2/token")]
        assert report["payment_mutation_requests"] == 0
        assert "fixture-" not in json.dumps(report)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "response,code",
    [
        (
            httpx.Response(401, json={"error": "PRIVATE_CREDENTIAL_ERROR"}),
            "PAYPAL_AUTH_CREDENTIALS_REJECTED",
        ),
        (
            httpx.Response(403, json={"error": "PRIVATE_CREDENTIAL_ERROR"}),
            "PAYPAL_AUTH_CREDENTIALS_REJECTED",
        ),
        (httpx.Response(500, text="PRIVATE_PROVIDER_BODY"), "PAYPAL_AUTH_HTTP_REJECTED"),
        (
            httpx.Response(302, headers={"Location": "https://api-m.paypal.com"}),
            "PAYPAL_AUTH_HTTP_REJECTED",
        ),
        (httpx.Response(200, text="PRIVATE_PROVIDER_BODY"), "PAYPAL_AUTH_INVALID_RESPONSE"),
        (httpx.Response(200, json=[]), "PAYPAL_AUTH_INVALID_RESPONSE"),
        (
            httpx.Response(200, json=token_response() | {"token_type": "Basic"}),
            "PAYPAL_AUTH_INVALID_RESPONSE",
        ),
        (
            httpx.Response(200, json=token_response() | {"access_token": "token with whitespace"}),
            "PAYPAL_AUTH_INVALID_RESPONSE",
        ),
        (
            httpx.Response(200, json=token_response() | {"expires_in": True}),
            "PAYPAL_AUTH_INVALID_RESPONSE",
        ),
        (
            httpx.Response(200, json=token_response() | {"expires_in": 0}),
            "PAYPAL_AUTH_INVALID_RESPONSE",
        ),
    ],
)
def test_auth_failures_have_safe_distinct_diagnostics(response, code):
    async def scenario():
        calls = []

        def handler(request):
            calls.append(request.url.path)
            return response

        client = SandboxPayPal(
            auth_settings(), read_only=True, transport=httpx.MockTransport(handler)
        )
        result = await auth_report(auth_settings(), client=client)
        assert result["status"] == "FAIL" and result["code"] == code
        assert calls == ["/v1/oauth2/token"]
        assert "PRIVATE_" not in json.dumps(result) and "fixture-" not in json.dumps(result)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "exception,code",
    [
        (httpx.ConnectError("PRIVATE_TRANSPORT_DIAGNOSTIC"), "PAYPAL_AUTH_CONNECTION_FAILED"),
        (httpx.ReadTimeout("PRIVATE_TRANSPORT_DIAGNOSTIC"), "PAYPAL_AUTH_TIMEOUT"),
        (httpx.RemoteProtocolError("PRIVATE_TRANSPORT_DIAGNOSTIC"), "PAYPAL_AUTH_TRANSPORT_ERROR"),
    ],
)
def test_auth_network_failure_redaction(exception, code):
    async def scenario():
        def handler(request):
            raise exception

        result = await auth_report(
            auth_settings(),
            client=SandboxPayPal(
                auth_settings(), read_only=True, transport=httpx.MockTransport(handler)
            ),
        )
        assert result["status"] == "FAIL" and result["code"] == code
        assert result["requests"][0]["http_status"] is None
        assert "PRIVATE_" not in json.dumps(result)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}/refund"),
        ("POST", "https://api-m.sandbox.paypal.com/v2/checkout/orders"),
        ("POST", f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{ORDER}/capture"),
        ("PATCH", f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{ORDER}"),
        ("PUT", "https://api-m.sandbox.paypal.com/v1/merchant"),
        ("DELETE", "https://api-m.sandbox.paypal.com/v1/merchant"),
        ("POST", "https://api-m.paypal.com/v1/oauth2/token"),
        ("POST", "https://api-m.sandbox.paypal.com.attacker.example/v1/oauth2/token"),
        ("POST", "http://api-m.sandbox.paypal.com/v1/oauth2/token"),
        ("GET", f"https://api-m.sandbox.paypal.com/v2/payments/captures/{CAPTURE}?private=value"),
    ],
)
def test_preflight_transport_blocks_mutations_before_dispatch(method, url):
    async def scenario():
        calls = []
        inner = httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))
        async with httpx.AsyncClient(transport=SandboxReadOnlyTransport(inner)) as client:
            with pytest.raises(Problem, match="PAYPAL_PREFLIGHT_REQUEST_FORBIDDEN"):
                await client.request(method, url)
        assert calls == []

    asyncio.run(scenario())


def test_preflight_client_refund_disabled_before_oauth():
    async def scenario():
        calls = []
        client = SandboxPayPal(
            auth_settings(),
            read_only=True,
            transport=httpx.MockTransport(
                lambda request: calls.append(request) or httpx.Response(200)
            ),
        )
        with pytest.raises(Problem, match="PAYPAL_MUTATION_FORBIDDEN"):
            await client.refund(CAPTURE, "25.00", "USD", str(uuid4()))
        with pytest.raises(Problem, match="PAYPAL_MUTATION_FORBIDDEN"):
            await client._request("POST", f"/v2/payments/captures/{CAPTURE}/refund")
        assert not calls
        await client.close()

    asyncio.run(scenario())


def test_capture_preflight_makes_only_oauth_and_reads():
    async def scenario():
        calls = []

        def handler(request):
            calls.append((request.method, request.url.path))
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            return httpx.Response(
                200, json=order_data() if "orders" in request.url.path else capture_data()
            )

        settings = sandbox_settings()
        client = SandboxPayPal(settings, read_only=True, transport=httpx.MockTransport(handler))
        report = await capture_report(settings, CAPTURE, client=client)
        assert report["status"] == "PASS"
        assert report["checks"] == {
            "capture_get": "PASS",
            "order_get": "PASS",
            "refund_post": "NOT AUTHORIZED / NOT RUN",
        }
        assert [method for method, _ in calls] == ["POST", "GET", "GET"]
        assert CAPTURE not in json.dumps(report) and settings.merchant_id not in json.dumps(report)

    asyncio.run(scenario())


def test_capture_preflight_wrong_merchant_is_not_eligible():
    async def scenario():
        capture, order = capture_data(), order_data()
        capture["payee"]["merchant_id"] = order["purchase_units"][0]["payee"]["merchant_id"] = (
            "OTHER12345678"
        )

        def handler(request):
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json=token_response())
            return httpx.Response(200, json=order if "orders" in request.url.path else capture)

        settings = sandbox_settings()
        report = await capture_report(
            settings,
            CAPTURE,
            client=SandboxPayPal(settings, read_only=True, transport=httpx.MockTransport(handler)),
        )
        assert report["status"] == "FAIL" and report["code"] == "MERCHANT_MISMATCH"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode,base",
    [
        ("offline", "https://api-m.sandbox.paypal.com"),
        ("sandbox", "https://api-m.paypal.com"),
        ("sandbox", "https://api-m.sandbox.paypal.com.attacker.example"),
    ],
)
def test_auth_settings_reject_wrong_modes(mode, base):
    with pytest.raises(ValidationError):
        SandboxOAuthSettings(
            payment_mode=mode,
            paypal_base_url=base,
            client_id=SecretStr("fixture-id"),
            client_secret=SecretStr("fixture"),
        )


def test_dotenv_conflict_is_explicit_atomic_and_private(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    content = (
        "PAYMENT_MODE=sandbox\nPAYPAL_CLIENT_SECRET=private-file-value\nAI_MODE=deterministic\n"
    )
    env.write_text(content)
    monkeypatch.setenv("PAYMENT_MODE", "offline")
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)
    with pytest.raises(Problem) as error:
        load_env(env)
    assert str(error.value) == "ENVIRONMENT_OVERRIDE_CONFLICT:PAYMENT_MODE"
    assert "private-file-value" not in str(error.value)
    assert env.read_text() == content
    assert "PAYPAL_CLIENT_SECRET" not in __import__("os").environ


def test_dotenv_identical_inherited_values_preserved(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("PAYMENT_MODE=sandbox\nPAYPAL_CLIENT_SECRET=fixture-private-value\n")
    monkeypatch.setenv("PAYMENT_MODE", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "fixture-private-value")
    load_env(env)
    assert __import__("os").environ["PAYPAL_CLIENT_SECRET"] == "fixture-private-value"


@pytest.fixture
def cli_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    names = [
        "PAYMENT_MODE",
        "AI_MODE",
        "PAYPAL_ENVIRONMENT",
        "PAYPAL_BASE_URL",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_MERCHANT_ID",
        "PAYPAL_CAPTURE_IDS",
        "MAX_REFUND",
        "SENTINEL_STATE_DIR",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    for name, value in {
        "PAYMENT_MODE": "sandbox",
        "PAYPAL_CLIENT_ID": "fixture-client-id",
        "PAYPAL_CLIENT_SECRET": "fixture-client-secret",
    }.items():
        monkeypatch.setenv(name, value)
    return tmp_path


def test_cli_missing_capture_does_not_authenticate(cli_environment, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["refund-sentinel", "check-capture"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["code"] == "BLOCKED_NO_CAPTURE_ID" and not report["requests"]
    assert not list(cli_environment.glob(".state*"))


def test_cli_missing_credentials(cli_environment, monkeypatch, capsys):
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET")
    monkeypatch.setattr(sys, "argv", ["refund-sentinel", "check-auth"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 2
    assert json.loads(capsys.readouterr().out)["code"] == "BLOCKED_CREDENTIALS"


def test_cli_auth_no_capture_and_no_state(cli_environment, monkeypatch, capsys):
    # Only the consumer factory is replaced; no Runtime monkeypatch and no real transport.
    monkeypatch.setattr(
        "refund_sentinel.preflight.readonly_client",
        lambda settings: SandboxPayPal(
            settings,
            read_only=True,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=token_response())
            ),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["refund-sentinel", "check-auth"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PASS" and report["source"] == "MOCK"
    assert "fixture-" not in json.dumps(report)
    assert not list(cli_environment.glob(".state*"))


@pytest.mark.parametrize(
    "merchant",
    [
        "merchant@example.com",
        "Refund Sentinel",
        "DEMO-MERCHANT",
        "client-identifier-is-not-merchant",
    ],
)
def test_normal_sandbox_settings_reject_invalid_merchant(merchant):
    with pytest.raises(ValidationError):
        Settings(
            payment_mode="sandbox",
            merchant_id=merchant,
            capture_ids=(CAPTURE,),
            client_id=SecretStr("fixture-id"),
            client_secret=SecretStr("fixture-secret"),
        )


def test_normal_settings_still_require_capture_and_auth_does_not(cli_environment):
    assert SandboxOAuthSettings.from_env().payment_mode == "sandbox"
    with pytest.raises(ValidationError):
        Settings.from_env()


def test_python_313_contract_matches_runtime():
    from importlib.metadata import distribution

    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert project["project"]["requires-python"] == ">=3.13,<3.14"
    assert project["tool"]["ruff"]["target-version"] == "py313"
    assert distribution("agentic-intent-gate").metadata["Requires-Python"] == "<3.14,>=3.13"
    verify_python_version()
