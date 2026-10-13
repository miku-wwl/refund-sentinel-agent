# Phase 2 backend freeze

Qualified on **14 October 2026, Pacific/Auckland**. Scope: single-operator,
loopback-hosted **PayPal Sandbox Hackathon MVP**. This is a stable handoff baseline,
not production, multi-user, distributed-HA or universal exactly-once qualification.
The published annotated tag is `phase2-backend-freeze`; release verification and
content hashes are in `evidence/phase2-freeze/`.

## Frozen software and contracts

- Python `>=3.13,<3.14`; consumer distribution `refund-sentinel==0.1.0`.
- Installed `agentic-intent-gate==0.2.0`, immutable Git commit
  `7261fdd2f47d2b15fabe8faac527eeee37338eb1`, annotated upstream `v0.2.0`, MIT.
- FastAPI 0.143.0, Uvicorn 0.54.0, Pydantic 2.14.1, HTTPX 0.28.1;
  exact `uv.lock` and pip snapshot. Private dependency access needs authenticated
  Git; credentials must never be embedded in source, URLs or build logs.
- Only `agentic_intent_gate.runtime` is imported for consumer integration.
  No copied Runtime, monkeypatch, alternative ledger or execution framework.
- Core owns persistent Runs, exact Approval binding, Action admission, independent
  Authorization, durable claiming, effect identity, CAS, terminal outcomes and
  command receipts. Consumer owns policy, model/provider adapters and verified
  financial observations/Receipt storage.

```text
Real Ollama recommendation → trusted policy → immutable single-step Plan
→ exact human Approval → public admission → independent Action Authorization
→ separate host execute permission → public Gateway durable claim
→ fresh Capture GET || Order GET → one Refund POST → independent Refund GET
→ durable financial Receipt → terminal Action
```

The model proposes a recommendation only. Host code registers the single trusted
`paypal_partial_refund@1` SIDE_EFFECT tool and compiles strict bounded arguments.
Model output cannot select credentials, adapter code, bindings, scopes, deadlines,
authorization or arbitrary network destinations. Target is
`paypal-sandbox-refunds`, adapter `paypal-sandbox-adapter`.

## Five- and fifteen-second identities

| Property | Legacy/default | Reviewed Sandbox opt-in |
|---|---|---|
| Public adapter budget | 5 seconds | 15 seconds |
| Binding revision | `refund-binding-v1` | `refund-binding-v2.exec-15s` |
| HTTP read ceiling | 2 seconds | 4 seconds |
| Connect/write/pool ceilings | 1.1 seconds | 1.1 seconds |
| Additional pre-dispatch reserve | Existing deadline/cancel checks | 9 seconds remaining |
| State | Existing legacy format | Fresh UUIDv4 scope and separately bound private gate/ledger/receipt store |

Extended startup uses public `execution_budget_binding` and `open_runtime` with
exact matching capability, registry, verifier, policy and store identities.
Persisted profile/binding/scope must match on restart. Input bodies/LLM/browser
parameters cannot increase the trusted budget. Caller monotonic deadlines only
shorten it. Existing Actions, Approvals, grants, effects and receipts are never
migrated or elevated. Extended compilation uses action-compiler-v3/action-spec-v3.

Claim/finish are outside the adapter timer. HTTP phases are separately capped by
the public AttemptContext's remaining budget. The pilot uses the direct public
Gateway; bundled Core HTTP routes retain a ten-second parent deadline. Nine seconds
is an engineering verification/persistence reserve, not a guarantee. Rechecks after
synchronous persistence, HTTP preparation/OAuth and exclusive dispatch-marker fsync
prevent starting a new financial effect after expiry/cancellation. Blocking Python
cannot be preempted by cooperative cancellation; remote effects cannot be recalled.

## Financial controls that must remain intact

- Fixed Sandbox origin, strict capture allowlist, merchant identity and exact money.
  No Live mode or currency fallback. Capture/Order identity, gross amount, currency,
  merchant, original buyer, purchase unit, CAPTURE intent and prior-refund eligibility
  are checked before the real pilot; internal revalidation remains mandatory.
- Decimal partial-refund policy; strict argument schema and exact incident/Plan
  binding. No model-generated credential, scope, tool or endpoint authority.
- Approval and Authorization are independent. The real pilot additionally records
  separate human **EXECUTE ONCE** permission in trusted host orchestration.
  Do not claim the shared Runtime or generic `/execute` route independently
  implements that third human-consent record.
- The durable Action effect key maps to PayPal-Request-Id. Public Gateway claiming
  and the additional exclusive one-POST audit fence remain in place.
- No automatic financial retry/replay/reconciliation. Lost acknowledgment, Pending,
  uncertain verification and late outcomes remain Unknown. Unknown means stop.
- Independent Refund GET must validate exact refund/capture identity, amount,
  currency, trusted link origin/path/relation/method and COMPLETED status before
  success. Provider HATEOAS URLs are evidence only and are never followed directly.
- A local Receipt and remote completion are distinct. Both are required for E2E PASS.
- Keep credentials, capabilities, private ledgers, raw provider payloads and buyer
  personal information out of browser responses, Git, screenshots and logs.

## Genuine historical qualification

The archived [sanitized proof](../evidence/phase2-freeze/verified-refund.json) is an
immutable historical observation, **not a live PayPal query**. Its customer incident
description is synthetic; the local Ollama recommendation and Sandbox API payment
operations were genuine. No new financial operation is authorized by this freeze.

| Fact | Verified value |
|---|---|
| Original captured payment | NZD 20.00; Capture `1YA65594665951620` |
| Merchant | `EZL4XDY2TTLVW`; independent buyer verified privately |
| Partial refund | **NZD 5.00, COMPLETED** |
| Refund ID | `1XN74010T5365280D` |
| Action | `26a5748a-7b1a-4dc7-a52c-a98e6bf0a4a1`, **Succeeded v4** |
| Durable financial Receipt | `e1415750-0971-4347-a88d-a3704dbb79c8` |
| Exactly one observed genuine Refund POST | HTTP 201, **2.148422 s** |
| Independent Refund GET | HTTP 200, **1.392813 s** |
| Direct Gateway wall time | **4.766604 s**, configured adapter budget 15 s |
| Human confirmations | Three separate exact Approval / Authorization / Execute replies |
| Persistence | Independently checked from a new process and read-only SQLite |

Historical failed Action `5f7f7713-56f3-4afc-b5ef-1bd8c24c92d5` remains **Failed v4**,
with zero genuine Refund POSTs. Both historical Actions are terminal. Never execute,
reauthorize, reset, migrate or reuse either. Neither legacy nor completed request
keys can be substituted as the identity of a new financial operation.

## API and UI integration boundary

The existing application is FastAPI plus vanilla HTML/CSS/JavaScript under
`src/refund_sentinel/static`. Its CLI loads private `.env` for operational mode;
Phase 3 must use a separate safe presentation entrypoint that ignores these values.

| Existing route | Behavior / boundary |
|---|---|
| `GET /`, `/static/*` | Operational frontend assets; do not mount them as the presentation console |
| `GET /api/config` | Public sanitized mode, allowlist, max-refund, Runtime pin and trusted budget; not a credential source |
| `GET /api/incidents` | Capability-authenticated sanitized incident list |
| `GET /api/incidents/{id}` | Capability-authenticated Run/Plan/Action/observation read; caller scope checked |
| `POST /api/incidents` | Model analysis and new Run proposal; not a read-only operation |
| `POST .../decision`, `.../admit`, `.../authorize` | Distinct exact-Plan/version/capability-gated durable operations |
| `POST .../execute` | Financial-capable public Gateway operation; never connect the Phase 3 demo to it |
| `POST .../verify` | Provider GET plus appended evidence; no financial retry, but not a filesystem-pure read |

Core Run states include AwaitingApproval/Approved; Action states include Pending,
Authorized, Executing, Succeeded, Failed and Unknown. The verified financial Receipt
contains only the effect/payload binding and allowlisted refund status/money/IDs.
The application's capability token is private. Never return `.env`, raw database
rows, arbitrary file reads, private OAuth material, full unfiltered provider bodies,
or an executable historical financial command to the presentation browser.

Phase 3 uses a consumer-owned read-only archived proof fixture with explicit response
schemas. Its separate interactive demo must force offline provider and simulated
recommendation, use synthetic capture/merchant and fresh isolated scopes/state,
and reuse public Runtime APIs for the three conceptual gate steps. It must not load
the real private state or `.env`, expose operational mutation routes, obtain PayPal
credentials, call genuine PayPal endpoints or execute historical Actions. A future
authenticated financial UI is outside scope.

## Freeze qualification and reopening

The original qualified baseline had **476 tests**. Stage A revalidates the full
enabled suite, Ruff/format, exact installed release/RECORD hashes, locks/dependencies,
wheel build and installed-wheel public integration outside the checkout, financial
gate/no-replay checks, private historical hashes and publication hygiene. Actual
counts/outcomes and public content hashes are recorded in
`evidence/phase2-freeze/validation.json` and `manifest.json`.

One regression formerly conditionally imported a private historical runner and
skipped in a clean clone. It now tests the distributable production one-POST fence
with the same duplicate/restart assertions and isolated MockTransport. It remains
enabled; private state is no longer a prerequisite. No financial backend assertion
or execution protection was weakened.

Reopen backend work only for a concrete reproduced safety/compatibility defect or
separately scoped requirement with explicit review, isolated regressions, new
version/binding where required and preservation of historical state. UI convenience
alone does not justify changing payment policy, execution deadlines, grants, claim
semantics, terminal handling or effect identity. Any future financial pilot needs
new, exact human consent and may never be an automatic retry of Unknown.

Known limits: single Sandbox sample, no complete refundable-balance ledger, unknown
latency tails, cooperative cancellation, cross-store crash windows, provider-specific
idempotency retention, no generic multi-tool Runtime or authenticated production
multi-user service. A successful fast sample is not a five-second or fifteen-second
success guarantee. Freeze and presentation development grant no financial authority.
