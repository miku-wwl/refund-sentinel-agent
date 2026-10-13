# Refund Sentinel

**AI-Powered Refund Incident Responder** — a local merchant dashboard that turns a synthetic customer refund message into a reviewed, bounded PayPal Sandbox partial-refund proposal.

The Phase 2 backend is qualified and frozen as a **local Sandbox MVP**. One genuine NZD 5.00 partial refund is independently verified COMPLETED, with one observed Refund POST, a durable financial Receipt and terminal Succeeded v4. See [backend freeze](docs/PHASE2-BACKEND-FREEZE.md) and [sanitized qualification](evidence/phase2-freeze/verified-refund.json). Earlier phase reports and screenshots describe historical checkpoints.

AI interprets the request, amount and reason. Trusted capture/order facts and deterministic merchant policy decide whether a Plan is eligible. The merchant approves the exact Plan, separately authorizes execution, and inspects the provider's status and durable receipt. PayPal is central: the real adapter reads Payments v2/Orders v2 facts, refunds the original capture, and verifies the refund through an independent GET.

Default mode is **simulated payments + deterministic analysis**, which needs no external credentials. Real model and real PayPal Sandbox modes are independent and visibly labeled. Simulation is not a real refund.

## Reused Runtime

Execution control is provided by the external `agentic-intent-gate` version **0.2.0**, pinned to `7261fdd2f47d2b15fabe8faac527eeee37338eb1` (annotated Git release, Python 3.13, MIT). Runtime validation, Runs, exact approval, authorization, durable claiming, CAS, effect identity and duplicate/Unknown behavior are not reimplemented here. Startup verifies the installed distribution's Git provenance. One explicitly registered `SIDE_EFFECT` tool executes one refund step. Payment reads belong to this application; the bundled Demo UI/prompt is not used.

Legacy state retains the default five-second adapter budget. A trusted Sandbox-only profile provisions a fresh scope and `refund-binding-v2.exec-15s` identity with a 15-second public Gateway budget, four-second HTTP read ceiling and nine-second pre-dispatch reserve. It uses a separately bound private receipt store. Human Approval, independent Authorization and one-time financial execution permission are required afresh; old Actions/grants/effect keys are never elevated or copied. The pilot uses the direct public Gateway, because the bundled Runtime HTTP routes impose a ten-second parent deadline.

## Install and run

Python **>=3.13,<3.14** and Git are required, matching the pinned Runtime. Verified locally with Python 3.13.9 on Windows. Git access to the dependency must be available; never put tokens in URLs. `uv.lock` and the pip dependency snapshot retain the immutable release pin.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e '.[dev]' --no-deps
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
.\.venv\Scripts\refund-sentinel.exe init
.\.venv\Scripts\refund-sentinel.exe serve --port 8879 --predecessor-stopped
```

Open **http://127.0.0.1:8879**. On macOS/Linux use `.venv/bin/python` and `.venv/bin/refund-sentinel`; platform execution there has not been verified. `pip install -e '.[dev]'` can install directly from pyproject instead of the tested lock snapshot.

`init` accepts only a new empty state directory; it provisions the operator capability, persisted trusted configuration, and the explicitly fake payment fixture. Startup never creates or captures a PayPal payment. `--predecessor-stopped` confirms the previous owner stopped; do not use multiple workers or simultaneous processes against the same state. Stop with Ctrl+C before restarting. The CLI loads `.env` without changing its contents. Identical inherited values are preserved; conflicting inherited variables stop execution with `ENVIRONMENT_OVERRIDE_CONFLICT` and variable names only. Clear unintended shell overrides before retrying.

The startup example applies to an offline configuration or a fully configured Sandbox capture workflow. If your existing private `.env` enables Sandbox with no capture IDs, use the independent preflight commands below; normal `init`/`serve` still requires a valid merchant and explicit capture allowlist.

## Sandbox read-only preflight

```powershell
.\.venv\Scripts\refund-sentinel.exe check-auth
.\.venv\Scripts\refund-sentinel.exe check-capture --capture-id YOUR_ACTUAL_ALLOWLISTED_CAPTURE_ID
```

`check-auth` requires Sandbox mode and private client credentials, but no merchant/capture/model configuration or Runtime state. It prints a sanitized status and latency, validates the Bearer response, demonstrates token cache reuse, and permits only the OAuth POST. Invalid credentials, timeouts, connections and response errors have distinct codes. An empty capture allowlist causes `check-capture` to print `BLOCKED_NO_CAPTURE_ID` without any request. Protected preflight transport permits only OAuth and fixed-origin capture/order/refund GETs; all payment-changing requests are rejected before dispatch. These commands do not open or provision state databases.

On 2026-10-13, genuine Sandbox OAuth passed; capture/order reads remained blocked and no refund was authorized or attempted. See the [Phase 2.1 report](docs/phase-2.1-report.md) for redacted evidence, compatibility tests, deadline limits and required human actions. Refund endpoint tests use isolated mocks only.

## Demo workflow

1. Load `.state-offline/operator.capability` using the dashboard's local file selector. Keep it private; it remains in browser memory.
2. Choose `DEMO0000000000001` and enter: **The item arrived damaged. Please refund USD 25.00.**
3. Inspect the simulated USD 120.00 capture, merchant, recommendation, policy and exact persisted Plan.
4. Click **Approve this exact plan** (or Reject). Approval alone has no refund effect.
5. Click **Prepare durable action**, then **Authorize execution**. Neither calls the refund provider.
6. Click **Execute refund**. Inspect SIMULATED completion, refund ID, Runtime receipt and persisted observations.
7. Reload, load the capability again, and reopen the saved incident. Restart preserves the result. The read-only status button does not issue another refund.

Each capture permits **one incident** in this MVP, including rejected/interrupted cases. Repeat submission is blocked. For another isolated offline demonstration, explicitly initialize a separate directory with `--state .state-demo2`; never use a new directory to retry unresolved real refunds. A server at `.state-browser` was used for the recorded browser evidence, separate from the untouched default demo state.

## Configuration

| Variable | Default / purpose |
|---|---|
| `PAYMENT_MODE` | `offline` (simulated) or `sandbox` (real Sandbox API client) |
| `AI_MODE` | `deterministic` test fixture or `real` Chat Completions provider |
| `PAYPAL_ENVIRONMENT`, `PAYPAL_BASE_URL` | Only `sandbox`, `https://api-m.sandbox.paypal.com` accepted |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | Private Sandbox app credentials; required for sandbox mode |
| `PAYPAL_MERCHANT_ID` | Trusted merchant identity; offline default `DEMO-MERCHANT` |
| `PAYPAL_CAPTURE_IDS` | Explicit allowlist; default `DEMO0000000000001` |
| `MAX_REFUND` | Two-decimal maximum, default `100.00` |
| `SENTINEL_STATE_DIR` | Default `.state-offline`; mode/merchant/allowlist/policy persist here |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Trusted endpoint including `/v1`, configured model, optional private credential |
| `LLM_FORMAT` | `json_object` or `json_schema`; use schema mode when supported |

Real model mode sends synthetic customer text and minimal payment facts to the configured endpoint. It has no tool-calling privileges. Strict outputs reject extra keys, incorrect types, malformed money, refusal and truncation; no automatic fallback to deterministic mode. Interpretation uncertainty does not grant execution authority.

For local Ollama already running: set `AI_MODE=real`, `LLM_BASE_URL=http://127.0.0.1:11434/v1`, `LLM_MODEL=phi4-mini:latest`, `LLM_FORMAT=json_schema`, and a separate state directory. [Sandbox setup](docs/sandbox-setup.md) covers the real PayPal workflow and deliberate Orders v2 fixture preparation.

## Validate

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/pytest.xml
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/collect_evidence.py
```

Offline tests use the genuine installed Runtime, persisted fake provider calls/effects and HTTPX mock transports. They do not contact PayPal or a model. Evidence collection uses explicit synthetic offline cases. See [test report](docs/test-report.md), [implementation status](docs/implementation-status.md) and [architecture](docs/architecture.md).

## Current limits and submission status

This is a single-operator loopback Sandbox MVP. Policy accepts only USD/NZD partial refunds on completed captures without previous refunds; malformed IDs, merchant mismatches, excessive amounts and insufficient evidence are rejected. There is no live payment support, SaaS authentication, multi-step orchestration or guaranteed exactly-once remote delivery.

The default profile limits executor work to five seconds; the separately provisioned trusted Sandbox profile allows fifteen. Claim/finish are outside the adapter timer, and cooperative cancellation cannot preempt blocking Python or recall remote effects. Pending/failed/cancelled provider observations and ambiguous outcomes remain **Unknown**, with no automatic retry or reconciliation. A local receipt and provider completion are distinct. Manual checks only append read-only provider evidence. Cross-store crash consistency and remote activity from other clients have practical limits described in architecture notes.

New competition work is the product, policy, AI/PayPal clients, consumer executor, UI and tests. The shared Runtime remains untouched. Genuine local AI analysis and one human-gated PayPal Sandbox refund have been verified. The app and pinned v0.2.0 Runtime are MIT licensed. The qualified baseline is recoverable through the annotated `phase2-backend-freeze` tag once published; video recording and final competition submission remain separate work. No production-readiness or remote exactly-once guarantee is claimed.
