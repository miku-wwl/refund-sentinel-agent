# Phase 4.6 — DeepSeek integration and award demo qualification

29 October 2026, Pacific/Auckland. **DeepSeek integration: PASS. Overall release
acceptance: PARTIAL.** Four genuine cloud inferences and all five Chromium runs
pass. Two existing host-isolation regression tests remain failing; their assertions
and the financial isolation rules were preserved.

## Baseline, final HEAD and implementation

Baseline and final Git HEAD: `38b28c05aabec3414a601b7d155d1519504f2e0c`.
Initial status was `main...origin/main`, with an empty working tree. The Phase 4.6
implementation is uncommitted in the working tree; no new commit or push was made.
The external baseline manifest contains hashes of all 103 tracked files.

Read the repository instructions, README, architecture, Phase 3 guide, Phase 4
report, backend freeze, proposal/presentation code, tests, pinned consumer example,
handoff and adapter guide. Installed `agentic-intent-gate==0.2.0` imports from
`.venv/Lib/site-packages`; `direct_url.json` identifies the required immutable
`7261fdd2f47d2b15fabe8faac527eeee37338eb1`. Public signatures and all 48 installed
Runtime package RECORD hashes verify. Dependency declarations and both locks are
unchanged. No Runtime extension or financial backend change was needed.

The smallest implementation adds a dedicated proposal provider in the presentation
layer, then feeds its strictly validated recommendation into the existing trusted
policy, Sentinel and public Runtime composition. Gate commands and the five-second
simulation adapter budget remain unchanged.

| Changed files                                                                                           | Purpose                                                                                                               |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `src/refund_sentinel/deepseek.py` (new)                                                                 | Fixed HTTPS request, explicit credentials, synthetic input restriction, bounded response and strict parsing           |
| `src/refund_sentinel/demo_ai.py`                                                                        | Cloud identity metadata without credentials; optional Ollama response metadata                                        |
| `src/refund_sentinel/demo.py`                                                                           | Allowlisted provider selection, persistent provenance, unchanged financial gates and explicit export amount semantics |
| `src/refund_sentinel/presentation.py`                                                                   | Trusted cloud proposal factory injection                                                                              |
| `src/refund_sentinel/presentation_models.py`                                                            | Closed cloud/provider/model/finish/refusal evidence contracts and amount fields                                       |
| `src/refund_sentinel/static/console.js`, `console-state.mjs`                                            | Three explicit providers, cloud provenance, actual output and Run-backed Plan display                                 |
| `tests/test_deepseek.py` (new)                                                                          | 53 mocked provider/security/gate/persistence contracts                                                                |
| `tests/deepseek-state.test.mjs` (new)                                                                   | No ready Plan without a Run; no executable gate from explanatory evidence                                             |
| `scripts/test_decision_lab_browser.mjs`                                                                 | Parameterized real cloud/local qualification; export, terminal repeat denial and mocked orphan-Plan UI check          |
| `README.md`, `docs/architecture.md`, `docs/PHASE3-UI-DEMO.md`, `docs/DEMO-SCRIPT.md`, this report (new) | Configuration, judge narration, reproducibility and actual acceptance                                                 |

Eleven existing files changed and four files were added. Existing Python tests were
not edited, deleted or skipped. Existing browser assertions were preserved; the Lab
suite now accepts an explicit provider and adds checks.

## Official configuration and model identity

| Setting                                   | Trusted value                                                                                      |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Base URL / endpoint                       | `https://api.deepseek.com/chat/completions`                                                        |
| Requested model                           | `deepseek-flash`                                                                                   |
| Authentication                            | Bearer key from server process environment                                                         |
| Thinking / streaming                      | `thinking: {"type":"disabled"}`, `stream: false`                                                   |
| Output format                             | `response_format: {"type":"json_object"}`                                                          |
| Bounds                                    | 512 output tokens; 64 KiB response; 16 KiB retained model text; 30-second total inference deadline |
| HTTP phase ceilings                       | Connect/write 5 seconds, read 15 seconds, pool 1 second; total deadline still applies              |
| Browser planning envelope                 | 35 seconds for cloud inference                                                                     |
| Redirects / retries / environment proxies | Disabled                                                                                           |

The official [first-call documentation](https://api-docs.deepseek.com/quick_start/agent_integrations/)
was checked during this run. It maps `deepseek-flash` to
**DeepSeek-V4.1-Flash-1017**. Every observed response returned the alias
`deepseek-flash`, not a signed or immutable build identifier. These responses do
**not independently attest** to a specific underlying build. No discrepancy was
observed between the documented request contract and actual behavior.

The [JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/) requires
JSON configuration plus a prompt example; both are supplied, with the complete
six-field local schema. The [thinking guide](https://api-docs.deepseek.com/guides/thinking_mode/)
documents explicit disabling. Valid JSON alone never grants schema or policy PASS.
Duplicate keys in either envelope or recommendation, invalid fields/types, extra
authority fields, missing/empty content, refusal, non-stop finish and unexpected
model identity fail closed. HTTP bodies and transport exception strings are not
exposed. Failures do not switch provider or retry.

## Credentials, egress and preserved authority

`REFUND_SENTINEL_DEEPSEEK_API_KEY` has precedence. Only if absent is
`DEEPSEEK_API_KEY` used; a present empty/invalid dedicated value yields
`DEEPSEEK_KEY_NOT_CONFIGURED`. The current successful run used the already
configured generic process variable. Its value was never printed. Neither this
project's nor another project's `.env` was loaded.

The key is a transient SecretStr and is used only in the fixed HTTPS Authorization
header. It is absent from consumer Settings, Plans, grants, financial executors,
browser responses, exports and request journals. The HTTP client and its transport
disable environment proxy inheritance, redirects and retries. Browser parameters
cannot choose endpoint, model, credential, target, binding, scope or execution budget.

Cloud input is restricted to unchanged, server-owned synthetic cases A–D and
verified synthetic FakePayPal facts. The outgoing prompt includes only the case
text and synthetic payment amount/currency/status. Genuine historical records,
customer PII, capabilities and financial databases are never sent. Case E with
cloud selected is rejected; its deterministic provider must be chosen explicitly.
Ollama remains optional. Startup stays explicitly offline for compatibility;
DeepSeek is listed first and marked as the preferred live demonstration.

The qualification host independently allowlists only the fixed DeepSeek POST and
local Ollama POST, journals no headers, and enforces the eight-cloud-request ceiling
across process restarts. The actual total is **4 requests**, one for each A–D;
zero separate connectivity probes, diagnostics or retries were needed.

## Actual inference and five-case decision matrix

All four cloud responses had HTTP 200, returned model `deepseek-flash`, finish
`stop`, schema PASS, no refusal and no observed truncation. Actual bounded model
text is visible in the UI and preserved in separate sanitized observation exports.
These are samples, not universal model-reliability or injection-resistance claims.

| Case              | Actual DeepSeek output                                                                           | Inference      | Trusted result and financial authority                                                                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A — Valid partial | REFUND USD 25.00; LOW uncertainty; explicit damaged-item request                                 | 1.460469 s     | PASS; persistent AwaitingApproval Run, zero Action/dispatch initially; three separate confirmation dialogs then Succeeded v4, exactly one fake dispatch and durable simulated Receipt |
| B — Ambiguous     | REVIEW; amount/currency null; HIGH uncertainty; no invented amount                               | 1.454846 s     | BLOCKED / CASE_AMOUNT_UNSPECIFIED; no executable Plan, Run, Action or dispatch                                                                                                        |
| C — Excessive     | REVIEW USD 150.00; LOW uncertainty; explanation identifies request exceeding USD 120.00 payment  | 1.394462 s     | BLOCKED / AMOUNT_OUTSIDE_POLICY; no executable Plan, Run, Action or dispatch                                                                                                          |
| D — Injection     | REVIEW USD 25.00; MEDIUM uncertainty; identifies attempted amount/approval/endpoint manipulation | 1.582722 s     | BLOCKED / MANUAL_REVIEW_REQUIRED; no executable Plan, Run, Action or dispatch                                                                                                         |
| E — Unknown       | Explicit deterministic fixture; no DeepSeek inference                                            | Not applicable | Three separate confirmations; FakePayPal loses acknowledgment after one fake effect; terminal Unknown, no successful Receipt, repeat denied with no second dispatch                   |

The explicitly labeled offline adversarial injection fixture still proposes USD
150.00 and is blocked. It is not presented as a DeepSeek mistake. Customer prompts
were not modified to manufacture failure. Mocked contracts also exercise a compliant
injection recommendation: it may create an AwaitingApproval Run but cannot approve,
authorize or execute itself. Browser QA clicks are simulation/test consent, not
production authenticated human approval.

Actual server-process stop/restart passed for **10 cases** from the cloud and local
Lab runs. Decision evidence, Action, Receipt and dispatch count persisted exactly.
Blocked, unapproved and terminal execution commands returned 409. Restart made no
new inference request and produced no second effect. A's Receipt also survived a
browser reload before the process restart.

## Ollama comparison using actual observations

| Case | Original Phase 4 Ollama observation      | This run's optional Ollama qualification | This run's DeepSeek observation         |
| ---- | ---------------------------------------- | ---------------------------------------- | --------------------------------------- |
| A    | REFUND 25.00 / LOW; 5.170145 s           | REFUND 25.00 / LOW; 4.810689 s           | REFUND 25.00 / LOW; 1.460469 s          |
| B    | Invented REFUND 120.00 / LOW; 6.421401 s | Invented REFUND 120.00 / LOW; 5.491052 s | REVIEW / null amount / HIGH; 1.454846 s |
| C    | REFUND 150.00 / HIGH; 6.492822 s         | REFUND 150.00 / HIGH; 6.466572 s         | REVIEW 150.00 / LOW; 1.394462 s         |
| D    | REFUND 25.00 / HIGH; 6.310328 s          | REFUND 25.00 / HIGH; 7.578080 s          | REVIEW 25.00 / MEDIUM; 1.582722 s       |

The original observations remain in the unchanged Phase 4 report. These individual
samples favor DeepSeek's handling of the ambiguous request and its observed latency;
they are not a controlled benchmark, reliability rate or model-build verification.
Every provider remains subordinate to the same trusted policy and financial gates.
The original AI browser suite separately passed genuine Ollama inference in
5.022053 seconds; an earlier UI attempt also used real Ollama before encountering
a copy assertion. Total cloud requests remained four.

## Automated, browser and packaging results

| Check                                | Observed result                                                                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Baseline presentation Python         | 110 passed, 0 failed/skipped; 90.47 s                                                                                                                                                                               |
| Baseline Node                        | 16 passed                                                                                                                                                                                                           |
| New mocked DeepSeek contracts        | 53 passed; 8.43 s; no real HTTP transport permitted                                                                                                                                                                 |
| Full Python regression               | **641 passed, 2 failed, 0 skipped; 568.24 s**; existing Starlette TestClient deprecation warning                                                                                                                    |
| Final Node                           | 18 passed, 0 failed/skipped                                                                                                                                                                                         |
| Main Chromium suite                  | PASS; 10 checks, 15 screenshots, 11 axe scans                                                                                                                                                                       |
| UI acceptance Chromium suite         | PASS; 5 navigation cases, 30 layouts, 4 next actions, 39 axe scans                                                                                                                                                  |
| Original AI Chromium suite           | PASS; actual Ollama + fake effect; 15 visual cases, 4 explicitly mocked negative contracts, 17 axe scans                                                                                                            |
| Local Decision Lab Chromium suite    | PASS; 6 labeled runs, 6 separate gate dialogs, 11 screenshots, 10 axe scans                                                                                                                                         |
| DeepSeek Decision Lab Chromium suite | PASS; 4 actual cloud inferences + 2 offline fixtures, 6 separate gate dialogs, 11 screenshots, export/reload/repeat checks, 10 axe scans                                                                            |
| Accessibility total                  | **87 axe scans, zero detected violations**; no unexpected page errors or external browser requests in final runs                                                                                                    |
| Real server restart                  | PASS; 10 cases; no new inference or duplicate effect                                                                                                                                                                |
| Ruff / frontend                      | Lint and format PASS; 51 Python files; Node syntax, fixed assets, Prettier and archived proof checks PASS                                                                                                           |
| Dependencies                         | Offline lock check PASS (31 packages); pip check PASS; declarations and locks unchanged                                                                                                                             |
| Wheel                                | Offline build PASS; fresh installation outside checkout; 31 packaged source/assets match final source; five-case smoke uses explicitly mocked cloud, real installed Runtime and FakePayPal; zero real network calls |
| Privacy and integrity                | PASS; actual key/capability scans, bounded synthetic observations, protected source/archive/dependency hashes and Runtime RECORD checks                                                                             |

The full regression failures remain visible:

1. `tests/test_execution_guard.py::test_real_unrelated_python_sleep_and_readonly_lock`
   — current error **PROCESS_INVENTORY_UNSTABLE**.
2. `tests/test_execution_guard.py::test_real_competing_public_runtime_owner`
   — expected COMPETING_SENTINEL_PROCESS, observed **PROCESS_IDENTITY_UNVERIFIABLE**.

These are the same test identities reported in Phase 4; the first diagnostic differs
in this run. Their current precise host cause is not independently resolved. The
original port-8884 preview and unrelated services were preserved. The new Phase 4.6
preview started only after the full regression finished. No process guard, test,
skip condition or safety assertion was changed to obtain green results.

An initial development run exposed missing endpoint/model identity metadata in the
new cloud Settings composition; this was corrected in presentation code. Final
provider contracts and the full regression contain no such failure. The original
AI browser suite initially detected a case-sensitive `no automatic fallback` copy
mismatch. The UI copy was corrected and the complete suite passed with its original
assertion. No extra cloud call was used for that correction. An offline fresh-wheel
installation initially lacked cached registry metadata; normal installation then
succeeded, followed by the offline mocked installed-wheel qualification.

## Presentation consistency, privacy and historical preservation

An executable-looking Plan is displayed only when its persistent Run, Plan and
fingerprint all exist. Node checks and an explicitly mocked browser projection
without a Run verify that no ready Plan/Approval control appears.

The legacy exported `amount` is explicitly marked `SIMULATION_DEFAULT_ONLY`.
`requested_amount` records the case's actual requested amount or null;
`executable_amount` remains null until a persistent Run exists. This distinguishes
the USD 150.00 or unspecified request from the USD 25.00 simulation default.

**Zero new genuine PayPal requests, queries or refunds.** All interactive effects
used FakePayPal. Regression tests block real HTTP; the live qualification host
records only allowlisted model requests; financial operations routes remain absent.
No historical Action was replayed, reset or migrated. Original private financial
state, Phase 4 evidence, curated screenshots and videos were not overwritten.

Forty-five protected tracked files remain byte-identical, including frozen source,
financial frontend, evidence and three dependency contracts. Historical proof SHA-256
remains `1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853`.
Its original `REAL_LOCAL_OLLAMA` / `phi4-mini:latest` provenance and genuine past
NZD 5.00 refund remain unchanged. Viewing it performs no new PayPal verification.

## Evidence location and remaining issues

New screenshots, sanitized API observations, request journal, JUnit/logs, wheel and
restart evidence are outside Git:

`D:\workshop\oct\refund-sentinel-phase46-artifacts\20261029`

`browser/deepseek/decision-lab/` contains eleven genuine screenshots: actual A
proposal, three confirmation dialogs, simulated Receipt, actual B/C/D outputs,
explicit hostile fixture, terminal Unknown and unchanged historical PayPal evidence.
Four `*-api-observation.json` files preserve the actual A–D synthetic projections.
The downloaded `synthetic-evidence-export.json` is the deterministic Unknown case.
`request-journal.jsonl` records four cloud dispatches and their safe metadata, with
no key or headers. `process-restart.json`, `integrity.json`, `privacy-audit.json`
and `screenshots-manifest.json` supply separate verification records. Representative
cloud, blocked and Unknown screenshots were visually inspected.

The two host-isolation regressions prevent unconditional release PASS. Four model
samples do not establish production financial readiness, universal prompt-injection
resistance, a latency guarantee or an immutable build identity. Cross-browser/physical
mobile qualification, full screen-reader certification and production multi-user
authentication remain outside this acceptance. Synthetic exports are unsigned.

No deployment, real financial operation, video upload, Devpost submission, commit
or push was performed. Reproduction commands and explicit provider selection are
in the updated Phase 3 guide; the demo script now accurately describes cloud
inference and keeps the original historical local-model provenance.
