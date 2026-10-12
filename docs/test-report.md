# Test report — 2026-10-12

## Automated quality gates

Environment: Windows, Python 3.13.9, installed `agentic-intent-gate==0.1.0` from the full qualified Git commit. No tests call PayPal or a model service.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/pytest.xml
# 91 passed, 1 warning in 36.08s
.\.venv\Scripts\ruff.exe check src tests scripts
# All checks passed!
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\python.exe -m pip check
# No broken requirements found.
.\.venv\Scripts\python.exe scripts/collect_evidence.py
# Evidence saved: evidence\offline-workflows.json
git diff --check
```

The one warning is Starlette's deprecation of HTTPX for its TestClient in favor of HTTPX2. The tested pinned dependency set still works; this warning was retained, not suppressed. Initial implementation runs exposed an approval-enum mapping bug and an incorrect HTTP-status test expectation. Both were corrected; the final JUnit report has zero failures/errors.

## Acceptance coverage

| Required case | Evidence / actual assertion |
|---|---|
| 1. Happy path | Exact Plan, Approved Run, Pending/Authorized Action, one fake POST, verified fake refund, persisted Succeeded/receipt |
| 2. Invalid model response | Invalid JSON, duplicate keys, numeric money, extra tool field, excessive decimals, refusal/truncation rejected |
| 3. Unknown tool | Real installed Runtime rejects custom invalid Plan; registry refuses unknown executor identity |
| 4. Wrong target/binding/scope | Runtime Plan validator, registry, bound authorization and executor reject mismatches with zero provider calls |
| 5. Missing authorization | Pending Action execute returns ACTION_NOT_EXECUTABLE; missing capability returns 401; no refund |
| 6. Stale/mismatched approval | Expected Run version and exact Plan fingerprint mismatches rejected; Run stays AwaitingApproval |
| 7. Duplicate execution | Same command replays its stored result; new command cannot dispatch terminal Action; one provider call |
| 8. Conflicting identity/payload | Reused command key with changed content returns IDEMPOTENCY_CONFLICT; changed refund payload rejected against persisted incident |
| 9. Uncertain remote effect | Fake commits refund then loses acknowledgment; Runtime records Unknown; no re-dispatch |
| 10. Trusted amount limits | Zero/full/over-capture/over-policy amounts and currency mismatches create no Plan |
| 11. Concurrency | Two execute attempts: one 200 and one 409, one provider effect. Same-capture analysis reservation also prevents duplicates |
| 12. Restart | Persisted Succeeded/receipt/effects survive reopen; actual five-second timeout then restart preserves Unknown and blocks retry |
| 13. Missing credentials | Settings fails closed; missing HTTP capability denied; no credential-bearing errors |
| 14. Live environment | Live/alternate/lookalike URLs rejected; real client fixes Sandbox origin and disables redirects |
| 15. Pending vs completed | COMPLETED requires exact refund GET evidence; PENDING/FAILED/CANCELLED display provider state with Unknown Action |

Additional provider tests verify OAuth request form/token caching, capture/order association, payee consistency, explicit partial-refund body, UUID idempotency header, refund identity/amount/capture-link verification, redacted 4xx/5xx/redirect/transport errors and no retries. The cancellation test uses the unmodified Runtime's real five-second deadline after the fake provider commits an effect; it does not merely manufacture an Unknown UI string.

`runtime-integrity.json` verifies 47 installed core files against wheel RECORD hashes. `runtime-api.json` records actual public signatures and Git provenance. This establishes the installed dependency used locally; it does not qualify production/distributed behavior.

Packaging: `python -m pip wheel --no-deps . --wheel-dir .state-packaging` passed. The generated application wheel includes all three static assets and the immutable Runtime dependency SHA in its metadata (`packaging.json`). The final capability-literal/credential-URL scan and `git diff --check` passed; AGENTS.md remained unchanged. `verification.json` summarizes the final checked state.

## Real local AI evidence

Read-only discovery found the already-running Ollama server's `phi4-mini:latest`. No runtime installation, model download or service settings were changed. Three explicit synthetic analysis checks were recorded separately:

| Artifact | Actual result | Refund calls |
|---|---|---|
| `real-ai-smoke.json` | JSON-object output rejected as INVALID_MODEL_RESPONSE, 18.38 seconds | 0 |
| `real-ai-schema-smoke.json` | Genuine schema-valid REFUND/25.00/USD, HIGH interpretation uncertainty; policy blocked, 11.55 seconds | 0 |
| `real-ai-validated-smoke.json` | After clarifying that uncertainty concerns interpretation, genuine REFUND/25.00/USD/DAMAGED_ITEM/LOW; policy PASS, real Runtime AwaitingApproval, 12.03 seconds | 0 |

The final check uses the real `ChatCompletionsAnalyst`, `http://127.0.0.1:11434/v1`, `LLM_FORMAT=json_schema`, fake capture facts and the installed Runtime. No approval, authorization or refund was executed in that AI check. It proves local model analysis/Plan creation, not PayPal integration. For another explicit check with a pre-existing compatible local model:

```powershell
.\.venv\Scripts\python.exe scripts/collect_evidence.py --real-ai
```

## Browser and persistence

Chrome was controlled through computer-use on http://127.0.0.1:8879. File loading, synthetic request analysis, exact approval, Action admission, separate authorization, fake execution, provider evidence and read-only status check worked. Provider calls were **0 after authorization**, then **1 after execution**. The owned server process was stopped and restarted; the browser reopened the same Succeeded Action/receipt with the provider call count still 1. `browser-workflow.json` and authentic viewport screenshots capture this separately from automated TestClient evidence.

Desktop browser workflow: **PASS**. Phone viewport QA: **PASS** at 390 × 844 after a reload applied the delayed viewport override: document width 375, single layout column 339.111 pixels, no horizontal overflow. `browser-mobile.jpg` shows the persisted result with wrapped controls and two-column evidence cards. Initial measurements were stale and were not used as mobile evidence. Full-page screenshot export timed out in CDP; ordinary viewport screenshots succeeded.

## External verification

PayPal OAuth, capture/order GET, real refund POST and refund GET: **NOT RUN**. No PayPal credentials or specific human-approved refund test case were available. Client readiness is mock-tested. No live PayPal environment is supported; no Sandbox fixture side effects, real refunds, publishing or submission occurred.
