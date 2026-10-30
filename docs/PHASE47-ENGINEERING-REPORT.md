# Phase 4.7 engineering qualification

30 October 2026, Pacific/Auckland. **Decision-evidence hardening: PASS.
Gate 1: PARTIAL.** Full regression has two retained Windows host-isolation
failures. This is not unconditional release or recording qualification.

## Baseline and scope

Initial local HEAD, origin/main and live HTTPS remote main all identified
`3811725cec176012b883161140b3a6a529bb69d6`. The initial worktree was clean.
HEAD remains unchanged; this implementation is uncommitted. Artifacts are outside
Git at `D:\workshop\oct\refund-sentinel-phase47-artifacts\20261030-030524`.

Read the actual AGENTS.md, supplied Phase 4.7 requirements, project documentation,
consumer integration and tests, plus the pinned core consumer example, handoff and
adapter guide. Installed Python is 3.13.9; Node is 26.5.0. The installed Runtime
reports 0.2.0 and the exact required Git source commit
`7261fdd2f47d2b15fabe8faac527eeee37338eb1`, importing from `.venv/Lib/site-packages`.
The local annotated v0.2.0 tag peels to that SHA. All 57 hashed distribution RECORD
entries verified. Actual public API signatures were inspected. No Runtime extension,
dependency update, extended execution budget or financial backend change is used.

## Root cause and correction

`DemoSession.generate_lab()` previously wrote an explanatory policy PASS before
awaiting `Sentinel.analyze()`. An unexpected Runtime exception could reach the
existing finally-save path with that PASS still present. A policy acceptance alone
did not establish that a matching durable Plan existed. A product incident could
also remain reserved after a creation fault or cancellation.

The smallest correction stays in the synthetic presentation consumer:

- Separate strict schema validity, trusted `policy_eligibility`, and
  `workflow_status`. ELIGIBLE alone exposes no executable authority.
- Record PASS/READY only after reading the Run using the public Runtime API,
  comparing its Plan, Run identity and canonical fingerprint with the analysis
  result, and verifying the initial AwaitingApproval state with no Action.
- Preserve controlled and unexpected Runtime failures as FAILED/NOT_EVALUATED.
  Preserve policy rejection as BLOCKED, and cancellation as INTERRUPTED.
  Private exception messages are not placed into evidence.
- Save the expected Run ID and fingerprint in the new explanatory record.
  Recheck them on reads. If unavailable or mismatched, return an explicitly failed
  projection with no executable Plan/Run/Action/Receipt and refuse commands.
  Do not rewrite the persisted evidence during this read failure.
- Reject generation replay and approval/admission/authorization/execution on
  failed or interrupted cases, including a case with an orphan AwaitingApproval
  Run after cancellation. The Runtime still owns every actual grant and effect.
- Optional fields default to null for legacy records. Old evidence is not
  rewritten or assigned a newly invented historical readiness status.
- Hide frontend gates for non-ready decisions, including deliberately stale Run
  projections. Final UI titles and progress show generation failure/interruption,
  with no residual AwaitingApproval heading or policy PASS badge.

The initial frontend failure screenshot revealed a stale AwaitingApproval heading
despite hidden controls. That defect was corrected; initial captures remain under
`browser/readiness`. A later heading assertion caught a separate old title
calculation, which was also corrected. Final acceptance uses
`browser/readiness-stable-final`; failed/intermediate runs remain preserved.

## Actual changed files

| File                                           | Change                                                                                    |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `src/refund_sentinel/demo.py`                  | Durable Plan verification, explicit failure/interruption states, read and command fencing |
| `src/refund_sentinel/presentation_models.py`   | Four compatible optional evidence fields                                                  |
| `src/refund_sentinel/static/console-state.mjs` | Non-ready gate suppression and accurate failure progress/title                            |
| `src/refund_sentinel/static/console.js`        | Separate eligibility/readiness evidence and bounded failure explanations                  |
| `tests/test_decision_lab.py`                   | Ten additional fault, persistence, interruption/restart and legacy cases                  |
| `tests/decision-lab-state.test.mjs`            | Three additional stale-projection cases                                                   |
| `docs/PHASE47-ENGINEERING-REPORT.md`           | Engineering findings and qualification                                                    |
| `docs/PHASE47-IAB-REHEARSAL-REPORT.md`         | Actual IAB blocker and separate headless results                                          |
| `docs/PHASE47-FINAL-DELIVERY-REPORT.md`        | Final gate status, artifact paths and remaining work                                      |

## Negative-test evidence

All tests use synthetic state and the real installed Runtime. Model HTTP contracts
are explicitly mocked; regression fixtures forbid real HTTP transport. Fault
injection at a public boundary is test-only and does not modify the installed core.

| Requirement                                       | Actual coverage                                                                                            |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| T01 invalid JSON; T02 invalid schema              | Existing `test_invalid_actual_output_is_preserved_but_never_executable` cases                              |
| T03 policy rejection; T04 missing trusted amount  | Existing `test_untrusted_valid_schema_cannot_override_case_or_policy` cases                                |
| T05 Runtime creation failure                      | New `test_runtime_creation_fault_retains_reserved_incident_without_executable_plan`, two failures injected |
| T06 controlled; T07 unexpected exception          | New `test_runtime_failure_never_exposes_policy_pass_or_authority`                                          |
| T08 missing durable Run; T09 fingerprint mismatch | New generation and read-projection tests, including persisted Plan/result mismatch                         |
| T10 interruption                                  | Existing model cancellation plus new cancellation after the Run is persisted                               |
| T11 restart after interruption                    | New `test_interruption_after_persisted_run_stays_non_executable_after_restart`                             |
| T12 repeated/concurrent Generate                  | Existing duplicate/concurrency tests and new repeat denial after failure                                   |
| T13 inference creates no Action                   | Direct SQLite counts in new faults and existing case tests; orphan Run has zero Actions                    |
| T14 no dispatch before authorization              | Existing gate tests and denial of all commands on new fault projections                                    |
| T15 no duplicate dispatch after restart           | Existing five-case terminal restart tests, including Unknown, and new interrupted-Run restart test         |

New Runtime failures have schema PASS and policy ELIGIBLE but **no policy PASS**,
no executable amount or Plan, zero Actions and zero fake dispatches. Controlled
creation faults retain the reserved incident; they do not manufacture a Run.
The interrupted-after-persistence test proves one durable Run and zero Actions,
then restarts the application and proves all execution commands remain denied.

## Host isolation investigation

Both requested tests were run individually and together before changes to any
guard code; no guard code was subsequently changed:

| Run                                      | Result                                                                            | Pytest duration |
| ---------------------------------------- | --------------------------------------------------------------------------------- | --------------- |
| unrelated literal sleep + read-only lock | FAIL: PROCESS_IDENTITY_UNVERIFIABLE                                               | 7.22 s          |
| competing public Runtime owner           | FAIL: expected COMPETING_SENTINEL_PROCESS, observed PROCESS_IDENTITY_UNVERIFIABLE | 12.59 s         |
| both together                            | 2 failed; same identity errors                                                    | 18.92 s         |

`host-process-diagnosis.json` records three further actual double-CIM attempts.
One rejected a changing inventory; the precise transient change remains
**UNRESOLVED**. Two stable inventories both identified blocking PID **27980**,
created `2026-10-29T09:18:14.377Z`, whose executable was
`D:\workshop\oct\crowdquest-ai\.artifacts\phase45-browser\core\Scripts\python.exe`.
It is outside the guard's exact trusted set of the current interpreter and base
interpreter. Its safe command fingerprint is
`85561456d427ee994d3489d81d761dcca3b7107e85734c9d6d0e43f2df9f0c50`.
This is direct evidence of why the stable inventories fail closed on this host.

The classifier validates every interpreter before classifying competitor roles.
Consequently the unrelated executable is rejected before the synthetic competing
owner can yield the more specific expected code. Existing Refund Sentinel previews
are also active; removing only the CrowdQuest process would not establish an
isolated success environment. The read-only owner-fence assertion in the competing
test passed before its classifier assertion failed. The first test's owner-lock
probe is not reached when inventory classification is denied.

The full suite reproduced the same two identity failures. This is a host with
existing Python services, not the clean-host condition assumed by these success
assertions. No defect justifying weaker identity checks was established. No
CrowdQuest, existing Refund Sentinel or unrelated service was stopped. A dedicated
isolated Windows process environment was not provisioned or qualified. Safe next
step: run the exact tests on a separate Windows host/VM, with the pinned environment,
no other Python services and no payment credentials; then run full regression.
Do not claim that isolated-host run has already passed.

## Regression and packaging

Commands below were run from the actual project with the installed virtual
environment. Paths after `--junitxml` point into the artifact directory.

| Check / command                                                                                                                                                            | Actual result                                                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| New Python faults: `python -m pytest -q tests/test_decision_lab.py -k 'runtime_failure or creation_fault or rechecks_persistent or interruption_after or legacy_evidence'` | 10 passed, 55 deselected, 0 failed; 5.88 s; `new-negative-tests.xml`                                                                               |
| `python -m pytest -q tests/test_decision_lab.py tests/test_deepseek.py tests/test_demo_ai.py tests/test_presentation.py --tb=short`                                        | 173 passed, 0 failed/skipped; 90.29 s; `targeted.xml`, `targeted.log`                                                                              |
| `python -m pytest -q --tb=short`                                                                                                                                           | **651 passed, 2 failed, 0 skipped; 535.83 s**; `full-pytest.xml`, `full-pytest.log`, `full-run.json`                                               |
| After final frontend correction: `python -m pytest -q tests/test_presentation.py tests/test_publication_audit.py --tb=short`                                               | 31 passed, 0 failed/skipped; 23.72 s; `post-visual-python.xml`                                                                                     |
| `node --test tests/presentation-state.test.mjs tests/decision-lab-state.test.mjs tests/deepseek-state.test.mjs`                                                            | Final 21 passed, 0 failed/skipped; 389.7866 ms; `node-accepted.log`                                                                                |
| `ruff check src tests scripts`; `ruff format --check src tests scripts`                                                                                                    | PASS; 51 Python files formatted                                                                                                                    |
| Prettier and `node scripts/verify_presentation.mjs`                                                                                                                        | PASS; native assets, syntax and pinned proof verified                                                                                              |
| `python scripts/check_submission.py`                                                                                                                                       | PASS; 48 existing local links, eight curated image hashes, immutable proof; zero network requests                                                  |
| `uv lock --check --offline`; `uv pip check --python .venv/Scripts/python.exe`                                                                                              | PASS; frozen lock resolves 31 packages; installed packages compatible                                                                              |
| `uv build --wheel --offline --out-dir <artifacts>/wheels-accepted`                                                                                                         | PASS; final source and all 31 packaged source/assets match                                                                                         |
| Fresh external wheel install and `wheel_smoke_accepted.py`                                                                                                                 | Five cases PASS with mocked cloud, installed Runtime and FakePayPal; zero genuine network; Succeeded / NO_ACTION / NO_ACTION / Succeeded / Unknown |
| `uv pip check --python <artifacts>/wheel-env/Scripts/python.exe`                                                                                                           | PASS; all 31 installed packages compatible                                                                                                         |

Full regression includes provider contracts, runtime boundaries, approval/binding,
execution budgets, pre-dispatch and ambiguous outcomes, and recovery tests. The
only failures are the two named host-isolation tests. The Starlette/httpx TestClient
deprecation warning remains; dependencies were not changed to suppress it.
The first external wheel installation attempt could not resolve cached Ruff offline;
the exact lock was then installed normally. The final wheel replacement and build
were offline. Hardlink fallback to copying was reported. No package pin changed.
Non-Python checks were partly run in combined command batches; separate per-command
timing was not measured where absent from the log. No duration is invented.

Final headless browser details and the actual IAB blocker are in the
[rehearsal report](PHASE47-IAB-REHEARSAL-REPORT.md). The full Python run preceded the
last frontend-only title/progress correction. Python production code was unchanged
after that full run; final Node, relevant Python, browser and wheel checks cover the
corrected frontend.

## Frozen boundary, evidence and acceptance

The baseline manifest covers all 107 previously tracked files. Exactly six baseline
files are intentionally changed; the remaining 101 must match the recorded hashes.
This includes financial source, guard source, proof/evidence, dependency declarations
and both lockfiles. Final machine-readable checks are in `integrity.json`.
The historical proof SHA-256 is
`1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853`.
No historical private financial state, Action identity or Receipt was opened for
execution, rewritten, reset, relabeled or replayed. New application state is isolated.

No genuine PayPal request was made by Phase 4.7 work. Regression real transports
are forbidden, wheel inference uses MockTransport, and the new preview permits
only fixed, bounded DeepSeek proposal egress with a persistent four-request cap.
Actual new cloud calls remain zero while genuine IAB access is blocked. This is a
statement about this task's executions, not a host-wide traffic audit of unrelated
processes. Historical Phase 4.6 inference samples are not new acceptance results.

Engineering consistency is corrected and tested. Gate 1 remains PARTIAL because
the mandatory full regression is not all green and clean-host qualification has
not been performed. Do not start final recording or declare submission readiness.
No commit, push, deployment, upload or Devpost submission was performed.
