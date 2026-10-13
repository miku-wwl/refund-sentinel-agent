# Phase 2.3.4 — HTTP timeout fix and Sandbox E2E recovery

**Conclusion: BLOCKED / NO-GO for a new genuine refund pilot.** Consumer code and
offline qualification pass, but the limited real read-only qualification did not
fully pass: the second Order GET returned no HTTP response and ended with
`CAPTURE_READ_UNCERTAIN` after **2.007682 s**. No further PayPal request, new candidate
or financial execution followed that failure. This is a payment-read failure,
not a failed or ambiguous PayPal refund.

## Exact root cause and scoped fix

The previous original Action's genuine failure is retained in
[Phase 2.3.3](phase-2.3.3-refund-e2e.md): HTTPX **ReadTimeout** during the Gateway's
Order GET, measured **1.136642 s**, with configured read limit **1.1 s**. Gateway wall
time was **1.331788 s**; its immutable five-second adapter budget was not exhausted.
The scalar `EXECUTION_HTTP_TIMEOUT_SECONDS=1.1` was used for all four HTTPX phases,
and the old private runner explicitly restored that scalar after external preflight.

HTTPX phase limits apply to connection acquisition, connection establishment, writes
and reads; read timeout limits waiting for a data chunk, rather than whole-workflow
elapsed time. The unchanged Runtime independently bounds the complete awaited
adapter operation. [HTTPX timeout documentation](https://www.python-httpx.org/advanced/timeouts/).

Only consumer code changed:

- `src/refund_sentinel/paypal.py`: introduced `EXECUTION_HTTP_TIMEOUT` with
  **connect 1.1 / read 2.0 / write 1.1 / pool 1.1 seconds**. The observed successful
  1.135-second read and requested 1.1–1.8-second offline read range justified a
  larger read allowance. Other phases were not increased to five seconds.
- `paypal_http_attempt` binds the **public** AttemptContext using a ContextVar.
  `_roundtrip` recomputes remaining time from its public monotonic deadline and
  caps each HTTPX phase for each request. Per-request kwargs avoid changing the
  shared client's limits during parallel reads. The context reaches OAuth, both
  Capture/Order child tasks, Refund POST and independent Refund GET. It is reset
  on exit and the transport rechecks expiry/cancellation after HTTPX preparation.
- `src/refund_sentinel/integration.py`: `RefundExecutor.execute` enters that context
  and delegates to the existing execution body. Fresh payment validation, parallel
  GETs, OAuth/cache/connection reuse, synchronous durable dispatch evidence,
  post-persistence deadline checkpoint, independent verification and receipt
  persistence remain intact. No financial retry was added.

The read ceiling is not reserved execution time or a guarantee of completing the
remaining POST/GET. Every later request is capped again by its then-remaining
budget. The original public Runtime supplies the deadline, performs durable
claiming and cancellation, and was not patched, bypassed or replaced. Historical
one-shot runners and their source manifests were preserved and are not reused.

## Offline full-path qualification

Added `tests/test_phase234_timeouts.py` with **9 tests**, including eight full public
Gateway scenarios and context isolation/remaining-budget checks. Each scenario
uses an isolated MockTransport, synthetic state, separate SQLite simulated remote
effects and normal synthetic Approval/Authorization. The handler models HTTPX's
per-read-phase limits explicitly: MockTransport does not enforce socket timeouts
itself. Delays and simulated refund results are assumptions, not genuine PayPal
Refund POST performance.

| Mock scenario | Gateway s | Adapter s | Claim/finish + gateway overhead s | Final state | Mock refund POSTs |
|---|---:|---:|---:|---|---:|
| Warm: Capture 0.9 / Order 1.1 | 1.916021 | 1.673233 | 0.242788 | Succeeded | 1 |
| Warm: Capture 1.3 / Order 1.8 | 2.939114 | 2.675149 | 0.263965 | Succeeded | 1 |
| Order requested 2.2, selected read ceiling 2.0 | 2.259638 | 2.022850 | 0.236789 | Failed v4 | 0 |
| Cold OAuth 0.65 + slow parallel reads | 3.816595 | 3.463005 | 0.353590 | Succeeded | 1 |
| Cancellation before financial dispatch | 0.402375 | 0.091245 | 0.311130 | Unknown | 0 |
| Sync persistence crosses deadline immediately before POST | 5.280821 | 5.051623 | 0.229197 | Unknown | 0 |
| Remote mock refund commits, acknowledgment lost | 0.321290 | 0.101475 | 0.219815 | Unknown | 1 |
| Refund GET exceeds remaining public budget | 5.223052 | 5.007094 | 0.215958 | Unknown | 1 |

Each is one deterministic sample, not a statistical latency distribution. The
successful adapter samples span **1.673–3.463 s**. Separate observational claim and
finish timings are in mock evidence (private local diagnostic; not published):
claim **0.103–0.190 s**, finish **0.107–0.171 s** across these cases. Overhead includes
claim/finish and orchestration; these components must not be summed twice.

The five-second timer covers the adapter, not whole Gateway wall time. Cooperative
cancellation cannot interrupt synchronous SQLite waits: the deliberately blocked
commit crossed the deadline, then the preserved checkpoint stopped before POST.
The greater-than-five-second wall measurements above are real local mock-test
observations, not a modified Runtime limit or a promise of a whole-call five-second
upper bound. Refund GET's HTTPX read limit was demonstrably below its requested
delay because the remaining budget had shrunk; the post-dispatch result stayed
Unknown with retained evidence.

All scenarios verified zero late/duplicate dispatch. Repeated commands and restart
were exercised **only in synthetic state**, with no additional remote mock effect.
The synthetic Failed v4 Action rejected both another execute command and another
authorize command, preserving its snapshot. The genuine original Failed Action
was never sent either command and remains byte-for-byte unchanged.

Focused new + existing deadline/parallel-read qualification: **37 passed in
60.78 s**. Final full regression: **420 passed in 274.86 s**, including the new
profiling instrumentation. Focused tests (private local diagnostic; not published),
full tests (private local diagnostic; not published).

## Genuine read-only Sandbox observations

Two bounded Capture/Order observations were attempted, separated by **1.5 s**, using
one client/token cache and the updated execution phase defaults. Each used a public
AttemptContext with a five-second deadline; this was a **read-only qualification
context**, not a Gateway financial attempt. `SandboxReadOnlyTransport` allowed only
Sandbox OAuth and bounded GETs, making a payment mutation unavailable.

| Genuine request | HTTP result | Measured client elapsed s |
|---|---|---:|
| Cold OAuth | 200; token not recorded | 0.951288 |
| First Capture GET | 200, COMPLETED | 1.145737 |
| First Order GET | 200, COMPLETED | 1.088354 |
| Second Capture GET | 200, COMPLETED | 1.502033 |
| Second Order GET | **No HTTP response; CAPTURE_READ_UNCERTAIN** | **2.007682** |

At **2026-10-13 08:18:36.024661 UTC**, the first joined observation completed in
**2.099275 s** including cold OAuth. It verified:

- Capture **`1YA65594665951620`**, Order **`3KT99923NY800615C`**, original completed
  gross payment **NZD 20.00**, CAPTURE intent.
- Merchant **`EZL4XDY2TTLVW`**, exact Order/Capture relationship, one purchase unit
  and one matching Capture, original incident facts unchanged.
- No refunds reported in the checked Order response, and existing policy eligibility
  for **NZD 5.00**. These responses provide no authoritative complete refundable-
  balance ledger; absence of a reported refund is not a complete-ledger guarantee.

The second Capture response independently retained COMPLETED / NZD 20.00 / matching
merchant and original Order ID. Its Order response was not obtained, so complete
payment qualification could not be repeated. `capture()` folds child-request
exceptions into CAPTURE_READ_UNCERTAIN: the underlying exception subtype was not
saved by this read-only harness. The **2.007682 s** failure is consistent with the
configured **2.0 s** read ceiling, but is not presented as a captured raw ReadTimeout
traceback or a provider rejection. No retry or third read observation was made.

Successful Capture reads: n=2, range **1.146–1.502 s**; successful Order reads: n=1,
**1.088 s**, plus one censored/no-response outcome at **2.008 s**. This small sample
cannot establish tail percentiles or a reliable financial end-to-end latency.
The original narrow-read defect is repaired, but genuine qualification still failed
within the selected bounds. Increasing limits again solely to obtain a green sample
would not prove room for Refund POST, verification and durable receipt under five
seconds. No genuine Refund POST latency has been measured.

Actual read telemetry (private local diagnostic; not published),
sanitized genuine responses (private local diagnostic; not published).
Unredacted provider bodies are retained only in Git-ignored private evidence.

## Regression, packaging and preservation

- Ruff lint / formatting: **PASS**, 31 source/test files checked.
- `pip check`: **PASS**. Installed `agentic-intent-gate` is **0.1.0**, pinned commit
  **fd742b783058a53400c465b4ab59c6e80715895a**; all **54** baseline Runtime hashes match.
- Wheel build and isolated installed-wheel smoke: **PASS**, including imports from
  the actual wheel target, static assets, the new timeout defaults and an isolated
  MockTransport GET. Wheel metadata retains the Runtime commit pin and excludes
  secrets/private state. Initial non-isolated build lacked setuptools; normal
  isolated PEP 517 build succeeded without installing/changing the shared Runtime.
  Package evidence (private local diagnostic; not published).
- All **3945** historical private files, original databases, audits, fixture,
  capability and `.env` remain unchanged. The test-generated earlier mock evidence
  file was restored to its pre-test bytes. No commit, push or deployment.
  Integrity (private local diagnostic; not published).

## Candidate and financial outcome

Public installed Runtime constructors/signatures and the core consumer reference
were inspected. The supported new lifecycle is fresh provisioned trusted identity
and independent real-model incident/Run, exact Plan Approval, admission generating
a new Action/effect key, separate Authorization, then separately permitted execute.
The original terminal Action must not be reset or its Approval/grant copied. This
lifecycle was **not entered** because Parts A/B/D passed but Part C did not pass.

| Required final item | Actual outcome |
|---|---|
| Original Action | `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5`, **Failed v4**, unchanged; one historical attempt |
| New real-Ollama inference / Plan / Run | **NOT RUN / NONE / NONE**, blocked before Part E; no deterministic substitute |
| New Action / durable effect key | **NONE / NONE** |
| New APPROVE / AUTHORIZE / EXECUTE ONCE records | **NONE / NONE / NONE** |
| Genuine Refund POST count in Phase 2.3.4 | **0** |
| Genuine Refund POST count across the preserved original pilot | **0** |
| New financial dispatch / Gateway calls | **0 / 0** |
| Refund ID / status / financial Receipt | **NONE / NOT QUERIED / NONE** |
| Financial Unknown / automatic retry / reconciliation | **NONE / 0 / 0** |
| E2E acceptance | **NOT PASS** |

**STOP / NO-GO.** The blocker is incomplete genuine read qualification within the
current bounds, with unmeasured real POST/verification latency. A future separately
reviewed qualification needs bounded read-tail evidence and enough modeled budget
for POST, GET and persistence; if that cannot fit the immutable adapter limit, a
separately reviewed Runtime budget extension remains an option. No such extension,
further network experiment, new candidate or human approval gate was initiated here.
