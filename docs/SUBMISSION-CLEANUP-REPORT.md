# Final submission cleanup and release qualification

14 October 2026 — **PASS for local final qualification; GO for demo rehearsal and final Hackathon preparation.**
Publication requires the final index/object privacy gates and verified normal push.

Baseline: `86a179fc6ca02568a849c51e765d6dca123dced7`. Tested executable code: `2c7c5f584c0a5f362299293c276116e1d7962f7f`.
Final release commit: the Batch 5 commit **chore: qualify final Refund Sentinel submission tree**
that first adds this report. Its exact SHA is resolved by
`git log -1 --format=%H -- docs/SUBMISSION-CLEANUP-REPORT.md` and recorded in the
verified publication result. This avoids a self-referential commit hash in its own contents.

## Five batches

| Batch | Outcome | Reviewed result |
| --- | --- | --- |
| 1 — Evidence | PASS | 117 old public paths removed; frozen proof/contracts and two consumed latency fixtures kept; eight representative images; six focused tests, 64 links and image hashes passed |
| 2 — Documentation | PASS | 20 superseded reports consolidated into six current guides; README promotes the credential-free presentation; 38 current local links passed |
| 3 — Tooling | PASS | All eight original tools retained; generated outputs moved to ignored QA; new reference/proof checker; eight focused Python and 12 Node tests passed; 87 original assertions unchanged |
| 4 — Hygiene | PASS | Known text/binary attributes without renormalization; precise generated ignores; 130 exact local-only exclusions; user AGENTS edit preserved |
| 5 — Qualification | PASS | Full regression, actual browser/model, fresh install/start, installed wheel, package/dependency, privacy and integrity checks; final report/summary only |

Earlier batch commits:

- `99c2154d550365e90ce2a44b2e1e9abdef1301c1` — chore: streamline public submission evidence
- `cea81394b149e06c2c8f7299a4c44e619a35f1ff` — docs: consolidate Refund Sentinel submission guides
- `c6c4b18824a117e95775480fe9c1b11483c46884` — chore: remove obsolete development tooling
- `2c7c5f584c0a5f362299293c276116e1d7962f7f` — chore: normalize repository hygiene for submission

## Public tree and retained evidence

| Category | Before | After |
| --- | ---: | ---: |
| All public files | 220 | 98 |
| Public evidence | 123 | 18 |
| Documentation under docs | 26 | 7 |
| Maintained scripts | 8 | 9 |

No tests, financial source, Runtime source, dependency pins or functioning legacy UI
were deleted. Removed old paths: **117 evidence + 20 documentation**; safe public
history is retained at the pinned baseline. New paths are the curated evidence set,
reference checker, attributes and this report. See the exact
[Batch 1 deletion manifest](../evidence/submission/cleanup-manifest.json) for every
evidence path, reason, references and archive. Documentation's unique current
information lives in architecture, Sandbox setup, UI/QA, demo script, competition
and the unchanged backend freeze; chronological diagnostics stay in Git history.

The original [verified refund](../evidence/phase2-freeze/verified-refund.json),
freeze manifest, historical validation and publication validation are unchanged.
Refund `1XN74010T5365280D`: NZD 5.00 from NZD 20.00, POST **201**, independent GET
**200 / COMPLETED**, exactly one observed POST, durable Receipt
`e1415750-0971-4347-a88d-a3704dbb79c8`. Those are archived observations, not a new
PayPal lookup or today's refund balance. Two sanitized historical read-latency
fixtures remain because offline tests consume them.

[Curated evidence](../evidence/submission/README.md) contains eight reviewed
representative screenshots and one [final summary](../evidence/submission/qa-summary.json).
Images preserve original bytes and provenance; they depict multiple isolated
synthetic/archive cases, not another real financial execution.

## Tools and Git decisions

Retained tools: `audit_publication.py`, `collect_evidence.py`, `presentation_ready.mjs`, `test_presentation_ai_browser.mjs`, `test_presentation_browser.mjs`, `test_ui_acceptance_browser.mjs`, `validate_phase235_wheel.py`, `verify_presentation.mjs`, `check_submission.py`.
No original script was proven obsolete. Consumer/browser/mock outputs now default
to ignored QA directories; no regression assertion was weakened. The new checker
validates current Markdown references, screenshot hashes and immutable proof.

The initial inventory found 49 raw CRLF/LF-only differences and two meaningful
local edits. Attributes specify known text and binary types but preserve native
checkout policy; no blanket rewrite or protected source conversion occurred.
The user's duplicate `build/` addition was explicitly reviewed and merged into
one equivalent rule, with original bytes backed up privately. Extra ignore rules
cover wheels and generated evidence XML/logs, not general source/tests/JSON evidence.

All 130 earlier untracked diagnostics remain byte-identical, including the personal
network report. Exact paths are excluded only in local `.git/info/exclude`, not a
broad public ignore. `.env`, private state/databases/provider records/capabilities,
prior human grants, environments and caches remain local. The original AGENTS
blank-line edit remains byte-identical and uncommitted. No private cleanup occurred.

## Actual final qualification

| Check | Actual result |
| --- | --- |
| Full Python | **535 passed**, 0 failures/errors/skips, **553.19s**; one existing Starlette/HTTPX warning |
| Node | **12 passed**, no failures/skips |
| Chromium | 156.0.8078.4; 10 main E2E checks, five skip/history cases, three unknown routes, 30 mobile layout cases and four desktop action/mode cases |
| Local AI | Genuine `phi4-mini:latest`, HTTP **200**, **14.525721s**; real local proposal, three separate simulated confirmations, Succeeded v4 and durable fake Receipt after reload |
| Additional UI | 15 AI visual cases, four explicitly mocked negative-model contracts; Unknown/Failed terminal, reset/reload and no duplicate dispatch |
| Accessibility | **67 axe scans, zero detected violations** |
| Lint/format/assets | Ruff PASS, 47 Python files formatted; Prettier and ESM/assets PASS |
| Dependencies | Offline lock check: 31 packages; pip check PASS; official npm audit: zero vulnerabilities |
| Fresh public-source installation | Clean Git export without private state; exact README uv sync PASS in a new environment; pinned installed Runtime verified; start returned 200 for home/assets/proof and 404 for financial routes |
| Wheel | Isolated offline build; all 29 package source/assets byte-match; actually installed into the fresh environment and exercised outside checkout |
| Installed Runtime flows | Both five- and fifteen-second profiles Succeeded with one mock POST and durable Receipt each; restart produced zero duplicate posts; socket audit forbids real network |
| Installed presentation | All frontend assets/proof 200; real operations routes, private .env and legacy operations JS 404 |
| Integrity | **4,058 private files, 19 frozen backend files, three dependency contracts and 57 original installed Runtime files unchanged** |
| Images/privacy | Eight images visually reviewed plus ten Windows OCR tiles; metadata/private-literal scans PASS; raw OCR and logs remain private |

The full Python run used the absolute qualified interpreter with preview stopped
and no concurrent Python tools. Generated timing records went to new private QA
output; no old diagnostic needed restoring. Clean-source qualification used only
public Git contents and newly installed dependencies, not a copied financial state.
Wheel installation used that fresh environment after verifying the README's source
install/start. The code-level import inspection was rerun from the correct export
working directory after its initial local harness directory mismatch; no application
assertion or security check was bypassed.

The Runtime remains **0.2.0**, pin
`7261fdd2f47d2b15fabe8faac527eeee37338eb1`, with clean shared core checkout.
The annotated Phase 2 tag remains on `04fac090b6aa0a77ef1c50b9e6b451404fccc58f`.
Final publication scans cover the exact index and all newly reachable Git objects;
a sensitive finding blocks push. Normal fast-forward publication must verify
local/tracking/live remote SHA equality and the unchanged freeze tag.

## Limits and remaining entrant work

200% text is Chromium QA font magnification, not native Firefox zoom. Physical
mobile, complete screen-reader certification, other browser engines/OS ownership
and production multi-user/HA behavior are not qualified. One genuine past Sandbox
sample is not a latency distribution, authoritative current balance or universal
exactly-once guarantee. Slow/lost verification can still yield terminal Unknown.

**Cleanup issued zero genuine PayPal requests or mutations**, never replayed a
financial Action and never modified shared Runtime source. No force push, new/moved
tag, deployment or GitHub release is part of this task. The [official competition
requirements](competition.md) were checked, but narrated rehearsal/recording,
YouTube upload, eligibility verification and the final entry remain separate work.
**GO for safe demo rehearsal and final Hackathon preparation.**
