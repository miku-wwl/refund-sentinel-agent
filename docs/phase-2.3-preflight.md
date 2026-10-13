# Phase 2.3 — Sandbox NZD 5.00 Refund Preflight

Date: **2026-10-13, Pacific/Auckland**. Recommendation: **NO-GO for a genuine refund through the current Executor.** Safe preflight work is complete. Genuine PayPal reads and genuine local Ollama planning passed; isolated tests demonstrate the current deadline, durable Unknown behavior and two consumer defects that must be addressed before payment execution.

**Real Refund POST: NOT AUTHORIZED / NOT RUN, count 0.** No order creation, capture, refund retry, existing-state reset, credential edit, shared Runtime modification, commit, push or deployment occurred. OAuth token POSTs authenticate read-only clients and do not change payments. Mock refund effects below are synthetic SQLite records, never PayPal transactions.

## Genuine Capture and Order verification

The original fixture Capture ID, the sole private `.env` allowlist entry and the captured order identity matched. Both read-only passes used the existing `SandboxPayPal.capture` implementation behind the restricted read-only transport. Full provider bodies and identifiers remain in the new Git-ignored `.state-phase23-private/` directory. Public evidence: [readonly-real.json](../evidence/phase-2.3/readonly-real.json) and [real-model-plan.json](../evidence/phase-2.3/real-model-plan.json).

| Genuine operation | HTTP | Measured seconds | Result |
|---|---:|---:|---|
| Initial OAuth | 200 | 1.005112 | Valid Sandbox credentials |
| Initial Capture GET | 200 | 0.976141 | COMPLETED, NZD 20.00, correct merchant and related order |
| Initial Order GET | 200 | 0.976267 | COMPLETED, CAPTURE intent, one purchase unit, exactly the original capture |
| OAuth for isolated real-model analysis | 200 | 0.850505 | Authentication only |
| Capture GET for real-model analysis | 200 | 0.871025 | Same eligible captured payment |
| Order GET for real-model analysis | 200 | 0.980105 | Same associated merchant/order facts |

Capture amount, purchase-unit amount and the order's capture entry all match NZD 20.00. Both capture payee and purchase-unit payee match the configured Sandbox Business merchant. No duplicate capture or reported refund entry was present. The original fixture remains VERIFIED; current capture/order statuses are COMPLETED.

**Refundability: policy eligibility PASS; independently certified refundable balance PARTIAL.** The observed COMPLETED capture has gross NZD 20.00 and zero reported refunds; NZD 5.00 is positive, below that amount and within the configured limit. These responses do not provide an authoritative `refundable_balance` field or a guarantee that the order embeds a complete refund ledger. Seller net proceeds/fees are not substituted for refundable balance. Thus the observed payment supports the candidate, but an independently guaranteed available balance is not claimed. No genuine Refund GET was possible: there is no existing refund ID and no refund was created.

Official contracts checked: [Capture GET](https://developer.paypal.com/api/payments/v2/captures-get), [Order GET](https://developer.paypal.com/api/orders/v2/orders-get), [partial refund POST](https://developer.paypal.com/api/payments/v2/captures-refund), [Refund GET](https://developer.paypal.com/api/payments/v2/refunds-get), and [PayPal idempotency](https://developer.paypal.com/api/rest/reference/idempotency/). The documented partial-refund request includes an amount object. Provider idempotency has endpoint/retention constraints; it does not establish exactly-once remote delivery.

## Complete Executor request and persistence path

Audited sources: `src/refund_sentinel/integration.py`, `paypal.py`, `service.py`, `store.py`, `models.py`, and the installed Runtime gateway and SQLite Action repository. Installed public signatures and the core's `examples/consumer/app.py` were inspected. The qualified distribution is **0.1.0**, pinned to **fd742b783058a53400c465b4ab59c6e80715895a**; no internal override or core patch was made.

1. **Before dispatch:** exact persisted Plan approval, Action admission and independent execution authorization are required. Runtime synchronously commits the Action claim/attempt before invoking the explicitly registered single SIDE_EFFECT Executor. Receipt replay returns without invoking it again.
2. **Executor validation:** exact tool/version/adapter/binding/target/scope, identity revision and UUID effect/attempt identities must match. Strict arguments must equal the stored incident arguments. Stored payment facts and recommendation must pass the narrow policy.
3. **Capture GET → Order GET:** validate the allowlisted capture, provider amount/currency/status, related order, unique matching capture entry and merchant. Reapply policy and require fresh facts to equal the proposed incident's facts. Changed facts or any reported refund block the narrow policy. A cold/expired OAuth token adds a token POST; a warm client reuses its token.
4. **Synchronous `REFUND_DISPATCH` observation:** persist the capture, canonical amount/currency, digest and request identity. This is evidence, not authorization. The current expiry check is immediately **before** this write.
5. **Refund POST:** fixed Sandbox capture-refund path; explicit body `{"amount":{"value":"5.00","currency_code":"NZD"}}`; `PayPal-Request-Id` is the Runtime's durable `effect_key`; `Prefer: return=representation`. The client has no automatic request retry and never sends an empty full-refund body. Definitive provider rejection may be Failed; lost acknowledgment, duplicate/in-progress ambiguity or uncertain transport remains Unknown.
6. **Acknowledgment persistence:** validate the real refund ID and persist `REFUND_RESPONSE` before the extra GET. Missing/malformed acknowledgment cannot establish success.
7. **Refund GET → verification → receipt:** require exact expected refund ID, Decimal amount/currency and a GET `up` relationship to the original capture. Merchant association is inherited from the freshly verified capture/order chain; Refund GET is not claimed to independently expose a merchant. Persist `VERIFIED_REFUND`, then check deadline and COMPLETED status. Pending, mismatch or uncertainty remains Unknown; only verified COMPLETED with a durable receipt can become Succeeded.
8. **Runtime finish:** synchronously commit the terminal Action/receipt after adapter execution. No database transaction is held across the network awaits. A process interruption or ambiguous result cannot authorize another POST; read-only evidence does not silently convert a terminal Unknown to Succeeded or make it executable again.

Normal HTTPX timeout is **1.1 seconds per connect/read/write/pool phase**, not a 1.1-second total request cap. Preflight uses the separate read-only timeout. There are four sequential resource requests inside execution, or five with OAuth. Genuine reads near one second do not measure Refund POST/GET latency or demonstrate that this whole path fits five seconds. Model inference happens before execution and does not consume that adapter budget.

Consumer SQLite operations are synchronous with a two-second busy timeout. The Runtime uses synchronous FULL/WAL transactions and a 250 ms SQLite busy timeout. Its five-second async deadline begins **after claim** and ends **before finish**: it is not a five-second cap on the whole gateway wall time, and it cannot preempt synchronous Python/SQLite work.

## Isolated HTTP Mock qualification

Added [test_phase23_preflight.py](../tests/test_phase23_preflight.py). Tests run the real consumer client/Executor and the unchanged installed Runtime, with HTTPX MockTransport, synthetic credentials/IDs and separate temporary provider/application/gate databases. The existing regression transport fence forbids real HTTP transports. Synthetic provider effects commit before acknowledgment, allowing loss/cancellation to be verified against durable effects instead of printed success.

The only instrumentation is consumer subclasses that delegate to the existing implementation and observational `sys.setprofile` timings of claim/finish. Core methods/registry/deadline are not replaced. MockTransport does not enforce real socket timeout phases: delays model composite request latency, while explicit ReadTimeout faults model lost responses. These tests genuinely exercise the Runtime's real five-second cancellation.

Results from the final full regression: http-mock-qualification.json (private local diagnostic; not published).

| Synthetic scenario | Durable Action | Gateway seconds | Persisted effect / behavior |
|---|---|---:|---|
| Verified COMPLETED, warm token | Succeeded | 0.340067 | One COMPLETED effect and verified receipt |
| Verified COMPLETED, cold OAuth | Succeeded | 0.333573 | Same contract including token refresh |
| Effect completed; POST response lost | Unknown | 0.301971 | One COMPLETED effect; no fabricated refund ID |
| Provider PENDING | Unknown | 0.389522 | One PENDING effect; never Succeeded |
| Success acknowledgment missing refund ID | Unknown | 0.336941 | One COMPLETED effect; no verification identity |
| Refund GET timeout | Unknown | 0.297010 | Known refund ID preserved; no success claim |
| Refund associated with another capture | Unknown | 0.380315 | Association mismatch rejected |
| Exact capture, legacy Sandbox `up` origin | Unknown | 0.353908 | Current verifier rejects the alternative Sandbox origin |
| Four requests at 1.35 s composite latency | Unknown | 5.220749 | POST acknowledged; deadline cancels Refund GET |
| Cold OAuth plus requests at 1.1 s composite latency | Unknown | 5.186159 | POST acknowledged; deadline cancels Refund GET |
| Effect commits; POST acknowledgment waits 10 s | Unknown | 5.191724 | Effect persisted once before five-second cancellation |
| 1.8 s capture/order reads plus 1.6 s dispatch write wait | Unknown | 5.478715 | **Mock POST began after the actual context deadline** |

Every scenario persisted exactly **one** mock effect/POST. Replay of the same command, a new execute command after terminal completion and reopening the same persistent identity produced no second POST. Every scenario also proved: generating Plan, approving it, admitting it and authorizing it separately do not dispatch a payment; execution before Authorization is rejected. All 12 behavior assertions passed. This characterizes current behavior and defects; it is **not** a readiness PASS for genuine refunds.

Every execution supplied a caller deadline of 30 seconds. The actual Runtime limit remained five seconds. The 5.19–5.22 s gateway times include synchronous claim/finish outside that adapter deadline; the longer caller deadline did not extend it.

Persistence measurements: persistence-timing.json (private local diagnostic; not published). Ordinary individual consumer observation commits were 3.955–77.589 ms, median 5.575 ms. Runtime claim measured 86.799–126.794 ms, median 91.658 ms; finish measured 87.257–154.152 ms, median 94.826 ms. These include profiling/validation overhead and local test workload; they are not production latency promises. The synchronous-delay case modeled a 1.6 s wait below the consumer's two-second busy timeout. Its mock effect committed at gateway elapsed 5.371906 s and the captured actual `AttemptContext.deadline` had already expired when the mock POST handler started.

## Genuine local model Plan and independent gates

**PASS — genuine local inference, no deterministic fallback.** Read-only Ollama status showed version 0.35.1, loaded `phi4-mini:latest`, `size_vram=0`, corroborated 100% CPU and Forever residency. The real OpenAI-compatible `/v1/chat/completions` request took **13.019331 s** and returned a strict validated recommendation:

```json
{
  "recommendation": "REFUND",
  "requested_amount": "5.00",
  "currency": "NZD",
  "reason_code": "DAMAGED_ITEM",
  "uncertainty": "LOW"
}
```

The synthetic damaged-item message and minimal status/amount/currency facts were sent locally. Capture/merchant identifiers, credentials, capability tokens and tool bindings were not sent to the model. Host validation then compiled the trusted single-step `paypal_partial_refund`, version `1`, target `paypal-sandbox-refunds`, risk `SIDE_EFFECT` Plan for the actual allowlisted capture. Its complete identity and Plan are privately persisted in the new isolated preflight state.

That actual Run is **AwaitingApproval**, policy PASS, **zero Actions**, no Approval and no execution Authorization. No real gate-transition or execute command was issued. Read-only transport also forbids payment mutation. The unchanged `.env` still says deterministic; the genuine inference used explicit in-memory real-mode settings for this isolated state. Its evidence cannot be mistaken for the `.env` default mode. Official interface references: [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

## NO-GO reasons and smallest repair proposal

**1. Consumer refund-link compatibility.** Real Capture GET returned `api.sandbox.paypal.com` self/refund links. Capture/order validation already admits this exact Sandbox response-metadata alias alongside `api-m.sandbox.paypal.com`. `verified_refund`, however, accepts only exact `api-m.sandbox.paypal.com` for `up`. The isolated refund-GET example with the other exact Sandbox origin becomes Unknown even though its ID, capture, NZD 5.00 and COMPLETED status match. This is a demonstrated validator behavior and an inference about a possible future refund response, **not** a fabricated genuine Refund GET.

Smallest repair: reuse the existing bounded Sandbox metadata-origin policy for the refund relationship, preserving exact path, capture identity, GET method, amount/currency and refund ID. Keep dispatch on `api-m.sandbox.paypal.com`; do not follow returned links. Add positive alias tests and negative live/lookalike-host, userinfo/query/fragment/port, wrong-method and wrong-capture tests.

**2. Expired dispatch after synchronous persistence.** The current Executor checks `context.expired()` before writing `REFUND_DISPATCH`, but not after it. A legal synchronous wait can consume the remaining budget. The isolated test observed a POST handler starting after the actual deadline; async cancellation alone cannot preempt that wait. The terminal Unknown result is correctly conservative, but does not prevent this late dispatch.

Smallest repair: check the context again immediately after the dispatch observation and at the final payment-dispatch boundary; if expired, stop without sending POST and retain conservative durable evidence. Define a minimum remaining dispatch/verification budget and qualify token refresh, blocking storage and cancellation at each boundary. Do not skip fresh payment reads, approval, independent authorization, durable claim or independent Refund GET to fit the budget. Re-run these scenarios with explicit assertions that no POST can begin after expiry.

**3. Deadline and execution-state qualification remain incomplete.** Four/five sequential calls can consume the hard limit; current real evidence does not establish Refund POST/GET latency. The configured Sandbox application state directory does not yet exist; the older four application identities are offline configurations and cannot be reused for this payment. Read-only Windows process inspection found zero identifiable Sentinel/uvicorn servers and zero uninspectable Python processes; no application server was started. The isolated genuine-model Plan has its own durable scope and is not an approved/authorized production Action.

Consumer fixes above do **not** require changing or bypassing the shared Runtime. After them, qualify the complete path within the unchanged five-second budget, preserving Unknown/no-retry semantics. If product requirements still demand a longer verification budget, request a separately reviewed upstream public-API extension and requalify a new immutable release pin; passing a longer caller deadline cannot accomplish that. No such extension, timeout override, detached work or direct refund bypass was implemented here.

Before a later payment attempt, explicitly select a durable Sandbox execution identity and matching trusted real-mode settings, verify a single owner, preserve the exact Plan/scope, obtain its human approval and separate execution authorization, then repeat fresh payment checks. Never copy a Plan to another scope and reuse an old approval or regenerate an Unknown Action to retry it.

## Regression, integrity and stop point

- **302 passed**, one existing Starlette/httpx deprecation warning, **75.25 s**; JUnit (private local diagnostic; not published), test output (private local diagnostic; not published). This includes the previous 290 cases plus 12 isolated HTTP Mock cases.
- Ruff lint **PASS**; formatting **PASS, 25 files**; `pip check` **PASS**. Python 3.13 and the actual installed immutable Runtime pin passed the existing qualification guard. No dependency upgrade was performed.
- The first new-test harness run failed on an empty tuple/list assertion before dispatch; the assertion was corrected, then 11 focused cases passed, and the final expanded 12-case set passed in full regression. Initial/focused JUnit artifacts are retained. No genuine payment or Unknown operation was retried.
- All **54 hashed installed Runtime-distribution files** match RECORD. All **53 preexisting private files, including `.env` and fixture/application history**, match their preflight SHA256 baseline. The existing Phase 2.1 deadline evidence was restored byte-for-byte after its legacy regression test wrote a fresh mock measurement. New model/test state is isolated; no existing application state was opened for execution or reset.
- Private credential/payment/buyer/Plan/capability values were scanned against public deliverables; no private-value leak was found. Git HEAD and index are unchanged. Scope contains only new Phase 2.3 tests/evidence/report; previous Phase 2.2 work remains intact.

Additional evidence: state-safety.json (private local diagnostic; not published), process-status.json (private local diagnostic; not published), checks.json (private local diagnostic; not published), integrity.json (private local diagnostic; not published). **Stop here.** The original payment remains captured; the real candidate Plan remains unapproved and unauthorized. Genuine NZD 5.00 Refund POST, genuine refund verification and any retry are NOT RUN. A later authorization must be separate, and current NO-GO blockers should be resolved and requalified first.
