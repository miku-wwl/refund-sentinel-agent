# Phase 3.1 source publication qualification

**Qualification PASS — 14 October 2026, Pacific/Auckland.** This report records
checks completed before the separately authorized normal push to `origin/main`.
The resulting commit SHA and remote references are verified after commit; this
document does not invent a future SHA or claim a hosted deployment.

The checkpoint contains the existing five-screen presentation, isolated synthetic
workflow, optional genuine local Ollama proposal, tests and reviewed evidence.
No new feature, financial execution change or shared Runtime modification was made
for publication. README and presentation documentation now describe the source
checkpoint; earlier development reports retain their historical then-local status.

| Check | Actual result |
|---|---|
| Full pytest | 535 passed; zero failures/errors/skips; 498.59 seconds |
| Node frontend tests | 12 passed; zero failures |
| Ruff / Python format | PASS |
| Frontend syntax / format | PASS |
| Frozen dependency lock / pip dependency check | PASS |
| Consumer wheel / outside-checkout installation | PASS; deterministic and explicitly mocked AI compatibility |
| Actual Chromium | 156.0.8078.4; preserved E2E 10 checks; 15 screen/viewport combinations |
| Genuine local Ollama UI | PASS; `phi4-mini:latest`, HTTP 200, 4.969951-second inference |
| Accessibility | 28 axe scans; zero detected violations |
| Browser errors / clipping / page overflow | None detected |
| Genuine PayPal requests in this task | 0 |

The genuine local proposal completed three separate automated **simulation**
confirmations, one local fake dispatch, Succeeded v4 and a persisted synthetic
receipt. This is not another PayPal refund or a private financial confirmation
transcript. Negative model contracts use mocks; the browser model qualification
above used actual loopback Ollama. Existing Starlette/HTTPX TestClient deprecation
remains a warning, not a test failure. Other platforms and browsers are not qualified.

## Publication and privacy boundary

The exact proposed checkpoint has **62 changed files**: 10 presentation source/assets,
4 browser/verification scripts, 3 test files, 4 documents, README, 32 reviewed PNGs
and 8 sanitized JSON records. The complete list is in
[publication validation](https://github.com/miku-wwl/refund-sentinel-agent/blob/86a179fc6ca02568a849c51e765d6dca123dced7/evidence/phase3-ui/publication-validation.json).
Existing package configuration, LICENSE, placeholder `.env.example`, AGENTS.md
and ignore rules remain present in the tree without dependency changes.

All 32 PNGs were visually reviewed. PNG envelopes were inspected for textual/EXIF
metadata. Candidate content and the exact index are checked against actual private
credentials, OAuth tokens, capability tokens and buyer identities without printing
values. Reachable historical blobs, commit metadata and annotated tag metadata are
also inspected; secrets in old history would block publication rather than be
hidden by a deletion commit. Candidate files contain no machine-specific absolute
paths. One existing published historical report mentions a generic wheel test
directory; it contains no credential or private financial record and is unchanged.

Private SQLite, `.env`, raw provider responses, confirmation transcripts, local
state, caches, build outputs and unrelated diagnostics remain local. Explicit path
selection is used; no broad staging, cleanup, history rewrite, force push or new
tag is authorized. Two unrelated tracked whitespace/duplicate-ignore changes are
preserved outside this commit. Original and regenerated mock timing evidence are
both retained locally.

## Preserved financial baseline

- `phase2-backend-freeze` peels to
  `04fac090b6aa0a77ef1c50b9e6b451404fccc58f`; annotated tag is not moved.
- Installed Runtime `agentic-intent-gate==0.2.0`, immutable pin
  `7261fdd2f47d2b15fabe8faac527eeee37338eb1` remains unchanged.
- SHA checks preserve 4,058 original private files, 19 frozen backend files,
  three dependency contracts and 57 installed Runtime files; core checkout clean.
- The original genuine refund, failed/successful terminal Actions, receipt,
  Approval/Authorization, identities, profiles and financial deadlines are unchanged.

The historical real Sandbox proof remains archived and read-only. Viewing it makes
no live PayPal query. Git publication grants no additional financial authority.

## Independent UI review

**GO for independent ChatGPT Work UI review**, after independently verified normal
remote publication. Start the presentation locally:

```powershell
uv sync --frozen --all-extras
.venv\Scripts\python -m refund_sentinel.presentation --port 8880
```

Open **http://127.0.0.1:8880**. Deterministic Demo needs no model or credentials.
Optional Local AI Demo needs local Ollama `phi4-mini:latest`. Its proposal can fail
closed; fallback is explicit and manual. Payments always remain synthetic, and
historical provider proof is a separate read-only archive. See the
[English recording script](DEMO-SCRIPT.md). Independent UI review, timed video,
upload, deployment and competition submission have not been performed here.
