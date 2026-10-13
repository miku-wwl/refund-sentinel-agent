# Phase 2.3.3 — BLOCKED Root Cause Diagnosis

Date: **2026-10-13, Pacific/Auckland**. **The exact historical failing predicate remains UNDETERMINED.** Evidence places the failure in `inspect_local` before PayPal client initialization and strongly narrows it to the final process-inventory checks: original lines **119 or 121**. A concrete false-positive at line 121 is reproducible, but the original process snapshot was not saved; reproduction is not proof of which predicate failed at 03:42 UTC.

**Original Runtime state is resumable:** a supported public-API read validation on the original state succeeded, retaining **Approved Run v5 → Authorized Action v2**, exact Plan/binding/scope/effect key and original grant, with no previous attempt or financial Unknown. **The old one-shot runner is not ready to be directly rerun.** Its audit files already exist, and renewed execution needs a separately permitted, reviewed invocation that preserves those files. No financial execution occurred during diagnosis.

## Original runner and failure boundary

Original file: `.state-phase233-private/execute-once.py`, function **`inspect_local(review)`**, originally lines 61–122. The pre-change source is preserved as `.state-phase233-diagnosis-private/execute-once.original.py`, SHA256 **`11f5c05080f77bef6f438e337994c67023d741291ca4a52c7fb27c25cbe86d58`**. Only source was archived; no gate database, Approval or Action was copied to another state directory.

Execution order in that original source:

1. `main` reads Gate 3 review and exclusively records the actual human confirmation.
2. It creates an in-memory BLOCKED outcome and calls `inspect_local` at original line 149.
3. `inspect_local` checks frozen IDs/state/version/arguments/hashes, absence of execution markers, matching real-mode configuration, installed pin/source, historical files, immutable/read-only gate/application data and original fixture/client fingerprint.
4. It runs a local PowerShell process inventory, parses JSON, identifies the current interpreter and its Windows venv launcher, then performs the final two assertions.
5. Only after `inspect_local` returns does `main` assign `outcome['runtime_pin']`, construct the transport and PayPal client, enter public Runtime composition, perform fresh provider reads and eventually invoke Gateway execute.

The original [BLOCKED report](phase-2.3.3-refund-e2e.md) and private `execution-outcome.private.json` contain **AssertionError / local_preconditions**, timestamp **2026-10-13 03:42:02.177518 UTC**, and zero Gateway/POST counts. They contain **no runtime_pin, transport evidence or client telemetry**. The exception handler recorded the type and an optional `.code`, but discarded Python traceback, assertion message and locals. `AssertionError` has no `.code`, so that field is null.

The original Codex session output at record line **2678**, timestamp **03:42:06.699 UTC**, independently retains the same limited outcome. It contains no Python traceback, predecessor assertion message or runtime pin. Later session records include source/documentation, not a recovered original traceback. Sanitized session-log summary (private local diagnostic; not published).

## Historical evidence and remaining candidates

Windows **Windows PowerShell** events retain the exact original inventory command, including `Get-CimInstance Win32_Process`, the refund-sentinel/Python filter and selected process fields:

| Event | Record ID | PowerShell PID | UTC |
|---|---:|---:|---|
| Engine start, ID 400 | 292012 | 34452 | 03:42:00.0452074 |
| Engine stop, ID 403 | 292013 | 34452 | 03:42:01.9923602 |

These match the original attempt interval and source command. They support that inspection reached the final process inventory, after the earlier identity/version/hash/SQLite checks. They do **not** retain its Win32_Process result, the Python current/parent PID or the failing predicate. Security process-creation logging was unavailable to this session (`LogInfoUnavailable`); Sysmon was not present (`NoMatchingLogsFound`). No privilege escalation or guessed historical PID was used. Windows-event summary (private local diagnostic; not published).

The remaining original assertions are:

```python
# Original line 119
assert len(current) == 1

# Original line 121
assert all(p in current or p in launchers for p in processes), "POSSIBLE_ACTIVE_PREDECESSOR"
```

The first requires the current interpreter to appear exactly once. The second rejects every matched Python/uvicorn/refund-sentinel process except this interpreter and a parent with an exactly equal command line. Possible explanations include an unrelated interpreter, a launcher command-line mismatch/unavailable field, or a process inventory not identifying the current interpreter. **None is established as the exact original circumstance.**

| Investigated cause | Evidence / conclusion |
|---|---|
| Wrong expected versions | Original precondition correctly expects Run **Approved v5** and Action **Authorized v2**; current database and public Runtime agree |
| Wrong state path or deterministic replacement | Original directory, real-mode persisted identity, Plan and binding match; no default state was substituted |
| Persistent hash/configuration/fixture drift | Post-Authorization hashes match, source/pin match and original fixture/allowlist identities match; earlier checks precede the logged inventory |
| Shared Runtime owner-lock failure | Its OS lock is acquired after client initialization; that boundary was not reached in the original failure. It raises a typed ActionError rather than this bare AssertionError. Current public owner-fence acquisition succeeds |
| SQLite sidecars or table-state failure | Those assertions occur before process inventory; current immutable reads pass, with zero attempts/observations and no Executing/Unknown state |
| Process-inventory assumptions | Both final predicates can block before client initialization. Line 121 is directly reproduced with an unrelated interpreter; original snapshot is missing |

Historical classification: **UNDETERMINED at individual-predicate/process level**, with the process-inventory stage as the strongest evidenced failure family. The original state is not labeled financially Unknown and no PayPal rejection/timeout is invented.

## Strictly local reproduction

The diagnostic harness imports the runner without executing `main`, blocks its consumer execution/client/composition entry points, denies Python socket connection/address resolution and calls only local `inspect_local`. SQLite uses immutable, read-only connections. An instrumented copy evaluates each original predicate exactly once, then preserves the original assertion and its failure behavior. It records booleans and source positions, never credentials or raw command lines.

| Controlled case | Result | Exact evidence |
|---|---|---|
| Original function, ordinary file invocation | PASS | No failed predicate |
| All original assertions, instrumented | PASS | **33 evaluations**, including repeated `db_read` checks |
| Original function with controlled unrelated Python | BLOCKED | Sanitized real traceback: **execute-once.py:121**, `inspect_local` |
| Same case, instrumented | BLOCKED | `all(p in current or p in launchers for p in processes)` = **False**; all preceding predicates passed |
| Original function after worker exits | PASS | State hashes unchanged |

The controlled worker only imported `time` and slept, opened no gate/application database and held no Runtime owner lock. It was started hidden and stopped using its own process handle. Its rejection demonstrates that the broad inventory rule can block an otherwise valid local candidate because of an unrelated interpreter. The test does not establish that such a worker existed during the original attempt. Predicate/traceback evidence (private local diagnostic; not published).

## Minimal diagnostic fix and tests

The concrete confirmed implementation defect was **loss of failure evidence**. Changes are limited to the private local orchestration:

- Added `.state-phase233-private/precondition_diagnostics.py`: exclusive/fsynced sanitized process snapshots; exception type and basename/function/line traceback; a reviewed static assertion identifier/predicate. It records no arbitrary exception message, frame locals, raw command line, OAuth data or capability value.
- Added one snapshot call before the existing process assertions in `execute-once.py`, and `capture_failure(exc)` in its existing error handler.
- Preserved **all 68 original assertion ASTs exactly**, including identity, versions, financial evidence, deadlines and the strict predecessor rule. No assertion, security fence or Runtime method was bypassed. The broad process rule remains fail-closed because the actual original snapshot is unknown; changing that policy needs its own review.

The patched function reproduces the same controlled rejection at **current execute-once.py:123**, corresponding to original line 121. Its retained traceback names the file, function, line and predicate plus **POSSIBLE_ACTIVE_PREDECESSOR**. The state remains unchanged. Patched traceback (private local diagnostic; not published).

**9 local diagnostic tests passed in 1.14 s.** They cover redaction of arbitrary sensitive assertion messages, exact failure site/static identifier, exclusive sanitized process records, equality of every original assertion, and continued refusal of wrong Action/version/scope/Capture/Plan digest. One initial test was affected by pytest's own assertion-message rewriting; it was changed to raise the same normal AssertionError used by production Python, without relaxing the helper. JUnit (private local diagnostic; not published).

New helper/tests Ruff lint/format passed. Existing production lint, formatting (**28 files**) and `pip check` passed. No production payment code or shared Runtime changed; the prior full 389-test regression was not re-run or represented as a new result.

## Supported Runtime continuation and stop point

At **2026-10-13 05:18:28 UTC**, the original directory and matching **real** configuration were opened through the unchanged public `composition/open_runtime`. Startup recovery candidates were proven empty beforehand. Only private capability read verification, `run_service.get`, `gateway.get/list_for_run` and local Executor argument validation were used. A no-provider adapter and socket fence prohibited network I/O. Normal supported startup performs schema/no-op transactions; all original file hashes were checked afterwards to prove no state transition or persisted modification.

Validated original candidate:

- Run `d57ccc23-7849-4854-90b9-cd7352d569e6`: **Approved v5**, exact original Plan SHA256.
- Action `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`: **Authorized v2**, original compiled specification, scope and grant.
- Effect key / PayPal request-id: `5320d555-d195-4a71-97e0-d2bf8ac11fe3`, unchanged.
- Original NZD 5.00 arguments, trusted Capture and merchant match; zero attempts, execute receipts or provider observations; no financial Unknown.
- Original OS owner fence acquired and released; pinned **0.1.0 / fd742b783058a53400c465b4ab59c6e80715895a**, immutable five-second budget unchanged.

Public Runtime continuation evidence (private local diagnostic; not published). This proves supported local state continuity; **remote payment eligibility was NOT QUERIED** and still needs fresh Capture/Order validation after separately renewed permission.

A separate deterministic entry obstacle remains: `main` exclusively writes the already-existing `gate3-confirmation.json` **before its try block**, and exclusively writes the existing outcome later. Directly invoking that old one-shot main again would encounter FileExistsError; this is **not** the original AssertionError. Those historical records were not deleted, replaced or relabeled. A future explicit continuation needs a reviewed invocation using separate attempt audit artifacts while retaining this same Run, Action, grant, state directory and financial effect key. No new Approval/Authorization or replacement Action is warranted by the current validated state.

Decision: **GO for original public Runtime state continuity; NO-GO for directly rerunning the old runner or executing without the user's separate permission.** The historical individual predicate remains UNDETERMINED. Current local checks pass when the strict process assumptions hold; diagnostics now make a future failure identifiable. Existing five-second/Unknown risk and refund-balance uncertainty remain.

All **3921** phase-start private files were compared: only the explicitly repaired private runner and its derived bytecode changed. Financial databases, original confirmation/outcome evidence, fixture, Plan archive, owner, capability and `.env` remain byte-for-byte unchanged. All **54** hashed Runtime files and **16** production source/assets remain unchanged. Git HEAD/index unchanged. Integrity (private local diagnostic; not published).

**STOP.** Gateway execute, real provider calls, Refund POST, new Run/Action/Approval/Authorization, financial-state changes, automatic retry/reconciliation, commit and push are all **0** during diagnosis. Wait for separate permission before any renewed financial execution attempt.
