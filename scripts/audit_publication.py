"""Inspect an explicit public file set or Git index without printing sensitive values."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from refund_sentinel.config import read_env


def git(*args):
    return subprocess.check_output(["git", *args])


def private_literals(root):
    values = [
        value
        for key, value in read_env(root / ".env").items()
        if len(value) >= 16 and any(term in key for term in ("SECRET", "CLIENT_ID", "KEY", "TOKEN"))
    ]
    values += [p.read_text("ascii").strip() for p in root.glob(".state*/**/operator.capability")]
    # Only selected personal identity fields; known public Sandbox transaction IDs are excluded.
    for path in root.glob(".state*/**/*order*.private.json"):
        try:
            data = json.loads(path.read_text("utf-8"))
        except (ValueError, UnicodeError):
            continue
        payer = data.get("payer", {}) if isinstance(data, dict) else {}
        for key in ("payer_id", "email_address"):
            value = payer.get(key)
            if isinstance(value, str) and len(value) >= 8:
                values.append(value)
    return {value.encode() for value in values if value}


def inspect(name, body, literals):
    reasons = []
    path = Path(name)
    parts = path.parts
    if (
        any(p.startswith(".state") or p in {".venv", "__pycache__", "node_modules"} for p in parts)
        or path.name.startswith(".env")
        and path.name != ".env.example"
        or re.search(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$", name)
        or path.suffix in {".pyc", ".whl", ".log"}
        or "private.json" in name
    ):
        reasons.append("PRIVATE_OR_GENERATED_PATH")
    if any(value in body for value in literals):
        reasons.append("PRIVATE_LITERAL_MATCH")
    if re.search(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----", body):
        reasons.append("PRIVATE_KEY")
    if re.search(
        rb"(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,})", body
    ):
        reasons.append("CREDENTIAL_TOKEN_PATTERN")
    credential_body = body
    if name == "tests/test_phase231_links.py":
        # Exact, reviewed negative contract sample; literal-secret scanning still applies above.
        credential_body = credential_body.replace(
            b"https://" + b"user:password@api.sandbox.paypal.com", b"TEST_INVALID_URL"
        )
    if re.search(rb"https?://[^\s/'\"]+:[^\s/'\"]+@", credential_body):
        reasons.append("CREDENTIAL_URL")
    if path.suffix == ".json":
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            reasons.append("INVALID_JSON")
        else:

            def visit(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in {
                            "ProcessId",
                            "ExecutablePath",
                            "CommandLine",
                            "processes",
                            "ownership",
                            "sanitized_traceback",
                        }:
                            reasons.append("LOCAL_PROCESS_OR_DEBUG_RECORD")
                        if (
                            key
                            in {"access_token", "client_secret", "client_id", "operator_capability"}
                            and item
                        ):
                            reasons.append("CREDENTIAL_FIELD")
                        if (
                            key
                            in {"email_address", "payer_id", "address_line_1", "national_number"}
                            and item
                            and ".invalid" not in str(item)
                            and not (
                                name == "tests/fixtures/paypal-order-approved.sanitized.json"
                                and (key, item)
                                in {
                                    ("email_address", "synthetic-account@example.test"),
                                    ("payer_id", "BBBBBBBBBBBBB"),
                                }
                            )
                            and not str(item).startswith(("SYNTHETIC", "REDACTED", "TEST"))
                        ):
                            reasons.append("UNREDACTED_PERSONAL_FIELD")
                        visit(item)
                elif isinstance(value, list):
                    for item in value:
                        visit(item)

            visit(data)
    return sorted(set(reasons))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=Path)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--head", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    literals = private_literals(root)
    if args.files:
        names = json.loads(args.files.read_text("utf-8"))
    else:
        names = (
            git("ls-tree", "-r", "--name-only", "HEAD").decode().splitlines()
            if args.head
            else git("ls-files").decode().splitlines()
        )
    failures, manifest = [], {}
    for name in sorted(names):
        body = (
            git("show", ("HEAD:" if args.head else ":") + name)
            if args.staged or args.head
            else (root / name).read_bytes()
        )
        reasons = inspect(name, body, literals)
        if reasons:
            failures.append({"path": name, "reasons": reasons})
        manifest[name] = hashlib.sha256(body).hexdigest()
    report = {
        "status": "BLOCKED" if failures else "PASS",
        "files_scanned": len(names),
        "failures": failures,
        "manifest": manifest,
        "scope": "HEAD" if args.head else "INDEX" if args.staged else "EXPLICIT_FILES",
        "sensitive_values_printed": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "manifest"}, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
