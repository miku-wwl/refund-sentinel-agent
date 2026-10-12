# Phase 2.1 — Sandbox Preflight & Engineering Hardening

Date: **2026-10-13, Pacific/Auckland**. Scope: local changes/tests, genuine Sandbox OAuth, allowed read-only queries and sanitized evidence. **Real order creation, payment capture and refund execution were not authorized and were not run.** No application server was started and no existing state directory was reset. This report records implementation verification before separately authorized Git delivery; no tag, release or submission occurred.

## A. Code Changes

- Added installed CLI command `check-auth` using the existing `SandboxPayPal.token` implementation. `SandboxOAuthSettings` validates only the trusted Sandbox mode/origin and private OAuth credentials, allowing authentication without a capture, merchant lookup, model or state database. Normal application validation remains strict.
- Added a separate preflight module and `SandboxReadOnlyTransport`: exact HTTPS Sandbox origin, OAuth token POST and bounded capture/order/refund GET paths only. Payment-changing requests, redirects to other origins, query-bearing/arbitrary paths and live/lookalike hosts cannot dispatch through this transport. Consumer refund methods reject read-only mode before OAuth. Reports explicitly label REAL_SANDBOX or MOCK.
- OAuth now distinguishes credential rejection, HTTP rejection, connection failure, timeout, protocol/transport failure and malformed Bearer responses. Access-token size/type/characters/expiry are validated; token cache is reused in-client and cleared on close. Latency telemetry contains only operation names, methods, HTTP status and durations, never URLs containing identifiers, headers or provider bodies.
- `check-capture` reports empty allowlists as `BLOCKED_NO_CAPTURE_ID` before authentication. Eligible configured captures use read-only transport and the same trusted capture-policy helper as the normal refund policy; output contains validation status rather than merchant/capture/amount values.
- `.env` loading rejects conflicting inherited values atomically and names the conflicting variables without their values. It preserves file bytes and matching inherited values. Normal Sandbox settings reject merchant emails/app names, missing capture allowlists and offline DEMO IDs.
- Capture/order verification checks exact identity, order association, semantic Decimal amount/currency equality, statuses and payee consistency. Relevant returned HATEOAS links must match fixed resources/methods. Missing optional links are recorded without inventing them. Refund arrays must have valid shape, identity, status and money/currency; any reported refund blocks the narrow policy.
- Documented provider money strings with zero/one/two decimal places normalize exactly to two decimals; floats and excess precision fail without rounding. Outgoing refund/model amounts remain canonical two-decimal strings. Minimal 200/201 acknowledgment still needs a complete matching refund GET; duplicate/in-progress provider errors are not no-effect proof.
- Application metadata, Ruff, README and version guard now require **Python >=3.13,<3.14**, matching the unchanged pinned Runtime. Added regression HTTP-transport fencing: all automated tests use ASGI, isolated fake providers or MockTransport; a real HTTP transport raises before network dispatch.

Root AGENTS.md, shared Runtime source, qualified SHA, existing private credentials and existing application state were preserved. No dependency upgrades were introduced; only this application's editable metadata was refreshed.

## B. Environment Validation

Only presence/validity is reported; values are not printed or stored here.

| Configuration | Observed status |
|---|---|
| `.env` | Present, Git-ignored, byte-for-byte unchanged |
| `PAYMENT_MODE` | Present; expected Sandbox mode matches |
| `AI_MODE` | Present; deterministic interpretation matches the configured test mode |
| `PAYPAL_ENVIRONMENT` | Present; Sandbox matches |
| `PAYPAL_BASE_URL` | Present; exact expected HTTPS Sandbox origin matches |
| `PAYPAL_CLIENT_ID` | Present; genuine OAuth accepted the credentials |
| `PAYPAL_CLIENT_SECRET` | Present; genuine OAuth accepted the credentials |
| `PAYPAL_MERCHANT_ID` | Present; merchant-ID format valid; account identity/ownership not independently verified |
| `PAYPAL_CAPTURE_IDS` | Empty; no real identifier fabricated or substituted |
| `MAX_REFUND` | Present |
| `SENTINEL_STATE_DIR` | Present; distinct expected Sandbox directory configuration matches |
| Inherited environment conflicts | None at inspection; conflict behavior is covered by tests |
| Local Python / installed application metadata | Python 3.13.9 / `<3.14,>=3.13` |

OAuth validates client credentials, not the supplied Business merchant ID or refund eligibility. Merchant ownership requires the later matching capture/order evidence. Auth-only did not initialize a Sandbox database. Evidence: `evidence/phase-2.1/environment-status.json`.

## C. PayPal Sandbox Results

| Genuine operation | Result | Actual evidence |
|---|---|---|
| OAuth authentication | **PASS** | Installed `refund-sentinel.exe check-auth`; one token POST, HTTP 200, valid Bearer response |
| Capture GET | **BLOCKED — BLOCKED_NO_CAPTURE_ID** | Installed `check-capture`; empty allowlist, zero HTTP requests |
| Order GET | **BLOCKED — BLOCKED_NO_CAPTURE_ID** | No capture association available; zero HTTP requests |
| Refund POST | **NOT AUTHORIZED / NOT RUN** | Zero real refund requests |
| Order creation / payment capture | **NOT AUTHORIZED / NOT RUN** | Zero real payment mutations |

Executed commands:

```powershell
.\.venv\Scripts\refund-sentinel.exe check-auth
# Exit 0; genuine OAuth PASS
.\.venv\Scripts\refund-sentinel.exe check-capture
# Exit 2; BLOCKED_NO_CAPTURE_ID; no request
```

The allowed OAuth POST took **1.520656 seconds**; auth command work took **1.521497 seconds**. A second token access hit the cache and issued no second POST. No access token, credential, full response or payment identifier was persisted. Evidence: `oauth-real.json`, `capture-order-real.json` under `evidence/phase-2.1/`. These results are separate from mocked contract tests.

## D. PayPal API Compatibility

Official primary sources were read: [capture details](https://developer.paypal.com/api/payments/v2/captures-get), [order details](https://developer.paypal.com/api/orders/v2/orders-get), [capture refund](https://developer.paypal.com/api/payments/v2/captures-refund), [refund lookup](https://developer.paypal.com/api/payments/v2/refunds-get), [OAuth](https://developer.paypal.com/api/rest/authentication/) and [idempotency](https://developer.paypal.com/api/rest/reference/idempotency/).

Confirmed in isolated mocked contracts: explicit partial `amount.value/currency_code` body, Bearer authorization, stable durable effect UUID in `PayPal-Request-Id`, `Prefer: return=representation`, HTTP 200/201 acknowledgments, independent refund-ID GET, exact capture-link/amount/currency matching and current COMPLETED/PENDING status handling. A POST acknowledgment is never enough for success. Missing IDs, missing verification fields and unrecognized responses preserve Unknown. PENDING/FAILED/CANCELLED provider observations remain distinct from the Runtime terminal state.

Provider string-money normalization supports documented integer/decimal representation without float arithmetic. Missing capture payee can use the uniquely associated order payee; missing order association or merchant evidence fails closed. Returned conflicting or live-origin resource links are rejected and never followed. Prior refund information is labeled NONE_REPORTED or REPORTED, rather than inventing a confirmed refunded total or claiming complete historical coverage.

PayPal idempotency is retention/endpoint dependent; duplicate/in-progress errors do not prove that a previous operation had no effect. No retries were added. Actual merchant-specific capture/order/refund response shapes remain unverified because no eligible capture exists. Some official examples use live-origin links; those are not silently converted into Sandbox verification evidence. Future real mismatches require review, not relaxation of checks.

## E. Timeout Analysis

- Unchanged normal client HTTPX timeout: **1.1 seconds for each connect/read/write/pool phase**. This is not a 1.1-second wall-clock request cap: connection phases, multiple reads and sequential calls can accumulate.
- Normal execution may require capture GET → order GET → refund POST → refund GET → local evidence/receipt persistence; expired token caching adds OAuth. Analysis already reads payment facts before approval. Fresh execution-time reads remain necessary to detect changed status/refunds/payee/amount; removing them would weaken the safety boundary. Cached OAuth is safe within the same client and expiry margin; the preflight token is not shared with a later application process or stored on disk.
- Read-only diagnostics use connect/write/pool **5 seconds**, read **10 seconds**. These apply only to preflight, where no payment mutation can dispatch. They do not modify normal executor timeouts or the Runtime budget.
- Real data available: one OAuth sample, **1.520656 seconds**. Real capture/order latency and real refund latency are **NOT RUN**, so neither an overall five-second feasibility claim nor an incompatibility claim is established.
- Installed `ActionExecutionGateway` constrains `tool_timeout_seconds` to at most 5; `execute(deadline=...)` uses `min(internal_deadline, caller_deadline)`. Caller deadlines can shorten, never extend, the limit. The actual installed source and public signature were inspected; the shared consumer reference was read.
- New deterministic test supplied a 30-second caller deadline. The isolated fake provider committed one refund and delayed acknowledgment; execution finished after **5.136312 seconds**, durably **Unknown**. Replaying the command produced no second provider attempt. The existing cancellation/restart/duplicate/concurrent protections also passed. Evidence: `deadline-mock.json` and final JUnit report.

No background execution, detached requests, core monkeypatch, timeout extension or automatic reconciliation was implemented. If later authorized reads/refund evidence show the budget is unsuitable, propose a separately reviewed bounded timeout option in the core's public composition API, with cancellation/Unknown/restart/idempotency qualification and a new immutable qualified pin. Do not implement that change in the consumer or promise remote exactly-once behavior.

## F. License Audit

Pinned SHA: `fd742b783058a53400c465b4ab59c6e80715895a`, installed version 0.1.0. Anonymous pinned Git-tree inspection was complete: no LICENSE/COPYING/NOTICE paths; pinned README had no license mention; pinned pyproject had no license/license-files declaration. Installed License, License-Expression and License-File metadata were absent. All **47** installed hashed core files still match RECORD. Evidence: `runtime-license-audit.json`.

Anonymous HTTPS Git tag access succeeded with credential helpers, global/system configuration and extra authentication headers disabled. Independent judges can retrieve the qualified source without this machine's private Git credentials, subject to ordinary connectivity. A complete install in an independent clean judge environment was **NOT RUN**; Python 3.13 and dependency access remain prerequisites.

Licensing remains **UNRESOLVED**. Public source access alone does not supply open-source reuse/distribution permissions; this application's MIT license does not license its dependency. [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains the distinction.

The Runtime owner should determine the applicable rights, add an explicit license and distribution metadata, and provide either an explicit grant covering this exact pinned commit or a separately reviewed licensed release. A new release should use a new version/tag and be requalified before changing the consumer pin; do not move v0.1.0 or rewrite its SHA. No Runtime license/source/tag/metadata changes were made here.

## G. Regression Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/phase-2.1/pytest.xml
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir .state-phase21-packaging-final
git diff --check
```

Results: **157 passed, 1 warning in 42.76 seconds**, zero failures/errors in final JUnit; original 91 regression cases retained. Before final integration, focused preflight suite: 41 passed; focused contract/deadline suite: 25 passed. The one retained warning is Starlette's existing HTTPX TestClient deprecation; unrelated dependencies were not upgraded or warnings suppressed. Lint passed, all 18 Python files were formatted, pip reported no broken requirements, and application wheel build passed.

All regression network dispatch is blocked except isolated ASGI/fake/MockTransport paths. Coverage includes OAuth credentials/network/response failures, token cache/secret redaction, missing captures without authentication, mode/origin/merchant checks, dotenv conflicts without file writes, minimal refund acknowledgments, semantic string-money variation, malformed links/history, exact verified effects, real Runtime deadline/cancellation and existing approval/authorization/restart/duplicate/concurrency guards. Mock effects are persisted and counted, rather than asserting a UI success string.

Wheel inspection verifies Python constraint, unchanged core SHA, bundled static assets/preflight module and source consistency. Final redaction/immutability checks verify `.env` bytes, AGENTS.md and installed core hashes; no staged secrets or payment mutation evidence is introduced. Original implementation evidence remains separate and unchanged. Details: `packaging.json`, `verification.json` and `pytest.xml` under `evidence/phase-2.1/`.

## H. Remaining Human Tasks

1. Explicitly authorize a later Sandbox fixture-creation/capture phase, or provide an existing completed capture belonging to the configured Business account. Complete any Sandbox buyer login/approval interactively; no known capture can be invented or automatically created in this phase.
2. Add the actual capture ID to the private allowlist and confirm account identity using subsequent read-only evidence. Keep the already-valid credentials private; do not replace them with placeholders.
3. Resolve the dependency license with its owner before claiming the complete stack is openly licensed/distribution-ready.
4. Later approve one exact refund test case: actual capture ID, currency and amount, then separately authorize execution through the Runtime gates. This phase grants no such payment authorization.

## I. Phase 2.2 Recommendation

First obtain explicit authorization for a small synthetic Sandbox order/capture using the same merchant app (or reuse a verified completed capture). Follow the official [Orders create](https://developer.paypal.com/api/orders/v2/orders-create) and [Orders capture](https://developer.paypal.com/api/orders/v2/orders-capture) workflow with an interactive Sandbox buyer. No fixture code runs during startup or offline tests.

After recording the actual capture ID privately, add it to `PAYPAL_CAPTURE_IDS`, run `check-capture` and inspect HTTP/identity/eligibility evidence plus genuine GET latency. Reject incomplete, mismatched, pending or previously refunded captures. Only then prepare a strictly partial USD/NZD Plan within merchant limits. Show the exact test case for explicit human approval; retain separate execution authorization and durable admission. Do not execute until a later prompt authorizes that specific test. Stop at Unknown and never create fresh state/request IDs to retry an ambiguous effect.
