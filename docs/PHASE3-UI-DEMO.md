# Phase 3 UI and isolated demo

**Phase 3/3.1 source checkpoint, qualified locally; no hosted deployment.** The published Phase 2
baseline is commit `04fac090b6aa0a77ef1c50b9e6b451404fccc58f`, annotated tag
`phase2-backend-freeze`. Phase 3 adds a separate FastAPI presentation app and native
browser ESM/CSS. It does not rewrite the frozen financial application.

## Open the application

From the repository, using its Python 3.13 environment:

```powershell
uv sync --frozen --all-extras
.venv\Scripts\python -m refund_sentinel.presentation --port 8880
```

Open **http://127.0.0.1:8880**. The entrypoint binds loopback and ignores `.env`.
No capability upload or PayPal login is required. Deterministic Demo needs no
model service; optional Local AI Demo uses an already installed local Ollama
`phi4-mini:latest`. Do not use the
older `refund-sentinel` CLI for this presentation: it serves the separate
financial-capable operations app.

## Product and evidence

| Screen | Working behavior | Evidence boundary |
|---|---|---|
| Operations overview | Qualified refund card, actual money/status/latency, policy indicators and nine-stage execution trail | Archived genuine Sandbox facts; no invented business KPIs |
| AI refund review | Preserved real Ollama recommendation, synthetic incident label, exact structured Plan, fingerprint, tool and risk | Genuine historical inference; opening the page calls no model |
| Trust workflow | Three explicit gates and keyboard-accessible state explanations | Read-only explanation; no financial command |
| Verified evidence | Real Refund/Action/Capture/Order/merchant, HTTP 201/200, measured elapsed times, Succeeded v4, receipt modal and provenance references | Immutable sanitized archive; no current PayPal query or replay |
| Interactive demo | Sample → chosen proposal mode → Runtime Plan → Approval/admission → independent Authorization → one synthetic execution → verification → durable receipt | Prominent **DEMO MODE — SIMULATED PAYMENTS**, synthetic USD 25.00 of USD 120.00; optional genuine loopback model inference, always fake payments |

The archived real case remains **NZD 5.00 of NZD 20.00**. Simulation deliberately
uses the frozen fake provider's default USD fixture and fresh identities, making
the paths visibly distinct. The default recommendation is a deterministic fixture.
Local AI Demo calls the genuine local model only after an explicit selection and
Generate Plan click. A `REAL LOCAL OLLAMA` indicator appears only after a parsed,
eligible recommendation is preserved; choosing the mode alone claims no inference.

Navy/charcoal surfaces, teal controls, semantic green/amber states, responsive
cards, native confirmation dialogs, keyboard focus, reduced-motion support and
explicit loading/empty/error views provide the presentation experience. The demo
offers Completed, lost-acknowledgment Unknown and definitive rejection Failed.

## Integration boundary and source changes

All Phase 2 financial source files, their original static assets, dependency pin,
profiles, policy, executor and shared Runtime are preserved. Added files:

| File | Responsibility |
|---|---|
| `src/refund_sentinel/presentation.py` | Independent loopback app, fixed asset routes, archived proof and simulation API |
| `src/refund_sentinel/presentation_models.py` | Closed input/output schemas and explicit field whitelist |
| `src/refund_sentinel/demo.py` | Forced offline settings, fresh synthetic state, public Runtime composition and commands |
| `src/refund_sentinel/demo_ai.py` | Bounded fixed-loopback Ollama transport and existing consumer recommendation parser |
| `static/console.html`, `console.css`, `console.js`, `console-state.mjs`, `console-icon.svg` | Five-screen native frontend, accessible gates and read-only receipts |
| `static/qualified-case.json` | Byte-identical copy of the published sanitized proof |
| `tests/test_presentation.py` | API isolation, genuine public Runtime gates, durable synthetic receipt, failure/no-replay tests |
| `tests/presentation-state.test.mjs` | Frontend gate eligibility, escaping, terminal handling and receipt display |
| `scripts/verify_presentation.mjs`, `test_presentation_browser.mjs` | ESM/asset validation and reproducible Chromium/accessibility QA |

The proof is checked against SHA-256
`1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853`
before startup. Typed nested models reject extra fields. Browser responses never
include secrets, OAuth bodies, capability tokens, raw ledger rows, arbitrary file
content or real execution commands.

| Presentation route | Contract |
|---|---|
| `GET /presentation/proof` | Typed immutable historical proof |
| `GET /presentation/demo` | Current isolated simulation projection, or null before loading |
| `POST /presentation/demo` | Explicit sample/reset; closed scenario and planning-mode enums only |
| `POST /presentation/demo/generate` | Case/mode must match; selected proposal, policy and genuine public Runtime Plan validation |
| `POST /presentation/demo/command` | Closed approve/admit/authorize/execute command, exact Plan fingerprint/version and explicit confirmation |

The real `/api/incidents/...` routes are **not mounted**. Assets have fixed names;
the original operations JS and private paths return 404. Browser POSTs require a
custom simulation header and reject cross-origin requests. Trusted loopback hosts,
same-site HttpOnly simulation cookie, CSP, no-store and no-referrer headers apply.
Validation/exception responses are sanitized and do not echo request bodies.

## State, gates and failure behavior

Simulation state lives only in `.state-presentation-demo/<fresh UUID>/`, with a
simulation marker. An existing non-demo directory is rejected before writing.
The browser cannot select a state directory, Capture, merchant, credentials,
budget or execution scope. Each reset creates a fresh isolated identity and
retains previous records; no Approval, grant or Action is copied.

The unchanged public Runtime creates the Run, validates the Plan, records exact
Approval, admits a Pending Action, grants independent Authorization, durably
claims execution and finishes the terminal state. Consumer code only serializes
browser commands and projects whitelisted views. It does not implement another
durable state machine. The third confirmation belongs to the consumer host.

The fake provider has no spawned helpers or background executions. A resumed
case must pass the existing read-only OS owner-fence probe; the public Runtime
then reacquires and holds its original lock. A competing controller cannot resume
the same owned case. This resume path is qualified on **Windows**. Cross-platform
resume and other browser engines were not qualified.

The demo uses the unchanged **default five-second** adapter profile, distinct from
the archived genuine **fifteen-second** Sandbox profile. Loading, planning,
Approval and Authorization produce no fake dispatch. Execute requires a separate
confirmation. Runtime state polling is local read-only; it never queries a
provider, retries the command or reconciles Unknown. A lost response disables
further execution pending an explicit state refresh. Success presentation requires
Succeeded plus the Runtime's exact receipt reference and matching payload digest;
a durable observation alone cannot elevate Unknown. Terminal Succeeded, Failed
and Unknown never offer replay or reauthorization.

## Phase 3 baseline validation

- **27 new pytest tests PASS**, including genuine installed Runtime integration,
  independent gate separation, stale version/Plan rejection, concurrent execute
  dispatch protection, Unknown/Failed, receipt resume, retained reset history,
  private directory rejection and prohibited real routes/settings. A real
  five-second synthetic deadline test delays receipt persistence by 5.05 seconds:
  the observation remains durable, the Action is Unknown, the browser gets no
  successful receipt and another dispatch is rejected.
- **12 Node tests PASS**, zero skipped; escaping, independent gates, exact command
  binding, all terminal states and independently required receipt presentation.
- **Chromium 156.0.8078.4 PASS**, actual rendered browser execution, not source inspection:
  five screens, cancel safety, three separate confirmations, real synthetic durable
  receipt, reload/no replay, Unknown and Failed, keyboard controls and mobile layout.
- **11 axe-core WCAG 2/2.1 A/AA scans:** zero detected violations. Desktop
  1440×1060 and mobile 390×844; no page-level horizontal overflow.
- **15 actual screenshots**, zero external/browser PayPal requests, zero real
  mutation routes requested and zero unexpected browser console/page errors.
- ESM syntax and fixed asset references PASS; native browser frontend adds **zero
  application runtime dependencies**. Ruff/format, lock and package checks apply.
- Phase 3 wheel built with isolated `uv build`; outside-checkout installation
  served all presentation assets and completed a synthetic public Runtime flow
  with one dispatch and a durable receipt. External network was prohibited.

Final full-suite counts, integrity results and publication status are recorded in
[delivery report](MASTER-DELIVERY.md) and
[final verification](../evidence/phase3-ui/final-verification.json).
The known Starlette/HTTPX TestClient deprecation warning remains; it is not a test
failure and was not used to change frozen dependencies.

## Reproduce frontend checks

```powershell
node scripts/verify_presentation.mjs
node --test tests/presentation-state.test.mjs
.venv\Scripts\python -m pytest tests/test_presentation.py -q
```

Node is needed for development checks, not to serve the app. Optional browser QA
tools are development-only and can be installed under an ignored private directory:

```powershell
npm install --prefix .state-ui-qa playwright axe-core prettier
$env:PLAYWRIGHT_MODULE = ([Uri](Join-Path $PWD '.state-ui-qa/node_modules/playwright/index.mjs')).AbsoluteUri
$env:AXE_CORE_PATH = Join-Path $PWD '.state-ui-qa/node_modules/axe-core/axe.min.js'
.state-ui-qa\node_modules\.bin\playwright.cmd install chromium
node scripts/test_presentation_browser.mjs
```

Run the presentation server first. This browser script refuses non-loopback
targets and records sanitized paths/checks only. Stop the preview before running
the full pytest suite: the real ownership tests intentionally fail closed if a
competing Python consumer is alive.

## Screenshots and presentation handoff

See [overview](../evidence/phase3-ui/01-overview.png),
[AI review](../evidence/phase3-ui/02-ai-review.png),
[trust workflow](../evidence/phase3-ui/03-trust-workflow.png),
[genuine evidence](../evidence/phase3-ui/04-verified-evidence.png),
[completed simulation](../evidence/phase3-ui/09-demo-completed.png),
[Unknown](../evidence/phase3-ui/11-demo-unknown.png), and
[mobile demo](../evidence/phase3-ui/14-mobile-demo.png).
The complete 15-image set and
[browser verification](../evidence/phase3-ui/browser-verification.json) are local
artifacts. [Demo script](DEMO-SCRIPT.md) supplies a natural English 2–3 minute
walkthrough and a 60-second pitch.

Remaining scope: single-operator local demo, archived evidence rather than live
payment facts, synthetic interactive incident/provider, one genuine Sandbox
sample, no production/multi-user/HA qualification or universal exactly-once claim.
A video, upload and final competition submission have not been performed.
The development qualification records below precede the separately authorized
[publication checkpoint](PHASE3.1-PUBLICATION.md). Next: independently review the UI,
rehearse and record the English demonstration without another financial operation.

## Phase 3.1: live local proposal and recording polish

The new mode is a thin consumer addition. New cases persist an immutable planning
mode in their identity; old deterministic cases remain resumable without migration.
Payment mode is always offline, credentials are empty, the allowed Capture is
`DEMO0000000000001`, merchant is `DEMO-MERCHANT` and adapter budget remains five
seconds. No real payment routes are mounted. Model output cannot select bindings,
tools, scopes, budgets, provider environments or human grants.

`LocalProposal` reuses the frozen `ChatCompletionsAnalyst` prompt, strict six-field
Recommendation parser and existing policy. Its consumer transport fixes requests
to `http://127.0.0.1:11434/v1/chat/completions`, model `phi4-mini:latest`, streaming
off, temperature zero and 384 output tokens. The response is read in bounded
chunks with a 64 KiB envelope limit; the existing parser further bounds JSON and
explanation. Redirects, environment proxies, credentials and automatic transport
retries are disabled. The existing HTTP ceiling is 30 seconds and the model call
has a 45-second total deadline; browser planning has a 50-second envelope. These
planning limits do not change any financial execution deadline.

Inference and policy checking occur before reserving an incident or creating a
Run. Non-refund, unclear, malformed, extra-field, wrong-currency, wrong-amount,
oversized, refused, truncated, expired or unavailable results preserve the prior
safe workflow state. Only the exact synthetic USD 25.00 request is accepted. The
validated recommendation then enters unchanged Sentinel/IncidentPlanProvider and
public Runtime schema/semantic validation. The model never supplies executable
Python or an arbitrary Plan. Each human gate still requires separate confirmation.
Failure never silently switches modes; **Switch to Deterministic Demo** explicitly
creates a fresh case and retains the old record. Mode selection applies only to a
new simulation.

Evidence provenance shows the archived observation timestamp, original identities,
genuine POST 201, independent GET 200/COMPLETED, one observed POST and the durable
receipt reopened from a separate process. Both public links are pinned to the
already published freeze commit, not unpublished Phase 3 documents. The proof JSON
and hash remain unchanged. The current dashboard makes no new PayPal GET.

Recording text uses 14px reading and 13px label tokens for gates, recommendations,
evidence, forms and errors; headings and workflow labels were selectively enlarged.
The dark palette, five screens, responsive layouts, focus and reduced motion remain.
Navigation readiness alone was reproduced at opacity **0.4** with an active 220ms
entry animation. The original screenshot lacked contemporaneous animation metadata,
so its exact cause remains unproven. Capture now awaits rendered state, fonts,
finite animations/transitions, full opacity and three stable geometry frames;
no arbitrary long sleep was introduced. Stable screenshot names were retaken.

Actual Chromium qualification includes deterministic gates/receipt/reset/reload,
genuine Ollama inference followed by synthetic gates, stale/mismatched bindings,
mocked error UI and manual fallback. Five screens are rendered at **1440×900,
1920×1080 and 390×844**. See
[Phase 3.1 browser evidence](../evidence/phase3-ui/phase31-browser-verification.json),
[real local AI Plan](../evidence/phase3-ui/16-live-ollama-plan.png),
[synthetic completion](../evidence/phase3-ui/17-live-ai-simulation-completed.png) and
[mobile provenance](../evidence/phase3-ui/quality-390-evidence.png).
Negative model contracts use HTTP mocks and do not prove real inference. Final
regression, installed-wheel, integrity and audit results appear in
[Phase 3.1 final verification](../evidence/phase3-ui/phase31-final-verification.json).

**Phase 3.1 PASS; GO for independent UI review in ChatGPT Work.** Full pytest:
**535 passed**, no failures/errors/skips, 494.96 seconds; **12 Node tests passed**.
Ruff, Python/frontend formatting, syntax, lock, pip dependency checks and installed
wheel compatibility passed. The wheel test's optional AI response is explicitly
MockTransport; genuine browser inference was separately observed at **10.240636s
and 5.000926s** using actual Ollama. Both completed three independent browser gates
and one synthetic dispatch. These are two observations, not a latency guarantee.
The final synthetic receipt was reopened after stopping the prior server and
starting a new process: same Plan/Action/receipt, one dispatch, no new model call.

The preserved browser E2E has 10 checks and 11 axe scans. The added qualification
has 15 screen/viewport combinations, 17 axe scans and four explicitly mocked error
UI cases. **28 total scans, zero detected violations; 32 real screenshots**.
All measured captures had loaded fonts, full opacity and stable geometry; no
critical text clipping, page overflow or unexpected console/page errors was found.
No new genuine PayPal request occurred. SHA checks preserved all **4,058 historical
private files, 19 frozen backend files, three pinned dependency contracts and 57
installed Runtime files**. The freeze commit/tag stayed unchanged. Regenerated
timing artifacts from full regression were retained privately while preserving
pre-task historical reports. No broad cleanup, commit, push, tag or deployment.

Remaining recording considerations: model latency varies and its service must be
running before rehearsal. Proposals can fail closed; use the explicitly labeled
deterministic fallback if needed. Long Plans and evidence pages require deliberate
scrolling at 900px height and on mobile. Automated axe does not replace independent
visual/accessibility review. No video or ChatGPT Work UI review was performed here.
