# Backend freeze, secure publication and local UI delivery

This document records the original development checkpoints and their then-local
publication status. Phase 3/3.1 source publication is covered by the separately
authorized [publication qualification](PHASE3.1-PUBLICATION.md); earlier statements
that changes were uncommitted describe the time those checks were recorded.

**2026-10-14, Pacific/Auckland — Stage A PASS; Stage B PASS; Stage C PASS for the
qualified local Windows Sandbox/demo scope.** No new genuine PayPal request,
Order, Capture or Refund occurred. The original terminal financial Actions and
private evidence remain preserved. Phase 3 is local, uncommitted and undeployed.

## A — Backend feature freeze

Full baseline: **476 passed**, zero failures/errors/skips, 468.81 seconds. Ruff,
formatting, lock/dependency validation, consumer wheel build and installed-wheel
integration outside the checkout passed. Both default five-second and separately
bound fifteen-second profiles completed offline public Runtime workflows with a
durable receipt and no duplicate dispatch after restart.

Installed Runtime **v0.2.0**, commit
`7261fdd2f47d2b15fabe8faac527eeee37338eb1`, its annotated release and all **57**
recorded file hashes were verified. The shared core repository remains clean.
The [freeze document](PHASE2-BACKEND-FREEZE.md) and
[manifest](../evidence/phase2-freeze/manifest.json) define the protected backend.
The previously private-dependent regression now tests the distributable one-POST
fence without weakening its duplicate/restart assertions or skipping the test.

The archive preserves the genuine completed pilot: **NZD 5.00**, Refund
`1XN74010T5365280D`, independent HTTP 200 verification, **Succeeded v4**, receipt
`e1415750-0971-4347-a88d-a3704dbb79c8`, exactly one observed Refund POST.
Its measured Gateway time was **4.766604 s**, POST **HTTP 201 / 2.148422 s** and
Refund GET **HTTP 200 / 1.392813 s**. Those are historical observations, not new
queries or statistically qualified latency. See
[sanitized proof](../evidence/phase2-freeze/verified-refund.json).

## B — Secure release

| Publication fact | Verified result |
|---|---|
| Public repository | https://github.com/miku-wwl/refund-sentinel-agent |
| Existing tracking branch | `main` → `origin/main` |
| Freeze commit | `04fac090b6aa0a77ef1c50b9e6b451404fccc58f` |
| Commit description | `feat: freeze verified Refund Sentinel Sandbox backend` |
| Annotated tag | `phase2-backend-freeze` |
| Annotated tag object | `7a271334c37030a8290d372b9f2c86366f3daa35` |
| Remote branch and peeled tag | Both equal the full freeze commit |
| Changed files / full public tree | 61 changed files / 101 reviewed files |
| Published dependency | Exact v0.2.0 commit; dependency repository also publicly accessible |

Normal pushes used the existing remote; no force push, history rewrite, tag
replacement, secret publication or deployment. The explicit publication list and
staged tree passed content scanning and cached diff checks. **109 historical Git
blobs** passed checks against actual private literals and credential patterns.
Four existing screenshots were visually reviewed. Negative URL tests and the
explicit synthetic buyer fixture have narrowly scoped scanner exceptions; tests
prove actual private literals and other credentials remain rejected.

All **174 untracked candidates** were inspected. **130 unneeded diagnostics** were
retained locally rather than published, including flagged process/debug records.
Private state, original raw provider bodies, full human confirmations, `.env`,
capabilities, databases and build caches were excluded. Public reports use
sanitized summaries; unpublished evidence links are explicitly local diagnostics.
Exact file/hash lists and publication receipts are retained privately; public
[publication validation](../evidence/phase2-freeze/publication-validation.json)
records the allowlisted outcomes.

A clean publication export installed from the lock and exercised **480 distinct
enabled tests**. The first run had 478 passes and two fail-closed ownership-test
failures while a parallel Python validation process was alive. No assertion or
owner check was changed. In an exclusive test environment, all 26 ownership and
publication checks passed. The final Phase 3 full suite later passed every test
in a single invocation, including those original ownership tests.

A genuine HTTPS clone of the remote annotated tag subsequently
installed all **31 locked packages** with `uv sync --frozen --all-extras`.
Its **37 workflow/publication tests passed in 24.97 s**, without original private
state or credentials. Installation and import were from the clone, not this
checkout. This proves the tested Windows installation path; it does not claim
every platform or offline cache can install it.

## C — Local UI and simulation

Delivered all five working screens: Operations Overview, genuine historical
AI Refund Review, Trust Workflow, verified historical evidence and interactive
synthetic demo. The separate entrypoint is:

```powershell
.venv\Scripts\python -m refund_sentinel.presentation --port 8880
```

Local preview: **http://127.0.0.1:8880**. It binds loopback, ignores `.env` and
uses the fake provider with new synthetic scopes. No real financial mutation
routes are mounted. Approval, Authorization and Execute Simulation require
separate explicit decisions. The unchanged installed Runtime owns durable
transitions and effect protection. Unknown stops; reset retains old simulations
and creates a fresh identity. No historical financial Action can be resumed by
this browser.

| Final check | Actual result |
|---|---|
| Full pytest | **507 passed**, zero failures/errors/skips, **480.70 s** |
| New API/isolation regressions | 27 passed |
| Node state/escaping/gate tests | 12 passed, zero skipped |
| Ruff and Python format | PASS |
| Native ESM syntax/assets | PASS; no added application runtime dependency |
| Frontend formatting | Prettier check PASS for new HTML/CSS/JS/MJS; SVG HTML parser checked separately |
| Chromium | Actual 156.0.8078.4 browser execution PASS |
| Browser scenarios | Five screens, separate gates, cancellation, receipt, reload/reset, no replay, Unknown/Failed and service error |
| Accessibility | 11 axe WCAG 2/2.1 A/AA scans, zero detected violations |
| Responsive checks | 1440×1060 desktop, 390×844 mobile; no page overflow |
| Browser errors / external requests | Zero unexpected console/page errors; zero external/PayPal requests |
| Package | Wheel build and outside-checkout installation/asset/gated simulation PASS |
| Locks/dependencies | `uv lock --check --offline`, `pip check` PASS; browser development-tool npm audit reports zero vulnerabilities |
| Frozen backend | All **19** original backend/static file hashes unchanged |
| Historical private state | All **4058** original file hashes unchanged, including `.env` |
| Runtime | Pin and 57 recorded hashes unchanged; core Git checkout clean |
| Genuine PayPal operations in this task | **0** |

The final browser rerun also passed after frontend formatting and screenshot
capture adjustments. Its exact route log contains only presentation/simulation
requests; no real operations endpoint was used. The simulated receipt is an
actual durable local artifact, clearly labeled as simulation rather than a
second genuine PayPal transaction.

An additional presentation safeguard requires Succeeded and the Runtime's exact
receipt reference/payload binding before displaying a successful receipt. A
synthetic synchronous persistence delay of 5.05 seconds crosses the unchanged
five-second budget: the verified observation remains durable, the Runtime Action
is Unknown, successful receipt presentation is withheld and repeat execution is
rejected. The first implementation accidentally called an ExecutionSpec method
on CompiledSpec; three synthetic tests failed. This was corrected using the
inspected public `ExecutionSpec.from_compiled` API. All 27 presentation tests then
passed in 24.02 seconds. Failed/interrupted test records remain private. No
Runtime or financial backend source was changed, and no assertion was bypassed.

One blank line appeared in the working instruction document relative to the
freeze commit. Its cause was not established. The existing working copy and a
private backup were preserved; all instruction tokens and dependency identity
match. No security instruction or frozen financial source was changed, and the
published tag was not moved. The immutable freeze document/manifest remain intact.
Timing artifacts regenerated by tests were preserved separately; the original
historical evidence bytes were restored without clearing state.

Build-tool recovery was local only: a pip build without isolation lacked
setuptools, so the successful build used the project's isolated `uv build` path.
The Windows ASGI harness's internal loopback self-pipe was allowed while external
connections remained forbidden. Neither issue required a product or Runtime
change. A known Starlette/HTTPX TestClient deprecation warning remains.

## Artifacts and next step

- [UI architecture and safe startup](PHASE3-UI-DEMO.md)
- [English 2–3 minute demo and 60-second pitch](DEMO-SCRIPT.md)
- [Overview screenshot](../evidence/phase3-ui/01-overview.png)
- [Simulation screenshot](../evidence/phase3-ui/09-demo-completed.png)
- [Mobile screenshot](../evidence/phase3-ui/14-mobile-demo.png)
- [Browser/accessibility evidence](../evidence/phase3-ui/browser-verification.json)
- [Installed-wheel verification](../evidence/phase3-ui/wheel-verification.json)
- [Final integrity/regression result](../evidence/phase3-ui/final-verification.json)

The published Phase 2 commit and tag remain the recovery baseline. Stage C
changes and screenshots remain **local and unstaged**; unrelated original local
diagnostics are retained. No Stage C commit, push, deployment, narrated video,
YouTube upload or final competition submission occurred.

Next submission action: review this UI, separately authorize Phase 3 publication,
then rehearse/record the English video and complete the competition submission
checks. No further genuine financial operation is needed for the demonstration.
Remaining limits include local single-operator security, Windows-qualified resume,
one genuine Sandbox sample, incomplete refund-balance ledger, unknown latency
tails, cooperative cancellation/cross-store crash windows and no universal remote
exactly-once guarantee.

## Phase 3.1 addendum — targeted demo polish

**PASS; GO for independent UI review in ChatGPT Work.** Full regression:
**535 pytest / 12 Node passed**, no test failures; 494.96-second pytest run.
Actual Chromium: both model modes, 15 screen/viewport combinations, **28 axe scans
with zero detected violations**, 32 screenshots, no critical clipping/overflow or
unexpected browser errors. Real local inference was observed at 10.240636 and
5.000926 seconds; wheel AI compatibility used explicit mocks, not fabricated live
inference. The real-AI synthetic receipt survived a new server process unchanged.
Ruff/format, frontend syntax/format, lock, pip, wheel and secret checks passed.
Protected SHA counts remain **4,058 private / 19 financial source / 57 Runtime**;
three immutable dependency files and the freeze commit/tag also remain unchanged.
No genuine PayPal API call, financial state change, commit, push or deployment.

The optional Local AI Demo now invokes genuine loopback Ollama `phi4-mini:latest`
for the fixed synthetic incident. It reuses the frozen recommendation parser,
payment policy and public Runtime integration. Fixed credentials-free model
transport, bounded output and planning deadline do not change the offline payment
provider or five-second simulation execution profile. Rejected/unavailable/expired
proposals preserve the prior safe state, and fallback is a separate manual choice.
No financial route, grant, historical Action or execution budget was changed.

Evidence Provenance explains genuine historical APIs versus the current sanitized
archive, independent Refund GET and separate-process receipt verification. Links
reference the published freeze SHA. Recording typography was selectively increased,
and screenshot readiness now waits for fonts, finite animations and stable layout.
An active opacity-0.4 animation was reproduced after navigation readiness; the
original image's exact cause cannot be proved from its missing timing metadata.

Exact Phase 3.1 source changes:

- `src/refund_sentinel/demo_ai.py` — new bounded loopback proposal adapter.
- `src/refund_sentinel/demo.py` — immutable mode, proposal staging and safe resume.
- `src/refund_sentinel/presentation.py` — closed mode-aware presentation API.
- `src/refund_sentinel/presentation_models.py` — mode/source/model timing contracts.
- `src/refund_sentinel/static/console.js` — selectable modes, explicit fallback,
  real-inference indicator, provenance and unchanged independent human gates.
- `src/refund_sentinel/static/console.css` — recording typography/responsive controls.
- `scripts/presentation_ready.mjs` — new explicit visual readiness helper.
- `scripts/test_presentation_browser.mjs` — preserved E2E with stable capture timing.
- `scripts/test_presentation_ai_browser.mjs` — real Ollama and mocked negative UI QA,
  all five screens at all three requested viewports.
- `tests/test_demo_ai.py` — isolated HTTP contract, policy, cancellation and binding
  tests; these mocks are not presented as genuine inference qualification.

Documentation changes are this addendum, [UI implementation](PHASE3-UI-DEMO.md)
and the [English demo script](DEMO-SCRIPT.md). Updated screenshots and machine-readable
qualification live under `evidence/phase3-ui/`; previous Phase 3 artifacts were
preserved privately before retaking stable names. No broader evidence was cleaned.

See [Phase 3.1 browser results](../evidence/phase3-ui/phase31-browser-verification.json)
and [final qualification](../evidence/phase3-ui/phase31-final-verification.json)
for actual counts, timing, integrity, package and security evidence. The original
Phase 3 record above remains a historical checkpoint. Current readiness and
remaining limitations are described in the Phase 3.1 section of the UI document.
