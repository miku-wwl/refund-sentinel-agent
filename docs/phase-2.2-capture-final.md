# Phase 2.2 Final — Verified Sandbox Capture

Date: **2026-10-13, Pacific/Auckland**. **PASS — the original Sandbox order has one genuine, independently verified COMPLETED capture for NZD 20.00.** One authorized Capture POST was sent. No new order, create retry, capture retry, refund, application-state reset, Runtime modification, commit, push or deployment occurred.

## Genuine requests and outcome

All requests used the fixed PayPal Sandbox origin, disabled redirects and zero transport retries. Values below are measured request wall times, not HTTPX per-phase timeout bounds.

| Operation | HTTP | Seconds | Verified observation |
|---|---:|---:|---|
| OAuth before capture | 200 | 0.903748 | Valid credentials; token retained only in client memory |
| Fresh order GET before capture | 200 | 0.823316 | APPROVED, CAPTURE intent, one unit, NZD 20.00, matching merchant/reference, distinct buyer, no existing payment entries |
| **Only Capture POST** | **201** | **1.482361** | COMPLETED order; one completed capture ID extracted from `purchase_units[0].payments.captures[0].id` |
| Post-capture order GET | 200 | 1.110254 | Same order, COMPLETED, exactly that capture |
| OAuth for independent verification | 200 | 0.826578 | Authentication only |
| Independent capture GET | 200 | 0.994596 | Same real capture ID, COMPLETED, NZD 20.00, related order identity |
| Independent order GET | 200 | 0.877511 | COMPLETED, one capture, matching merchant/buyer/reference and amount |
| OAuth for installed application check | 200 | 0.972362 | Authentication only |
| Installed `check-capture`: capture GET | 200 | 0.973165 | PASS |
| Installed `check-capture`: order GET | 200 | 0.971184 | PASS |

No unexpected duplicate capture was observed. The associated order reported no prior refunds. Order and Capture IDs are distinct and consistently match the POST acknowledgment, capture GET and order payment entry. `check-capture` returned CAPTURE_POLICY_ELIGIBLE with zero payment mutations. Public machine-readable evidence is `evidence/phase-2.2/capture-final-real.json`; full provider responses and identifiers are Git-ignored private artifacts, not included in this report.

Official contracts: [Orders capture](https://developer.paypal.com/api/orders/v2/orders-capture), [capture GET](https://developer.paypal.com/api/payments/v2/captures-get), [order GET](https://developer.paypal.com/api/orders/v2/orders-get), [idempotency](https://developer.paypal.com/api/rest/reference/idempotency/). The capture request used an empty body on the already-approved order, `Prefer: return=representation` and the existing durable capture UUID in `PayPal-Request-Id`. Provider idempotency is retention/endpoint dependent; no exactly-once claim or retry was introduced.

## Identity, history and allowlist

The earlier UNKNOWN_CREATE came from a now-corrected response-link alias check. For this explicitly authorized continuation, an explicit fixture option admitted reconciliation only after a fresh strict APPROVED order GET, matching the existing create marker and capture authorization. The original fixture JSON was archived byte-for-byte as `.state-paypal-fixture/pre-capture.fixture.json`. The original order/merchant/client binding, create UUID, capture UUID, create-attempt marker, exact create body and history prefix were preserved. UNKNOWN_CAPTURE was fsynced with an exclusive capture-attempt marker before dispatch; that marker permanently prevents another capture request through this utility. UNKNOWN_CAPTURE cannot be reconciled into another capture attempt.

The fixture is now VERIFIED, with the actual Capture ID recorded privately. As authorized, only the `PAYPAL_CAPTURE_IDS` value in the local `.env` changed. All other file bytes/settings/credentials were preserved; private files remain Git-ignored. The installed application's read-only check passed using that actual allowlisted capture. Existing application databases/state were not initialized or reset.

## Regression and remaining risks

Before dispatch, related fixture tests: **75 passed**. Eight new cases cover explicit reconciliation, byte-for-byte history archival, preserved IDs, matching create marker, fresh payment preconditions and permanent replay/UNKNOWN_CAPTURE rejection. Final full regression: **290 passed, 1 existing warning in 40.84 seconds**, zero failures/errors, recorded in `pytest-capture-final.xml`; lint, formatting (24 Python files) and dependency checks passed. The initial full run had one Windows PermissionError in a temporary mock fixture (289 passed); the affected case plus new group passed 9/9 on focused rerun. That initial JUnit is retained as `pytest-capture-final-initial.xml`. No payment operation was repeated and no permission/retry bypass was added. All 54 hashed installed Runtime-distribution files, the qualified pin and Git HEAD remain unchanged; public evidence passed private credential/payment/buyer-identifier scans.

**Phase 2.3 fixture preparation is READY** for a separately authorized NZD 5.00 partial-refund candidate: 5.00 is below the verified 20.00 capture and within the configured limit. **Refund execution remains conditional and NOT AUTHORIZED / NOT RUN.** The exact Plan still needs human approval, independent execution authorization, durable Runtime admission and fresh payment reads. Capture/order GETs near one second and a 1.482361-second capture POST do not prove refund POST/GET latency or five-second execution feasibility; the normal per-phase timeout and unchanged Runtime deadline remain a material Unknown-outcome risk. This fixture flow runs outside the Runtime refund executor and does not qualify that budget. The pinned Runtime license remains unresolved for distribution; its source/pin were not changed.

Work stops after verified capture preparation and the authorized allowlist edit. No refund was proposed, approved, authorized or executed through the Runtime in this phase.
