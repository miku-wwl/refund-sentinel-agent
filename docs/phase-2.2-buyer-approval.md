# Phase 2.2 — Buyer Approval and Callback Repair

Date: **2026-10-13, Pacific/Auckland**. The user manually completed Sandbox Personal checkout and reported a redirect to HTTPS localhost followed by ERR_CONNECTION_REFUSED. This follow-up used the already-saved order ID for one genuine read-only order lookup. **No new/retried order, PATCH, capture, refund, buyer automation or original order-record edit/reset was performed.** New observations are archived separately from the original UNKNOWN_CREATE journal and earlier evidence.

## Genuine order result

OAuth authentication: HTTP 200, **1.060024 seconds**. The only payment-resource request was Order GET: **HTTP 200, 0.802608 seconds**. The existing read-only transport, fixed Sandbox request origin and disabled redirects/retries remained in force.

| Check | Actual provider result |
|---|---|
| Order status | **APPROVED** |
| Intent | **CAPTURE** |
| Amount / currency | **20.00 / NZD** |
| Purchase units | Exactly **1** |
| Order ID / purchase-unit reference | Match the saved original identities |
| Merchant ID | Matches the privately configured Sandbox Business merchant |
| Independent buyer evidence | Valid buyer account identity, distinct from merchant; consistent payer/wallet fields when both present |
| Prior payment entries | No captures, authorizations or refunds reported |
| Strict approved-order validation | **PASS** |

The order has moved from the previously observed PAYER_ACTION_REQUIRED to **APPROVED**. That confirms buyer approval at the actual GET observation; it does not confirm capture or settlement. [PayPal's Orders GET reference](https://developer.paypal.com/api/orders/v2/orders-get) shows the approved order details representation. No real Capture ID exists yet and no capture was attempted by this follow-up.

The full response, containing synthetic buyer account details, is stored only in Git-ignored `.state-phase22-buyer-return-private/`. Public evidence is `evidence/phase-2.2/buyer-approval-real.json`. Original `.env`, fixture JSON, exact create-order body, create-attempt marker and order/request identities are retained byte-for-byte. The local historical fixture phase remains UNKNOWN_CREATE; this observation does not silently reconcile it or authorize execution.

## Why the browser return failed

The exact original stored `payment_source.paypal.experience_context.return_url` is:

```text
https://localhost/refund-sentinel-sandbox/approved
```

It specifies HTTPS without an explicit port, so the browser connects to its own localhost on port 443 and expects a TLS-enabled HTTP server. The fixture did not provide/start that HTTPS receiver. Current local TCP inspection found zero listeners on ports 443 and 8766. This matches ERR_CONNECTION_REFUSED: the destination could not accept the connection. Changing only the scheme would still fail if no matching listener were running.

PayPal redirected after processing buyer checkout; the local navigation failure did not undo that approval. The genuine order GET, not the browser redirect, establishes APPROVED. The [Orders create reference](https://developer.paypal.com/api/orders/v2/orders-create) defines the Wallet experience-context return/cancel URLs. This is a local callback configuration issue; the original order is not rewritten or recreated to repair its return URL.

## Repair for future fixtures

Future local fixture preparation now freezes these paired addresses into its private manifest and request body:

```text
http://127.0.0.1:8766/refund-sentinel-sandbox/approved
http://127.0.0.1:8766/refund-sentinel-sandbox/cancelled
```

Added an explicit developer-only receiver, `refund_sentinel.fixture_callback`, bound to **127.0.0.1:8766 over HTTP**. It serves return/cancel information and a small health endpoint, with access logs disabled. It neither loads private credentials nor contacts PayPal, creates Runtime Actions, writes fixture state, echoes query tokens, confirms payment status from a redirect, nor exposes capture/refund endpoints. Return pages instruct the operator to use Order GET for status and retain separate Capture authorization. Cache/referrer/content policies avoid retaining or forwarding callback query values.

For future separately authorized fixtures, start and keep the receiver running on the same computer as the checkout browser:

```powershell
.\.venv\Scripts\python.exe -m refund_sentinel.fixture_callback
```

Future genuine creation requires the exact create authorization first, then a bounded credential-free GET to the fixed local health endpoint. Missing/wrong service, timeout or redirect blocks creation **before OAuth, a create-attempt marker or payment POST**. No listener is launched automatically by preparation, application startup or browser navigation. No receiver was started for the existing order in this follow-up.

Existing manifests lacking the new URL fields retain the original HTTPS localhost defaults. New preparation explicitly selects the working local pair. `order_body` reads the frozen pair and the existing review digest binds that request body. The actual existing order's body and review digest were checked unchanged after the repair. Arbitrary or mixed callback pairs fail validation; callbacks cannot silently switch for a prepared order.

[PayPal's local development examples](https://developer.paypal.com/v5/checkout/recurring/) use HTTP localhost return/cancel URLs, and its [quick-start integration](https://developer.paypal.com/checkout/integrate) starts a local HTTP server. This repair is qualified locally through isolated route/configuration tests; **creation of a future PayPal order using the new URLs was NOT RUN**, as new orders are prohibited in this follow-up. The current order's original URL remains unchanged.

## Tests and evidence preservation

Added a sanitized genuine APPROVED response fixture: field/list structure retained, with synthetic order/merchant/buyer/reference identities, names, email values and timestamps. Added 21 cases for frozen future URLs, legacy body/digest/record preservation, bounded URL-pair validation, return/cancel pages without token reflection or status certification, absence of payment endpoints, explicit loopback server configuration, readiness success/failure/no-retry, readiness admission before any payment attempt, approval-shape validation and no UNKNOWN-state promotion from browser navigation.

The first related run hit one Windows PermissionError while atomically replacing a temporary mock fixture during a duplicate-capture rejection. No real provider call was involved; the unchanged 10-case replay/uncertainty group passed on focused rerun. No retry/permission bypass was introduced and no safety assertion was removed. Final full regression: **282 passed, 1 existing warning in 41.77 seconds**, zero failures/errors, recorded in `evidence/phase-2.2/pytest-buyer-return.xml`. Ruff, formatting (23 Python files) and dependency checks passed. Prior JUnit/API observations and the original deadline evidence are preserved separately. Original fixture/credential-file hashes, request body and review digest, plus all 54 hashed installed Runtime-distribution files passed final verification; public evidence and test fixtures passed private credential/payment/buyer-identity scans.

## Stop point

**The existing Sandbox order is APPROVED; Capture remains NOT AUTHORIZED / NOT RUN.** Current records and identities are retained, with the new approved observation as separate evidence. Any later local reconciliation must be explicitly scoped and preserve the original create marker and identifiers; it must not retry creation. After separate Capture authorization, a fresh approved-order read and all merchant/buyer/amount checks remain necessary before one capture attempt. No allowlist or refund authorization is implied by this read-only follow-up.

Work stops here awaiting the user's next authorization. No commit, push, tag, release or submission was performed.
