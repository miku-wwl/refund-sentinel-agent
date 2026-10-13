# Phase 2.2 — Read-only Order Evidence Investigation

Date: **2026-10-13, Pacific/Auckland**. Scope: the already-created Sandbox order, one genuine order GET, offline response analysis, a bounded consumer validation fix and regression tests. **No Create Order retry, second order, buyer checkout, capture, refund, existing order-record edit/reset, commit or push.** This report supplements the original UNKNOWN_CREATE event; it does not overwrite the original private manifest or historical API evidence.

## Actual read-only observation

Loaded the saved order ID from the existing private fixture, verified Sandbox/account binding and used the existing `SandboxPayPal` read-only transport. Authentication required one OAuth POST, HTTP 200, **1.093218 seconds**. The only payment-resource API request was **GET order details**, HTTP 200, **0.893624 seconds**. No response links were followed and no other payment resource was queried. The current private configuration, original fixture JSON, exact create request and permanent create-attempt marker remained byte-for-byte unchanged.

| Observed field/check | Genuine result |
|---|---|
| `status` | **PAYER_ACTION_REQUIRED** |
| `intent` | **CAPTURE** |
| Purchase units | Exactly **1** |
| Amount / currency | **20.00 / NZD** |
| Order identity | Matches saved order ID |
| Purchase-unit reference | Matches saved create request identity |
| Payee merchant ID | Matches the privately configured Sandbox Business merchant |
| Captures, refunds, authorizations | No entries reported; the `payments` field is absent |
| Buyer details | `payment_source.paypal` is an empty object, consistent with pre-approval |
| Buyer approval URL | Genuine URL returned by GET; exact Sandbox origin/path/token checks pass and URL matches the saved provider URL |

Actual identifiers and private response values are stored only under `.state-phase22-investigation-private/`; the existing `.state-paypal-fixture/` records remain intact. Public evidence: `evidence/phase-2.2/order-readonly-investigation.json`. A raw response archive contains no OAuth token or request headers and is Git-ignored.

## Exact reproduced failure

The original validator compared the `self` link against one literal URL, `https://api-m.sandbox.paypal.com/v2/checkout/orders/{saved_order_id}`. The genuine response instead contains `https://api.sandbox.paypal.com/v2/checkout/orders/{saved_order_id}`, with the same order path and GET method. The shared `verify_links` function raised `ValueError("Resource link mismatch")`; `validate_order` collapsed it into `FIXTURE_ORDER_EVIDENCE_INVALID` before reaching the purchase-unit checks.

Using a copy of the saved genuine response, changing **only** that origin in memory made the original validator return PAYER_ACTION_REQUIRED. No provider record, private fixture, original response archive or live order was altered for that experiment. This isolates the currently reproduced failure to the response-link hostname, rather than an intent, money, merchant, reference, purchase-unit or status mismatch.

[PayPal's official standard integration example](https://developer.paypal.com/checkout/put-it-all-together/) contains Sandbox order `self` links on `api.sandbox.paypal.com`. Its [webhook integration example](https://developer.paypal.com/api/rest/webhooks/rest/) also uses that host for capture and order resource links. The [Orders API schema](https://developer.paypal.com/api/orders/v2/schema.json) identifies `api-m.sandbox.paypal.com` as the Sandbox request server. These primary sources and the genuine response support recognizing the two exact Sandbox origins in response metadata; they do not justify arbitrary PayPal subdomains, Live links or provider-selected request destinations.

## Scoped fix and safety checks

The consumer's `verify_links` now accepts resource/refund metadata URLs constructed from exactly either `https://api-m.sandbox.paypal.com` or `https://api.sandbox.paypal.com`. The URL still must exactly match the expected resource path/ID and HTTP method. Extra query/fragment/port/userinfo, non-HTTPS, Live/lookalike hosts, alternate resources, encoded paths and malformed URL values fail. Missing/mismatching order identity, merchant, intent, amount/currency, purchase unit/reference and required buyer approval retain their checks.

`validate_order` now reports a bad resource link specifically as `FIXTURE_ORDER_RESOURCE_LINK_INVALID`, without exposing the URL, identifiers or response body. No shared Runtime source, dependency pin, execution authorization, durable attempt marker, retry behavior or read-only transport was changed. Actual HTTP requests remain fixed to `https://api-m.sandbox.paypal.com`; the alias is accepted solely as response evidence and is not an allowed read-only network destination. The existing refund outcome verifier has not been relaxed or qualified against a real refund.

The unchanged genuine response now passes the fixed validator and still yields **PAYER_ACTION_REQUIRED**. Validation is a pure observation: the original fixture remains **UNKNOWN_CREATE**, with its original permanent create marker and no capture marker. No automatic reconciliation or retry path was added. This fix does not authorize creation, buyer checkout, capture or refund, and does not allow a previously attempted POST to be resent.

## Regression evidence

Added `tests/fixtures/paypal-order-payer-action-required.sanitized.json`, retaining the observed field/list structure, empty PayPal wallet and official alias links while replacing the order/merchant/reference identifiers and timestamp with synthetic values. No actual payment identifier, private merchant value, credential or token is included.

Added 37 regression cases covering that response shape, both exact documented metadata origins, hostile/Live origins, URL/path/ID/method violations, malformed values, money/merchant/intent/reference/purchase-unit failures, missing buyer approval, exact capture/refund metadata relationships, alias network rejection, and pure read-only observation without fixture-byte changes. Existing fixture authorization, no-retry, unknown-state, capture/refund safety and preflight regressions remain in place. All pytest network calls are fenced and use MockTransport, local ASGI or isolated fake effects.

Related suites: **193 passed, 1 existing warning in 5.40 seconds**. Full regression: **261 passed, 1 existing warning in 44.55 seconds**, zero failures/errors, recorded separately in `evidence/phase-2.2/pytest-order-investigation.xml`. Ruff and dependency checks passed; all 21 Python files passed formatting. Earlier Phase 2.1/2.2 evidence remains unchanged, including the deadline artifact that the full regression historically regenerates. Original `.env`/fixture files and all 54 hashed installed Runtime-distribution files passed final integrity verification; public changed files passed credential/payment-identifier redaction checks.

## Buyer approval readiness and stop point

**YES, the observed existing order can safely proceed to the next separately instructed manual Sandbox buyer-approval step.** The fixed validator confirms the saved order, CAPTURE intent, one purchase unit, NZD 20.00, expected merchant/reference and genuine saved Sandbox approval URL. PAYER_ACTION_REQUIRED means buyer action is still required; it is neither an APPROVED order nor evidence of a captured payment. See the [official PayPal Wallet creation flow](https://developer.paypal.com/api/orders/v2/orders-create).

No buyer approval is requested or performed in this investigation. The user controls the next step. The original UNKNOWN_CREATE journal state is intentionally preserved under the instruction not to edit existing order records; any later explicit local reconciliation must preserve the order/request identities and original create marker and must not retry Create Order. Capture remains separately gated by real APPROVED/buyer/merchant evidence and explicit authorization. No real Capture ID exists and Phase 2.3 refund readiness is not established.

Only one additional genuine order GET latency sample is available. Neither that timing nor the response-link fix proves that a later refund fits the unchanged five-second Runtime budget. Work stops after this investigation, awaiting the user's next authorization.
