import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "publication_audit", Path(__file__).parents[1] / "scripts/audit_publication.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_actual_private_literal_always_rejected():
    assert "PRIVATE_LITERAL_MATCH" in audit.inspect(
        "tests/test_phase231_links.py",
        b"https://" + b"user:password@api.sandbox.paypal.com PRIVATESECRET",
        {b"PRIVATESECRET"},
    )


def test_credential_url_requires_exact_reviewed_sample_and_path():
    body = b"https://" + b"user:password@api.sandbox.paypal.com"
    assert not audit.inspect("tests/test_phase231_links.py", body, set())
    assert "CREDENTIAL_URL" in audit.inspect("example.py", body, set())
    assert "CREDENTIAL_URL" in audit.inspect(
        "tests/test_phase231_links.py",
        b"https://" + b"user:realsecret@api.sandbox.paypal.com",
        set(),
    )


def test_payer_allowlist_requires_exact_synthetic_fixture():
    body = b'{"payer_id":"BBBBBBBBBBBBB","email_address":"synthetic-account@example.test"}'
    assert not audit.inspect("tests/fixtures/paypal-order-approved.sanitized.json", body, set())
    assert "UNREDACTED_PERSONAL_FIELD" in audit.inspect("evidence/payment.json", body, set())
    assert "UNREDACTED_PERSONAL_FIELD" in audit.inspect(
        "tests/fixtures/paypal-order-approved.sanitized.json", b'{"payer_id":"REAL_BUYER"}', set()
    )


def test_private_process_and_database_records_rejected():
    assert "LOCAL_PROCESS_OR_DEBUG_RECORD" in audit.inspect(
        "evidence/outcome.json", b'{"ownership":{}}', set()
    )
    assert "PRIVATE_OR_GENERATED_PATH" in audit.inspect("evidence/runtime.db-wal", b"", set())
