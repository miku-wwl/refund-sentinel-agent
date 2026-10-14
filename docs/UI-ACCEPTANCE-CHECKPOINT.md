# Safe pre-cleanup UI acceptance checkpoint

14 October 2026. Baseline: `096b89eff51db9aa2dc5a6b04fe3ff19506a8c63`.
This checkpoint preserves the completed Phase 3.1 milestone before incremental
Submission Cleanup. No cleanup, deletion of legacy project files, deployment or
genuine PayPal operation is part of this checkpoint.

The [acceptance report](UI-ACCEPTANCE-FIX-REPORT.md) retains the original manual
browser review and its measurements. The
[checkpoint verification summary](https://github.com/miku-wwl/refund-sentinel-agent/blob/86a179fc6ca02568a849c51e765d6dca123dced7/evidence/ui-acceptance/checkpoint-validation.json)
records the fresh tests below; the older screenshot/model measurements remain
historical evidence and are not relabeled as this rerun.

## Reviewed publication scope

Initial inspection found 52 tracked files with raw byte differences: 47 had only
line-ending differences and five had content changes. Git's normalized diff
showed those five content changes. There were 186 untracked files. Every changed
or untracked file was read and classified; JSON/XML evidence was parsed, and all
45 candidate screenshots received visual and supplemental Windows OCR review
across 111 image tiles. OCR is supplemental, not a guarantee against disclosure.

The explicit checkpoint set contains **62 files: four modified and 58 new**.

| Category | Modified | New | Contents |
| --- | ---: | ---: | --- |
| Presentation source | 2 | 0 | `console.js`, `console.css` |
| Browser QA scripts | 1 | 1 | `presentation_ready.mjs`, `test_ui_acceptance_browser.mjs` |
| README | 1 | 0 | Links to acceptance and checkpoint documentation |
| Documentation | 0 | 2 | Acceptance report and this checkpoint |
| Sanitized acceptance evidence | 0 | 55 | 45 screenshots and ten JSON summaries/manifests |
| **Total** | **4** | **58** | **62** |

All four fixes remain: skip-link activation preserves the screen/history;
narrow layouts and enlarged text reflow; local AI and simulated payment labels
are accurate; and the same next-step control is visible on desktop. The narrow
evidence table has a keyboard focus target and visible focus indication.
Approval, Authorization, execution handlers and the financial backend are unchanged.

No line-ending-only edit is staged. README was among the initial 47; it is now
included for the reviewed documentation links. The other 46 are untouched.
The existing `.gitignore`
and `AGENTS.md` edits remain local. Another **130 untracked files** are excluded:
129 older diagnostic evidence files and one personal network investigation report.
They are retained, not deleted. `.env`, private `.state-*` directories, original
financial databases, capabilities, raw provider records, original private human
gate records, logs, caches and environments are excluded from publication.
The gate screenshots show only synthetic simulation dialogs; the historical
Receipt screenshot contains only previously published, sanitized Sandbox proof.

## Fresh qualification

| Check | Actual result |
| --- | --- |
| Full pytest | **535 passed**, 0 failures/errors/skips, 533.31 seconds; one existing Starlette/HTTPX deprecation warning |
| Node | **12 passed**, 0 failures |
| Chromium | 156.0.8078.4; ten preserved E2E checks, five skip/history cases, three unknown-route cases, 30 mobile layouts, four desktop action/mode cases |
| Model/browser workflow | Real `phi4-mini:latest`, HTTP 200, **16.348125 seconds**; three separate simulation confirmations, Succeeded v4, one fake dispatch, durable SIMULATED_PROVIDER Receipt after reload |
| Additional AI UI checks | 15 visual cases and four explicitly mocked negative-model contracts |
| Accessibility | **67 axe scans, zero detected violations** |
| Terminal-state safety | Unknown/Failed survive refresh/reload without replay, reconciliation or successful Receipt claims |
| Ruff / Python format | PASS; 46 Python files formatted |
| Prettier / frontend syntax and assets | PASS |
| Dependencies | Offline lock check PASS, 31 packages; pip check PASS; official npm QA-tool audit reports zero vulnerabilities |
| Package | Offline isolated wheel build PASS; all 29 packaged source/assets byte-match the working source; immutable Runtime pin retained |
| Integrity | 4,058 original private files, 19 frozen backend files, three dependency contracts and 57 installed Runtime files unchanged |
| Privacy | Screenshot/metadata review PASS; full staged tree of 220 files and 301 candidate Git objects (blobs, trees, commits and annotated tag) scanned without sensitive findings; historical object/path audit also passed |

An initial non-isolated wheel attempt lacked `setuptools` in the application
environment; the normal isolated offline build succeeded from cached build
dependencies without changing application dependencies. The first browser launch
was NOT RUN because its matching binary was absent; installing that binary in a
new ignored D-drive QA cache enabled all three successful browser suites. Both
initial attempt logs are retained privately.

The tests prohibit genuine HTTP payment transport. Browser testing used a new
synthetic presentation state on loopback, separate from original financial state;
the presentation factory ignores `.env`, uses FakePayPal and exposes no financial
execution routes. Local Ollama inference was genuine. All payment executions were
simulated. The original port-8880 preview and earlier synthetic records are retained.

Test-generated mock timing records were saved separately, then the original 34
evidence files were restored byte-for-byte. No private financial state was reset.
The installed Runtime remains **0.2.0**, imported from the installed environment,
at `7261fdd2f47d2b15fabe8faac527eeee37338eb1`; its public API was checked and the
shared core checkout is clean. `phase2-backend-freeze` still peels to
`04fac090b6aa0a77ef1c50b9e6b451404fccc58f` locally and remotely.

## Reproduce safely

Use a fully qualified Python interpreter for Windows process-identity tests.
Stop the preview before full pytest; do not run other Python checks concurrently
with its real owner-lock tests. Store test output in a new ignored QA directory.

```powershell
$qa = Join-Path $PWD ('.state-checkpoint-qa-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $qa | Out-Null
$qualifiedPython = (Resolve-Path '.venv/Scripts/python.exe').Path
& $qualifiedPython -m pytest -q --junitxml="$qa/full-tests.xml"
node --test tests/presentation-state.test.mjs
.venv\Scripts\ruff.exe check src tests scripts
.venv\Scripts\ruff.exe format --check src tests scripts
uv lock --check --offline
& $qualifiedPython -m pip check
uv build --wheel --offline --out-dir "$qa/wheels"
npm install --prefix "$qa/tools" playwright axe-core prettier
$env:PLAYWRIGHT_MODULE = ([Uri](Join-Path $qa 'tools/node_modules/playwright/index.mjs')).AbsoluteUri
$env:AXE_CORE_PATH = Join-Path $qa 'tools/node_modules/axe-core/axe.min.js'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $qa 'browsers'
node "$qa/tools/node_modules/playwright/cli.js" install chromium --only-shell
```

Start the independent presentation server against a **new synthetic state** in a
separate terminal. Never use the financial operations app for browser QA:

```powershell
$qualifiedPython = (Resolve-Path '.venv/Scripts/python.exe').Path
$browserQa = Join-Path $PWD ('.state-browser-checkpoint-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $browserQa | Out-Null
Push-Location $browserQa
try { & $qualifiedPython -m refund_sentinel.presentation --port 8881 }
finally { Pop-Location }
```

From the QA directory, use absolute script paths so generated screenshots and
results stay local and earlier published evidence is not overwritten:

```powershell
$projectRoot = $PWD.Path
$env:SENTINEL_PRESENTATION_URL = 'http://127.0.0.1:8881'
Push-Location $qa
try {
  node "$projectRoot/scripts/test_presentation_browser.mjs"
  node "$projectRoot/scripts/test_ui_acceptance_browser.mjs"
  node "$projectRoot/scripts/test_presentation_ai_browser.mjs"
} finally { Pop-Location }
```

Live-AI qualification needs local Ollama with `phi4-mini:latest`. The artifact
manifest hashes **published Git blob bytes**, including normalized LF for JSON,
not platform-dependent CRLF checkout bytes. Verify text artifacts using the bytes
from `git show HEAD:evidence/ui-acceptance/<filename>`.

Before publication, the complete staged tree and final commit's reachable Git
objects must pass the credential/private-data scanner; `git diff --cached --check`
must pass, and explicit staging must match the reviewed file list exactly. A
sensitive finding blocks push. Normal push must preserve the freeze tag and
verify local/tracking/live remote commit equality. No force push or tag movement.

200% text uses QA styles in real Chromium, not native Firefox text-only zoom.
Physical mobile, a complete screen-reader/WCAG certification, fresh dependency
environment installation and a narrated recording are NOT RUN. No current
PayPal balance or production reliability claim is made. **GO for separately
scoped incremental Submission Cleanup after the verified checkpoint push.**
