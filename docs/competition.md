# PayPal AI Hackathon 2026

Verified on 2026-10-12 from the [official overview](https://paypalaihackathon.devpost.com/) and [official rules](https://paypalaihackathon.devpost.com/rules).

The rules require a functioning application meaningfully using PayPal Sandbox and an AI tool/model. A public open-source repository must include a license and complete run instructions; a hosted demo is optional. The public YouTube demonstration must be under three minutes and show the working application. Submission materials require English or English translations. Existing projects must document significant new work during the submission period; permitted reused software remains subject to its licenses. Judges must retain access through judging.

Deadline: **2026-11-12 12:00 PST / 2026-11-13 09:00 NZDT**. Judging uses five equally weighted criteria: Technological Implementation, Design, Potential Impact, Innovation/Idea, Presentation. Additional sponsor tools are optional unless entering their specific prize categories. Individual eligibility, ownership and excluded jurisdictions require entrant verification.

Refund Sentinel contributes the merchant workflow, analysis schema/provider, deterministic refund policy, PayPal adapter, browser UI, and product tests. Agentic Intent Gate remains an external pinned dependency. Offline fixtures demonstrate engineering behavior; they do not prove PayPal Sandbox execution or satisfy the real-integration demonstration on their own.

## API sources used

| Official source | Implementation decision |
|---|---|
| [OAuth authentication](https://developer.paypal.com/api/rest/authentication/) | Client credentials exchanged for a cached Bearer token; no token logging. |
| [Capture details](https://developer.paypal.com/api/payments/v2/captures-get) | Look up the selected capture with merchant credentials. |
| [Order details](https://developer.paypal.com/api/orders/v2/orders-get) | Cross-check capture association, merchant, amount, status and existing refunds. |
| [Capture refund](https://developer.paypal.com/api/payments/v2/captures-refund) | Explicit partial amount/currency; `PayPal-Request-Id`; representation response. |
| [Refund details](https://developer.paypal.com/api/payments/v2/refunds-get) | Independently read the returned refund ID before confirming completion. |
| [Payments schema](https://developer.paypal.com/api/payments/v2/schema.json) | Documented refund states: COMPLETED, PENDING, FAILED, CANCELLED. |
| [PayPal idempotency](https://developer.paypal.com/api/rest/reference/idempotency/) | Retention and endpoint support are limited; simultaneous requests can fail. No universal exactly-once claim or automatic retry. |
| [Create order](https://developer.paypal.com/api/orders/v2/orders-create), [capture order](https://developer.paypal.com/api/orders/v2/orders-capture) | Developer-operated Sandbox fixture preparation, separate from this application's refund tool. |
| [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | Configurable Chat Completions JSON object/schema mode; independently validate outputs. JSON mode alone does not establish schema compliance. |
| [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) | Local model option using `/v1/chat/completions`; actual model compatibility must be tested. |

## Verification gaps

The initial implementation lacked a genuine Sandbox test. That checkpoint is superseded by the [Phase 2 freeze](PHASE2-BACKEND-FREEZE.md): one genuine NZD 5.00 refund was independently verified COMPLETED with a durable receipt. Competition rules above are the dated 2026-10-12 observation, not a fresh rules review. Entrant eligibility, YouTube upload and final submission remain unverified.

The original v0.1.0 licensing gap was resolved by the separately released, immutably pinned Runtime v0.2.0. Its MIT license and distribution metadata were verified during qualification. Judges still need access to the pinned dependency; repository access is not granted by a local successful installation. No core source or release tag was changed by this application task.
