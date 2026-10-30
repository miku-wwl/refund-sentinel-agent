"""Decision evidence and public Runtime gates; model transport is explicitly mocked here."""

import asyncio
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from refund_sentinel import integration
from refund_sentinel.decision_lab import CASES
from refund_sentinel.demo import DemoController
from refund_sentinel.demo_ai import LocalProposal
from refund_sentinel.models import Problem
from refund_sentinel.presentation import COOKIE, create_presentation_app


def proposal(**changes):
    return {
        "recommendation": "REFUND",
        "requested_amount": "25.00",
        "currency": "USD",
        "explanation": "Mocked local-model contract, not live inference.",
        "reason_code": "DAMAGED_ITEM",
        "uncertainty": "LOW",
        **changes,
    }


def envelope(content, **message):
    return {"choices": [{"finish_reason": "stop", "message": {"content": content, **message}}]}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A synthetic presentation must never construct SandboxPayPal")

    monkeypatch.setattr(integration, "SandboxPayPal", forbidden)
    monkeypatch.setenv("PAYMENT_MODE", "sandbox")
    app = create_presentation_app(tmp_path / "lab", delay=0)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        yield client, app


def generate(lab, case, *, raw=None, handler=None):
    client, app = lab
    mode = "local_ai" if raw is not None or handler else "deterministic"
    body = {"scenario": case, "planning_mode": mode}
    response = client.post("/presentation/demo", json=body)
    assert response.status_code == 200
    session = app.state.demo.get(response.json()["session_id"])
    if mode == "local_ai":
        session.proposal_factory = lambda: LocalProposal(
            transport=httpx.MockTransport(
                handler or (lambda r: httpx.Response(200, json=envelope(raw)))
            )
        )
    result = client.post("/presentation/demo/generate", json=body)
    assert result.status_code == 200, result.text
    return result.json(), session, body


def command(view, operation, **changes):
    obj = view["run" if operation == "approve" else "action"] or {}
    return {
        "operation": operation,
        "confirmed": True,
        "expected_version": obj.get("version", 1),
        "plan_digest": view["plan_sha256"] or "0" * 64,
        "idempotency_key": str(uuid4()),
        **changes,
    }


def step(client, view, operation):
    result = client.post("/presentation/demo/command", json=command(view, operation))
    assert result.status_code == 200, result.text
    return result.json()


def assert_blocked(client, view, session):
    assert view["run"] is None and view["plan"] is None and view["action"] is None
    assert view["receipt"] is None and view["simulated_dispatches"] == 0
    assert session.store.list() == [] and session.fake.persisted_refunds() == []
    # Inspect durable state, not only a printed result or projection.
    with closing(sqlite3.connect(session.directory / "gate.sqlite3")) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in ("runs", "actions"):
            assert table in tables
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    for operation in ("approve", "authorize", "execute"):
        assert (
            client.post("/presentation/demo/command", json=command(view, operation)).status_code
            == 409
        )
    assert session.fake.recorded_calls() == []


@pytest.mark.parametrize("case", CASES)
def test_every_deterministic_case_has_durable_honest_evidence(lab, case):
    client, _ = lab
    view, session, body = generate(lab, case)
    evidence = view["decision"]
    assert evidence["source"] == "SIMULATED_DETERMINISTIC_FIXTURE"
    assert evidence["schema_verdict"] == "PASS" and view["model"] is None
    assert json.loads(evidence["model_output"]) == view["recommendation"]
    if case in {"ambiguous", "excessive", "injection"}:
        assert evidence["policy_verdict"] == "BLOCKED"
        assert_blocked(client, view, session)
    else:
        assert evidence["policy_verdict"] == "PASS"
        assert view["run"]["state"] == "AwaitingApproval"
        assert view["action"] is None and view["simulated_dispatches"] == 0
    assert client.post("/presentation/demo/generate", json=body).status_code == 409
    assert client.get("/presentation/demo").json() == view
    assert json.loads((session.directory / "decision.json").read_text("utf-8")) == evidence


@pytest.mark.parametrize(
    "case,overrides,reason",
    [
        ("ambiguous", {}, "CASE_AMOUNT_UNSPECIFIED"),
        ("ambiguous", {"requested_amount": None, "currency": None}, "CASE_AMOUNT_UNSPECIFIED"),
        ("excessive", {}, "AMOUNT_OUTSIDE_POLICY"),
        ("excessive", {"requested_amount": "150.00"}, "AMOUNT_OUTSIDE_POLICY"),
        ("valid_partial", {"requested_amount": "100.01"}, "AMOUNT_OUTSIDE_POLICY"),
        ("valid_partial", {"requested_amount": "120.00"}, "AMOUNT_OUTSIDE_POLICY"),
        ("valid_partial", {"requested_amount": "0.00"}, "AMOUNT_OUTSIDE_POLICY"),
        ("valid_partial", {"requested_amount": "24.00"}, "CASE_AMOUNT_UNSUPPORTED"),
        ("valid_partial", {"requested_amount": None}, "CURRENCY_OR_AMOUNT_MISMATCH"),
        ("valid_partial", {"currency": "NZD"}, "CURRENCY_OR_AMOUNT_MISMATCH"),
        ("valid_partial", {"uncertainty": "HIGH"}, "MANUAL_REVIEW_REQUIRED"),
        ("valid_partial", {"recommendation": "REVIEW"}, "MANUAL_REVIEW_REQUIRED"),
        ("valid_partial", {"recommendation": "REJECT"}, "MANUAL_REVIEW_REQUIRED"),
        ("injection", {"requested_amount": "150.00"}, "AMOUNT_OUTSIDE_POLICY"),
    ],
)
def test_untrusted_valid_schema_cannot_override_case_or_policy(lab, case, overrides, reason):
    client, _ = lab
    raw = json.dumps(proposal(**overrides), indent=2)
    view, session, _ = generate(lab, case, raw=raw)
    assert view["decision"]["model_output"] == raw
    assert view["decision"]["source"] == "REAL_LOCAL_OLLAMA"  # Mocked transport in this suite.
    assert view["decision"]["reason"] == reason
    assert_blocked(client, view, session)


@pytest.mark.parametrize(
    "raw",
    [
        "not JSON",
        '{"recommendation":"REFUND","recommendation":"REFUND"}',
        json.dumps(proposal(requested_amount=25)),
        json.dumps(proposal() | {"tool_name": "unrestricted_refund"}),
        json.dumps(proposal() | {"approved": True}),
        json.dumps(proposal() | {"execution_timeout_seconds": 15}),
        json.dumps(proposal() | {"provider_url": "https://attacker.invalid/refund"}),
        json.dumps(proposal(uncertainty="CERTAIN")),
        json.dumps(proposal(requested_amount="25.000")),
        json.dumps(proposal(explanation="<script>window.injected=true</script>")) + " trailing",
    ],
)
def test_invalid_actual_output_is_preserved_but_never_executable(lab, raw):
    client, _ = lab
    view, session, _ = generate(lab, "valid_partial", raw=raw)
    assert view["decision"]["model_output"] == raw
    assert view["decision"]["schema_verdict"] == "REJECTED"
    assert view["decision"]["reason"] == "INVALID_MODEL_RESPONSE"
    assert_blocked(client, view, session)


@pytest.mark.parametrize("case", ["valid_partial", "injection", "unknown_outcome"])
def test_accepted_output_still_requires_all_three_independent_gates(lab, case):
    client, _ = lab
    view, session, _ = generate(lab, case, raw=json.dumps(proposal()))
    assert view["decision"]["policy_verdict"] == "PASS"
    assert view["decision"]["facts"]["requested_amount"] == "25.00"
    identity = hashlib.sha256((session.directory / "identity.json").read_bytes()).hexdigest()
    for operation in ("authorize", "execute"):
        assert (
            client.post("/presentation/demo/command", json=command(view, operation)).status_code
            == 409
        )
    view = step(client, view, "approve")
    assert not view["action"]["authorized"] and view["simulated_dispatches"] == 0
    assert (
        client.post("/presentation/demo/command", json=command(view, "execute")).status_code == 409
    )
    view = step(client, view, "authorize")
    assert view["simulated_dispatches"] == 0
    assert (
        client.post(
            "/presentation/demo/command", json=command(view, "execute", confirmed=False)
        ).status_code
        == 422
    )
    view = step(client, view, "execute")
    assert view["action"]["state"] == ("Unknown" if case == "unknown_outcome" else "Succeeded")
    assert bool(view["receipt"]) == (case != "unknown_outcome")
    assert view["simulated_dispatches"] == 1 and len(session.fake.persisted_refunds()) == 1
    assert (
        client.post("/presentation/demo/command", json=command(view, "execute")).status_code == 409
    )
    assert (
        hashlib.sha256((session.directory / "identity.json").read_bytes()).hexdigest() == identity
    )
    assert view["adapter_seconds"] == 5 and len(session.fake.recorded_calls()) == 1


@pytest.mark.parametrize("failure", ["connect", "http", "refusal", "oversized", "timeout"])
def test_model_failures_are_durable_and_no_automatic_fallback(lab, failure):
    client, _ = lab

    def handler(request):
        if failure == "connect":
            raise httpx.ConnectError("PRIVATE_TRANSPORT_DETAIL", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE_TRANSPORT_DETAIL", request=request)
        if failure == "http":
            return httpx.Response(503, text="PRIVATE_TRANSPORT_DETAIL")
        if failure == "oversized":
            return httpx.Response(200, content=b"x" * 65537)
        return httpx.Response(200, json=envelope(None, refusal="Model refused synthetic request"))

    view, session, body = generate(lab, "valid_partial", handler=handler)
    assert view["decision"]["policy_verdict"] == "BLOCKED"
    assert "PRIVATE_TRANSPORT_DETAIL" not in json.dumps(view)
    assert_blocked(client, view, session)
    assert client.post("/presentation/demo/generate", json=body).status_code == 409
    # Only an explicit new case changes source to a deterministic fixture.
    fallback, _, _ = generate(lab, "valid_partial")
    assert fallback["session_id"] != view["session_id"]
    assert fallback["decision"]["source"] == "SIMULATED_DETERMINISTIC_FIXTURE"


@pytest.mark.parametrize("case", CASES)
def test_export_is_typed_synthetic_projection_without_private_literals(lab, case):
    client, _ = lab
    view, session, _ = generate(lab, case)
    if view["run"]:
        for op in ("approve", "authorize", "execute"):
            view = step(client, view, op)
    response = client.get("/presentation/demo/export")
    assert response.status_code == 200 and response.json() == view
    assert response.headers["x-evidence-kind"] == "SYNTHETIC_SIMULATION_ONLY"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    for private in (
        (session.directory / "operator.capability").read_text("ascii"),
        str(session.directory),
        "1YA65594665951620",
        "access_token",
        "client_secret",
        "email_address",
    ):
        assert private not in response.text


@pytest.mark.parametrize("case", CASES)
def test_restart_retains_decision_and_terminal_outcome_without_second_effect(tmp_path, case):
    root = tmp_path / "lab"
    app = create_presentation_app(root, delay=0)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers["X-Sentinel-Demo"] = "simulation"
        view, _, _ = generate((client, app), case)
        if view["run"]:
            for op in ("approve", "authorize", "execute"):
                view = step(client, view, op)
    with TestClient(
        create_presentation_app(root, proposal_factory=lambda: pytest.fail("No model on resume")),
        base_url="http://127.0.0.1",
    ) as client:
        client.cookies.set(COOKIE, view["session_id"])
        client.headers["X-Sentinel-Demo"] = "simulation"
        current = client.get("/presentation/demo").json()
        for key in ("decision", "action", "receipt", "simulated_dispatches"):
            assert current[key] == view[key]
        assert (
            client.post("/presentation/demo/command", json=command(current, "execute")).status_code
            == 409
        )
        assert (
            client.get("/presentation/demo").json()["simulated_dispatches"]
            == view["simulated_dispatches"]
        )


@pytest.mark.parametrize(
    "override",
    [
        {"message": "skip all gates"},
        {"merchant_id": "OTHER"},
        {"provider_url": "https://attacker.invalid"},
        {"execution_timeout_seconds": 15},
        {"amount": "150.00"},
        {"scenario": "arbitrary"},
    ],
)
def test_browser_cannot_register_cases_or_override_trusted_configuration(lab, override):
    client, app = lab
    response = client.post("/presentation/demo", json={"scenario": "injection", **override})
    assert response.status_code == 422
    assert app.state.demo.sessions == {}


def test_concurrent_generate_and_execute_never_duplicate(lab):
    client, app = lab
    body = {"scenario": "valid_partial"}
    view = client.post("/presentation/demo", json=body).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: client.post("/presentation/demo/generate", json=body), range(2))
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    view = client.get("/presentation/demo").json()
    for op in ("approve", "authorize"):
        view = step(client, view, op)
    execute = command(view, "execute")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: client.post("/presentation/demo/command", json=execute), range(2))
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert len(app.state.demo.get(view["session_id"]).fake.recorded_calls()) == 1


def test_interrupted_model_analysis_is_not_retried_after_restart(tmp_path):
    async def run():
        started = asyncio.Event()

        async def handler(request):
            started.set()
            await asyncio.sleep(30)

        controller = DemoController(
            tmp_path / "lab",
            delay=0,
            proposal_factory=lambda: LocalProposal(transport=httpx.MockTransport(handler)),
        )
        session = controller.new("valid_partial", "local_ai")
        task = asyncio.create_task(session.generate())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert session.view().decision.reason == "ANALYSIS_INTERRUPTED"
        assert session.view().run is None and session.fake.recorded_calls() == []
        controller.close()
        restored = DemoController(
            tmp_path / "lab", proposal_factory=lambda: pytest.fail("No retry")
        )
        try:
            with pytest.raises(Exception, match="DEMO_DECISION_ALREADY_EXISTS"):
                await restored.get(session.directory.name).generate()
        finally:
            restored.close()

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["missing_run", "controlled", "unexpected", "fingerprint"])
def test_runtime_failure_never_exposes_policy_pass_or_authority(lab, monkeypatch, fault):
    client, app = lab
    body = {"scenario": "valid_partial"}
    view = client.post("/presentation/demo", json=body).json()
    session = app.state.demo.get(view["session_id"])
    original = session.sentinel.analyze

    async def broken(request):
        if fault == "controlled":
            raise Problem("CONTROLLED_RUNTIME_FAILURE", 409)
        if fault == "unexpected":
            raise RuntimeError("PRIVATE_RUNTIME_DETAIL")
        if fault == "missing_run":
            return {}
        detail = await original(request)
        detail["plan_digest"] = "0" * 64
        return detail

    monkeypatch.setattr(session.sentinel, "analyze", broken)
    response = client.post("/presentation/demo/generate", json=body)
    assert response.status_code == 200
    view = response.json()
    assert view["decision"]["schema_verdict"] == "PASS"
    assert view["decision"]["policy_eligibility"] == "ELIGIBLE"
    assert view["decision"]["policy_verdict"] == "NOT_EVALUATED"
    assert view["decision"]["workflow_status"] == "FAILED"
    assert "PRIVATE_RUNTIME_DETAIL" not in response.text
    assert view["run"] is None and view["plan"] is None and view["plan_sha256"] is None
    assert view["action"] is None and view["receipt"] is None
    assert view["executable_amount"] is None and view["simulated_dispatches"] == 0
    with closing(sqlite3.connect(session.directory / "gate.sqlite3")) as db:
        assert db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == (
            1 if fault == "fingerprint" else 0
        )
    for operation in ("approve", "admit", "authorize", "execute"):
        assert (
            client.post("/presentation/demo/command", json=command(view, operation)).status_code
            == 409
        )
    assert client.post("/presentation/demo/generate", json=body).status_code == 409
    assert session.fake.recorded_calls() == []


@pytest.mark.parametrize("error", [Problem("RUNTIME_CREATE_FAILED", 409), RuntimeError("private")])
def test_runtime_creation_fault_retains_reserved_incident_without_executable_plan(
    lab, monkeypatch, error
):
    client, app = lab
    body = {"scenario": "valid_partial"}
    view = client.post("/presentation/demo", json=body).json()
    session = app.state.demo.get(view["session_id"])

    async def fail_create(*args, **kwargs):
        raise error

    # Fault injection at the public API boundary only; installed Runtime is unchanged.
    monkeypatch.setattr(session.runtime.run_service, "create", fail_create)
    view = client.post("/presentation/demo/generate", json=body).json()
    assert len(session.store.list()) == 1
    assert view["decision"]["workflow_status"] == "FAILED"
    assert view["decision"]["policy_verdict"] != "PASS"
    assert view["run"] is None and view["plan"] is None and view["action"] is None
    assert session.fake.recorded_calls() == []
    with closing(sqlite3.connect(session.directory / "gate.sqlite3")) as db:
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0


@pytest.mark.parametrize("fault", ["missing", "fingerprint"])
def test_ready_projection_rechecks_persistent_run_without_rewriting_evidence(
    lab, monkeypatch, fault
):
    client, _ = lab
    view, session, _ = generate(lab, "valid_partial")
    assert view["decision"]["workflow_status"] == "READY"
    assert view["decision"]["run_id"] == view["run"]["id"]
    assert view["decision"]["plan_sha256"] == view["plan_sha256"]
    path = session.directory / "decision.json"
    if fault == "missing":
        monkeypatch.setattr(session.runtime.run_service, "get", lambda *a: None)
    else:
        evidence = json.loads(path.read_text("utf-8"))
        evidence["plan_sha256"] = "0" * 64
        path.write_text(json.dumps(evidence), "utf-8")
    before = path.read_bytes()
    current = client.get("/presentation/demo").json()
    assert current["decision"]["workflow_status"] == "FAILED"
    assert current["decision"]["policy_verdict"] != "PASS"
    assert current["run"] is None and current["plan"] is None and current["action"] is None
    assert path.read_bytes() == before
    assert (
        client.post("/presentation/demo/command", json=command(current, "approve")).status_code
        == 409
    )
    assert session.fake.recorded_calls() == []


def test_interruption_after_persisted_run_stays_non_executable_after_restart(tmp_path):
    async def run():
        root = tmp_path / "interrupted-lab"
        controller = DemoController(root, delay=0)
        session = controller.new("valid_partial")
        original = session.sentinel.analyze
        started = asyncio.Event()

        async def interrupted(request):
            detail = await original(request)
            assert detail["run"]["state"] == "AwaitingApproval"
            started.set()
            await asyncio.Event().wait()

        session.sentinel.analyze = interrupted
        task = asyncio.create_task(session.generate())
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        before = session.view().model_dump()
        assert before["decision"]["workflow_status"] == "INTERRUPTED"
        assert before["decision"]["policy_verdict"] != "PASS"
        assert before["run"] is None and before["action"] is None
        with closing(sqlite3.connect(session.directory / "gate.sqlite3")) as db:
            assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0
        controller.close()
        with TestClient(create_presentation_app(root), base_url="http://127.0.0.1") as client:
            client.cookies.set(COOKIE, session.directory.name)
            client.headers["X-Sentinel-Demo"] = "simulation"
            current = client.get("/presentation/demo").json()
            assert current["decision"] == before["decision"]
            for operation in ("approve", "admit", "authorize", "execute"):
                assert (
                    client.post(
                        "/presentation/demo/command", json=command(current, operation)
                    ).status_code
                    == 409
                )
            assert (
                client.post(
                    "/presentation/demo/generate", json={"scenario": "valid_partial"}
                ).status_code
                == 409
            )
            assert client.get("/presentation/demo").json()["simulated_dispatches"] == 0

    asyncio.run(run())


def test_legacy_evidence_is_not_reinterpreted_or_rewritten(lab):
    client, _ = lab
    view, session, _ = generate(lab, "valid_partial")
    path = session.directory / "decision.json"
    legacy = json.loads(path.read_text("utf-8"))
    for key in ("workflow_status", "policy_eligibility", "run_id", "plan_sha256"):
        legacy.pop(key)
    path.write_text(json.dumps(legacy), "utf-8")
    before = path.read_bytes()
    current = client.get("/presentation/demo").json()
    assert current["decision"]["workflow_status"] is None
    assert current["decision"]["policy_verdict"] == "PASS"
    assert current["run"] == view["run"] and current["plan_sha256"] == view["plan_sha256"]
    assert path.read_bytes() == before
