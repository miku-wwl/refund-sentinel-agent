# Implementation status — 2026-10-12

This is the initial implementation snapshot. The [2026-10-13 Phase 2.1 report](phase-2.1-report.md) records subsequent Python compatibility, preflight, contract and licensing checks. Genuine Sandbox OAuth now passed; capture/order reads remain blocked because no capture ID is configured. Refund execution remains unauthorized and was not run.

| Phase | Status | Evidence / remaining boundary |
|---|---|---|
| 0 — Verification/scaffolding | PASS | Root instructions preserved; fixed Runtime installed/API inspected; annotated tag verified; reference consumer read; official sources recorded; project/dependency configuration and MIT application license added |
| 1 — Offline vertical slice | PASS | Complete FastAPI/browser workflow, genuine Runtime, persistent fake effects/calls, approval/authorization separation and receipt; actual process restart verified |
| 2 — Real Sandbox readiness | PARTIAL | Real OAuth/Payments/Orders/refund client and documented deliberate fixture setup implemented and mock-tested; actual Sandbox API smoke awaits credentials and approved case |
| 3 — Quality gates | PASS | 91 automated tests passed, lint and dependency checks passed, desktop workflow/restart and 390 × 844 mobile layout verified |

## Implemented

Merchant capture allowlist and synthetic natural-language request entry; independent deterministic/real analysis modes; strict recommendation validation; Decimal policy; capture/order/payee evidence; persistent single refund Plan; exact human approval/rejection; durable admission; separate authorization and execute operations; registered PayPal executor; stable effect UUID as PayPal-Request-Id; verification GET; separate provider evidence and Runtime receipt/state; read-only manual status checks; restart inspection; concurrency/duplicate/Unknown safeguards through the external Runtime.

Real local Ollama interpretation produced an eligible Plan without making any refund calls. Fake-provider and HTTP-mocked PayPal results are marked as simulated; no claim of real PayPal completion is made.

## Core remains external

Version `0.1.0`, SHA `fd742b783058a53400c465b4ab59c6e80715895a`; live annotated tag object `ce0a516baf857bf79b53237677fff7fd3c50de95` peels to that SHA. All 47 installed hashed core files match their RECORD entries. No shared Runtime source, sibling repository, release tag or root AGENTS.md was changed.

The five-second executor deadline, missing Pending terminal state and restricted no-effect vocabulary are documented limitations. The consumer preserves Unknown and does not implement retries/reconciliation or bypass Runtime claiming.

## Outstanding engineering

- Run OAuth and capture/order read checks against configured Sandbox credentials; inspect actual PayPal response shapes and latency against the baseline deadline.
- Execute one specifically human-approved Sandbox partial refund through the dashboard; verify exact remote evidence and persisted receipt. A read-only verification mismatch must remain Unknown until reviewed; do not relax evidence checks to make the smoke pass.
- If real Sandbox latency regularly exceeds the baseline deadline, propose a separately reviewed minimal core change; do not monkeypatch or copy the Runtime in this application.

## Human/external requirements

- Supply private Sandbox app credentials, merchant identity and an eligible capture; approve its exact test amount/currency.
- Clarify the pinned Runtime dependency's license/access for public judging. The qualified commit and installed metadata currently provide no license declaration; the application MIT license covers only this repository's work.
- Verify personal competition eligibility/ownership, make an authorized public repository available, record/upload the under-three-minute public YouTube demo, and complete Devpost submission. These actions were not authorized/executed in this session.

This report records the initial implementation before separately authorized Git delivery. No Sandbox refund, tag, release or final submission was performed during that implementation.

## Next narrow task

“Using the current implementation and private Sandbox credentials, run OAuth and capture/order GET checks, identify one eligible synthetic capture, and show me an exact proposed partial-refund test case. Stop before Sandbox refund execution until I approve the capture ID, amount and currency. Preserve all Runtime gates and capture redacted evidence.”
