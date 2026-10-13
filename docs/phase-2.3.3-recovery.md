# Phase 2.3.3 — Final Gate 3 recovery readiness

**Subsequent execution outcome: FAILED before Refund POST.** After the new explicit
`EXECUTE ONCE` reply, one genuine Gateway execution changed the original Action to
**Failed v4** on a repeated Order GET ReadTimeout. Genuine Refund POST count is **0**;
no refund ID or financial receipt exists. No retry was made. See the
[final genuine outcome](phase-2.3.3-refund-e2e.md#final-gate-3-recovery--actual-authorized-execution).
The readiness snapshot below is retained as the earlier pre-confirmation evidence.

**Local readiness: PASS. Financial execution: NOT RUN. Awaiting one fresh explicit
`EXECUTE ONCE` reply.** This task prompt and the historical stopped permission were
not used as execution permission. The original failure's exact historical predicate
remains UNDETERMINED; the reproduced unrelated-process false positive is fixed in
the new execution path.

## Scoped repair and qualification

Added `src/refund_sentinel/execution_guard.py`. The new runner replaces the broad
"every other Python process is a predecessor" assertion with two consistent local
CIM snapshots, verified interpreter executable paths, process IDs, parent linkage,
creation metadata and parsed Windows command lines. A complete literal
`import time; time.sleep(...)` program is recognized as unrelated. This is an AST
match of the entire program, not a substring exemption. A verified venv launcher
must be the current interpreter's parent with the same parsed arguments.

Commands referring to Sentinel or the original repository/state are competing
processes. Other opaque programs, inaccessible identities, inconsistent snapshots
and unknown executables fail closed. No claim is made that arbitrary Python code
can be proven harmless from its command line. Diagnostics expose classifications,
PIDs and command digests, never raw command lines or credentials.

The guard additionally probes the existing `gate.sqlite3.owner` one-byte OS lock
without creating or writing it. An unavailable/unverifiable lock blocks. This
released probe grants no ownership: unchanged public `composition/open_runtime`
still acquires and holds the real Runtime fence over all actual state reads and
future execution. The owner marker is not treated as a PID file. No shared Runtime
source, approval, authorization, claiming or financial dispatch code was changed.

The old runner and all its audits are preserved. A separate Git-ignored runner at
`.state-phase233-recovery-private/recovery_runner.py` uses invocation
**`3881a7f5-6145-4051-a4a3-cdb8ce225d40`** and its own exclusively created audit files.
The original Runtime directory is used directly; no database, Approval, Action or
capability was copied or provisioned. Its execution entry requires a fresh reply
bound to this invocation and exact operation; old permission records cannot enter
it. An exclusive entry marker prevents reentry. All **37** original financial/
Runtime assertions in the old execution body and the frozen local identity checks
are retained; the two process assumptions are replaced with the qualified guard.
Seven source files are frozen by hash for this invocation.

Validation:

- Full offline regression: **411 passed in 252.90 s**, including **22** new guard
  tests. Real unrelated sleep processes pass. A separate synthetic public Runtime
  owner is detected both through process identity and through its held OS lock;
  graceful owner exit releases the lock. Tests also cover missing identity,
  opaque/malicious inline code, wrong launcher, duplicate PIDs, changing inventory,
  unknown executables and absent lock markers. No genuine payment API was used.
- Private runner qualification: **10 passed in 1.26 s**. Missing/wrong/historical
  permission and consumed invocation stop before financial entry; AST checks prove
  preservation of the original financial assertions and absence of mutation calls
  from the local dry-run.
- Ruff lint, formatting (**32 files**) and `pip check`: **PASS**. Installed Runtime
  resolves to **0.1.0 / fd742b783058a53400c465b4ab59c6e80715895a**; all **54** baseline
  Runtime hashes and **16** existing consumer source/assets remain unchanged.

Full tests (private local diagnostic; not published),
runner tests (private local diagnostic; not published).

## Actual strictly local dry-run

At **2026-10-13 07:37:19.241261 UTC**, the new invocation completed in **6.473118 s**,
including local CIM inspection and supported Runtime startup/read verification.
This is preparation time, **not** a measurement of the five-second financial
adapter execution or real Refund POST latency.

| Verified original candidate | Result |
|---|---|
| Run | `d57ccc23-7849-4854-90b9-cd7352d569e6`, Approved v5 |
| Plan review SHA256 | `54e654840966a12319f54999019fdf90c82a8712931cb63397e1d10570b5773b` |
| Action | `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`, Authorized v2 |
| Independent Authorization | Original grant `b2adff84-855d-4deb-a86b-49cf23c040a3`, exact match |
| Effect key / PayPal-Request-Id | `5320d555-d195-4a71-97e0-d2bf8ac11fe3` |
| Capture / merchant | `1YA65594665951620` / `EZL4XDY2TTLVW` |
| Proposed operation | NZD 5.00 partial refund, PayPal Sandbox only |
| Execution scope | `0b81fa19-2e6c-4a0e-960c-a34beec9b78e` |
| Tool / adapter / binding | paypal_partial_refund@1 / paypal-sandbox-adapter / refund-binding-v1 |
| Competing owner | None at observation; original public owner fence acquired/released |
| Startup recovery candidates / financial Unknown | 0 / none |
| Gateway attempts / execute receipts / provider observations | 0 / 0 / 0 |
| All genuine PayPal requests / Refund POSTs | 0 / 0 |
| New Plan, Approval, Authorization, Action or Capture | None |
| Historical private files | **3929 unchanged**, including original financial databases, old invocation audits, fixture, capability and `.env` |

Original real-Ollama identity is restored only in memory, matching the existing
identity file. Default deterministic-mode composition is not substituted. The
immutable Plan, compiled spec, trusted binding, principal scope, independent grant,
policy arguments and original incident facts match through supported public reads.
No Gateway execute or model inference occurred.

Dry-run evidence (private local diagnostic; not published),
sanitized ownership evidence (private local diagnostic; not published),
preservation evidence (private local diagnostic; not published).

## Exact pending operation and stop point

Only after the fresh human confirmation, recheck local predicates and genuine
Capture/Order facts for the original NZD 20.00 COMPLETED payment. Any failed
prerequisite stops before financial POST. The existing public Runtime Gateway will
execute this existing Authorized v2 Action once; its unchanged Executor repeats
payment validation and uses the original durable effect key as PayPal-Request-Id:

`POST https://api-m.sandbox.paypal.com/v2/payments/captures/1YA65594665951620/refund`

Body: `{"amount":{"value":"5.00","currency_code":"NZD"}}`.

At most **one** genuine Refund POST; no new Action, retry or additional financial
operation. The transport audit retains its deadline/cancellation recheck after
synchronous persistence. Independent Refund GET and durable receipt verification
are required to claim success. Unknown means preserve evidence and STOP without
another provider request, automatic reconciliation or retry.

Fresh remote eligibility is **NOT QUERIED** in this local-only preparation. Prior
reads do not establish today's refundable balance; the provider lacks an
authoritative remaining-balance field/complete-ledger guarantee in the checked
response path. Fresh reads and policy validation remain mandatory. The unchanged
five-second Runtime adapter budget can expire after PayPal has succeeded, leaving
an Unknown local outcome. The probe and preparation do not guarantee remote
latency, exactly-once delivery or completed receipt verification.

**STOP pending fresh EXECUTE ONCE.** No permission file, execution-entry marker,
Gateway-attempt marker or POST marker exists in this invocation. No commit or push.
