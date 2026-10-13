import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from agentic_intent_gate.runtime import EXTERNAL_PAYLOAD_REVISION, AttemptContext, ExecutionSpec
from conftest import analyze, approved, command, ready, step, synthetic_recommendation
from fastapi.testclient import TestClient

from refund_sentinel.integration import composition, verify_distribution
from refund_sentinel.llm import DeterministicAnalyst
from refund_sentinel.models import RequestInput
from refund_sentinel.paypal import FakePayPal
from refund_sentinel.service import Sentinel
from refund_sentinel.web import create_app


def test_full_workflow_durable_receipt_and_duplicate(browser):
    client, fake, app = browser
    data = analyze(client)
    assert data["run"]["state"] == "AwaitingApproval"
    assert data["run"]["version"] == 4
    assert fake.recorded_calls() == []
    data = approved(client, data)
    assert data["run"]["state"] == "Approved"
    assert fake.recorded_calls() == []
    data, _ = step(client, data, "admit")
    assert data["action"]["state"] == "Pending"
    data, _ = step(client, data, "authorize")
    assert data["action"]["state"] == "Authorized" and fake.recorded_calls() == []
    data, body = step(client, data, "execute")
    assert data["action"]["state"] == "Succeeded"
    receipt = data["action"]["result"]["receipt_reference"]
    assert receipt in [row["id"] for row in data["evidence"]]
    assert fake.recorded_calls()[0]["request_id"] == data["action"]["effect_key"]
    assert fake.persisted_refunds()[0]["amount"]["value"] == "25.00"
    replay = client.post(f"/api/incidents/{data['id']}/execute", json=body)
    assert replay.status_code == 200
    assert replay.json()["action"] == data["action"]
    assert len(fake.recorded_calls()) == 1
    persisted = app.state.sentinel.runtime.actions.get(data["action"]["action_id"])
    assert persisted.state.value == "Succeeded" and persisted.result["receipt_reference"] == receipt
    assert (
        client.post(
            "/api/incidents",
            json={"capture_id": data["capture_id"], "message": "Please refund USD 25.00 again."},
        ).status_code
        == 409
    )


def test_missing_authorization_and_credentials(browser):
    client, fake, _ = browser
    data, _ = step(client, approved(client, analyze(client)), "admit")
    response = client.post(
        f"/api/incidents/{data['id']}/execute",
        json=command(data, action=True, idempotency_key=str(uuid4())),
    )
    assert response.status_code == 409
    assert response.json()["error"] == "ACTION_NOT_EXECUTABLE"
    client.headers.pop("Authorization")
    assert client.get("/api/incidents").status_code == 401
    assert (
        client.post(
            f"/api/incidents/{data['id']}/authorize",
            json=command(data, action=True, idempotency_key=str(uuid4())),
        ).status_code
        == 401
    )
    assert fake.recorded_calls() == []


def test_stale_and_mismatched_approval(browser):
    client, fake, _ = browser
    data = analyze(client)
    url = f"/api/incidents/{data['id']}/decision"
    assert (
        client.post(url, json=command(data, decision="approve") | {"expected_version": 3}).json()[
            "error"
        ]
        == "STALE_RUN_VERSION"
    )
    assert (
        client.post(url, json=command(data, decision="approve") | {"plan_digest": "0" * 64}).json()[
            "error"
        ]
        == "PLAN_CONFIRMATION_MISMATCH"
    )
    assert client.get(f"/api/incidents/{data['id']}").json()["run"]["state"] == "AwaitingApproval"
    assert fake.recorded_calls() == []


def test_rejected_plan_never_admitted(browser):
    client, fake, _ = browser
    data = analyze(client)
    rejected = client.post(
        f"/api/incidents/{data['id']}/decision", json=command(data, decision="reject")
    ).json()
    assert rejected["run"]["state"] == "Rejected"
    response = client.post(
        f"/api/incidents/{data['id']}/admit", json=command(rejected, idempotency_key=str(uuid4()))
    )
    assert response.status_code == 409 and fake.recorded_calls() == []


@pytest.mark.parametrize(
    "message,policy",
    [
        ("Please refund USD 121.00.", "AMOUNT_OUTSIDE_POLICY"),
        ("Please refund USD 120.00.", "AMOUNT_OUTSIDE_POLICY"),
        ("Please refund USD 101.00.", "AMOUNT_OUTSIDE_POLICY"),
        ("Please refund USD 0.00.", "AMOUNT_OUTSIDE_POLICY"),
        ("Please refund NZD 25.00.", "CURRENCY_OR_AMOUNT_MISMATCH"),
        ("Please refund something, I am not sure.", "MANUAL_REVIEW_REQUIRED"),
    ],
)
def test_policy_rejections(browser, message, policy):
    client, fake, _ = browser
    result = analyze(client, message)
    assert result["policy"] == policy and "run" not in result
    assert fake.recorded_calls() == []


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        synthetic_recommendation(requested_amount=25.0),
        synthetic_recommendation(extra_tool="execute_anything"),
        synthetic_recommendation(requested_amount="25.001"),
        '{"recommendation":"REFUND","recommendation":"REJECT"}',
    ],
)
def test_invalid_model_response(environment, raw):
    path, settings = environment
    with TestClient(
        create_app(path, settings, analyst=DeterministicAnalyst(raw), predecessor_stopped=True),
        base_url="http://127.0.0.1",
    ) as client:
        client.headers["Authorization"] = "Bearer " + (path / "operator.capability").read_text()
        data = analyze(client)
        assert data["policy"] == "INVALID_MODEL_RESPONSE" and "run" not in data
        assert FakePayPal(path / "fake-paypal.sqlite3").recorded_calls() == []


@pytest.mark.parametrize("behavior", ["PENDING", "FAILED", "CANCELLED", "TIMEOUT_AFTER_EFFECT"])
def test_unknown_does_not_retry_or_reconcile(browser, behavior):
    client, fake, _ = browser
    fake.behavior = behavior
    data, body = step(client, ready(client), "execute")
    assert data["action"]["state"] == "Unknown"
    assert len(fake.recorded_calls()) == len(fake.persisted_refunds()) == 1
    if behavior != "TIMEOUT_AFTER_EFFECT":
        assert data["evidence"][-1]["data"]["provider_status"] == behavior
        checked = client.post(f"/api/incidents/{data['id']}/verify", json={}).json()
        assert checked["action"]["state"] == "Unknown"
    assert client.post(f"/api/incidents/{data['id']}/execute", json=body).status_code == 200
    assert (
        client.post(
            f"/api/incidents/{data['id']}/execute",
            json=command(data, action=True, idempotency_key=str(uuid4())),
        ).status_code
        == 409
    )
    assert len(fake.recorded_calls()) == 1


def test_definitive_provider_rejection(browser):
    client, fake, _ = browser
    fake.behavior = "REJECT"
    data, _ = step(client, ready(client), "execute")
    assert data["action"]["state"] == "Failed"
    assert len(fake.recorded_calls()) == 1 and fake.persisted_refunds() == []


def test_conflicting_command_payload(browser):
    client, fake, _ = browser
    data, body = step(client, ready(client), "execute")
    response = client.post(
        f"/api/incidents/{data['id']}/execute", json=body | {"expected_version": 3}
    )
    assert response.status_code == 409 and response.json()["error"] == "IDEMPOTENCY_CONFLICT"
    assert len(fake.recorded_calls()) == 1


def test_concurrent_execution_single_provider_attempt(browser):
    client, fake, _ = browser
    fake.delay = 0.15
    data = ready(client)

    def invoke(_):
        return client.post(
            f"/api/incidents/{data['id']}/execute",
            json=command(data, action=True, idempotency_key=str(uuid4())),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(invoke, range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert len(fake.recorded_calls()) == len(fake.persisted_refunds()) == 1


def test_restart_persists_action_and_provider(environment):
    path, settings = environment
    token = (path / "operator.capability").read_text()
    for iteration in range(2):
        with TestClient(
            create_app(path, settings, predecessor_stopped=True),
            base_url="http://127.0.0.1",
            raise_server_exceptions=False,
        ) as client:
            client.headers["Authorization"] = "Bearer " + token
            if iteration == 0:
                data, body = step(client, ready(client), "execute")
            else:
                observed = client.get(f"/api/incidents/{data['id']}").json()
                assert observed["action"] == data["action"]
                assert observed["evidence"] == data["evidence"]
                assert (
                    client.post(f"/api/incidents/{data['id']}/execute", json=body).status_code
                    == 200
                )
    assert len(FakePayPal(path / "fake-paypal.sqlite3").recorded_calls()) == 1


@pytest.mark.parametrize(
    "field,value", [("tool_name", "unregistered_tool"), ("target", "other-target")]
)
def test_runtime_rejects_unregistered_plan(environment, field, value):
    async def scenario():
        path, settings = environment

        class InvalidPlanProvider:
            async def generate_plan(self, intent, **kwargs):
                incident = store.get(json.loads(intent.text)["incident_id"])
                plan = {
                    "goal": "Refund",
                    "target": executor.binding.target,
                    "risk_class": "SIDE_EFFECT",
                    "steps": [
                        {
                            "tool_name": executor.binding.tool_name,
                            "tool_version": "1",
                            "arguments": incident["refund_arguments"],
                        }
                    ],
                }
                if field == "target":
                    plan[field] = value
                else:
                    plan["steps"][0][field] = value
                return json.dumps(plan)

        with composition(
            path, settings, provider=InvalidPlanProvider(), predecessor_stopped=True
        ) as (runtime, store, fake, model, executor):
            app = Sentinel(runtime, store, fake, model, settings)
            data = await app.analyze(
                RequestInput(capture_id=settings.capture_ids[0], message="Please refund USD 25.00.")
            )
            assert data["run"]["state"] == "PlanRejected" and fake.recorded_calls() == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "field,value",
    [
        ("adapter_id", "wrong-adapter"),
        ("binding_revision", "wrong-revision"),
        ("execution_scope", str(uuid4())),
        ("target", "wrong-target"),
        ("tool_name", "unknown-tool"),
    ],
)
def test_registry_and_executor_reject_identity(environment, field, value):
    async def scenario():
        path, settings = environment
        with composition(path, settings, predecessor_stopped=True) as resources:
            runtime, store, fake, model, executor = resources
            data = await Sentinel(runtime, store, fake, model, settings).analyze(
                RequestInput(capture_id=settings.capture_ids[0], message="Please refund USD 25.00.")
            )
            spec = ExecutionSpec(
                **vars(executor.binding),
                arguments=data["refund_arguments"],
                identity_revision=EXTERNAL_PAYLOAD_REVISION,
            )
            wrong = replace(spec, **{field: value})
            with pytest.raises(Exception) as rejected:  # noqa: B017 -- public API omits error type
                runtime.gateway.registry.resolve(wrong)
            assert rejected.value.code.value == "TOOL_NOT_BOUND"
            context = AttemptContext(
                str(uuid4()), asyncio.get_running_loop().time() + 5, asyncio.Event()
            )
            result = await executor.execute(wrong, str(uuid4()), context)
            assert result.category.value == "CONFIRMED_FAILURE" and fake.recorded_calls() == []

    asyncio.run(scenario())


def test_conflicting_refund_arguments_rejected(environment):
    async def scenario():
        path, settings = environment
        with composition(path, settings, predecessor_stopped=True) as resources:
            runtime, store, fake, model, executor = resources
            data = await Sentinel(runtime, store, fake, model, settings).analyze(
                RequestInput(capture_id=settings.capture_ids[0], message="Please refund USD 25.00.")
            )
            spec = ExecutionSpec(
                **vars(executor.binding),
                arguments=data["refund_arguments"] | {"amount": "26.00"},
                identity_revision=EXTERNAL_PAYLOAD_REVISION,
            )
            assert executor.binding.matches(spec)
            context = AttemptContext(
                str(uuid4()), asyncio.get_running_loop().time() + 5, asyncio.Event()
            )
            outcome = await executor.execute(spec, str(uuid4()), context)
            assert outcome.category.value == "CONFIRMED_FAILURE" and fake.recorded_calls() == []

    asyncio.run(scenario())


def test_runtime_distribution_is_exact_pin():
    assert verify_distribution() == {
        "version": "0.2.0",
        "commit": "7261fdd2f47d2b15fabe8faac527eeee37338eb1",
    }


def test_web_origin_host_and_assets(browser):
    client, fake, _ = browser
    assert client.get("/").status_code == 200
    assert "frame-ancestors 'none'" in client.get("/").headers["Content-Security-Policy"]
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/config", headers={"Host": "attacker.example"}).status_code == 400
    assert (
        client.post(
            "/api/incidents",
            headers={"Origin": "https://attacker.example"},
            json={"capture_id": "DEMO0000000000001", "message": "USD 25.00"},
        ).status_code
        == 403
    )
    assert fake.recorded_calls() == []
