# Phase 4.7 browser rehearsal and recording preflight

30 October 2026, Pacific/Auckland. **Actual IAB rehearsal: BLOCKED.
Gate 2 summary: PARTIAL.** Three separate headless Chromium suites pass, but they
do not satisfy the requirement to interact with the real ChatGPT Desktop Work IAB.

## Actual browser capability

The documented first inventory call was `await cua.getState()`. It returned no
browsers and this error: **The browser access host is unavailable**. One documented
safe recovery attempted a fresh visible `iab` tab for the existing localhost preview;
it returned the identical error. No stale tab was repeatedly operated. An asynchronous
request asked the owner to restore the right-side browser through normal app controls.
No restoration was confirmed before this report.

The desktop application inventory and browser capability are separate observations.
An open ChatGPT window does not establish a functioning browser bridge. Native
desktop input was not used to bypass the missing bridge. No alternate browser or
headless run is relabeled as IAB rehearsal or recorded IAB footage.

## Correct application and source

The initial listeners were loopback 8884 (PID 47108) and 8886 (PID 7300), started
on 29 October before this work. Both were preserved, as were the CrowdQuest services.
Their imported backend code cannot be assumed to reflect these edits.

The Phase 4.7 preview uses **http://127.0.0.1:8887/#demo**, launched from the actual
Windows checkout with a new synthetic root under the artifact directory. Its
`preview.py` does not launch the financially capable operations app. It permits
only fixed DeepSeek proposal egress, with a persistent four-request cap; other
HTTPX egress is denied. No cloud inference has actually been requested.

`preview-identity.json` records PID, port, baseline Git HEAD and startup source
hashes. The Python source hashes match the running code's startup snapshot.
Frontend assets are served from files; final integrity checks compare their actual
HTTP response hashes with the final source files. HEAD remains
`3811725cec176012b883161140b3a6a529bb69d6` plus the explicit uncommitted Phase 4.7
changes, not a new published revision.

The new preview was stopped through its own scoped stop marker and restarted once.
`process-restart.json` verifies eight existing synthetic cases retained identical
decision, Run, fingerprint, Action, Receipt and dispatch projections. The three
fake dispatches present before restart remained three after restart, with no model
call or automatic effect replay. Later QA created new, separate synthetic cases.

## Required IAB observations

| Required scene                                             | Phase 4.7 actual IAB result                   |
| ---------------------------------------------------------- | --------------------------------------------- |
| A, genuine DeepSeek response/latency and visible gates     | NOT_RUN — IAB unavailable                     |
| B, actual ambiguous-model output and policy block          | NOT_RUN — IAB unavailable                     |
| E, deterministic Unknown with visible confirmations/reload | NOT_RUN — IAB unavailable                     |
| Historical genuine PayPal proof viewed in IAB              | NOT_RUN — IAB unavailable                     |
| Twelve named IAB screenshots in the master prompt          | NOT_CREATED                                   |
| Estimated duration of a measured IAB rehearsal             | NOT_MEASURED; storyboard target only is 175 s |

**Actual DeepSeek calls: 0 of 4 permitted.** No fresh A/B model response or latency
is claimed. Mocked provider contracts and historical Phase 4.6 observations are
not genuine new inference. Remaining request budget is four for future rehearsal
and recording, normally A+B in each. Never repeat inference for cosmetic reasons.

## Separate automated Chromium qualification

Browser: Chromium **156.0.8078.4**, launched headlessly with QA dependencies already
installed outside the frozen manifest. Tests use the new 8887 preview. Genuine
browser clicks and actual rendering are tested here, but this is not the IAB.

| Final suite                                       | Actual result                                                                                                                               | Timed command |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `node scripts/test_presentation_browser.mjs`      | PASS; 10 checks, 15 screenshots, 11 axe scans; completed/Unknown/rejected deterministic simulations and real UI confirmations               | 25.7275 s     |
| `node scripts/test_ui_acceptance_browser.mjs`     | PASS; five navigation cases, 30 layouts, four next actions, 39 axe scans                                                                    | 49.7599 s     |
| External `node <artifacts>/readiness-browser.mjs` | PASS; one actual deterministic READY result plus three explicitly mocked stale-Run failure/interruption/blocked projections; four axe scans | 6.8290 s      |

The final accepted set has **54 axe scans, zero detected violations**, no unexpected
page errors, no external browser requests and no genuine cloud or PayPal calls.
Final main/layout outputs are under `browser/accepted-main/presentation` and
`browser/accepted-ui/ui-acceptance`; final failure-state outputs are under
`browser/readiness-stable-final`. Exact commands, environment and durations are
preserved in the suite scripts, logs and `browser-runs.jsonl`.

The new failure-state script initially captured a stale AwaitingApproval title;
the product title/progress calculation was corrected. A subsequent early scan
reported color-contrast before the new harness required completed rendering.
The project already has a finite-animation/font/geometry readiness helper; the
new harness now uses that same helper before every axe scan and screenshot.
Final captures record opacity 1, loaded fonts, three stable frames and no horizontal
overflow. No axe rule was disabled and the original failure logs were preserved.
The precise transient state of the earlier closed browser was not retained, so
that earlier contrast observation is not retrospectively declared a proven CSS
defect or a proven environmental failure.

Representative images were actually viewed: persistent READY, failed/interrupted
readiness, simulated Receipt, terminal Unknown and historical proof. The corrected
failure screenshots show no approval/generation/execution controls, no policy PASS
badge and no residual AwaitingApproval heading. They visibly say no executable
authority and no automatic retry. Critical text, source labels and panels are
readable in these samples; no clipped modal or exposed key/capability was observed.
This is sample visual review, not a claim that every automated screenshot received
an individual human review.

The required genuine A/B/E IAB rehearsal, twelve specific IAB screenshots and
measured storytelling duration remain unverified. Automated simulation consent
is test consent; it does not prove production authenticated human approval.

## Financial isolation and provenance

The final preview count is recorded separately in `integrity.json`: nine fake
dispatches across three independent main QA runs, with one dispatch per executed
synthetic case. There are six persisted fake effects; three definitive rejections
have no refund effect. Readiness tests create a Run but never admit or execute an
Action. Repeated execution and terminal Unknown remain denied. The installed-wheel
and regression tests use their own isolated fake stores, not this preview ledger.

New genuine PayPal requests from this task: **zero**, including archive reads.
The presentation serves a typed, hash-pinned archive and no financial operations
routes. Regression real transports are blocked and preview financial egress is
denied. This measurement concerns Phase 4.7 executions, not traffic in unrelated
pre-existing processes. The read-only archive retains the genuine historical
NZD 5.00 refund from NZD 20.00, POST 201, independent GET 200 and original local
Ollama provenance. It is never relabeled as the interactive USD 25.00 simulation
or as a DeepSeek-generated historical proposal.

## Recording preflight and next action

OBS **32.2.2** is installed at
`D:\Program Files\obs-studio\bin\64bit\obs64.exe`. The desktop inventory initially
reported it not running. Computer Use inventory is available; FFmpeg and ffprobe
were not found on PATH. That does not establish that no copy exists elsewhere.
Approximately 170 GB was free on D: at preflight.

No valid IAB capture target could be selected. No OBS scenes, profiles, permissions
or unrelated recording sessions were changed. A short actual test recording,
playback inspection, silent 1080p/30 capture and MP4 decode were **NOT_RUN**.
Therefore **recording capability = BLOCKED**; Gate 4's summary is PARTIAL for
installed-tool discovery only. Installed OBS is not proof of recording capability.

`Recording-Manual.md` supplies the exact safe OBS procedure, including preserving
existing scenes, disabling audio in a separate profile, a 5–8 second test and actual
playback/technical QA. `RefundSentinel_Phase47_Shotlist.md` specifies the real scene
and confirmation sequence. Both are in the external artifact directory. Final
recording remains NOT_RUN until Gates 1, 2 and 4 pass. Restore the IAB bridge and
obtain clean-host engineering qualification without stopping current services.
