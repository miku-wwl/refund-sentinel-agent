import json

import pytest
from test_fixture import (
    SandboxServer,
    approved,
    perform,
    settings,
)

from refund_sentinel.fixture import FixtureStore
from refund_sentinel.models import Problem


@pytest.fixture
def fixture(tmp_path):
    config = settings()
    store = FixtureStore(tmp_path / ".state-fixture")
    state = store.prepare(config, source="MOCK")
    return store, config, SandboxServer(state)


def make_unknown_creation(fixture):
    approved(fixture)
    store, config, _ = fixture
    state = store.load(config, "MOCK")
    state.phase = "UNKNOWN_CREATE"
    state.last_code = "FIXTURE_ORDER_EVIDENCE_INVALID"
    store.save(state)
    return state


def test_explicit_known_creation_reconciliation_archives_original_and_captures_once(fixture):
    state = make_unknown_creation(fixture)
    store, config, server = fixture
    original = store.path.read_bytes()
    create_marker = (store.directory / "create.attempt.json").read_bytes()
    ids = (state.order_id, state.create_request_id, state.capture_request_id)
    report = perform(fixture, "capture", reconcile_approved_creation=True)
    assert report["phase"] == "CAPTURED"
    assert (store.directory / "pre-capture.fixture.json").read_bytes() == original
    assert (store.directory / "create.attempt.json").read_bytes() == create_marker
    saved = store.load(config, "MOCK")
    assert (saved.order_id, saved.create_request_id, saved.capture_request_id) == ids
    assert json.loads((store.directory / "capture.attempt.json").read_bytes()) == {
        "request_id": ids[2]
    }
    assert sum(request.url.path.endswith("/capture") for request in server.calls) == 1
    before = len(server.calls)
    with pytest.raises(Problem, match="NO_RETRY"):
        perform(fixture, "capture", reconcile_approved_creation=True)
    assert len(server.calls) == before


def test_unknown_creation_still_requires_explicit_reconciliation_option(fixture):
    make_unknown_creation(fixture)
    before = len(fixture[2].calls)
    with pytest.raises(Problem, match="BUYER_APPROVAL_REQUIRED"):
        perform(fixture, "capture")
    assert len(fixture[2].calls) == before
    assert not (fixture[0].directory / "capture.attempt.json").exists()


def test_reconciliation_requires_existing_matching_create_marker(fixture):
    make_unknown_creation(fixture)
    store, _, server = fixture
    (store.directory / "create.attempt.json").write_text('{"request_id":"wrong"}')
    before = len(server.calls)
    with pytest.raises(Problem, match="CREATE_ATTEMPT_IDENTITY_MISMATCH"):
        perform(fixture, "capture", reconcile_approved_creation=True)
    assert len(server.calls) == before
    assert not (store.directory / "capture.attempt.json").exists()


@pytest.mark.parametrize("invalid", ["not_approved", "already_captured", "merchant", "amount"])
def test_reconciliation_cannot_bypass_fresh_approval_or_payment_preconditions(fixture, invalid):
    make_unknown_creation(fixture)
    store, config, server = fixture
    if invalid == "not_approved":
        server.status = "PAYER_ACTION_REQUIRED"
    elif invalid == "already_captured":
        server.status = "COMPLETED"
    else:

        def mutate(order):
            if invalid == "merchant":
                order["purchase_units"][0]["payee"]["merchant_id"] = "BBBBBBBBBBBBB"
            else:
                order["purchase_units"][0]["amount"]["value"] = "21.00"
            return order

        server.change_order = mutate
    with pytest.raises(Problem):
        perform(fixture, "capture", reconcile_approved_creation=True)
    assert store.load(config, "MOCK").phase == "UNKNOWN_CREATE"
    assert not (store.directory / "pre-capture.fixture.json").exists()
    assert not (store.directory / "capture.attempt.json").exists()
    assert not any(request.url.path.endswith("/capture") for request in server.calls)


def test_unknown_capture_never_reconciles_to_another_capture_attempt(fixture):
    state = make_unknown_creation(fixture)
    store, _, server = fixture
    state.phase = "UNKNOWN_CAPTURE"
    store.save(state)
    before = len(server.calls)
    with pytest.raises(Problem, match="BUYER_APPROVAL_REQUIRED"):
        perform(fixture, "capture", reconcile_approved_creation=True)
    assert len(server.calls) == before
    assert not (store.directory / "capture.attempt.json").exists()
