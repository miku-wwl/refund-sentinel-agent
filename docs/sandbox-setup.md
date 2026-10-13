# Real Sandbox setup and approved smoke test

## Phase 2.2: manually authorized fixture preparation

The isolated developer CLI is `python -m refund_sentinel.fixture`; it is not wired into application startup or the dashboard. It prepares one synthetic Sandbox NZD 20.00 order and capture, with separate human checkpoints for create, buyer checkout, capture and the private capture-allowlist edit. Start with local-only `prepare`; never supply payment authorization flags before the corresponding human approves. No refund is authorized in this phase. See the [Phase 2.2 report and exact commands](phase-2.2-report.md). Existing private credentials/state are preserved, and uncertain payment mutations cannot be retried or reset by the utility.

For **future** local fixtures, start the return-only receiver explicitly with `python -m refund_sentinel.fixture_callback` on the checkout browser's computer and keep it running through checkout. New preparation freezes HTTP loopback return/cancel URLs on port 8766; genuine create admission checks that receiver before contacting PayPal. Old fixtures retain their original URL/body/digest and cannot be re-prepared or retried. Callback navigation triggers no capture/refund; confirm approval with an explicit read-only order GET. See the [buyer approval and callback repair report](phase-2.2-buyer-approval.md).

## Phase 2.1: OAuth and read-only queries only

Use Python >=3.13,<3.14. Preserve any configured private `.env`; the current Phase 2.1 authorizes no payment creation, capture or refund. With Sandbox credentials configured, run:

```powershell
.\.venv\Scripts\refund-sentinel.exe check-auth
.\.venv\Scripts\refund-sentinel.exe check-capture --capture-id YOUR_ACTUAL_ALLOWLISTED_CAPTURE_ID
```

Auth-only does not require a capture ID, merchant ID, model or state provisioning. Capture-specific verification requires the actual Business merchant identity and an explicit eligible capture allowlist; an empty list reports `BLOCKED_NO_CAPTURE_ID` before any HTTP call. Sanitized reports omit credentials, tokens, payment identifiers and amounts. Differing inherited environment variables cause an explicit configuration conflict; the loader neither overwrites `.env` nor silently switches modes. Do not initialize or start a Sandbox state directory until its capture configuration is ready.

Genuine OAuth passed on 2026-10-13. Merchant-ID format was valid, but merchant ownership cannot be independently confirmed by client-credentials OAuth alone. Capture/order verification remains blocked until a real capture is provided. See [Phase 2.1 report](phase-2.1-report.md).

## Later phase: separately authorized payment preparation

The following workflow describes a later, explicitly authorized phase. No order, capture or refund operation below was executed in Phase 2.1.

1. Create/use a PayPal Developer account and a **Sandbox Business** account plus a separate **Sandbox Personal** buyer. Obtain your Sandbox app's client ID/secret and the Business merchant ID through the developer dashboard. Keep credentials private.
2. Prepare a completed Sandbox order/capture with no prior refunds. Record its capture ID and associated order ID. Use a small synthetic USD/NZD amount greater than the proposed partial refund. The application's policy needs capture/order association and merchant evidence.
3. Configure `.env`: `PAYMENT_MODE=sandbox`, `AI_MODE=real`, `PAYPAL_MERCHANT_ID`, `PAYPAL_CAPTURE_IDS` (explicit comma-separated allowlist), `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `SENTINEL_STATE_DIR=.state-sandbox`, plus a real `LLM_BASE_URL`, `LLM_MODEL` and optional `LLM_API_KEY`. Keep `PAYPAL_ENVIRONMENT=sandbox` and the fixed Sandbox URL. Use `LLM_FORMAT=json_schema` with a compatible model.
4. Install and initialize using the README. Verify credentials/payment facts with the read-only command:

   ```powershell
   .\.venv\Scripts\refund-sentinel.exe check-capture --capture-id YOUR17CHARCAPTURE
   ```

   This performs OAuth authentication and capture/order GETs. It creates no order, captures no payment and issues no refund. A failed check prints a redacted code. Do not put OAuth output in screenshots.

5. Start the local Sandbox dashboard, load its private operator capability, and enter synthetic customer text. Review the exact capture, merchant, amount, policy and Plan. **Stop before approval/authorization/execution until the human approves the specific capture ID, currency and refund amount.** No automatic Sandbox refund has been performed by this implementation session.
6. The human then approves the exact Plan, prepares the Action, separately authorizes, and executes the approved test case. Save redacted evidence of the Runtime Action, PayPal refund ID, lookup status and local receipt. COMPLETED is provider confirmation at that read, not a broader settlement guarantee. For Pending/Unknown, inspect the provider; never create a fresh incident/state directory or request ID to retry.

## Explicit fixture preparation, outside the refund tool

No fixture-creation program runs during startup or tests. Use the official [Orders create reference](https://developer.paypal.com/api/orders/v2/orders-create) in an authenticated developer REST tool to explicitly POST an `intent=CAPTURE` order with one Sandbox purchase unit. Sign in as the Sandbox buyer and complete the returned approval flow. Only after buyer approval, explicitly POST `/v2/checkout/orders/{order_id}/capture` as documented in [Orders capture](https://developer.paypal.com/api/orders/v2/orders-capture). Read the returned purchase-unit capture ID and check it using `check-capture`.

These create/capture operations are developer-operated test preparation, not additional registered Runtime tools. They must be deliberate actions; never automate buyer login, fixture payments, or a refund as a normal startup task. An existing eligible Sandbox capture may be used instead.

## Local AI option

A pre-existing Ollama server can use `LLM_BASE_URL=http://127.0.0.1:11434/v1`, `LLM_MODEL=phi4-mini:latest`, `LLM_FORMAT=json_schema`, blank API key. This repository does not install/start Ollama or download a model. Its real mode must be tested with the selected model; deterministic mode is always labeled separately. Only synthetic request data and amount/currency/status are sent to the model. Hosted endpoints require HTTPS.

Initial implementation verified local Ollama interpretation and Plan creation with fake payment facts. Phase 2.1 subsequently verified Sandbox OAuth only; no Sandbox refund has occurred. A separate `.state-*` directory is required when changing provider/merchant configuration; this is for distinct environments, never for retrying an unresolved capture.
