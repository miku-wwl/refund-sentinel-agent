"""Browser boundary and genuine public Runtime integration, exclusively synthetic effects."""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from refund_sentinel import integration, presentation
from refund_sentinel.demo import DemoController
from refund_sentinel.models import Problem
from refund_sentinel.presentation import COOKIE, create_presentation_app


@pytest.fixture
def console(tmp_path, monkeypatch):
    def real_provider_forbidden(*args, **kwargs):
        raise AssertionError("Presentation must never initialize a real provider")

    monkeypatch.setattr(integration, "SandboxPayPal", real_provider_forbidden)
    monkeypatch.setenv("PAYMENT_MODE", "sandbox")
    monkeypatch.setenv("PAYPAL_CAPTURE_IDS", "1YA65594665951620")
    app = create_presentation_app(tmp_path / "simulation", delay=0)
    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        yield client, app


def load(client, scenario="completed"):
    response = client.post("/presentation/demo", json={"scenario": scenario})
    assert response.status_code == 200, response.text
    return response.json()


def plan(client, scenario="completed"):
    load(client, scenario)
    response = client.post("/presentation/demo/generate", json={"scenario": scenario})
    assert response.status_code == 200, response.text
    return response.json()


def command(view, operation, **overrides):
    return {
        "operation": operation,
        "confirmed": True,
        "expected_version": view["run" if operation in {"approve", "admit"} else "action"][
            "version"
        ],
        "plan_digest": view["plan_sha256"],
        "idempotency_key": str(uuid4()),
        **overrides,
    }


def step(client, view, operation):
    response = client.post("/presentation/demo/command", json=command(view, operation))
    assert response.status_code == 200, response.text
    return response.json()


def test_archive_is_exact_sanitized_freeze_fixture(console):
    client, _ = console
    response = client.get("/presentation/proof")
    assert response.status_code == 200
    data = response.json()
    original = Path("evidence/phase2-freeze/verified-refund.json").read_bytes()
    assert hashlib.sha256(original).hexdigest() == presentation.PROOF_SHA256
    assert data == json.loads(original)
    assert data["execution"]["financial_post_count"] == 1
    assert "operator_capability" not in response.text and "email_address" not in response.text


def test_reading_archive_and_empty_demo_creates_no_case(console):
    client, app = console
    assert client.get("/presentation/demo").json() is None
    assert client.get("/presentation/proof").status_code == 200
    assert app.state.demo.sessions == {}
    assert list(app.state.demo.root.iterdir()) == [app.state.demo.root / "simulation.marker"]


def test_three_gates_real_runtime_and_durable_synthetic_receipt(console):
    client, app = console
    view = plan(client)
    assert view["run"]["state"] == "AwaitingApproval" and view["run"]["version"] == 4
    assert view["action"] is None and view["simulated_dispatches"] == 0
    view = step(client, view, "approve")
    assert view["run"]["state"] == "Approved" and view["action"]["state"] == "Pending"
    assert not view["action"]["authorized"] and view["simulated_dispatches"] == 0
    body = command(view, "execute")
    assert client.post("/presentation/demo/command", json=body).status_code == 409
    view = step(client, view, "authorize")
    assert view["action"]["state"] == "Authorized" and view["simulated_dispatches"] == 0
    body = command(view, "execute")
    response = client.post("/presentation/demo/command", json=body)
    view = response.json()
    assert response.status_code == 200 and view["action"]["state"] == "Succeeded"
    assert view["action"]["version"] == 4 and view["simulated_dispatches"] == 1
    assert view["receipt"]["source"] == "SIMULATED_PROVIDER"
    case = app.state.demo.get(view["session_id"])
    action = case.runtime.gateway.get(view["action"]["id"], case.principal)
    assert action.result["receipt_reference"] == view["receipt"]["id"]
    assert case.fake.recorded_calls()[0]["request_id"] == action.effect_key
    assert client.post("/presentation/demo/command", json=body).status_code == 409
    assert client.get("/presentation/demo").json()["simulated_dispatches"] == 1
    assert (case.directory / "operator.capability").read_text("ascii") not in json.dumps(view)


@pytest.mark.parametrize(
    "scenario,state,effects", [("unknown", "Unknown", 1), ("rejected", "Failed", 0)]
)
def test_terminal_failure_and_unknown_stop_without_reconciliation(
    console, scenario, state, effects
):
    client, app = console
    view = plan(client, scenario)
    for operation in ("approve", "authorize", "execute"):
        view = step(client, view, operation)
    assert view["action"]["state"] == state and view["receipt"] is None
    case = app.state.demo.get(view["session_id"])
    assert len(case.fake.persisted_refunds()) == effects
    before = case.store.observations(view["action"]["effect_key"])
    for operation in ("authorize", "execute"):
        assert (
            client.post("/presentation/demo/command", json=command(view, operation)).status_code
            == 409
        )
    assert client.get("/presentation/demo").json() == view
    assert case.store.observations(view["action"]["effect_key"]) == before
    assert len(case.fake.recorded_calls()) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("capture_id", "1YA65594665951620"),
        ("payment_mode", "sandbox"),
        ("amount", "5.00"),
        ("execution_scope", "original"),
        ("profile", "paypal-sandbox-15s"),
        ("client_secret", "PRIVATE_INPUT"),
    ],
)
def test_browser_cannot_select_real_identity_or_settings(console, field, value):
    client, app = console
    response = client.post("/presentation/demo", json={field: value})
    assert response.status_code == 422 and value not in response.text
    assert app.state.demo.sessions == {}


@pytest.mark.parametrize(
    "path",
    [
        "/api/incidents",
        "/api/incidents/26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1/execute",
        "/api/incidents/5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5/authorize",
        "/assets/app.js",
        "/assets/qualified-case.json",
        "/.env",
        "/docs",
    ],
)
def test_real_commands_and_private_assets_are_not_mounted(console, path):
    client, _ = console
    assert client.get(path).status_code == 404
    assert client.post(path, json={}).status_code == 404


def test_stale_version_changed_plan_and_missing_confirmation_never_dispatch(console):
    client, _ = console
    view = plan(client)
    for change in ({"expected_version": 3}, {"plan_digest": "0" * 64}, {"confirmed": False}):
        assert client.post(
            "/presentation/demo/command", json=command(view, "approve", **change)
        ).status_code in {409, 422}
        current = client.get("/presentation/demo").json()
        assert current["run"]["state"] == "AwaitingApproval" and current["action"] is None


def test_cross_origin_host_and_missing_demo_header_fail_closed(console):
    client, _ = console
    assert (
        client.post(
            "/presentation/demo", json={}, headers={"Origin": "https://evil.test"}
        ).status_code
        == 403
    )
    assert client.get("/presentation/proof", headers={"Host": "evil.test"}).status_code == 400
    del client.headers["X-Sentinel-Demo"]
    assert client.post("/presentation/demo", json={}).status_code == 403


def test_parallel_execute_dispatches_once(console):
    client, app = console
    view = plan(client)
    view = step(client, view, "approve")
    view = step(client, view, "authorize")
    body = command(view, "execute")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/presentation/demo/command", json=body).status_code, range(2)
            )
        )
    assert sorted(responses) == [200, 409]
    assert len(app.state.demo.get(view["session_id"]).fake.recorded_calls()) == 1


def test_reset_retains_old_case_and_does_not_copy_approvals(console):
    client, app = console
    old = step(client, plan(client), "approve")
    case = app.state.demo.get(old["session_id"])
    new = load(client)
    assert new["session_id"] != old["session_id"] and new["run"] is None
    assert case.view().action.state == "Pending"
    new = client.post("/presentation/demo/generate", json={}).json()
    new = step(client, new, "approve")
    assert new["action"]["execution_scope"] != old["action"]["execution_scope"]
    assert case.view().simulated_dispatches == 0


def test_runtime_state_resumes_receipt_without_replaying(tmp_path):
    root = tmp_path / "simulation"
    with TestClient(create_presentation_app(root, delay=0), base_url="http://127.0.0.1") as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        view = plan(client)
        for op in ("approve", "authorize", "execute"):
            view = step(client, view, op)
        cookie = client.cookies.get(COOKIE)
    with TestClient(create_presentation_app(root, delay=0), base_url="http://127.0.0.1") as resumed:
        resumed.cookies.set(COOKIE, cookie)
        current = resumed.get("/presentation/demo").json()
        assert current["action"] == view["action"] and current["receipt"] == view["receipt"]
        assert current["simulated_dispatches"] == 1


def test_existing_financial_directory_rejected_before_write(tmp_path):
    (tmp_path / "gate.sqlite3").write_bytes(b"PRESERVED_PRIVATE_STATE")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(Problem, match="DEMO_ROOT_UNSAFE"):
        DemoController(tmp_path)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_archived_fixture_tampering_blocks_startup(tmp_path, monkeypatch):
    (tmp_path / "qualified-case.json").write_text('{"client_secret":"PRIVATE"}', "utf-8")
    monkeypatch.setattr(presentation, "STATIC", tmp_path)
    with pytest.raises(Problem, match="ARCHIVED_PROOF_INTEGRITY_FAILURE"):
        presentation.archived_proof()


def test_concurrent_controller_cannot_resume_owned_case(console):
    client, app = console
    view = plan(client)
    second = create_presentation_app(app.state.demo.root)
    with TestClient(second, base_url="http://127.0.0.1", raise_server_exceptions=False) as reader:
        reader.cookies.set(COOKIE, view["session_id"])
        assert reader.get("/presentation/demo").status_code == 503
    assert client.get("/presentation/demo").json()["simulated_dispatches"] == 0


def test_late_verified_observation_cannot_present_unknown_as_success(console, monkeypatch):
    client, app = console
    view = plan(client)
    view = step(client, view, "approve")
    view = step(client, view, "authorize")
    case = app.state.demo.get(view["session_id"])
    original = case.store.observe

    def delayed_commit(*args, **kwargs):
        receipt = original(*args, **kwargs)
        if kwargs.get("phase") == "VERIFIED_REFUND":
            time.sleep(5.05)  # Genuine fixed Runtime budget; only synthetic persistence/effect.
        return receipt

    monkeypatch.setattr(case.store, "observe", delayed_commit)
    view = step(client, view, "execute")
    assert view["action"]["state"] == "Unknown"
    assert view["receipt"] is None and view["simulated_dispatches"] == 1
    rows = case.store.observations(view["action"]["effect_key"])
    assert any(row["data"].get("phase") == "VERIFIED_REFUND" for row in rows)
    assert (
        client.post("/presentation/demo/command", json=command(view, "execute")).status_code == 409
    )
    assert len(case.fake.recorded_calls()) == 1
