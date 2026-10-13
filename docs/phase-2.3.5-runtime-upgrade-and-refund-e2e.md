# Phase 2.3.5 — Runtime upgrade and Sandbox refund E2E

**PASS — genuine PayPal Sandbox NZD 5.00 partial refund independently verified
COMPLETED, with a durable financial Receipt and Runtime Action Succeeded v4.**
Exactly one genuine Refund POST and one public Gateway execution occurred after
three separate human confirmations. Refund ID: `1XN74010T5365280D`.
Financial Receipt: `e1415750-0971-4347-a88d-a3704dbb79c8`.
The Phase 2 backend is qualified for feature freeze within this tested Sandbox MVP
scope; production readiness or general latency guarantees are not claimed.

Qualification started **2026-10-13 11:44:37 UTC** (2026-10-14 in Auckland).
This task prompt was not treated as any of the three human confirmations.

## Release and trusted composition

- Installed `agentic-intent-gate==0.2.0`, pinned commit
  `7261fdd2f47d2b15fabe8faac527eeee37338eb1`.
- Genuine remote annotated `v0.2.0` tag object:
  `b193d38a4804725d44ca536a3bd9778679cc7b4c`; peeled commit matches the pin.
- Python 3.13; Runtime import verified under `.venv/Lib/site-packages`, with
  **57 RECORD-hashed files verified** and checked again after testing.
- Installed public API, pinned consumer example, handoff and adapter guide inspected.
  No shared Runtime modification or adjacent-checkout import. Its Git working tree
  remained clean. Release references: [consumer handoff](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/docs/V0.2.0-CONSUMER-HANDOFF.md),
  [adapter guide](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/docs/ADAPTER_GUIDE.md).
- `pyproject.toml` and pip snapshot updated; new `uv.lock` resolves **31 packages**.
  `.gitignore` explicitly permits this lockfile while retaining private-state ignores.

| Trusted profile | Legacy | New Sandbox pilot |
|---|---|---|
| Public adapter budget | 5 seconds | 15 seconds |
| Reviewed binding | `refund-binding-v1` | `refund-binding-v2.exec-15s` |
| Read / connect / write / pool | 2 / 1.1 / 1.1 / 1.1 s | 4 / 1.1 / 1.1 / 1.1 s |
| Additional pre-POST reserve | Existing deadline checks | At least 9 seconds remaining |
| Persisted profile | Existing legacy format | Exact reviewed profile plus binding |
| Receipt-store identity | Existing format | Exact binding, scope and profile checked on every connection |

The new scope is `0adba35b-e7b5-4e82-833b-94a3ff5db0bf`; private state is
`.state-phase235-private/real-model-plan-15s`. It has its own gate/Action ledger,
application observations database and operator capability. The public
`execution_budget_binding(base, 15)` supplies the canonical suffix. Composition
passes `execution_timeout_seconds=15` only for the reviewed Sandbox profile.
Registry, capability, verifier, policy and consumer store share the exact binding.
The profile cannot be chosen by model output, tool arguments or HTTP request bodies.
Live mode, wrong fixed base URL, unreviewed profiles and altered persisted identities
fail closed. Caller monotonic deadlines can only shorten the configured budget.

## Exact consumer changes

| Files | Change |
|---|---|
| `pyproject.toml`, `uv.lock`, `requirements.lock.txt`, `config.py` | Immutable release pin and dependency provenance |
| `profiles.py` | Frozen legacy/15-second profiles; Sandbox-only validation and exact persisted configuration |
| `integration.py` | v0.2.0 verification, fresh budget binding/scope provisioning, matching restart composition, public Runtime deadline, consumer reserve checkpoints |
| `store.py` | Separately bound extended receipt-store identity; explicit connection closing; reject missing/mismatched extended stores |
| `paypal.py` | Remaining-budget ContextVar plus reserve checks before POST, after synchronous persistence and at transport entry; wrapped-mock source labeling |
| `pilot_transport.py` | Parameterized Action/effect identity, exact Sandbox wire contract, exclusive durable one-POST reservation, post-fsync deadline check and sanitized exception classes |
| `web.py` | Read-only reporting of the actual trusted Gateway budget |
| `tests/test_workflow.py`, `tests/test_phase235_runtime.py`, `tests/phase235_worker.py` | New pin and actual installed public Gateway security, timing and separate-process tests |
| `scripts/validate_phase235_wheel.py`, `README.md`, `.gitignore` | Outside-checkout installed-wheel qualification and profile/lock documentation |

Historical `AGENTS.md` updates were supplied by the user; this implementation did
not alter them. No Runtime source was copied, forked, patched or monkeypatched.

## Payment execution path and budget

```text
Outside adapter timer: human gates → fresh external Capture/Order validation → claim
Inside adapter timer:  Capture GET || Order GET → durable dispatch evidence/check
                       → Refund POST → response evidence → independent Refund GET
                       → verified durable financial Receipt
Outside adapter timer: public Gateway finish
```

The pilot uses the **direct public Runtime Gateway**, as already used by
`Sentinel.execute`; it does not call the bundled Core HTTP routes with their
ten-second parent deadline. An actual v0.2.0 Gateway mock scenario completed in
**10.912233 seconds**, proving this path is not truncated by that parent limit.

Capture/Order reads retain all existing validations. External pilot validation
additionally checks original buyer, CAPTURE intent, single purchase unit/capture
and NZD 20.00 unit gross. Neither preflight nor internal revalidation was removed.
One AsyncClient/token cache is reused per invocation; hinted GETs use an owned,
joined TaskGroup. No detached execution or automatic retry exists.

Every HTTPX phase is capped by the public AttemptContext's remaining deadline.
Four seconds is an inactivity/read-phase ceiling, not a total request bound.
The nine-second dispatch reserve allocates ACK read 4 + verification read 4 +
receipt/margin 1 seconds. It is checked before dispatch evidence, after synchronous
persistence, after HTTP preparation/OAuth and after the exclusive pilot marker's
fsync. It is an engineering reserve, **not a guarantee**: connect/write/pool costs,
streaming bodies, provider tails and disk stalls can still exhaust the budget.

Expiry/cancellation before POST prevents financial dispatch. Ambiguous post-dispatch
responses, Pending and late/failed verification remain terminal Unknown, without
retry or automatic reconciliation. Cooperative cancellation cannot preempt blocking
Python persistence or recall a remote effect. Claim and finish are outside the
adapter timer, so fifteen seconds is not a hard wall-clock bound for the entire
Gateway call. The one-POST marker proves local reservation, not provider receipt.

## Regression and installation evidence

**Full pytest: 476 passed, 0 failed, 465.45 seconds.** This includes **40 new
Phase 2.3.5 tests** and 436 existing distinct tests. The previously reported 27
budget-review checks comprised 16 new cases plus 11 selected existing SDK cases;
they are not 27 additional distinct collected tests. The only warning is the
existing Starlette HTTPX TestClient deprecation.

Other completed checks:

- Ruff lint: PASS; formatting: **38 files**, PASS.
- `uv lock --check --offline`: PASS; exact installed dependency snapshot: PASS;
  `pip check`: PASS.
- Consumer wheel build and fixed Runtime pin in METADATA: PASS.
- Wheel installed under a fresh **D:\Ollama\Temp** directory and exercised from
  outside the repository with network connection attempts denied. Both real public
  Gateway profiles produced synthetic verified receipts; restart command replay
  produced **zero additional mock POSTs**. Consumer import came from that wheel.
- Before Gate 1, the exact new candidate resumed through public Runtime with network/model calls
  forbidden: Plan/version/profile unchanged; real OS owner fence acquired; zero
  new financial or approval records. Five candidate state-file hashes unchanged.
- **12 additional local payment-structure contract checks**, including eleven
  wrong ID/intent/units/captures/status/money/merchant/buyer/refund cases rejected.
- Original **3980 private files**, including `.env`, unchanged by SHA256. Original
  Action `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5` remains **Failed v4**, one historical
  Gateway attempt and zero genuine Refund POSTs. Its old effect key is not reused.
- Wheel contains zero private-state/credential files. Public-file scan found zero
  actual credential/operator-capability matches. Final scan is repeated after report
  creation. No commit, push or deployment.

Changed implementation paths pass `git diff --check`. The whole existing worktree
reports four user-supplied Markdown hard-break trailing spaces in `AGENTS.md`; that
instruction file was preserved. Older tests regenerate mock timing files: fresh
rerun output was retained separately, and nineteen historical mock case files were
restored from their preserved original aggregate evidence. Historical financial
evidence and reports were not replaced.

### Actual v0.2.0 public Gateway mock observations

Each row is one isolated deterministic timing sample, **not real PayPal refund
latency or a percentile distribution**. MockTransport explicitly models socket
phase expiry; it does not enforce socket timeouts itself.

| Scenario | Gateway s | Final Action | Mock POSTs |
|---|---:|---|---:|
| Warm OAuth; delayed reads/ACK/verification | 3.515878 | Succeeded | 1 |
| Cold OAuth | 4.363794 | Succeeded | 1 |
| Direct path exceeds ten seconds | 10.912233 | Succeeded | 1 |
| Read exceeds four-second limit | 4.197348 | Failed | 0 |
| Insufficient dispatch reserve | 0.306497 | Failed | 0 |
| Short caller deadline | 0.264928 | Unknown | 0 |
| Cancellation before POST | 0.370040 | Unknown | 0 |
| Sync commit crosses deadline | 15.187042 | Unknown | 0 |
| Remote mock commits, ACK lost | 0.303159 | Unknown | 1 |
| Provider Pending | 0.546170 | Unknown | 1 |
| Refund GET read expiry | 4.416478 | Unknown | 1 |
| Receipt persistence returns late | 15.547603 | Unknown | 1 |
| Wrong Capture | 0.302450 | Failed | 0 |
| Wrong merchant | 0.310522 | Failed | 0 |

Tests also cover invalid budget types/values, profile/store tampering, approval
digest/stale version, missing/wrong authorization/scope, concurrent commands,
terminal protection, repeated commands, real process restart, and exact pilot
request rejection. Duplicate/terminal replay tests make no second financial POST.
Sanitized telemetry preserves `ReadTimeout` and cancellation types before folding
provider errors. See full tests (private local diagnostic; not published),
mock samples (private local diagnostic; not published),
wheel qualification (private local diagnostic; not published) and
artifact checks (private local diagnostic; not published).

## Limited genuine read-only qualification and model

Bound enforced before transport: **at most one OAuth POST, two Capture GETs and
two original Order GETs**. There were no retries, substituted currencies,
financial POSTs or other PayPal operations. Both observation pairs independently
passed the original payment/buyer contract; the second pair supplied Plan analysis.

| Genuine operation | HTTP | Elapsed s |
|---|---:|---:|
| OAuth | 200 | 1.622894 |
| Qualification Capture GET | 200 | 1.074563 |
| Qualification Order GET | 200 | 1.214564 |
| Plan Capture GET | 200 | 0.825728 |
| Plan Order GET | 200 | 1.093677 |

First parallel-pair wall time, including cold OAuth: **2.841056 s**. One client
reused its token with three cache hits. These are sparse real observations;
actual TCP/TLS connection reuse was not independently traced and no p95/p99 is
established. Actual Refund POST/GET latency remains **NOT MEASURED**.

Capture `1YA65594665951620` and Order `3KT99923NY800615C` are COMPLETED,
gross **NZD 20.00**, intent CAPTURE, exactly one purchase unit and one matching
capture. Capture, embedded capture and unit money match. Merchant is
`EZL4XDY2TTLVW`; original independent buyer matches the preserved private reference.
The Order reports zero refunds. NZD 5.00 passes current local policy. These GETs
are **not an authoritative complete refundable-balance ledger**: concurrent or
otherwise unreported provider-side activity remains possible. Fresh checks and
provider acceptance are still required after Gate 3.

Real local Ollama `/v1/chat/completions` returned **HTTP 200**, reported
`phi4-mini:latest`, **493 prompt / 86 completion / 579 total tokens**. No fallback
or deterministic inference was used. Payment reads, model analysis and Run
creation took **12.223887 seconds**, outside the adapter execution timer. Trusted
host code compiled the validated real-model recommendation into the bounded Plan.
Unredacted provider/model responses remain private. See
sanitized read/model evidence (private local diagnostic; not published).

## Frozen candidate and human-gate records

| Item | Exact value |
|---|---|
| New Run | `397aee37-1138-4813-8a9e-da5b503a0660` — Approved v5; reviewed at AwaitingApproval v4 |
| Incident | `89a42a3b-be41-4bc5-b3ad-8d44a0596c07` |
| Plan review SHA256 | `2790e1b560ec2012d55c60e487457d4b280376cd299db40cf4ecf50f5813ac56` |
| Capture / merchant | `1YA65594665951620` / `EZL4XDY2TTLVW` |
| Proposed effect | One **NZD 5.00** PayPal Sandbox partial refund |
| Profile / binding | `paypal-sandbox-15s` / `refund-binding-v2.exec-15s` |
| Execution scope | `0adba35b-e7b5-4e82-833b-94a3ff5db0bf` |
| Approval / Action / Authorization | **RECORDED / Succeeded v4 / RECORDED** |
| New Action ID | `26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1` |
| New effect key / eventual PayPal-Request-Id | `f0e87507-1b25-4abd-be6b-4fbef82a5e4d` — derived by the public Runtime at admission |
| New Gateway attempts / genuine Refund POSTs | **1 / 1** |
| Genuine Refund ID / status / financial Receipt | `1XN74010T5365280D` / **COMPLETED** / `e1415750-0971-4347-a88d-a3704dbb79c8` |

Exact Plan:

```json
{
  "goal": "Issue one reviewed partial refund for this incident",
  "target": "paypal-sandbox-refunds",
  "steps": [
    {
      "tool_name": "paypal_partial_refund",
      "tool_version": "1",
      "arguments": {
        "amount": "5.00",
        "capture_id": "1YA65594665951620",
        "currency": "NZD",
        "incident_id": "89a42a3b-be41-4bc5-b3ad-8d44a0596c07"
      }
    }
  ],
  "risk_class": "SIDE_EFFECT"
}
```

| Separate human gate | Current outcome | Permitted subsequent transition |
|---|---|---|
| GATE 1 — APPROVE | **RECORDED** — separate user reply `APPROVE` | Approved v5; one new Action admitted Pending v1 |
| GATE 2 — AUTHORIZE | **RECORDED** — separate explicit Action-scoped user confirmation | One independent Authorization; Action Authorized v2 |
| GATE 3 — EXECUTE ONCE | **RECORDED** — separate explicit one-time user permission | Fresh preflight; one Gateway execution and one verified Sandbox Refund POST |

Gate 1 question: **Do you APPROVE this exact new Sandbox refund Plan?**

Review is frozen in private `human-review.md`/JSON and
sanitized exact candidate (private local diagnostic; not published).
Final public-API local review (private local diagnostic; not published)
is the preserved pre-Approval snapshot: one Run, zero approval/binding/Action/grant/
attempt/command-receipt/provider-observation rows, no competing owner, and zero
network/model calls. The Gate 1 outcome below supersedes its current-state counts.

## Gate 1 — Actual human Approval and Action admission

The user separately replied **`APPROVE`** to the exact Gate 1 question. The private
confirmation record retains that exact reply, the question, original reviewed v4,
Plan SHA256, amount/Capture/merchant/binding/scope and permitted transitions. Its
timestamp is local recording time, not a claim about message delivery time.
It grants Approval and admission only; it does not grant Authorization or execution.

One initial local inspection stopped with `OwnershipBlocked` before any Approval,
admission or network call. Its precise original guard subcode was not captured and
is **UNDETERMINED**; no historical cause is inferred from subsequent observations.
That audit and runner were preserved. A bounded read-only diagnostic verified the
owner fence available and only the current verified interpreter/venv launcher.
A new uniquely identified local invocation
`95e5ea04-c511-4672-8ef3-531c52630dca` independently passed the unchanged ownership
guard, all frozen source/Runtime/candidate checks and zero prior transition counts.
No assertion, owner check, Runtime lock or authorization protection was bypassed.
The earlier invocation made **zero** Approval/admission API calls; this was not a
retry of an executed financial or Runtime transition.

The installed public `run_service.decide(APPROVE, expected_version=4)` ran exactly
once and durably changed the Run to **Approved v5**, taking **0.074493 s**. Approval
binding timestamp: **2026-10-13 12:03:59.567725 UTC**, or
**2026-10-14 01:03:59.567725 Auckland**. Public `gateway.admit`, expected Run v5,
ran exactly once with a separately persisted UUIDv4 admission command key, taking
**0.083198 s**. It created one fresh **Pending v1** Action, not a replay.

| Exact admitted Action review | Value |
|---|---|
| Action ID | `26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1` |
| State / version | **Pending / 1** |
| Effect key / eventual PayPal-Request-Id | `f0e87507-1b25-4abd-be6b-4fbef82a5e4d` |
| Tool / target / adapter | `paypal_partial_refund@1` / `paypal-sandbox-refunds` / `paypal-sandbox-adapter` |
| Binding / profile / scope | `refund-binding-v2.exec-15s` / `paypal-sandbox-15s`, 15 seconds / `0adba35b-e7b5-4e82-833b-94a3ff5db0bf` |
| Capture / merchant / amount | `1YA65594665951620` / `EZL4XDY2TTLVW` / **NZD 5.00**, Sandbox only |
| Approval decision ID | `55a7ccc3-644a-408b-917f-3902554d25cc` |
| Approval binding | **BOUND_V1**, `approval-plan-v1` |
| Approval binding digest | `654496687f1df30ce3b0768e8698d4bfacc1836d528f924536799630743a33e1` |
| Runtime canonical Plan digest | `5e76bc72cafe29fcb705b97d34c4b5239fcf62c717629d8adcf7706c7d549b7a` |
| Compiled specification digest | `d77c801277f32763357d5302fda4fd7e15782ff5f82e40002d8ff9d43abd9632` |
| Compiler | `action-compiler-v3` |
| Authorization / attempts / financial Receipt | **NONE / 0 / NONE** |

Public Gateway reads and independent read-only SQLite verification confirm exactly
one Run, Approval decision, exact Approval binding, Action and admission command
receipt; **zero authorization, execution attempt or provider-observation rows**.
The approved Plan is unchanged; the specification arguments equal its exact step.
The new effect key differs from the old terminal Action's key. Application facts,
operator capability, identity configuration and all 3980 historical private files
are unchanged. No new model, Run or Plan was generated. All network operations
were denied during this local gate; actual network/model/Gateway-execution/financial-
POST counts are **zero**. The prior 476-test qualification remains applicable;
this turn made no product source change and verified the frozen source manifest.

Evidence: actual Gate 1 outcome (private local diagnostic; not published).
Original Gate 1 reviews/manifests and stopped-invocation evidence remain intact;
new state hashes and a separate private Gate 2 review were saved for the next gate.

Gate 2 question: **Do you AUTHORIZE this exact Action?**

An affirmative Authorization will grant this Action only. Execution remains blocked
until a separate GATE 3 **EXECUTE ONCE** reply. No commit, push or deployment.

## Gate 2 — Actual independent Authorization

The user separately replied **AUTHORIZE** and explicitly authorized only Action
`26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1`, the reviewed approved Plan, original scope
and trusted fifteen-second profile, for Sandbox NZD 5.00 against the exact Capture.
The same reply explicitly required **no execution, Refund POST, retry, commit or
push**, and waiting for a separate GATE 3 EXECUTE ONCE confirmation. Its full text,
scope and exact specification identity were durably recorded privately before the
Authorization API call. No previous or implied execution consent was substituted.

All frozen Gate 1 state, product source and 57 Runtime file hashes matched. The
unchanged process guard and existing OS owner lock passed. Run Approved v5, exact
Plan review digest, compiled specification, Scope, merchant, Capture, amount and
profile matched; the Action was Pending v1 with no grant, attempts, dispatch marker
or provider observations. No model/Plan/Run generation or PayPal request occurred.

The installed public `gateway.authorize(ActionCommand(Action, 1, key), principal)`
was called **exactly once**, taking **0.080060 s**, with its own persisted UUIDv4
command key. The result was not replayed. The independent grant is:

| Authorization evidence | Exact value |
|---|---|
| Authorization ID | `416b6fa2-ee46-48d8-8b93-8fcd05616ac7` |
| Authorized Action | `26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1` — **Authorized v2** |
| Trusted subject / policy revision | `merchant-operator` / `refund-policy-v1` |
| Grant timestamp | **2026-10-13 12:16:18.567246 UTC**, **2026-10-14 01:16:18.567246 Auckland** |
| Bound specification digest | `d77c801277f32763357d5302fda4fd7e15782ff5f82e40002d8ff9d43abd9632` |
| Effect key / eventual PayPal-Request-Id | `f0e87507-1b25-4abd-be6b-4fbef82a5e4d` — unchanged |
| Profile / binding / scope | 15 s / `refund-binding-v2.exec-15s` / `0adba35b-e7b5-4e82-833b-94a3ff5db0bf` — unchanged |
| Separate execution permission | **NOT GRANTED** |
| New Gateway attempts / financial POST / financial Receipt | **0 / 0 / NONE** |

Public Gateway reads and independent read-only SQLite inspection confirm one
Authorization row with the exact Action/specification/subject/policy binding. There
are two command receipts: admission accepted v1 and authorization accepted v2;
**no execute command or attempt exists**. Run, Plan, Approval binding, payment facts,
capability and execution identity remain unchanged. All 3980 historical private
files, `.env` and shared Runtime remain unchanged. No product code change or blind
retry occurred. Previous 476-test qualification is retained; this gate verified
actual public API results, persistent rows and frozen manifests without financial
dispatch. Original Gate 1/2 reviews and manifests remain preserved; a separate
Gate 3 review and post-Authorization state manifest are retained privately.

Evidence: actual independent Authorization (private local diagnostic; not published).

### Exact pending one-time financial operation

```http
POST https://api-m.sandbox.paypal.com/v2/payments/captures/1YA65594665951620/refund
PayPal-Request-Id: f0e87507-1b25-4abd-be6b-4fbef82a5e4d
Prefer: return=representation
Content-Type: application/json

{"amount":{"value":"5.00","currency_code":"NZD"}}
```

Only the Authorized v2 Action above may execute this Sandbox-only operation for
merchant `EZL4XDY2TTLVW`. **At most one genuine Refund POST** is proposed. After a
separate confirmation, fresh payment/merchant/buyer/refund-policy and owner checks
must pass before the direct public Runtime Gateway is invoked. Failed preconditions
stop before POST. This Authorization record alone grants no orchestration permission
to invoke Gateway execute.

The total Runtime adapter budget is **15 seconds**, with a four-second HTTP read
ceiling and a nine-second pre-dispatch reserve. Lost acknowledgment, provider tails
or late verification/persistence can still produce Unknown. A refund may succeed
remotely even if local verification times out. **Unknown means STOP immediately,
with no automatic retry, duplicate POST, new-Action retry or automatic reconciliation.**
No independently verified refund or financial Receipt exists yet.

Gate 3 question: **Do you permit exactly ONE genuine PayPal Sandbox NZD 5.00
Refund POST, accepting that Unknown means STOP with NO automatic retry?**
Await a separate explicit **EXECUTE ONCE** reply.

## Gate 3 — Actual permitted genuine execution

The user separately replied **EXECUTE ONCE**, explicitly permitting at most one
Sandbox NZD 5.00 Refund POST for this exact Action/Capture/request-id, conditional
on fresh checks, with Unknown STOP and no retry, replay, second POST or automatic
reconciliation. All three confirmations belong to this new Plan/Action; none was
inherited from the original Failed v4 pilot. The full third reply and exact scope
were fsync-persisted privately before provider preflight, recorded at
**2026-10-13 12:43:23.009661 UTC / 2026-10-14 01:43:23.009661 Auckland**.
These are local recording timestamps, not inferred message delivery times.

| Human gate | Separate confirmation | Durable resulting transition |
|---|---|---|
| 1 | `APPROVE` | Run Approved v5, exact Approval binding; Action Pending v1 |
| 2 | Explicit `AUTHORIZE` for Action/Capture/approved Plan/original scope/15-second profile, with **do NOT execute yet** | Independent grant `416b6fa2-ee46-48d8-8b93-8fcd05616ac7`; Action Authorized v2 |
| 3 | Explicit `EXECUTE ONCE` with the exact Action, Capture and PayPal-Request-Id, fresh-check condition and Unknown STOP | One durable claim/attempt; Action Executing v3 → Succeeded v4 |

A new execution invocation `6ca029a7-322f-450c-967c-e41b76374c0f` retained its own
runner, source hash, dry-run, command, exclusive invocation entry, transport marker,
provider evidence and outcome. Historical runners/audits were not reused or
overwritten. The pure local dry-run passed with zero network requests, zero Gateway
execution and unchanged Authorized v2 state. **Eight existing focused wire/context/
exact-request/reserve/restart-fence tests passed in 1.77 seconds**, in addition to
the earlier full **476-test** qualification; these are reruns, not eight new tests.
No product or shared Runtime source was changed for the execution.

The live invocation repeated all frozen source/Runtime/state/Plan/Action/grant/
binding/scope checks and verified no prior attempt, dispatch marker or ambiguous
state. The process guard and actual public Runtime owner lock passed. Both external
and Gateway-internal original Capture/Order pairs were freshly read and fully
validated, including gross NZD 20.00, CAPTURE intent, one unit/capture, correct
merchant, original independent buyer, relationship and no reported refunds.
Facts matched the preserved incident. Local NZD 5.00 partial-refund policy passed.
The external read alone still does not establish a complete balance ledger; the
actual provider accepted and independently completed this specific refund.

### Actual genuine provider observations

| Phase / operation | HTTP | Full SDK elapsed s |
|---|---:|---:|
| Preflight OAuth | 200 | 1.769999 |
| Preflight Capture GET | 200 | 1.041487 |
| Preflight Order GET | 200 | 1.101396 |
| Gateway Capture GET | 200 | 1.043781 |
| Gateway Order GET | 200 | 1.040767 |
| **Genuine Refund POST** | **201** | **2.148422** |
| **Independent Refund GET** | **200** | **1.392813** |

Provider POST response returned genuine Refund ID **`1XN74010T5365280D`**,
status **COMPLETED**, amount **NZD 5.00**. Independent GET returned the same ID,
COMPLETED and exact amount/currency; its validated `up` relationship identifies
Capture `1YA65594665951620`. Merchant verification uses that exact Capture's two
fresh Capture/Order merchant observations for `EZL4XDY2TTLVW`. It does not claim
that Refund GET independently exposes a merchant field when the response omits it.
Raw provider bodies remain private; only allowlisted facts, IDs and timings are
published. Requests stayed on the fixed Sandbox origin; no returned URL was followed.

Exact counts: **one OAuth POST, two Capture GETs, two Order GETs, one Refund POST,
one Refund GET; one public Gateway execute call**. No payment Order/Capture was
created. No financial retry, replay, second POST, additional financial operation or
automatic reconciliation occurred. One shared AsyncClient/token cache had five
cache hits. Actual TCP/TLS connection reuse was not independently traced.

### Fifteen-second budget outcome

External preflight wall time including cold OAuth: **2.874233 s**, outside the
adapter timer. Direct public Gateway wall time, including claim/finish:
**4.766604 s**. At Refund POST preparation the public attempt had
**13.946615 s** remaining, exceeding the nine-second reserve; at Refund GET it had
**11.791774 s**. All sampled contexts were unexpired. Durable receipt and successful
adapter result preceded Gateway finish; no timeout or Unknown occurred. Separate
claim/finish/receipt-commit elapsed times were not instrumented for this real pilot.

These are **one genuine sample**, not a p95/p99 or success guarantee. This execution
happened to complete within five seconds, which does not overturn the earlier
evidence of slower reads/ACK/verification tails. The trusted configured budget was
fifteen, HTTP read ceiling four, and reserve nine, using the original public Gateway
rather than a ten-second-parent Core HTTP route. POST/GET latencies are now genuinely
measured for this invocation; earlier model-only/NOT MEASURED statements above are
preserved pre-execution observations.

### Final durable state and Receipt

| Evidence | Exact value |
|---|---|
| Run | `397aee37-1138-4813-8a9e-da5b503a0660`, Approved v5; immutable Plan unchanged |
| Action | `26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1`, **Succeeded v4** |
| Gateway attempt | `2385f730-7acd-46a0-8dc1-39a3cc019d74` |
| PayPal-Request-Id / effect key | `f0e87507-1b25-4abd-be6b-4fbef82a5e4d` |
| Genuine Refund | `1XN74010T5365280D`, **COMPLETED, NZD 5.00** |
| Financial Receipt reference | `e1415750-0971-4347-a88d-a3704dbb79c8` |
| Financial payload digest | `08c3cdfd8156043b0029f3bd1e62de16d6709d33dd3bf8dca46c537c43adde51` |
| Receipt phase/source | `VERIFIED_REFUND` / `paypal-sandbox` |
| Receipt persisted at | **2026-10-13 12:43:30.727355 UTC / 2026-10-14 01:43:30.727355 Auckland** |
| Final Action updated at | **2026-10-13 12:43:30.760134 UTC** |

The financial Receipt binds the exact effect key, public ExecutionSpec payload
digest, Capture, Refund ID, amount/currency and independently verified COMPLETED
status. The Action's `EXECUTION_SUCCEEDED` result references that same Receipt.
SQLite contains one Action, one grant, one attempt, three command receipts
(admit/authorize/execute) and three financial observations (dispatch/response/
verified receipt), without duplicate execution or unexpected Actions.

After the invocation closed, a **new process** resumed the public Runtime for
local reads with all external requests forbidden. Public Action/Receipt reads and
independent read-only SQLite inspection confirmed the same terminal state and
financial Receipt. This was **not Gateway replay or another execute**. Five final
state-file hashes were unchanged by verification; all 3980 historical private
files, `.env`, old Failed v4 Action and shared Runtime remain unchanged.

Evidence:
genuine execution (private local diagnostic; not published),
durable Receipt verification (private local diagnostic; not published),
focused wire tests (private local diagnostic; not published).

## Phase 2 backend feature-freeze handoff

**PASS within the qualified local Sandbox MVP scope.** Real Ollama proposal →
immutable Plan → separate human Approval → admission → independent Authorization →
separate execute permission → public durable claim → exactly one Sandbox refund →
independent COMPLETED verification → durable Receipt → terminal Succeeded is now
demonstrated. Runtime v0.2.0 remains immutably pinned; legacy default five seconds
and the separately bound fifteen-second profile remain distinct. The 476-test,
lint/format/dependency/lock/wheel qualification and final artifact checks define
the baseline for Phase 3 UI work. No UI work, commit, push or deployment was started.

Keep the completed Action, effect/request key, all gate records, one-shot markers
and historical Failed evidence intact. They must not be reused for another refund.
Any later financial test requires separately authorized new work. Final secret/
private-state/Runtime-hash checks are recorded after this report update.

Remaining limits: single Sandbox observation, no production or multi-user/HA
qualification, no complete provider refund-balance ledger, unmeasured latency tails,
cooperative cancellation and cross-store crash windows, and no universal remote
exactly-once guarantee. The fifteen-second reserve is not a guarantee; future
dispatched Unknown must still STOP with no retry or automatic reconciliation.
No additional financial operation is pending or authorized by this completed pilot.
