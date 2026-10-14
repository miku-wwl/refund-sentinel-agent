# UI acceptance fixes and independent browser revalidation

**14 October 2026 — PASS. All four issues FIXED; GO for the next separately scoped Submission Cleanup phase.**
Baseline/recovery commit: `096b89eff51db9aa2dc5a6b04fe3ff19506a8c63`. Changes are local and uncommitted. The existing repository was editable and localhost was reached in the actual in-app browser before changes. Only presentation assets and browser QA were changed; no financial executor or shared Runtime implementation was modified.

## Issue outcomes

| Issue | Status | Root cause and implementation | Browser result |
| --- | --- | --- | --- |
| RS-UI-01 / P2 | **FIXED** | The skip anchor changed the hash to `main`, which the screen router treated as unknown and mapped to Overview. A semantic anchor click handler now prevents that route change, focuses the existing main element and scrolls to its content. Enter still activates the native link. Unknown-route fallback is unchanged. | All five screens retain hash, title and content, with focus on main and no extra history entry. Reload, keyboard continuation and Back/Forward pass. Unknown, `__proto__` and `constructor` hashes still fall back safely. |
| RS-UI-02 / P2 | **FIXED** | Automatic grid minimums and a non-wrapping long badge made the card wider than the viewport. Tracks now use `minmax(0, ...)`, panels can shrink, mobile headers/tags wrap and fact rows use bounded grid columns. Font-relative metric columns and flexible headings/topbar preserve reflow at enlarged text sizes. The horizontally scrolling evidence table is now a labeled, keyboard-focusable region with a visible focus outline. No blanket overflow hiding was added. | 30 combinations: five screens × 320/360/390 CSS px × normal/200% text. Native classic scrollbar gutter is 15px; every document scroll width fits client width, and measured fact/header boxes stay in bounds. Independent in-app measurements also passed at 320/360/390. |
| RS-UI-03 / P3 | **FIXED** | A shared offline heading and deterministic empty-state text were reused for live proposals. The header now says SIMULATED PAYMENTS; empty-state descriptions distinguish genuine local Ollama from deterministic recommendations. Existing provider configuration and manual fallback are unchanged. | Both modes have accurate text. Live inference is reported only after a genuine model response. The actual manual run took 8.936s; genuine automated E2E took 5.058390s. Both payment executions were fake. |
| RS-UI-04 / P3 | **FIXED** | The primary decision control followed the full incident details and fallback. The same control now appears in a compact, labeled next-decision region before the timeline. Confirmation handlers, command construction, exact identities and authorization checks are unchanged. All incident details, Plan, timeline and warnings remain. | Without scrolling, the button spans y=531.578–580.672 at 1440×900 and y=541.578–590.672 at 1920×1080, in both modes. Previously it began around y=1149 at 1920×1080. |

## Exact files changed

- `src/refund_sentinel/static/console.js`: skip-link handling, mode-specific copy, next-decision placement and accessible table markup.
- `src/refund_sentinel/static/console.css`: bounded mobile grids, wrapping headers/facts, enlarged-text reflow, table focus indication and compact decision-area styling.
- `scripts/presentation_ready.mjs`: overflow qualification uses document **clientWidth**, accounting for classic scrollbar space, rather than innerWidth.
- `scripts/test_ui_acceptance_browser.mjs`: new real-browser regressions for all four defects, with navigation, classic scrollbars, text magnification, desktop control bounds and axe.
- This report and new reviewed evidence under `evidence/ui-acceptance/`.

Original `.gitignore` and `AGENTS.md` local modifications are preserved. Historical evidence and private state are retained.

## Actual execution evidence

The author both implemented the fixes and personally interacted with the running application through the in-app browser. Automated Chromium tests complement that manual work; they do not replace it.

| Check | Actual result |
| --- | --- |
| New browser regressions | PASS: 5 skip/history cases, 3 unknown-route cases, 30 mobile layout cases, 4 desktop action/mode cases; 39 axe scans |
| Preserved browser E2E | PASS: 10 checks, 11 axe scans; completed simulation, terminal Unknown/Failed and service-error handling |
| Preserved AI browser E2E | PASS: actual `phi4-mini:latest`, generation endpoint HTTP 200, 5.058390s inference, three separate simulated confirmations, Succeeded v4 and durable fake Receipt; 15 visual combinations, 17 axe scans, 4 explicitly mocked negative model UI contracts |
| Combined automated accessibility | **67 scans, zero detected violations** |
| Manual browser | Five-screen skip-link activation; fresh genuine model Plan; separate Approval/Authorization/Execute dialogs; successful Receipt after refresh/reload; terminal Unknown and Failed after refresh/reload; reset into fresh scope; mobile reflow and historical Receipt |
| Full pytest | **535 passed**, zero failures/errors/skips, **481.46s**; one existing Starlette/HTTPX deprecation warning |
| Node | **12 passed**, zero failures |
| Ruff / Python format | PASS; 46 files already formatted |
| Frontend syntax / Prettier | PASS |
| Locked dependencies / pip | `uv lock --check --offline` PASS, 31 packages; pip check PASS |
| Browser QA dependencies | Official npm registry audit: 0 vulnerabilities. Configured mirror audit endpoint initially returned NOT_IMPLEMENTED; per-command official-registry fallback was used without changing registry configuration. |
| Wheel | Offline build PASS; five packaged presentation assets byte-match source, and Runtime dependency pin is retained |

The first complete Python run recorded **533 passed / 2 failed, 490.62s**. Both failures were real process-identity tests reporting `PROCESS_IDENTITY_UNVERIFIABLE`; no UI test or financial effect failed. The original logs are preserved privately. Running the ownership suite separately with the fully qualified interpreter path passed **22/22 in 15.03s**, with no guard or security assertion change. The final full run uses that qualified path, with preview stopped and other Python checks serialized. The exact first-run identity predicate was not retained beyond its failure traceback; concurrency was an initial hypothesis, not an established cause.

The manual successful simulation used Run `b3b95151-90ad-418e-866d-60cfe72aa4dd`, Action `7bcba657-578b-4899-88a3-3aeaab26fd50`, Receipt `79dbc3d1-14ac-48b1-9874-a42c89e135c7` and exactly one local fake dispatch. Approval left Authorization absent and dispatches at 0; Authorization survived reload with dispatches still 0. Only the third distinct confirmation executed the simulation. Unknown and Failed each remained terminal with count 1 and no Receipt/execute/retry button after reload. No ambiguous effect was retried.

The isolated QA preview used new synthetic state. A retained browser cookie from the earlier preview initially produced a fail-closed DEMO_SESSION_NOT_FOUND notice; loading a fresh sample established the QA session. No old grants or Actions were copied between directories.

## Screenshots and measurements

- [Machine-readable browser regression and request records](../evidence/ui-acceptance/browser-regression.json).
- [Fixed 320px review](../evidence/ui-acceptance/mobile-320-100-review.png) and [200% text review](../evidence/ui-acceptance/mobile-320-200-review.png).
- [Visible 1440px live next action](../evidence/ui-acceptance/desktop-1440-local_ai.png) and [1920px equivalent](../evidence/ui-acceptance/desktop-1920-local_ai.png).
- [Keyboard skip result](../evidence/ui-acceptance/skip-review.png).
- [Manual browser evidence](../evidence/ui-acceptance/manual-verification.json).

## Safety, limitations and acceptance

The presentation factory registers only the local FakePayPal provider and ignores `.env`. Browser QA blocks external browser requests and genuine `/api/` routes. The genuine model uses local loopback Ollama; it was not replaced by a deterministic fixture for qualification. Historical Sandbox evidence is a read-only archive, not a current provider lookup or balance assertion. No genuine PayPal Order, Capture or Refund operation occurred.

Before- and after-work SHA verification passed for 4,058 original private files, 19 frozen backend files, three dependency contracts and 57 installed Runtime files, with zero differences. Runtime remains `agentic-intent-gate==0.2.0`, pin `7261fdd2f47d2b15fabe8faac527eeee37338eb1`; the core checkout is clean and the freeze tag remains on `04fac090b6aa0a77ef1c50b9e6b451404fccc58f`. The 34 regenerated mock timing records from each full test attempt are retained separately while original evidence bytes are restored; no historical financial database is reset. The original synthetic preview has been restored on port 8880 with its earlier state retained.

200% text qualification doubled snapshotted computed text sizes inside actual Chromium, using QA-only styles and a fresh document for each case. It is not native Firefox text-only zoom. Mobile checks use resized browsers, not a physical touch device. Axe and manual keyboard checks are not a full screen-reader or WCAG certification. No narrated 2–3 minute recording, new environment installation, deployment or submission is claimed.

All four reported issues and the additional narrow-screen table focus defect are addressed. No remaining P2 defect was observed in the qualified browser matrix. Full existing regression tests and final integrity checks passed. **GO for Submission Cleanup**, which has not been started. No commit, push, tag, cleanup or deployment was performed.
