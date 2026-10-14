# Advanced Sandbox developer workflow

Judges should use the credential-free [presentation](PHASE3-UI-DEMO.md). This guide
describes the separate financial-capable operations app; it grants no authority
for new PayPal requests or money movements. The preserved genuine sample is already
complete and must never be replayed.

## Independent configuration

The operations CLI loads private `.env`; the presentation does not. Preserve any
existing configuration/state. Use an isolated checkout/configuration for offline
development, not a fresh directory to retry an unresolved real effect.

| Variable | Trusted configuration |
| --- | --- |
| `PAYMENT_MODE` | `offline` or `sandbox`; never Live |
| `AI_MODE` | `deterministic` or `real`, independent of payment mode |
| `PAYPAL_ENVIRONMENT`, `PAYPAL_BASE_URL` | `sandbox`, fixed `https://api-m.sandbox.paypal.com` |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | Private Sandbox app credentials |
| `PAYPAL_MERCHANT_ID` | Verified Business merchant identity; `DEMO-MERCHANT` offline |
| `PAYPAL_CAPTURE_IDS` | Explicit Capture allowlist; synthetic default only offline |
| `MAX_REFUND` | Positive two-decimal policy maximum, default `100.00` |
| `SENTINEL_STATE_DIR` | Private state; default `.state-offline` |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Trusted model endpoint including `/v1`, model, optional private key |
| `LLM_FORMAT` | `json_object` or compatible `json_schema` |

Conflicting inherited environment variables fail closed; the loader does not
overwrite private `.env`. Settings, merchant, allowlist, mode and policy bind to
persisted state. Empty or mismatched Sandbox configuration blocks startup.

## Offline operations UI on port 8879

For a new isolated **offline** developer configuration, install Python 3.13
dependencies using the README. Keep `PAYMENT_MODE=offline` and `AI_MODE=deterministic`
in its private configuration before initializing new state:

```powershell
.venv\Scripts\refund-sentinel.exe init --state .state-offline-developer
.venv\Scripts\refund-sentinel.exe serve --state .state-offline-developer --port 8879 --predecessor-stopped
```

Open **http://127.0.0.1:8879** and load that state's `operator.capability` using the
local file selector. It stays in browser memory, never URLs/localStorage. Confirm
the old owner stopped before asserting `--predecessor-stopped`. Initialization
accepts only new empty state; one process/worker owns it. Do not use an existing
financial directory for this example.

The operations workflow is analyze → exact Plan decision → durable admission →
separate authorization → execution → receipt/status. Each Capture permits one
incident, including rejected/interrupted cases. Unknown remains terminal. GET-only
manual status checking appends observations but never retries POST or changes the
Runtime outcome. The generic CLI uses the default five-second adapter profile.

## Read-only Sandbox preflight

If separately authorized to inspect a real Sandbox Capture, obtain private app
credentials and the verified Business merchant ID through the Developer Dashboard.
An independent Sandbox Personal buyer is needed for a new payment fixture.

```powershell
.venv\Scripts\refund-sentinel.exe check-auth
.venv\Scripts\refund-sentinel.exe check-capture --capture-id YOUR_ACTUAL_ALLOWLISTED_CAPTURE_ID
```

These commands perform OAuth/token exchange and, for capture verification, fixed
Capture/Order GETs. They do not open Runtime state, approve/authorize Actions, create
orders, capture payments or refund. Empty allowlists stop before the request.
OAuth alone cannot prove merchant ownership. Sanitized results omit credentials,
tokens and raw provider bodies. Never publish private buyer data or capabilities.

Eligibility requires a COMPLETED USD/NZD Capture, exact associated Order/merchant,
valid money and no reported previous refund. Missing reported history is explicitly
not a complete authoritative balance ledger; foreign clients can change PayPal
state. The historical already-refunded Capture is not eligible for another pilot
under the current conservative policy.

## Future fixtures and financial gates

Fixture preparation is developer-operated and never runs at startup. The isolated
`python -m refund_sentinel.fixture --help` describes supported commands. Local
preparation, a genuine Create Order, manual buyer checkout, Capture and the private
allowlist change are distinct steps requiring their own exact permissions. A
refund needs fresh exact Plan Approval, Action admission, independent Authorization
and separate one-time Execute permission. Neither documentation nor cleanup grants it.

For a future fixture, start `python -m refund_sentinel.fixture_callback` on the
checkout browser's computer. New preparation freezes HTTP loopback return/cancel
URLs at port 8766 and checks receiver readiness before Create. Callback navigation
does not capture/refund; explicit Order GET establishes approval. Earlier HTTPS
localhost callbacks had no TLS receiver; changing future configuration never
rewrites, recreates or retries the original Order.

The fixed Runtime permits a separately reviewed fifteen-second profile through
trusted host composition and the public Gateway, with fresh binding/scope/private
store identity and fresh human gates. There is no generic CLI profile flag. Old
Actions, grants and effects cannot gain that budget. See
[architecture](architecture.md) and the unchanged
[backend freeze](PHASE2-BACKEND-FREEZE.md) for deadline/reserve and Unknown rules.

Lost acknowledgment or ambiguous verification means preserve evidence and STOP:
no second POST, new request ID, new Action or state reset to retry. Provider request
IDs have bounded documented semantics, not universal exactly-once guarantees.

## Historical proof and AI

One genuine NZD 5.00 refund was verified on 13 October 2026 with independent GET
and durable Receipt; [the sanitized archive](../evidence/phase2-freeze/verified-refund.json)
records it. It is not today's balance or a new provider observation.

The existing local AI option is `LLM_BASE_URL=http://127.0.0.1:11434/v1`,
`LLM_MODEL=phi4-mini:latest`, `LLM_FORMAT=json_schema`, blank key. Only synthetic
request context and bounded payment facts reach the model; credentials and private
grants do not. Hosted model endpoints require HTTPS. The presentation's local
model option is independently fixed and its payment executor is always fake.
