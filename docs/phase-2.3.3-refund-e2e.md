# Phase 2.3.3 — Human-Gated Sandbox Refund E2E

Latest genuine recovery result: **FAILED before Refund POST**. The original Action
is now **Failed v4**, with **1 Gateway attempt and 0 Refund POSTs**. Fresh payment
preflight passed; the Gateway's repeated Order GET hit a ReadTimeout before dispatch.
No refund ID, financial Unknown or financial receipt exists. See the final recovery
outcome below and [recovery report](phase-2.3.3-recovery.md). Earlier stopped-attempt
history below is retained as historical evidence; E2E success is not claimed.

Status: **BLOCKED before Gateway execution or any network request. All three separate human confirmations were received, but the local execution runner stopped on a prerequisite AssertionError. Genuine Refund POST count: 0.** This is **not PASS** and is **not a financial Unknown**: the original Action remains Authorized with zero attempts.

Gate 1 inspection: **2026-10-13 02:52:52 UTC**. The original public Runtime composition was opened safely on `.state-phase23-private/real-model-plan`, using its matching real-mode identity in memory. No model inference, new Run, state substitution or gate transition occurred. Startup recovery candidates and preexisting Actions/financial observations were zero; the original OS owner lock was acquired and released. All 2977 historical private files and 54 hashed Runtime distribution files remained unchanged.

| Frozen candidate | Exact value |
|---|---|
| Run ID / current version / state | `d57ccc23-7849-4854-90b9-cd7352d569e6` / **5** / **Approved**; original reviewed version was 4 |
| Immutable Plan review SHA256 | `54e654840966a12319f54999019fdf90c82a8712931cb63397e1d10570b5773b` |
| Capture ID | `1YA65594665951620` |
| Merchant ID | `EZL4XDY2TTLVW` |
| Amount / environment | **NZD 5.00 / PayPal Sandbox** |
| Tool / adapter / binding | `paypal_partial_refund@1` / `paypal-sandbox-adapter` / `refund-binding-v1` |
| Target / execution scope | `paypal-sandbox-refunds` / `0b81fa19-2e6c-4a0e-960c-a34beec9b78e` |
| Runtime | `0.1.0` at `fd742b783058a53400c465b4ab59c6e80715895a` |

## Separate human confirmation records

| Gate | Confirmation | Durable transition |
|---|---|---|
| 1 — Exact Plan Approval | Separate user reply **`APPROVE`** after the exact Gate 1 question | **Approved v5**, exact binding persisted; Action admitted **Pending v1** |
| 2 — Independent Action Authorization | Separate explicit **AUTHORIZE** reply for this Action, Capture and original execution scope; explicitly **do NOT execute yet** | **Authorized v2**, independent durable grant |
| 3 — One-time genuine Refund POST permission | Separate explicit **EXECUTE ONCE** reply with the exact Action, Capture, amount, merchant and request-id; five-second/Unknown risks accepted | Recorded, but **Gateway execute NOT RUN** after local prerequisite failure |

Gate 1 question: **"Do you APPROVE this exact NZD 5.00 Sandbox refund Plan?"**

The actual separate user reply **`APPROVE`** was recorded in the private audit file before API transitions. Its record timestamp is the local recording time, not a claim about message delivery time. The initial task prompt remains distinct from that confirmation. This reply permitted Plan Approval and normal Action admission only; it was not treated as Authorization or execution permission.

Public `run_service.decide(ApprovalDecisionRequest(APPROVE, 4))` durably changed the original Run to Approved, version 5, at **2026-10-13 02:57:41.216636 UTC**. The Plan review SHA256 and exact arguments remained unchanged. Approval took **0.115511 s**. Public `gateway.admit` used a privately persisted stable admission command key, creating one Pending Action at **02:57:41.349588 UTC**, taking **0.128126 s**. Neither command was retried. Public gateway reads and independent read-only SQLite inspection confirmed the retained decision, exact Plan binding, single Action and admission receipt, with zero authorizations, attempts and provider observations.

| Durable admission / historical Gate 2 presentation before authorization | Exact value |
|---|---|
| Action ID / state / version | `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5` / **Pending** / **1** |
| Effect key / eventual PayPal-Request-Id | `5320d555-d195-4a71-97e0-d2bf8ac11fe3` |
| Approval decision ID | `acc5d7ba-f659-48aa-bb1a-f4fa7d2db61c` |
| Runtime compiled specification digest | `6440c9c99e02c50ab4328b141cfcec09bea5089d43b7e53012d8b12034e456ce` |
| Runtime canonical Plan digest | `afc62c6bfd8b6dcfc738ffbd8965cbd21ed7b4f9bf7c9eb9cfd6ada783e4fbd0` |
| Exact Approval binding | BOUND_V1 / approval-plan-v1; linked to this decision and immutable Plan |
| Authorization / execution attempt / financial receipt | **NONE / NONE / NONE** |

The Runtime canonical Plan digest includes its canonical identity revision and differs by design from the consumer review fingerprint; public admission/read validation bound the same original Plan. Tool/version, normalized NZD 5.00 arguments, capture, adapter, binding revision, target and original scope all match the Gate 1 review. Merchant is checked through the unchanged trusted configuration and incident payment facts.

Gate 2 question: **"Do you AUTHORIZE this specific Action to perform the NZD 5.00 Sandbox refund?"**

The actual second human reply was:

> AUTHORIZE
> I explicitly authorize Action `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5` to perform the planned NZD 5.00 PayPal Sandbox partial refund against Capture `1YA65594665951620`.
> This authorization applies only to this specific Action and execution scope.
> Do NOT execute the refund yet. Wait for my separate GATE 3 confirmation before sending any Refund POST.

This separate confirmation is recorded verbatim in the private audit before the API command. It permitted only independent Authorization of this existing Action/scope, and explicitly withheld financial execution. The current Plan, Run version, Action version, exact compiled specification, effect key, binding and original scope were checked before mutation. Public `gateway.authorize(ActionCommand(action_id, 1, stable_key), principal)` was called once, with no retry, and committed Authorization at **2026-10-13 03:12:52.521869 UTC**, taking **0.052437 s**. No `gateway.execute` call occurred.

| Durable Authorization / current Gate 3 candidate | Exact value |
|---|---|
| Action ID / state / version | `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5` / **Authorized** / **2** |
| Authorization ID | `b2adff84-855d-4deb-a86b-49cf23c040a3` |
| Grant subject / policy revision | `merchant-operator` / `refund-policy-v1` |
| Grant specification digest | `6440c9c99e02c50ab4328b141cfcec09bea5089d43b7e53012d8b12034e456ce` |
| Effect key / eventual PayPal-Request-Id | `5320d555-d195-4a71-97e0-d2bf8ac11fe3` |
| Run / Plan / binding / scope | Original approved Run and immutable Plan; exact original trusted identities unchanged |
| Execution attempt / provider observation / financial receipt | **NONE / NONE / NONE** |

Public gateway reads and independent read-only SQLite inspection verified one matching grant, one authorization command receipt, the unchanged compiled specification, zero Action attempts, zero execute command receipts and zero execution-claim events. The original application observation store remains empty. This is a valid pre-dispatch Authorized Action, with no previous financial dispatch or Unknown outcome. All transitions continue in the original state directory and matching real-mode composition, with the unchanged Runtime and original owner fence.

Gate 3 question: **"Do you permit exactly ONE genuine PayPal Sandbox NZD 5.00 Refund POST, accepting that Unknown means STOP with NO automatic retry?"**

The pre-confirmation explanation stated that the unchanged five-second adapter limit includes Executor validation, authenticated fresh Capture/Order reads, financial POST, independent Refund GET and receipt persistence. Core claim/finish are outside that timer; cooperative cancellation cannot recall a payment already sent. A remote PayPal refund may succeed even if its response or local verification times out. Any ambiguous outcome must preserve available evidence, remain Unknown and STOP without another POST, retry Action or automatic reconciliation. Fresh validation and Gateway execution required the separate third confirmation; its actual outcome follows.

## Third human confirmation and exact execution outcome

The third separate user reply began **EXECUTE ONCE** and explicitly permitted one genuine Sandbox partial Refund POST for:

- Action `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`.
- Capture `1YA65594665951620`, amount **NZD 5.00**, merchant `EZL4XDY2TTLVW`.
- PayPal-Request-Id `5320d555-d195-4a71-97e0-d2bf8ac11fe3`.

The reply also required fresh Capture/Order checks before execution, stopping on any failed prerequisite, accepted the five-second timeout risk, required immediate STOP for Unknown, prohibited automatic retries, duplicate POST, automatic reconciliation, additional financial operations, commit and push. The complete reply is recorded verbatim in private `gate3-confirmation.json`; recording time is not asserted to be message-delivery time. It is separate from Gate 1 APPROVE and Gate 2 AUTHORIZE. Local confirmation files are audit evidence and do not substitute for any Runtime gate.

The one-shot private execution runner was invoked once. At **2026-10-13 03:42:02.177518 UTC**, it recorded **BLOCKED / local_preconditions / AssertionError**, with **0 Gateway execute calls, 0 Refund POST transport attempts and 0 network requests**. It stopped before constructing the payment client/starting provider validation. No gateway-attempt marker or refund-transport-attempt marker was created.

**Diagnostic limitation:** the first runner captured the exception type but did not retain the failing assertion's location or predicate. A subsequent **local read-only** call of `inspect_local` passed: frozen file hashes, exact identities, installed source/pin, original Run/Action/Authorization, absence of prior attempts and ownership checks passed at that later observation. The first failure is therefore **unproven/unreproduced**, not assigned a fabricated root cause. In particular, no unsupported claim of identity drift, merchant mismatch, provider rejection or network failure is made. The later pass was not treated as permission to rerun execution: the explicit stop-on-prerequisite-failure instruction was respected.

Independent immutable/read-only SQLite inspection and file comparisons confirmed the original state after this stop:

| Actual result | Evidence |
|---|---|
| Run | Original ID, **Approved v5** |
| Action | Original ID, **Authorized v2**, original specification and effect key |
| Independent grants | **1**, the Gate 2 grant retained |
| Durable Action execution attempts | **0** |
| Execute command receipts / execution claim | **0 / 0** |
| Consumer provider observations | **0** |
| Genuine Refund POST / all PayPal requests | **0 / 0** |
| Refund ID / provider status | **NONE / NOT QUERIED** |
| Financial receipt | **NONE** |
| Five-second budget outcome | **NOT RUN**; no adapter timer was started |

Fresh genuine Capture GET, Order GET, OAuth, Refund POST and Refund GET are all **NOT RUN in Phase 2.3.3**; there is no genuine HTTP response, status or provider latency to report for this phase. The last successful payment reads remain the Phase 2.3.2 snapshot; unchanged local facts do not certify current remote payment status or refundable balance.

## Qualification and preservation

A private transport audit was prepared to allow only the fixed Sandbox OAuth/approved Capture/Order reads, one exact NZD 5.00 refund request with the durable effect key, and the resulting refund verification path. A durable exclusive POST-attempt record and a public AttemptContext deadline/cancellation recheck after that write prevent the audit itself from introducing late dispatch. It was never enabled for real financial I/O. The production Executor and shared Runtime were not modified, replaced or bypassed.

Its final isolated MockTransport qualification passed **4 tests in 1.13 s**: disabled/wrong request rejection, one-call/duplicate rejection, persistence-expiry refusal, and context propagation through the existing client/deadline transport. These use synthetic responses and no real HTTP; their simulated refund status is not provider evidence. Guard JUnit (private local diagnostic; not published). Production lint and `pip check` passed. The earlier full **389-test** regression remains the last full suite, with current production source/assets unchanged; a new full suite was not claimed or necessary for this stopped orchestration.

All **54** hashed installed Runtime files and all current production source/assets match their qualified baseline. After the blocked Gate 3 run, original gate/application databases, owner, identity, capability, Plan archive and `.env` match the exact post-Authorization hashes. The prior Gate 1/2 transitions are the only historical gate database changes; all other **2976** historical private files remain unchanged. The Capture fixture and original real-Ollama candidate were preserved. There was no new Action, financial operation, Runtime recovery of an ambiguous Action, state reset, secret change, commit, push or deployment.

Remaining blocker: the local runner's first failure cannot be qualified without a better sanitized assertion-location/predicate and process snapshot audit. Those diagnostics should be reviewed and exercised in a no-network dry check before any further execution instruction. Do not infer a PayPal problem or financial Unknown from this local failure. **STOP for review; the runner was not retried and the authorized Action was not replaced.**

Official contracts checked without financial calls: [partial refund request](https://developer.paypal.com/api/payments/v2/captures-refund), [independent Refund GET](https://developer.paypal.com/api/payments/v2/refunds-get), [idempotency constraints](https://developer.paypal.com/api/rest/reference/idempotency/). These references establish API contracts, not a genuine execution result.

## Current outcome

- Action ID: **`5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`**. Effect key/eventual PayPal request-id: **`5320d555-d195-4a71-97e0-d2bf8ac11fe3`**. Refund ID and financial receipt ID: **NONE**.
- Runtime Run is **Approved, version 5**; its one admitted Action is **Authorized, version 2**, with the matching independent grant and **no execution attempt**. Gate 3 permission was explicitly received, but the local prerequisite failure halted execution.
- Genuine Refund POST requests this phase: **0**. All PayPal payment API/OAuth requests this phase: **0**; no genuine provider HTTP result or latency exists for this phase. Official documentation browsing is not a payment API request.
- Five-second execution outcome: **NOT RUN**. The unchanged adapter deadline does not guarantee whole-call completion; a remote refund may complete while local verification becomes Unknown. Unknown requires STOP without retry or automatic reconciliation.
- Previous read evidence supports the candidate but does not certify current remote status or authoritative remaining refundable balance. Fresh Capture/Order validation was **NOT RUN** after the local failure.
- Only the original `gate.sqlite3` changed, through the explicitly confirmed public Runtime Approval, Admission and independent Authorization transitions. The other 2976 files from the historical baseline, including original application facts, Plan archive, identity, owner, capability, fixture and `.env`, remain byte-for-byte unchanged. No new Order/Capture, Live request, Runtime change, state reset, secret change, commit, push or deployment.

Exact Plan/request, all three separate human confirmations, command records and durable Gate reviews are retained in Git-ignored `.state-phase233-private/`, including `gate3-confirmation.json`, `execution-outcome.private.json` and `blocked-readonly-audit.json`. Public execution evidence (private local diagnostic; not published) records the actual stopped outcome. Local records are evidence, never substitutes for Runtime gates. This completed attempt report is **BLOCKED**, not an E2E success claim.

## Final Gate 3 recovery — actual authorized execution

**Final outcome: FAILED, confirmed before any Refund POST.** The local predecessor
false positive was repaired and qualified without modifying the pinned Runtime.
After the local-only readiness report, the user supplied a new separate reply,
exactly **`EXECUTE ONCE`**. It was recorded at **2026-10-13T07:53:43.337956+00:00** in
the new invocation's exclusive `fresh-execute-confirmation.json`; this is audit
recording time, not claimed message-delivery time. It applies to the exact original
Action, Capture, merchant, NZD 5.00 amount, original scope and effect key presented
in the preceding review. The earlier stopped permission was not reused.

The original **APPROVE** and **AUTHORIZE** records and resulting public Runtime
transitions above remain intact. No new Plan, Approval, Authorization or Action was
created. Recovery invocation: **`3881a7f5-6145-4051-a4a3-cdb8ce225d40`**. Its runner
was invoked **once** after the fresh confirmation; the old runner/outcome were not
overwritten. The original real-Ollama identity and original state directory were
used, with the unchanged public Runtime owner fence.

Fresh genuine preflight completed at **07:53:56.812674 UTC**: Capture and Order were
**COMPLETED**, NZD **20.00**, CAPTURE intent, exactly one purchase unit and one
matching Capture; merchant **EZL4XDY2TTLVW**, original independent buyer and original
incident payment facts matched. No refunds were reported; the existing NZD 5.00
policy passed. Remaining-balance uncertainty was disclosed: these fields do not
provide an authoritative remaining refundable balance or complete-ledger guarantee.

| Genuine request | HTTP result | Measured client elapsed |
|---|---|---:|
| Preflight OAuth POST | 200; credentials/token not recorded | 0.801505 s |
| Preflight Capture GET | 200, COMPLETED, NZD 20.00 | 0.930233 s |
| Preflight Order GET | 200, COMPLETED, exact association | 0.931595 s |
| Gateway Executor Capture GET | 200, COMPLETED | 1.135218 s |
| Gateway Executor Order GET | **No HTTP response obtained; ReadTimeout** | **1.136642 s** |
| Refund POST | **NOT SENT — 0 genuine requests** | NOT MEASURED |
| Refund GET | **NOT RUN** | NOT MEASURED |

The preflight Capture/Order reads ran concurrently after OAuth; joined preflight
wall time was **1.736210 s**. Client elapsed values include response-body handling
and evidence recording; transport-header timings are separately preserved. A null
HTTP status for the timed-out GET is not a fabricated provider rejection/status.

After preflight, `gateway.execute` was called **once** with the original Authorized
v2 Action. The unchanged Gateway durably claimed **Executing v3** at
**07:53:56.899185 UTC**, attempt ID **`2410420f-0410-4c97-904d-02c812b82930`**. Its
Executor repeated Capture/Order validation. The Order GET timed out under the
existing **1.1-second HTTP read-phase timeout**. `SandboxPayPal.capture` joined the
read tasks and raised **CAPTURE_READ_UNCERTAIN / no_effect=True**;
`RefundExecutor.execute` recorded **PRECHECK_REJECTED / CAPTURE_READ_UNCERTAIN** and
returned confirmed failure before `REFUND_DISPATCH` or `paypal.refund`.

The Gateway persisted **Failed v4** at **07:53:58.137008 UTC**, result code
**EXECUTION_CONFIRMED_FAILED**, with no financial receipt reference. Total Gateway
wall time was **1.331788 s**. The **five-second Runtime limit was not exhausted**;
the stricter network phase timeout stopped payment-facts validation first. No real
Refund POST, Refund GET or receipt-persistence latency was measured, so this attempt
does not qualify a successful refund within five seconds.

| Durable final result | Actual value |
|---|---|
| Run | `d57ccc23-7849-4854-90b9-cd7352d569e6`, Approved v5, immutable Plan unchanged |
| Action | `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`, **Failed v4** |
| Original effect key / intended PayPal-Request-Id | `5320d555-d195-4a71-97e0-d2bf8ac11fe3`; never sent in a refund request |
| Original independent grant | `b2adff84-855d-4deb-a86b-49cf23c040a3`, retained |
| Gateway executions / durable attempts / execute command receipts | **1 / 1 / 1** |
| Action events | ACTION_CREATED → ACTION_AUTHORIZED → EXECUTION_CLAIMED → EXECUTION_FAILED |
| Local precheck observation | `4c51c4f4-2973-4e67-be13-e737c46c7d67`; this is failure evidence, not a financial receipt |
| Refund POST / financial dispatch marker | **0 / absent** |
| Refund ID / provider refund status / financial receipt ID | **NONE / NOT QUERIED / NONE** |
| Financial Unknown | **NONE** |
| Retries / automatic reconciliation / further genuine provider calls after outcome | **0 / 0 / 0** |

Independent immutable/read-only SQLite inspection verified these final facts
without reopening Runtime or invoking another Gateway command. Of **3929** frozen
historical private files, only the authorized original gate/application databases
changed, to retain the claim/failure and precheck evidence. The other **3927**,
including previous invocation audits, Plan, identity, scope, capability, fixture and
`.env`, remain byte-for-byte unchanged. All seven frozen orchestration sources,
54 baseline Runtime files and 16 existing consumer source/assets remain unchanged.
No new Order/Capture, Live call, reset, secret change, commit or push occurred.

The preparation's full regression remains **411 passed in 252.90 s**, plus **10
runner tests in 1.26 s**. Following this real read failure, **11 isolated parallel-read
safety tests passed in 6.55 s**, covering child-task joining/cancellation and refusal
before financial dispatch. These mocks do not retry the genuine request or change
original state. Ruff, formatting and `pip check` passed; no full-suite rerun is
claimed for this unchanged-code execution.

Final sanitized execution (private local diagnostic; not published),
fresh human confirmation (private local diagnostic; not published),
sanitized genuine provider responses (private local diagnostic; not published),
durable local verification (private local diagnostic; not published),
post-execution safety tests (private local diagnostic; not published).

**STOP.** The original Action is terminal **Failed v4**, not resumable as the earlier
Authorized v2 candidate. This invocation is consumed. No repeat POST, repeated
Gateway execution, replacement Action or further provider investigation was made.
Phase 2.3.3 financial E2E is **not PASS**. The actual blocker is now a genuine
pre-dispatch Order GET timeout, not the prior local predecessor assertion.
