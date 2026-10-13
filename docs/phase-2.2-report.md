# Phase 2.2 — Final Sandbox Capture Preparation

Date: **2026-10-13, Pacific/Auckland**. **PASS: the original order has one genuine PayPal Sandbox Capture ID verified as COMPLETED for NZD 20.00.** Exactly one authorized capture POST was sent; no new order, create/capture retry or refund occurred. See the [concise final capture verification report](phase-2.2-capture-final.md) and `evidence/phase-2.2/capture-final-real.json` for measured requests and sanitized evidence. Actual identifiers and full provider responses remain in ignored private files.

## A. Fixture tool and safety

The developer-only `refund_sentinel.fixture` utility uses existing Sandbox credentials and one frozen NZD 20.00 CAPTURE-intent purchase unit. It is separate from application startup, the dashboard and the Runtime's registered refund SIDE_EFFECT executor. Exact account/money/order/reference/buyer validation, distinct durable request IDs, explicit operation consent and permanent POST-attempt markers remain enforced. Unknown results cannot trigger another POST.

The future-only local callback receiver and frozen callback URLs are covered in the [callback repair report](phase-2.2-buyer-approval.md). The current order retains its original callback/body/digest. The documented Sandbox metadata-host alias was corrected with exact origin/path/ID/method checks, while the network destination/read-only transport remained fixed; see the [read-only investigation](phase-2.2-order-investigation.md).

## B. Real Sandbox order creation

One separately authorized create POST returned HTTP 200 (1.295725 seconds), with a genuine order ID and Sandbox buyer link stored privately. The following order GET returned HTTP 200 (0.988876 seconds), but the then-strict `api-m` response-link check rejected the documented `api.sandbox` alias and retained UNKNOWN_CREATE. Creation was never retried. The original event is preserved in `order-create-real.json`.

A later expressly authorized read-only investigation reproduced and isolated that alias mismatch. All order/merchant/reference/money checks passed after the bounded metadata fix; the actual order was PAYER_ACTION_REQUIRED. That observation is retained in `order-readonly-investigation.json`.

## C. Sandbox buyer approval

The human used the independent Sandbox Personal buyer and completed checkout. Despite a failed navigation to the original inactive HTTPS localhost receiver, genuine order GET returned **APPROVED**, HTTP 200, 0.802608 seconds, with correct NZD 20.00, one unit and merchant/buyer identities. No payment capture was implied or executed at that checkpoint. Evidence: `buyer-approval-real.json` and the separate buyer report.

## D. Authorized real Capture

The user explicitly authorized one capture of the existing order. The capture utility's explicit `--reconcile-approved-creation` option required the exact capture consent/digest, existing matching create marker, absent capture marker and fresh strict APPROVED GET. It archived the old fixture bytes without changing identities or retrying creation. Before the payment POST, it durably claimed the existing capture UUID and saved UNKNOWN_CAPTURE.

Fresh order GET: HTTP 200, **0.823316 seconds**, all preconditions passed. Only Capture POST: **HTTP 201, 1.482361 seconds**. A real Capture ID was extracted from the sole `purchase_units[0].payments.captures[0]` entry. Post-capture order GET: HTTP 200, **1.110254 seconds**, COMPLETED with exactly that capture. The stable `PayPal-Request-Id` was the already-persisted capture UUID; no new ID or retry was used.

## E. Verified Capture ID and local configuration

Independent Capture GET: **HTTP 200, 0.994596 seconds**, COMPLETED, NZD 20.00, correct related order. Independent order GET: **HTTP 200, 0.877511 seconds**, COMPLETED, exactly one matching capture, expected merchant/reference and distinct buyer. No unexpected duplicate capture or prior refund was reported. The fixture is VERIFIED and the actual capture ID remains private.

As explicitly authorized, that identifier was added to local `.env` `PAYPAL_CAPTURE_IDS`. Every other byte/settings/credential was preserved. The original create marker/body, order/request identities and history prefix are intact; `pre-capture.fixture.json` preserves the original full fixture bytes. The new capture-attempt marker forbids re-execution.

## F. Actual application read-only check

The installed `refund-sentinel.exe check-capture` returned **PASS / CAPTURE_POLICY_ELIGIBLE**. Its Capture GET was HTTP 200, **0.973165 seconds**; Order GET was HTTP 200, **0.971184 seconds**; OAuth was HTTP 200, **0.972362 seconds**. It reported matching capture/order identity, amount/currency and configured merchant, with NONE_REPORTED prior refunds and **zero payment mutations**. No Runtime/database/server was started to perform this check.

## G. Current five-second Runtime risk

Fixture/preflight timeouts are separate from the unchanged Runtime refund execution budget. Actual reads are roughly 0.8–1.1 seconds; capture POST was 1.482361 seconds, which is not a refund timing. A refund execution still needs fresh capture/order reads, refund POST, refund GET, local persistence and possibly OAuth. HTTPX's normal 1.1-second phase timeout is not a wall-clock request limit. **Five-second refund feasibility is NOT PROVEN.** Expired OAuth, latency variation or delayed acknowledgments can yield Unknown. No core timeout extension, detached execution, automatic reconciliation or blind retry was introduced.

## H. Regression verification

Before genuine capture, **75 related tests passed**; eight newly added cases cover explicitly scoped reconciliation, original-history archival/identity retention, marker verification, fresh eligibility checks and no duplicate/UNKNOWN_CAPTURE retry. All ordinary pytest networking stays fenced to isolated fake/ASGI/MockTransport paths.

Final full regression: **290 passed, 1 existing warning in 40.84 seconds**, zero failures/errors, in `evidence/phase-2.2/pytest-capture-final.xml`. Lint, formatting (24 Python files) and `pip check` passed. The initial full run had 289 passes and one temporary Windows PermissionError in a mock fixture; that affected test and the new group then passed 9/9. Initial evidence is retained in `pytest-capture-final-initial.xml`; no real payment request was repeated. Historical Phase 2.1/2.2 evidence remains separate. All 54 hashed installed Runtime-distribution files, the qualified pin, AGENTS.md, existing application state and Git HEAD are preserved. Public changed files passed credential/payment/buyer-identifier scans.

## I. Remaining human actions

Capture preparation and the authorized private allowlist edit are complete. No further capture/order operation is needed in this phase. For a future NZD 5.00 partial-refund test, separately authorize that exact capture/currency/amount and use the existing Runtime's exact Plan approval, independent execution authorization and durable execution gates. Stop at Unknown. Resolve latency/API qualification before making reliability guarantees; resolve the unchanged Runtime license before distribution-readiness claims.

## J. Phase 2.3 readiness and stop point

**Fixture READY; refund execution CONDITIONAL.** The genuine completed capture passes the existing eligibility policy, 5.00 is strictly below 20.00 and within the configured limit, and the installed application read-only check passes. No real refund POST/GET has been qualified or timed; the five-second risk remains. NZD 5.00 is only a future candidate, **not authorized in this phase**. No Runtime refund Plan/Action approval or execution was created. No commit, push, deployment, release or submission occurred. Work stops after verification.
