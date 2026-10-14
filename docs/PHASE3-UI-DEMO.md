# Presentation setup and verification

This is the current guide for the independent five-screen presentation. The
unchanged [financial backend](PHASE2-BACKEND-FREEZE.md) remains available separately.

## Start and choose a mode

Python 3.13 and Git are required; first installation needs dependency access.

```powershell
uv sync --frozen --all-extras
.venv\Scripts\python -m refund_sentinel.presentation --port 8880
```

Open **http://127.0.0.1:8880**. No PayPal credentials, `.env`, buyer login or operator
capability is needed. The default Deterministic Demo works offline after install.
For optional genuine inference, provide local Ollama `phi4-mini:latest` at
`http://127.0.0.1:11434`, then select Local AI Demo and load a new sample.
This repository does not install Ollama or download models.

Local AI interprets the synthetic damaged-item request for **USD 25.00** from a
synthetic **USD 120.00** payment. A fixed-loopback transport reuses the consumer's
strict parser and trusted policy. Output is bounded to 64 KiB with a 45-second
total inference limit; the browser has a 50-second planning envelope. Invalid,
uncertain, wrong-money, refused or unavailable output does not grant authority.
Manual fallback creates a new deterministic case; automatic fallback is absent.

## Five screens and gates

| Screen | Behavior |
| --- | --- |
| Overview | Product entry and archived qualified Sandbox result |
| AI refund review | Preserved historical genuine recommendation, exact Plan and fingerprint |
| Trust workflow | Approval, independent Authorization and one-time execution explanation |
| Verified evidence | Historical HTTP results, provenance and durable Receipt |
| Interactive demo | Deterministic or live local proposal; simulated provider execution only |

In the interactive screen, confirm **Approve Plan**, then **Authorize Action**,
then **Execute Simulation** in three separate dialogs. The first two leave dispatch
count at zero. A successful third step produces one fake effect and a durable
SIMULATED_PROVIDER Receipt. Reload preserves state. Unknown/Failed are terminal:
no replay, reauthorization, successful Receipt claim or reconciliation is offered.
Reset creates a new scope and retains old cases; it never copies grants.

The next decision is visible on the qualified desktop sizes. Skip links preserve
the active route/history and focus main. The 320/360/390px mobile layouts reflow;
the evidence table has a keyboard focus target. Labels distinguish genuine model
inference from simulated payments, including before a model has responded.

## State and HTTP boundary

The presentation factory ignores `.env`, forces FakePayPal and stores cases only
under `.state-presentation-demo/` in its working directory. Existing non-demo state
is rejected. The browser cannot choose a private directory, real Capture/merchant,
credentials, scope or adapter deadline. Windows owner-lock resume is qualified.
One process owns each case; do not run multiple controllers against the same state.

Only fixed assets and typed `/presentation/proof`, `/presentation/demo`,
`/presentation/demo/generate` and `/presentation/demo/command` routes are exposed.
Real `/api/incidents/` routes and operations assets return 404. Simulation POSTs
require the local header/origin boundary; HttpOnly same-site cookies, CSP, no-store
and sanitized errors apply. The original archive is checked against SHA-256
`1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853`.

Planning is independent of the unchanged default five-second execution profile.
Provider lookup and adapter receipt persistence must finish before its deadline;
a late receipt does not elevate Unknown. Historical genuine evidence belongs to
the separately reviewed fifteen-second Sandbox profile, never to this simulation.

## Development verification

Run the full Python suite with the qualified interpreter and **preview stopped**.
Do not run other Python tools concurrently with the real owner-identity tests.
All HTTP payment tests use ASGI/FakePayPal/MockTransport and forbid real transport.

```powershell
.venv\Scripts\python.exe -m pytest -q
node --test tests/presentation-state.test.mjs
node scripts/verify_presentation.mjs
.venv\Scripts\python.exe scripts/check_submission.py
.venv\Scripts\ruff.exe check src tests scripts
.venv\Scripts\ruff.exe format --check src tests scripts
uv lock --check --offline
.venv\Scripts\python.exe -m pip check
uv build --wheel --offline
```

Browser dependencies are QA-only, not application runtime dependencies:

```powershell
$projectRoot = $PWD.Path
$qa = Join-Path $PWD '.state-qa'
npm install --prefix "$qa/tools" playwright axe-core prettier
$env:PLAYWRIGHT_MODULE = ([Uri](Join-Path $qa 'tools/node_modules/playwright/index.mjs')).AbsoluteUri
$env:AXE_CORE_PATH = Join-Path $qa 'tools/node_modules/axe-core/axe.min.js'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $qa 'browsers'
node "$qa/tools/node_modules/playwright/cli.js" install chromium --only-shell
$env:SENTINEL_PRESENTATION_URL = 'http://127.0.0.1:8880'
$env:SENTINEL_QA_OUTPUT_DIR = Join-Path $qa 'results'
node "$projectRoot/scripts/test_presentation_browser.mjs"
node "$projectRoot/scripts/test_ui_acceptance_browser.mjs"
node "$projectRoot/scripts/test_presentation_ai_browser.mjs"
```

All browser and mock-timing outputs default to ignored `.state-qa/`; the optional
`SENTINEL_QA_OUTPUT_DIR` chooses a new local QA destination. `collect_evidence.py`
also defaults to ignored `.state-qa/consumer-evidence`, with an explicit `--output`
override. Generated reports never overwrite the curated public archive by default.

Run those browser suites against a fresh synthetic presentation server, never the
advanced operations app. Set up a separate ignored working directory before
starting the presentation if preserving an existing demo session. Actual model
qualification needs Ollama; negative model contracts are explicitly mocked.

## Evidence and rehearsal

[Curated evidence](../evidence/submission/README.md) identifies genuine versus
simulated screenshots and the concise qualification summary. Earlier measurement
matrices remain in the pinned pre-cleanup Git checkpoint. The
[demo script](DEMO-SCRIPT.md) supplies English narration; rehearse inference and
review time before recording. No completed recording duration is claimed.

Text magnification uses QA styles in actual Chromium, not native Firefox text-only
zoom. Physical mobile, full screen-reader certification, other browser engines and
cross-platform ownership are unqualified. This is a local Sandbox MVP, not hosted
SaaS, production multi-user authentication or an exactly-once guarantee.
