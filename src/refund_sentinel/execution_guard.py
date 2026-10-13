"""Local predecessor inspection; the public Runtime retains the actual owner fence.

This probe never opens a gate database, dispatches an Action or replaces Runtime locking.
Only a verified, literal Python sleep is exempted as an unrelated interpreter. Opaque
commands, missing process metadata and Sentinel competitors remain fail-closed.
"""

import ast
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


class OwnershipBlocked(RuntimeError):
    def __init__(self, code, diagnostics=None):
        super().__init__(code)
        self.code = code
        self.diagnostics = diagnostics or {}


def _path_identity(value):
    return os.path.normcase(str(Path(value).resolve(strict=True)))


def windows_argv(command):
    if os.name != "nt" or not isinstance(command, str) or not command.strip():
        raise OwnershipBlocked("PROCESS_COMMAND_UNVERIFIABLE")
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not pointer:
        raise OwnershipBlocked("PROCESS_COMMAND_UNVERIFIABLE")
    try:
        return [pointer[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(pointer)


def literal_sleep(argv):
    """Recognize the complete harmless program, never a substring of arbitrary code."""
    if len(argv) != 3 or argv[1] != "-c":
        return False
    try:
        tree = ast.parse(argv[2])
    except (SyntaxError, ValueError):
        return False
    if len(tree.body) != 2:
        return False
    first, second = tree.body
    if not (
        isinstance(first, ast.Import)
        and len(first.names) == 1
        and first.names[0].name == "time"
        and first.names[0].asname is None
        and isinstance(second, ast.Expr)
        and isinstance(second.value, ast.Call)
    ):
        return False
    call = second.value
    return (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "time"
        and call.func.attr == "sleep"
        and not call.keywords
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Constant)
        and type(call.args[0].value) in (int, float)
        and 0 < call.args[0].value <= 86400
    )


def process_inventory():
    if os.name != "nt":
        raise OwnershipBlocked("PROCESS_PLATFORM_UNQUALIFIED")
    # Two independent CIM snapshots catch PID reuse, exit/start races and changing metadata.
    command = """
    $ErrorActionPreference = 'Stop'
    function Read-Owners {
      @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(python|pythonw|uvicorn|refund-sentinel).*'
      } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate)
    }
    @{first=@(Read-Owners); second=@(Read-Owners)} | ConvertTo-Json -Depth 4 -Compress
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        data = json.loads(result.stdout)
        first, second = data["first"], data["second"]
        if not isinstance(first, list) or not isinstance(second, list) or first != second:
            raise OwnershipBlocked("PROCESS_INVENTORY_UNSTABLE")
        return second
    except OwnershipBlocked:
        raise
    except Exception as exc:
        raise OwnershipBlocked("PROCESS_INVENTORY_UNAVAILABLE") from exc


def classify_processes(processes, *, repo, state, current_pid, parent_pid, executables):
    if len({p.get("ProcessId") for p in processes}) != len(processes):
        raise OwnershipBlocked("PROCESS_INVENTORY_DUPLICATE_PID")
    trusted = {_path_identity(p) for p in executables}
    current = [p for p in processes if p.get("ProcessId") == current_pid]
    if len(current) != 1:
        raise OwnershipBlocked("CURRENT_PROCESS_UNVERIFIABLE")
    records = []
    parsed = {}
    for process in processes:
        pid = process.get("ProcessId")
        try:
            if (
                type(pid) is not int
                or type(process.get("ParentProcessId")) is not int
                or not process.get("CreationDate")
                or not process.get("ExecutablePath")
                or not process.get("Name")
            ):
                raise ValueError
            executable = _path_identity(process["ExecutablePath"])
            argv = windows_argv(process.get("CommandLine"))
            if (
                executable not in trusted
                or not argv
                or _path_identity(argv[0]) not in trusted
                or Path(executable).name.casefold() != process["Name"].casefold()
            ):
                raise ValueError
        except (OSError, ValueError, TypeError, OwnershipBlocked) as exc:
            raise OwnershipBlocked("PROCESS_IDENTITY_UNVERIFIABLE", {"pid": pid}) from exc
        parsed[pid] = argv
        records.append(
            {
                "pid": pid,
                "parent_pid": process["ParentProcessId"],
                "executable_verified": True,
                "command_sha256": hashlib.sha256(process["CommandLine"].encode()).hexdigest(),
            }
        )
    self_argv = parsed[current_pid]
    state_strings = {str(Path(state).resolve()).replace("\\", "/").casefold()}
    repo_string = str(Path(repo).resolve()).replace("\\", "/").casefold()
    state_strings.add(Path(state).name.casefold())
    for record in records:
        pid = record["pid"]
        argv = parsed[pid]
        if pid == current_pid:
            role = "CURRENT_VERIFIED_INTERPRETER"
        elif pid == parent_pid and argv == self_argv and current[0]["ParentProcessId"] == pid:
            role = "VERIFIED_VENV_LAUNCHER"
        elif literal_sleep(argv):
            role = "UNRELATED_VERIFIED_LITERAL_SLEEP"
        else:
            normalized = " ".join(argv).replace("\\", "/").casefold()
            references = any(p in normalized for p in state_strings) or repo_string in normalized
            sentinel = any(
                p in normalized
                for p in ("refund_sentinel", "refund-sentinel", "execute-once", "recovery_runner")
            )
            code = (
                "COMPETING_SENTINEL_PROCESS" if references or sentinel else "OPAQUE_PYTHON_PROCESS"
            )
            raise OwnershipBlocked(code, {"pid": pid, "identity_verified": True})
        record["classification"] = role
    return records


def probe_owner_lock(gate_path):
    """Read-only probe of the existing one-byte OS fence; never create/write its file.

    This probe is released immediately. open_runtime must still acquire and hold its
    original lock around all actual reads/execution; the probe grants no ownership.
    """
    marker = Path(str(gate_path) + ".owner")
    if not marker.is_file() or marker.is_symlink() or marker.stat().st_size < 1:
        raise OwnershipBlocked("OWNER_MARKER_UNVERIFIABLE")
    try:
        with marker.open("rb") as handle:
            if os.name != "nt":
                raise OwnershipBlocked("OWNER_PLATFORM_UNQUALIFIED")
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                return {"existing_owner_fence": "AVAILABLE", "file_written": False}
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OwnershipBlocked:
        raise
    except OSError as exc:
        raise OwnershipBlocked("OWNER_LOCK_BUSY_OR_UNVERIFIABLE") from exc


def verify_no_predecessor(repo, state):
    records = classify_processes(
        process_inventory(),
        repo=repo,
        state=state,
        current_pid=os.getpid(),
        parent_pid=os.getppid(),
        executables=(sys.executable, sys._base_executable),
    )
    fence = probe_owner_lock(Path(state) / "gate.sqlite3")
    return {"processes": records, "owner_probe": fence, "fail_closed": True}
