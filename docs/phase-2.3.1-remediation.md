# Phase 2.3.1 — NO-GO Remediation

Date: **2026-10-13, Pacific/Auckland**. Recommendation: **GO for one separately authorized Sandbox NZD 5.00 pilot**, subject to the exact approval/authorization and fresh-payment checks below, and stopping permanently on an ambiguous result. This is a recommendation for a controlled experiment. **Real Refund POST/GET latency remains unmeasured; a COMPLETED receipt within five seconds is not guaranteed.**

The two correctness defects are fixed. Parallel authenticated reads provide a feasible path through the immutable budget in the qualified scenarios. A slower modeled path still becomes Unknown without repeat dispatch. No shared Runtime extension is necessary for this limited pilot. A broader latency requirement needs separate review; the proposed extension is described below.

**Real PayPal API calls this phase: 0. Real Refund POST: NOT AUTHORIZED / NOT RUN, count 0.** Existing genuine read observations were reused as requested. No genuine order creation, capture, refund, Unknown retry/reconciliation, credential edit, historical-state reset, Runtime modification, commit, push or deployment occurred. Full regression also runs the existing synthetic fixture tests; their effects are isolated mocks.

## Root causes and exact changes

| Blocker | Root cause | Consumer change | Result |
|---|---|---|---|
| Refund-link alias | `verified_refund` compared one hardcoded origin while capture/order validation already admitted two exact Sandbox origins | Shared strict URL/relation validator, required capture `up`, optional matching refund `self` | PASS |
| Late dispatch | Expiry check preceded a synchronous dispatch commit; OAuth and HTTPX preparation could also consume the remaining budget or queue cancellation | Checks after synchronous work, before POST, after token handling and at transport entry | PASS |
| Five-second path | Two sequential GETs consumed approximately two seconds before POST/GET verification, with optional OAuth and persistence still inside execution | Concurrent Capture/Order GET using an already verified, persisted Order ID; retain every fresh-facts check | Feasible in modeled envelope; slower cases remain Unknown |

Production edits are confined to:

- **`src/refund_sentinel/paypal.py`:** strict `verify_response_url` / `verify_links`; refund self/up verification; `execution_stopped`, `refund_dispatch_checkpoint`, `RefundDeadlineTransport`; trusted context propagation through refund/token/request boundaries; optional trusted `expected_order_id` and joined concurrent reads; matching FakePayPal protocol for offline qualification.
- **`src/refund_sentinel/integration.py`:** expiry/cancellation checks at relevant boundaries; pass the public Runtime attempt context into the client; supply the stored verified Order ID; reuse the immutable payload digest within one execution.

`store.py`, the tool argument schema, existing binding/scope identities, dependencies and the pinned Runtime are unchanged. Two existing delayed-fake tests now forward the new trusted keyword argument. The Phase 2.3 regression expectations now require alias success and zero POST on expired dispatch; its original evidence/report was preserved.

## Strict PayPal response-link contracts

The only allowed response hosts are **`api-m.sandbox.paypal.com`** and **`api.sandbox.paypal.com`**. PayPal documents both forms in its [capture API reference](https://developer.paypal.com/api/payments/v2/captures-get) and [Orders integration resource examples](https://developer.paypal.com/api/rest/integration/orders-api/api-use-cases/advanced/); the older form also appeared in the genuine Phase 2.3 capture response. This is metadata compatibility, with fixed outbound requests on `https://api-m.sandbox.paypal.com`.

Validation requires canonical HTTPS, an exact allowed hostname/authority, absent port or explicit 443, exact resource path and provider ID, exact relation and HTTP method. It rejects credentials/userinfo, other ports, queries/fragments including empty delimiters, controls/whitespace, non-ASCII host confusables, escapes/encoded paths, backslashes, trailing hostname dots, malformed authorities and path traversal. Relevant duplicate/conflicting relations fail closed. Unused unrelated relations cannot supply an execution URL.

A refund needs exactly one valid GET `up` relationship to the expected capture. A returned `self` link must identify that exact refund. Capture `self`/`refund` relations retain GET/POST respectively. Refund amount/currency/status and expected refund ID remain independently checked. **No returned URL is followed:** resource GET/POST paths are constructed from bounded IDs and the trusted Sandbox base URL.

New [link contract tests](../tests/test_phase231_links.py): **47 cases**, including both origins, explicit 443, malicious/live/lookalike hosts, bad ports, wrong IDs/paths/methods/relations, malformed shapes and duplicate relationships. Existing negative contracts remain intact, including their established diagnostic text.

## Deadline audit and financial dispatch protection

The registered Executor uses the unchanged public `AttemptContext`. Its public `expired()` signal, cancellation event and the current task's pending cancellation are observed. Cancellation is propagated as CancelledError at the async dispatch checkpoint; expiry conservatively produces Unknown. The checkpoint yields once to deliver queued cancellation/deadline callbacks before a new financial request.

| Operation / boundary | Persistence or await | Current protection / evidence |
|---|---|---|
| Initial identity/digest validation | Local synchronous work | Initial stop check; no payment can start here |
| Incident argument/policy validation | `Store.get`, synchronous SQLite | Recheck after validation, before external reads |
| Capture/Order reads and token lock | Joined TaskGroup and OAuth awaits | Core deadline wraps the group; failure/cancellation cancels and joins siblings; recheck after reads |
| Fresh facts policy/equality checks | Local synchronous validation | No cached payment facts substitute for current responses |
| `PRECHECK_REJECTED` | Synchronous observation commit | Preserve rejection evidence; recheck before classifying an expired attempt |
| `REFUND_DISPATCH` | Synchronous observation commit | Check **after commit**, immediately before entering refund |
| Refund client input/token/request preparation | Local work, token await, HTTPX preparation | Recheck before/after token handling and at final transport entry; pending cancellation is honored |
| POST response / provider error | Network await, then synchronous evidence commit | Persist known refund ID/error; expired/cancelled attempts cannot start another payment |
| `REFUND_RESPONSE` | Synchronous observation commit | Recheck before optional independent Refund GET; known identity retained if the budget is exhausted |
| Refund GET and relationship verification | Read-only await plus local validation | Mismatch/PENDING/uncertainty cannot become success |
| `VERIFIED_REFUND` | Synchronous receipt commit | Recheck after persistence; an expired attempt remains Unknown even with a completed mock effect |
| `VERIFICATION_UNCERTAIN` | Synchronous evidence commit | Unknown only; no dispatch/retry path |
| Runtime claim/finish | Synchronous core transactions | Kept intact; no consumer access replacing durable claiming/authorization |

The attempt context is carried only in a private HTTPX extension and removed before the inner transport; it is not a header, body, model input or remote credential. Direct low-level refund calls also honor task cancellation at the financial transport boundary. The registered Executor always passes its real Runtime context. Transport retries remain zero.

This protects **initiation of a new request at the transport boundary**. It cannot recall a request already sent or prevent an already-running provider operation from completing after cancellation. That situation remains Unknown. Async cancellation cannot preempt synchronous SQLite work or enforce a hard real-time wall-clock limit; local evidence/finish can outlast the adapter deadline.

New [deadline tests](../tests/test_phase231_deadlines.py): **17 cases**, with actual SQLite writer/exclusive locks released by an isolated timer thread, commit faults, already expired calls, queued/context cancellation, OAuth/preparation expiry, acknowledgment/receipt persistence delay, lost POST response and Pending. Public caller deadlines of 0.35 s exercise boundaries without altering the Runtime's five-second maximum. Additional inherited cases exercise the actual five-second cap with a caller requesting 30 s.

All pre-dispatch stop cases have **0 POST / 0 effects**. Post-dispatch ambiguous cases have **1 effect**, terminal Unknown, preserved available evidence and **0 additional POST** after same-command replay, a new execute command, and restart. All 17 cases report zero late dispatch. Deadline evidence (private local diagnostic; not published).

## Safe read concurrency

The executor derives the hint from the incident's previously authenticated capture facts, after strict local argument/policy validation. It validates that ID, then starts the two bounded GETs concurrently under `asyncio.TaskGroup`. Both use the same OAuth lock/cache; a cold client makes one token request. All children are joined on normal completion, provider failure or cancellation.

The hint only selects the expected read resource. The fresh capture's related Order ID must equal it; the fresh order ID, matching capture entry, amount/currency/status and merchant must still agree. Fresh facts must still equal the proposed incident's facts and satisfy the refund policy. No order identity, approval or payment facts are manufactured. Read-only preflight/analysis with no hint retains its existing sequential behavior.

New [parallel-read tests](../tests/test_phase231_parallel_reads.py): **11 cases**, proving overlap/one OAuth, failure and cancellation cleanup, rejection of changed order relationship/ID, merchant, amount, currency, status or refund history before POST, and low-level cancellation protection. This is consumer-owned read concurrency inside one trusted SIDE_EFFECT Executor, not an additional Runtime tool or workflow engine.

## Complete budget measurements and uncertainty

The installed public `open_runtime` has no timeout override. The actual gateway still caps adapter execution at **5 s** and clamps a caller deadline to that cap. Claim occurs before this timer and finish after it. Consequently, a whole gateway call can exceed five seconds even when the adapter succeeded; the serialized cold-mid reference did so at 5.033158 s. This behavior was not changed or concealed.

The client still uses **1.1 s per connect/read/write/pool phase**, not a total request cap. [HTTPX timeout documentation](https://www.python-httpx.org/advanced/timeouts/) describes these separate phases. MockTransport does not enforce socket phase timers; composite-delay models and explicit timeout faults are distinguished.

Existing genuine Phase 2.3 observations, **two per operation**, reused without new PayPal calls:

| Operation | Min s | Median s | Max s |
|---|---:|---:|---:|
| OAuth | 0.850505 | 0.927809 | 1.005112 |
| Capture GET | 0.871025 | 0.923583 | 0.976141 |
| Order GET | 0.976267 | 0.978186 | 0.980105 |

No real Refund POST or Refund GET sample exists. Refund timings below are **explicit hypotheses**. The network critical-path model changes from `OAuth_if_cold + Capture_GET + Order_GET + Refund_POST + Refund_GET` to `OAuth_if_cold + max(Capture_GET, Order_GET) + Refund_POST + Refund_GET`. Local validation, observations, HTTPX overhead and core claim/finish must also be counted; this is not moving OAuth or fresh reads outside the execution deadline.

New [budget experiments](../tests/test_phase231_budget.py): **24 isolated trials**, two existing read pairs × six refund-delay profiles × serial-reference/current-parallel modes. They run the real consumer Executor/client and installed Runtime, with durable synthetic effects. Measured gateway wall times below include claim/finish. **p95 is descriptive interpolation of two samples, not a population estimate or SLA.**

| Profile | Hypothetical POST / GET s | Serial median s / state | Parallel median s | Parallel p95 s | Parallel max s / state |
|---|---|---|---:|---:|---|
| Warm mid | 0.8 / 0.8 | 3.924214 / Succeeded | 2.898647 | 2.901756 | 2.902101 / Succeeded |
| Warm edge | 1.3 / 1.3 | 4.957130 / Succeeded | 3.925256 | 3.929799 | 3.930304 / Succeeded |
| Cold mid | 0.8 / 0.8 | 4.854971 / Succeeded | 3.888275 | 3.982158 | 3.992589 / Succeeded |
| Cold edge | 1.3 / 1.3 | 5.284266 / Unknown | 4.854798 | 4.924962 | 4.932758 / Succeeded |
| Warm tail | 2.0 / 1.4 | 5.322538 / Unknown | 4.717721 | 4.720118 | 4.720384 / Succeeded |
| Warm over budget | 2.5 / 2.0 | 5.312651 / Unknown | 5.289449 | 5.300481 | 5.301707 / Unknown |

The cold-edge successful whole-call margin was only **0.067242 s** in the slowest sample. The over-budget case commits one mock effect, persists its available acknowledgment, times out during verification, and stops Unknown. These outcomes prove a feasible bounded path and a safe stop behavior; they do not estimate real refund latency/failure probability. Equal weighting of chosen scenarios is not a production distribution.

Profiled local distributions across those trials:

| Operation | Calls | Median ms | Descriptive p95 ms | Max ms |
|---|---:|---:|---:|---:|
| Core claim | 24 | 142.862 | 197.977 | 212.587 |
| Core finish | 24 | 138.595 | 191.985 | 221.238 |
| Consumer incident read | 888 | 0.853 | 1.562 | 19.811 |
| Consumer argument validation | 888 | 1.025 | 1.932 | 20.121 |
| Consumer observation commit | 64 | 6.606 | 9.096 | 25.198 |

These include observational profiling overhead. Argument validation includes its incident read, and many validations occur during core claim/finish integrity checks: **do not sum overlapping timings**. They are repeated local function calls from 24 synthetic transactions, not independent production samples. Raw per-request statuses/durations, local timers, hypotheses and terminal states are in budget-qualification.json (private local diagnostic; not published).

Safe optimizations implemented: reuse the existing in-memory OAuth cache/lock, overlap the two authenticated reads using verified identity, and avoid recomputing the same immutable executor digest. No fresh payment check, human gate, durable claim, response verification or receipt commit was removed. Caching incident/payment validation across executions, detaching post-verification work, returning success from POST acknowledgment alone or retrying Unknown would weaken the contract and were not introduced.

## Pilot conditions and remaining limitations

The recommendation is **GO only for one controlled Sandbox attempt** with these concrete prerequisites:

1. Select the existing durable candidate/identity with matching trusted configuration and one active owner. The prior genuine local-model NZD 5.00 Run remains AwaitingApproval with zero Actions; its private files were not reopened for execution or changed. The configured default Sandbox directory remains uninitialized, and `.env` remains unchanged; do not substitute an offline state or copy an approval into another scope.
2. Obtain review of the exact Plan and separate execution Authorization through the public Runtime. Neither proposing a Plan nor approval/authorization alone may dispatch. No such real transition was performed here.
3. Re-read the original capture/order before execution and require the existing merchant, NZD 20.00 COMPLETED payment, original relationship, allowed capture, unchanged facts and no reported prior refunds. The last genuine observations are the prior preflight snapshots, not a fresh assertion about provider state today. Reported facts support NZD 5.00 eligibility but are not an independently complete refund-balance ledger.
4. Use that Action's durable effect key as PayPal request-id and send at most one POST. Only independent matching COMPLETED Refund GET plus durable receipt constitutes Succeeded. Pending, missing acknowledgment, cancellation, mismatch or exhausted budget remains Unknown and stops without retry or automatic reconciliation.

Remaining limits: real POST/GET latency is unknown; the two-read sample is small; SQL contention/response processing can consume the margin; the async cap is cooperative and excludes core claim/finish; reads cannot eliminate provider-side concurrent changes; provider idempotency is endpoint/retention dependent and does not establish exactly-once remote execution. The stricter alias/method/identity validation deliberately rejects unqualified response forms. See [PayPal partial refunds](https://developer.paypal.com/api/payments/v2/captures-refund) and [idempotency](https://developer.paypal.com/api/rest/reference/idempotency/).

If a later acceptance requirement demands completion across slower profiles, **NO-GO for that requirement under the current fixed cap**. A minimal separately reviewed upstream proposal is an additive **trusted composition timeout option**, preserving default five seconds, with a small bounded ceiling, caller-deadline clamping and policy/scope review. It must retain exact approval/authorization, one durable claim/dispatch, Unknown and zero retries; test cancellation/storage faults and old-state compatibility, then qualify a new immutable release pin. A larger adapter budget would reduce modeled verification cutoffs; it still would not create a hard wall-clock guarantee for synchronous persistence/finish. No proposed API exists in the installed release, no attribute override was used, and no Runtime source was changed here.

## Full validation and preservation

- **389 passed**, one existing Starlette/httpx deprecation warning, **223.89 s**. JUnit (private local diagnostic; not published), test output (private local diagnostic; not published). This includes 87 new contracts/guard/concurrency/budget cases and updated former defect expectations.
- Ruff **PASS**; formatting **PASS, 29 files**; dependency check **PASS**. Static checks (private local diagnostic; not published).
- Standard isolated PEP 517 wheel build **PASS**; install into a new private target **PASS**. Metadata pin/Python bounds/assets/secrets exclusion passed. All 13 bundled Python source files match the final source. Installed-wheel NZD 5.00 Mock Plan → Approval → Authorization → durable claim → one effect → alias COMPLETED verification → receipt/replay **PASS**. Build evidence (private local diagnostic; not published), wheel smoke (private local diagnostic; not published). The initial non-isolated build lacked setuptools; isolated build dependencies resolved this without changing existing app/Runtime dependencies.
- The first full run had **369 passed / 2 failed** on retained diagnostic text, corrected without relaxing rejection; its JUnit/output are archived. A focused low-level cancellation assertion exposed error propagation semantics; cancellation now propagates correctly, with zero dispatch. Final focused guards/concurrency were 28/28; final full suite passed. No genuine payment was retried.
- All **54 hashed Runtime-distribution files** match RECORD and the qualified `0.1.0` pin. All **750 preexisting private files**, including `.env`, original fixture/capture history and prior genuine-model state, match the phase-start SHA256 baseline. The legacy Phase 2.1 mock deadline artifact was restored byte-for-byte after its test generated a measurement. Integrity (private local diagnostic; not published).
- Public delivery files and the wheel passed private credential/payment/buyer/Plan/capability-value checks. Git HEAD/index are unchanged; previous unrelated/Phase 2.2 work remains intact. New tests/state/evidence are isolated. No application server, real model call, payment operation, commit, push or deployment was started.

**Stop for review.** Consumer remediation and local qualification are complete. The original Sandbox Capture and genuine unapproved Plan are preserved. The next real NZD 5.00 attempt needs separate explicit authorization and the exact Runtime gates; this report does not execute or authorize it.
