# Phase 2.3.2 — Final Pilot Readiness

Date: **2026-10-13, Pacific/Auckland**. Decision: **GO for exactly one separately approved and authorized Sandbox NZD 5.00 pilot on the original capture**, with explicit acceptance of the balance and Unknown risks below. **Refund execution is NOT AUTHORIZED / NOT RUN.** This decision does not promise that a genuine refund will complete or be verified within five seconds. **NO-GO for a guaranteed five-second end-to-end result.**

The original genuine Ollama Plan can be resumed through the installed public Runtime in its original state directory. Fresh PayPal reads match its preserved payment facts. No prior intended-refund Action, attempt, financial dispatch or ambiguous outcome was found. Real Approval, admission, Authorization and execute command counts this phase are all **0**; genuine Refund POST count is **0**. No order or capture was created, historical state or secrets changed, Runtime modified, commit, push or deployment performed.

## Original Plan, identity and safe resumption

Read `AGENTS.md`, [Phase 2.3.1 remediation](phase-2.3.1-remediation.md), [genuine capture verification](phase-2.2-capture-final.md), the current configuration, PayPal client, RefundExecutor, Store and installed Runtime public API. The core consumer example was inspected. Installed distribution is **agentic-intent-gate 0.1.0**, resolving to **fd742b783058a53400c465b4ab59c6e80715895a**.

The original private directory is **`.state-phase23-private/real-model-plan`**, resolved under this repository. Its original Run ID, incident, capture/order identities and execution scope were compared across the persisted incident, gate database, identity file, archived Plan and original verified fixture. They match. No state was cloned, provisioned or substituted for this genuine candidate.

The Plan content SHA256 is **`54e654840966a12319f54999019fdf90c82a8712931cb63397e1d10570b5773b`**. This is the consumer's exact review fingerprint of the persisted Plan. The Runtime independently validates and binds the exact Plan when a future human Approval is recorded; no approval-binding or compiled Action digest exists yet.

| Preserved identity / gate | Verified result |
|---|---|
| Model provenance | Original REAL_LOCAL_OLLAMA `phi4-mini:latest`, genuine 13.019331 s inference; no model call or regenerated Plan this phase |
| Recommendation | REFUND, NZD 5.00, DAMAGED_ITEM, LOW uncertainty; original recommendation and arguments unchanged |
| Run | Original Run, **AwaitingApproval**, **version 4**, one exact single-step SIDE_EFFECT Plan |
| Tool / version | `paypal_partial_refund` / `1` |
| Adapter / binding revision | `paypal-sandbox-adapter` / `refund-binding-v1` |
| Target / scope | `paypal-sandbox-refunds`; original persisted UUID scope matches capability, principal and Executor |
| Incident state / policy | READY / PASS |
| Human Approval | **PENDING**, zero decisions and zero approval bindings |
| Execution Authorization | **NOT GRANTED**, zero grants |
| Action / attempts / receipts | **NONE**, all corresponding tables empty |
| Consumer financial observations | Zero; no REFUND_DISPATCH or ambiguous provider observation |

`.env` still configures **deterministic** AI mode, while this original identity requires **real**. The readiness process loaded credentials normally, then restored real mode and the documented local model settings **in memory only**. All five persisted `Settings.identity()` fields matched exactly. The default state directory was not initialized. Future continuation must use this original directory and matching real-mode composition; starting the default configuration cannot substitute for it.

Initial SQLite inspection used immutable, read-only connections with no active WAL/SHM/journal present. There were zero startup Run recovery candidates and zero Actions. Process inventory found no other Python/app predecessor; the Windows venv launcher and audit interpreter were identified as the same readiness invocation. The public `composition`/`open_runtime` then acquired the **original OS single-owner lock**, validated the stored Run/history/binding and read `run_service.get` / `gateway.list_for_run`. Only the private capability's read verification was used; possession of it did not create an execution grant.

The public startup API includes recovery hooks. Their candidate sets were empty, so no historical transition or ambiguous-effect recovery occurred. The original Run snapshot, table counts, audit history and every historical private file were identical afterwards. The four original events remain RUN_CREATED → PLAN_GENERATION_STARTED → PLAN_VALIDATED → APPROVAL_REQUIRED. Runtime readiness evidence (private local diagnostic; not published).

The repository-wide scan of persisted application identities found this sole state associated with the genuine capture; it contains zero Actions, attempts and observations. This establishes **no prior application dispatch for this intended refund**, rather than a claim about every possible external merchant action.

## Fresh genuine PayPal reads

Observed **2026-10-13 02:26:02 UTC / 15:26:02 NZDT**. Exactly one Capture GET and one Order GET were sent concurrently, using the original verified Order ID as the trusted read hint. One cold OAuth POST authenticated them. The production client used **SandboxReadOnlyTransport**, fixed `https://api-m.sandbox.paypal.com`, disabled redirects and transport retries=0. Refund methods and financial POSTs were prohibited. The Executor was not executed.

| Genuine operation | HTTP | Measured seconds |
|---|---:|---:|
| OAuth, authentication only | 200 | 1.246065 |
| Capture GET | 200 | 0.950302 |
| Order GET | 200 | 1.043463 |

The joined read path, including OAuth and response validation, took **2.293630 s**. Each value is an observed request wall time, not a per-phase socket timeout measurement. Sanitized provider evidence (private local diagnostic; not published); full provider responses are preserved in Git-ignored `.state-phase232-private/capture-get.private.json` and `order-get.private.json`.

Verified facts:

- Original Capture and Order are both **COMPLETED**, with **CAPTURE** intent, **NZD 20.00**, exactly one purchase unit and exactly one capture entry.
- Capture amount, unit amount and embedded capture amount/status agree. Capture supplementary Order ID, Order ID and embedded Capture ID match the original fixture, allowlist and incident.
- Capture payee and Order payee both match the configured original Sandbox Business merchant. The original app client fingerprint matches. The independent buyer identity matches the original authenticated response and differs from the merchant.
- Fresh `CaptureFacts` equal the original proposed incident **exactly**. The preserved real model recommendation passes the current NZD 5.00 policy, strictly below the original NZD 20.00 payment and within the configured limit.
- The genuine responses again returned `api.sandbox.paypal.com` metadata links. The qualified narrow alias validation accepted them; outgoing requests remained on the fixed trusted origin. Returned links were not followed.

**Refund balance remains PARTIAL evidence.** Order payments contain `captures` and no `refunds` field; therefore no refund is reported. Capture breakdown contains gross amount, net amount and PayPal fee, with no total-refunded or authoritative remaining-refundable-balance field. These observations support the NZD 5.00 candidate, but do not certify a complete refund ledger or prevent concurrent provider-side changes. Net proceeds/fees were not used as refundable balance. No genuine Refund GET was sent because there is no prior refund identity. Contracts: [Capture GET](https://developer.paypal.com/api/payments/v2/captures-get), [Order GET](https://developer.paypal.com/api/orders/v2/orders-get), [partial refunds](https://developer.paypal.com/api/payments/v2/captures-refund).

## Exact proposed mutation and independent pending gates

The **literal original Run ID, Capture ID, Order ID, merchant ID, incident ID, scope, Plan fingerprint and full proposed request** are in the local, Git-ignored [exact human review](../.state-phase232-private/human-review.md), with its structured companion `human-review.json`. They are presented directly to the operator for confirmation; public evidence deliberately uses matching-identity results instead of private payment identifiers. Existing private Plan files remain untouched.

The proposed financial operation is **at most one**:

```text
POST https://api-m.sandbox.paypal.com/v2/payments/captures/{original_allowlisted_capture_id}/refund
```

```json
{"amount":{"value":"5.00","currency_code":"NZD"}}
```

No automatic retry is permitted. The current Action ID, effect key and PayPal request-id are **not yet assigned**. After separately confirmed human Approval of the original Run at expected version **4**, public admission would durably assign the Action/effect identity. The original Action's **effect_key maps directly to PayPal-Request-Id** throughout that Action's life; no substitute request-id will be generated for another attempt. Provider idempotency remains endpoint/retention dependent and is not an exactly-once guarantee. [PayPal idempotency](https://developer.paypal.com/api/rest/reference/idempotency/).

Required future confirmations are distinct:

1. **Approval:** approve only the exact original immutable Plan and NZD 5.00 arguments at Run version 4.
2. **Authorization:** separately grant execution permission for the original binding/scope and the durably admitted Action. Approval or capability possession alone is insufficient.
3. **One-time execution:** explicitly permit at most one genuine Refund POST, contingent on fresh unchanged payment checks, accepting the timeout/Unknown and balance limitations. Stop on ambiguity without retry or automatic reconciliation.

No confirmation or transition above was performed on the operator's behalf. Future continuation must recheck ownership, versions, absence of prior attempts and fresh provider facts after any waiting period. The existing Executor also repeats both payment reads and all policy/equality checks inside its claimed attempt.

## Executor, deadlines and Unknown behavior

The current qualified Executor, client and Store match the Phase 2.3.1 implementation and qualified wheel sources. Binding/identity revision, normalized incident arguments, policy, effect UUID and attempt UUID are checked. Runtime commits the durable Action claim before calling the Executor. Fresh merchant, currency, amount, status, order association and refund-history changes cannot be bypassed by cached facts or the model proposal.

Expiration/cancellation is checked after local validation and fresh reads, after synchronous REFUND_DISPATCH persistence, immediately before POST, after OAuth/request preparation and at transport entry. A queued cancellation is delivered at the async dispatch checkpoint; the trusted public AttemptContext is passed through the client. Post-dispatch acknowledgment and available refund identity are persisted, then an independent Refund GET must match the ID, capture relationship, NZD 5.00 and COMPLETED status. Receipt persistence is followed by another deadline check.

Lost response, missing ID, PENDING, mismatch, expiry or cancellation cannot become Succeeded. They preserve available evidence and stop **Unknown**, without retry or automatic reconciliation. A request already sent may still complete at PayPal after local cancellation. Only matching COMPLETED Refund GET plus a durable receipt constitutes verified success. No real Refund POST/GET result or latency is claimed in this phase.

The installed gateway still enforces **five seconds for adapter execution**, clamping a caller's longer deadline. Claim is before the timer, finish after it; synchronous SQLite is cooperative and cannot be preempted. The normal client has **1.1 s per connect/read/write/pool phase**, while the safe reads used the separate preflight timeout. A 1.246 s total OAuth observation does not prove it would pass or fail those individual execution socket-phase limits. MockTransport does not enforce actual socket timeouts.

In addition to rerunning the existing budget/deadline suite, five **fully isolated synthetic** trials reused this phase's measured GET/OAuth delays. All refund delays below are **hypotheses**, with synthetic credentials/identities and separate new Mock/Runtime state. Real HTTP transports were forbidden. Consumer instrumentation delegates to the current Executor; the shared Runtime was not changed.

| Model profile | Assumed POST / Refund GET s | Gateway wall s | Durable mock Action |
|---|---|---:|---|
| Warm mid | 0.8 / 0.8 | 2.788116 | Succeeded |
| Cold mid | 0.8 / 0.8 | 4.087298 | Succeeded |
| Warm edge | 1.3 / 1.3 | 3.811105 | Succeeded |
| Cold edge | 1.3 / 1.3 | 5.065874 | Succeeded |
| Warm over budget | 2.5 / 2.0 | 5.126223 | Unknown |

The cold-edge whole-call result exceeds five seconds because claim/finish lie outside the adapter timer; it does not establish a hard end-to-end cap. The over-budget trial committed one mock effect, preserved the acknowledgment and was cancelled during Refund GET. All five had one synthetic effect, **zero late dispatch and zero additional POST** on replay or a new execute command. Fresh latency model (private local diagnostic; not published).

There is **one fresh observation per operation and one trial per chosen profile**. These are concrete examples, not latency distributions, success probabilities or an SLA. Earlier two-sample distributions and uncertainty remain documented in Phase 2.3.1. The architecture supports this controlled pilot under the unchanged Runtime, but real refund latency, socket timeout behavior and persistence contention can still produce Unknown. A guaranteed completion requirement remains NO-GO and would require separate upstream review; no deadline extension or bypass was introduced.

## Regression, integrity and stop point

- Full regression: **389 passed**, zero failures/errors, one existing Starlette/httpx deprecation warning, **229.70 s**. Regression transport fences prohibit real network calls. JUnit (private local diagnostic; not published), output (private local diagnostic; not published), checks (private local diagnostic; not published). The five fresh synthetic latency trials are additional qualification experiments, not added to the pytest count.
- Ruff lint **PASS**, repository formatting **PASS, 43 files**, `pip check` **PASS**, working/index diff checks **PASS**. No production code or test source changed this phase. A new package build was **NOT RUN**; all **13** Python files in the previously qualified wheel match current source, and source/assets remain unchanged.
- All **54** hashed Runtime distribution files match RECORD, the phase baseline and the immutable pin. All **2977** preexisting private files, including `.env`, original Plan databases/owner/capability, capture fixture and prior evidence, remain byte-for-byte unchanged. The existing Phase 2.1 synthetic deadline artifact was restored exactly after its test generated a measurement. No approval or Action was copied between states. Integrity (private local diagnostic; not published).
- Exact payment identifiers, provider bodies and capability/credential values remain in Git-ignored private storage; public additions passed a private-value scan. Git HEAD/index are unchanged and prior work is preserved. No application server, real model inference, financial mutation, commit, push or deployment was started.

**STOP before genuine Refund POST.** Readiness is complete for review. Pending human Approval, separate execution Authorization and the proposed one-time execution require the operator's explicit confirmation. The balance limitation and possibility of a completed remote refund with a terminal local Unknown must be accepted before proceeding.
