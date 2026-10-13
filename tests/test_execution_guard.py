import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from refund_sentinel.execution_guard import (
    OwnershipBlocked,
    classify_processes,
    literal_sleep,
    probe_owner_lock,
    process_inventory,
    verify_no_predecessor,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Qualified Windows orchestration")


def record(pid, argv, *, parent=0, executable=None):
    executable = executable or sys.executable
    return {
        "ProcessId": pid,
        "ParentProcessId": parent,
        "Name": Path(executable).name,
        "ExecutablePath": executable,
        "CommandLine": subprocess.list2cmdline(argv),
        "CreationDate": "verified-start-time",
    }


def classify(rows, tmp_path):
    return classify_processes(
        rows,
        repo=tmp_path / "repo",
        state=tmp_path / "repo/original-state",
        current_pid=100,
        parent_pid=99,
        executables=(sys.executable, sys._base_executable),
    )


def self_record():
    return record(100, [sys.executable, "recovery_runner.py", "--dry-run"], parent=99)


def test_verified_sleep_is_unrelated(tmp_path):
    result = classify(
        [self_record(), record(200, [sys.executable, "-c", "import time; time.sleep(20)"])],
        tmp_path,
    )
    assert result[1]["classification"] == "UNRELATED_VERIFIED_LITERAL_SLEEP"
    assert "CommandLine" not in result[1]


def test_verified_venv_launcher(tmp_path):
    current = self_record()
    launcher = record(
        99,
        [sys.executable, "recovery_runner.py", "--dry-run"],
        executable=sys._base_executable,
    )
    assert classify([current, launcher], tmp_path)[1]["classification"] == "VERIFIED_VENV_LAUNCHER"


@pytest.mark.parametrize(
    "program",
    [
        "import time; time.sleep(20); import refund_sentinel",
        "import refund_sentinel; import time; time.sleep(20)",
        "import time; exec('time.sleep(20)')",
        "import time; time.sleep(float(input()))",
        "import time; time.sleep(True)",
        "import time; time.sleep(-1)",
        "import time as t; t.sleep(20)",
        "import time; time.sleep(20, extra=1)",
        "import time; time.sleep(20) # original-state",
    ],
)
def test_opaque_inline_programs_fail_closed(tmp_path, program):
    # A harmless comment does not turn the complete AST sleep into financial code.
    if program.endswith("# original-state"):
        assert literal_sleep([sys.executable, "-c", program])
        return
    with pytest.raises(OwnershipBlocked):
        classify([self_record(), record(200, [sys.executable, "-c", program])], tmp_path)


@pytest.mark.parametrize("field", ["CommandLine", "ExecutablePath", "CreationDate"])
def test_missing_identity_blocks_even_sleep(tmp_path, field):
    worker = record(200, [sys.executable, "-c", "import time; time.sleep(20)"])
    worker[field] = None
    with pytest.raises(OwnershipBlocked, match="PROCESS_IDENTITY_UNVERIFIABLE"):
        classify([self_record(), worker], tmp_path)


def test_missing_self_and_wrong_launcher_fail_closed(tmp_path):
    with pytest.raises(OwnershipBlocked, match="CURRENT_PROCESS_UNVERIFIABLE"):
        classify([], tmp_path)
    with pytest.raises(OwnershipBlocked, match="COMPETING_SENTINEL_PROCESS"):
        classify(
            [self_record(), record(99, [sys.executable, "recovery_runner.py", "--execute"])],
            tmp_path,
        )


def test_duplicate_pid_fails_closed(tmp_path):
    with pytest.raises(OwnershipBlocked, match="PROCESS_INVENTORY_DUPLICATE_PID"):
        classify([self_record(), self_record()], tmp_path)


def test_unstable_inventory_fails_closed(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            stdout=json.dumps({"first": [self_record()], "second": []})
        ),
    )
    with pytest.raises(OwnershipBlocked, match="PROCESS_INVENTORY_UNSTABLE"):
        process_inventory()


def test_explicit_original_state_competitor(tmp_path):
    with pytest.raises(OwnershipBlocked, match="COMPETING_SENTINEL_PROCESS"):
        classify(
            [
                self_record(),
                record(200, [sys.executable, "worker.py", str(tmp_path / "repo/original-state")]),
            ],
            tmp_path,
        )


def test_untrusted_executable_cannot_claim_to_be_sleep(tmp_path):
    worker = record(200, [sys.executable, "-c", "import time; time.sleep(20)"])
    worker["ExecutablePath"] = str(tmp_path / "missing-python.exe")
    with pytest.raises(OwnershipBlocked, match="PROCESS_IDENTITY_UNVERIFIABLE"):
        classify([self_record(), worker], tmp_path)


def test_missing_owner_marker_is_not_created(tmp_path):
    gate = tmp_path / "gate.sqlite3"
    with pytest.raises(OwnershipBlocked, match="OWNER_MARKER_UNVERIFIABLE"):
        probe_owner_lock(gate)
    assert not Path(str(gate) + ".owner").exists()


def test_real_unrelated_python_sleep_and_readonly_lock(tmp_path):
    state = tmp_path / "original-state"
    state.mkdir()
    marker = state / "gate.sqlite3.owner"
    marker.write_bytes(b"0")
    worker = subprocess.Popen(
        [sys._base_executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        result = verify_no_predecessor(tmp_path, state)
        assert any(
            p["pid"] == worker.pid and p["classification"] == "UNRELATED_VERIFIED_LITERAL_SLEEP"
            for p in result["processes"]
        )
        assert result["owner_probe"]["existing_owner_fence"] == "AVAILABLE"
        assert marker.read_bytes() == b"0"
    finally:
        worker.terminate()
        worker.wait(timeout=5)


def test_real_competing_public_runtime_owner(environment):
    state, _ = environment  # Synthetic state only: no original Run/Action or financial state.
    ready = state / "child-ready"
    program = """
import sys, time
from pathlib import Path
from refund_sentinel.config import Settings
from refund_sentinel.integration import composition
from refund_sentinel.paypal import FakePayPal
state = Path(sys.argv[1])
with composition(state, Settings(), predecessor_stopped=True,
                 paypal=FakePayPal(state / 'fake-paypal.sqlite3')):
    (state / 'child-ready').write_text('ready', encoding='ascii')
    deadline = time.monotonic() + 30
    while not (state / 'child-stop').exists() and time.monotonic() < deadline:
        time.sleep(0.02)
"""
    worker = subprocess.Popen(
        [sys.executable, "-c", program, str(state)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 20
        while not ready.exists() and worker.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "Synthetic public Runtime owner failed to start"
        with pytest.raises(OwnershipBlocked, match="OWNER_LOCK_BUSY_OR_UNVERIFIABLE"):
            probe_owner_lock(state / "gate.sqlite3")
        with pytest.raises(OwnershipBlocked, match="COMPETING_SENTINEL_PROCESS"):
            classify_processes(
                process_inventory(),
                repo=state.parent,
                state=state,
                current_pid=os.getpid(),
                parent_pid=os.getppid(),
                executables=(sys.executable, sys._base_executable),
            )
    finally:
        (state / "child-stop").write_text("stop", encoding="ascii")
        worker.wait(timeout=35)
    assert probe_owner_lock(state / "gate.sqlite3")["existing_owner_fence"] == "AVAILABLE"
