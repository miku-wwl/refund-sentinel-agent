# Phase 4.7 final delivery status

30 October 2026, Pacific/Auckland. **PARTIAL / NO_GO for final recording and
submission.** The decision-evidence correction, deterministic qualification,
packaging and reviewable narration/storyboard drafts are delivered. Genuine IAB
rehearsal is blocked, two mandatory host-isolation tests remain failing, and no
Phase 4.7 MP4 exists.

## A. Engineering and B. Security

See the [engineering report](PHASE47-ENGINEERING-REPORT.md) for the actual root
cause, six source/test changes, ten additional negative cases, legacy preservation
and exact commands. Schema validity, policy eligibility and verified durable Plan
readiness are now distinct. Failed or interrupted generation exposes no executable
Plan or controls and cannot be retried through the same case.

Full Python: **651 passed, 2 failed, 0 skipped**, 535.83 seconds (543.1849 seconds
including command envelope). The failures are the two requested live Windows owner
tests. Stable diagnosis identifies an existing CrowdQuest interpreter outside the
guard's trusted set; a separate transient inventory change is not localized. Guard
checks and tests were preserved. A dedicated clean Windows qualification is still
needed; unrelated applications and original previews were not stopped.

Targeted Python: 173 passed. Ten newly selected negative cases passed. Relevant
post-frontend Python checks: 31 passed. Final Node: 21 passed. Ruff lint/format,
frontend checks, dependency checks and packaging passed. No skipped security test
or changed dependency was used to manufacture green results.

## C. Browser and D. DeepSeek

See the [browser report](PHASE47-IAB-REHEARSAL-REPORT.md). Inventory and one fresh
IAB-tab attempt both returned `The browser access host is unavailable`. No genuine
IAB rehearsal or its twelve required captures was completed. Three separate final
headless Chromium suites passed, including 54 axe scans with zero detected
violations. Corrected failure-state screenshots and representative Receipt,
Unknown and archive images were actually inspected.

Actual new DeepSeek calls: **0**. No Phase 4.7 A/B output or measured cloud latency
is invented. Historical Phase 4.6 samples and mocked contracts are explicitly
separate. All four authorized cloud requests remain available for later rehearsal
and filming. The preview's persistent request cap is four across restarts.

## E. Runtime and F. Financial isolation

The installed, unchanged public Runtime is 0.2.0 from
`7261fdd2f47d2b15fabe8faac527eeee37338eb1`. All 57 hashed RECORD entries verify.
The baseline manifest contains 107 tracked files; the six intended source/test
files changed and the remaining **101 are byte-identical**, including frozen
financial source, execution guard, dependency declarations/locks and archived proof.
Three new reports are the only additional intended repository files.

Historical proof SHA-256:
`1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853`.
The original local-model provenance, NZD 5.00/20.00 financial evidence, Actions
and Receipts were not relabeled or replayed. New state is external and synthetic.

Actual Phase 4.7 genuine PayPal requests: **0**, scoped to this task's regression,
wheel and guarded preview executions. Other existing applications' network traffic
was not audited. The preview records nine fake dispatches in distinct cases across
three main QA passes, six persisted fake effects and three definitive rejections.
Final wheel smoke uses a separate fake store and four mocked cloud contracts;
its five cases include three local fake dispatches, with no genuine network.
Regression fixtures have their own per-test stores and are not added to the
preview count. Actual preview process restart retained eight cases and the same
three then-existing dispatches without model calls or another effect.

Final wheel: `<artifacts>\wheels-accepted\refund_sentinel-0.1.0-py3-none-any.whl`.
The external installed-wheel smoke matches all 31 packaged source/assets to final
source. It imports the consumer from the fresh external wheel environment and the
Runtime from installed site-packages. No adjacent core checkout is imported.

## G. Recording, H. Video QA and I. Narration

OBS 32.2.2 is installed; actual capture capability remains BLOCKED. The IAB target
is unavailable, no short test take was created, and engineering Gate 1 is PARTIAL.
Final filming is therefore NOT_RUN under the supplied gates. Video existence,
playback, full decode, duration, resolution, frame rate, black frames and final
visual/storytelling QA are NOT_RUN/NOT_VERIFIED. No replacement slideshow or
historical video is presented as a new final recording.

The external shotlist specifies seven scenes in 175 seconds, below the 179-second
maximum. The English narration draft contains **304 spoken words**. Its **30 SRT
cues** reproduce the same spoken text, with a planned endpoint of 175 seconds.
The script, subtitles, pronunciation guide and scene map are explicitly provisional:
there is no completed silent MP4 or owner voice track to align against. No owner
voice was synthesized or imitated. The owner records narration after the actual
silent video and its observations have been reviewed.

## J. Outstanding risks and exact next actions

1. Obtain isolated Windows qualification for the unchanged owner tests and full
   regression without terminating current CrowdQuest or other services.
2. Restore the real Desktop Work IAB using normal app controls. Safe rehearsal may
   continue while engineering is PARTIAL; filming still requires Gate 1 PASS.
3. Rehearse actual A/B with genuine DeepSeek, deterministic E and the historical
   proof; record the real observations, visible confirmations and screenshots.
4. Complete the actual OBS short capture/playback preflight, then the final silent
   take only after Gates 1, 2 and 4 pass. Preserve failed takes and the four-call cap.
5. Verify the actual MP4 and reconcile narration/SRT; receive the owner's voice.

The Phase 4.7 execution itself did not automatically commit, push, tag, deploy,
upload or submit to Devpost, as its prompt required. After that work was complete,
the user separately instructed publication of the repository contents; this report
is included in that scoped Git delivery. No tag, deployment, upload or Devpost
submission is implied by the push.

## Artifact paths and machine-readable results

Artifact root:
`D:\workshop\oct\refund-sentinel-phase47-artifacts\20261030-030524`.

| Artifact                                 | Actual location under that root                                                                           |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Baseline / final integrity / privacy     | `baseline-manifest.json`, `integrity.json`, `privacy-audit.json`                                          |
| Host diagnosis / live-test reproductions | `host-process-diagnosis.json`, `guard-baseline-1.xml` through `guard-baseline-3.xml`, corresponding logs  |
| Complete regression                      | `full-pytest.xml`, `full-pytest.log`, `full-run.json`                                                     |
| Other Python / Node                      | `targeted.xml`, `new-negative-tests.xml`, `post-visual-python.xml`, `node-accepted.log`                   |
| Final browser evidence                   | `browser/accepted-main/`, `browser/accepted-ui/`, `browser/readiness-stable-final/`, `browser-runs.jsonl` |
| Genuine process restart                  | `process-restart.json`, `restart-before.json`, `preview-identity.json`                                    |
| Final installed-wheel qualification      | `wheels-accepted/`, `installed-wheel-smoke-accepted.json`, `wheel-smoke-accepted.log`                     |
| Shotlist / recording procedure           | `RefundSentinel_Phase47_Shotlist.md`, `Recording-Manual.md`                                               |
| Narration / subtitles                    | `RefundSentinel_Phase47_Voiceover_EN.md`, `RefundSentinel_Phase47_Subtitles_EN.srt`                       |
| Pronunciation / draft checks             | `RefundSentinel_Phase47_Pronunciation.md`, `voiceover-package-check.json`                                 |

Private databases, capabilities, installed environments, large browser artifacts and
wheel files remain outside the Git repository. Do not upload the entire artifact
root: it also contains private synthetic state and diagnostic/intermediate runs.

```text
PROJECT=Refund Sentinel
PHASE=4.7
BASELINE_HEAD=3811725cec176012b883161140b3a6a529bb69d6
PHASE47_HEAD_AT_REPORT=3811725cec176012b883161140b3a6a529bb69d6
WORKTREE_STATUS_AT_REPORT=MODIFIED; 6 source/test files and 3 new reports; uncommitted
GATE_0_PREFLIGHT=PARTIAL
GATE_1_ENGINEERING=PARTIAL
GATE_2_IAB=PARTIAL
GATE_3_STORYBOARD=PASS
GATE_4_RECORDING_PREFLIGHT=PARTIAL
GATE_5_RECORDING=NOT_RUN
GATE_6_VIDEO_QA=NOT_RUN
GATE_7_VOICEOVER_PACKAGE=PARTIAL
GATE_8_FINAL_HANDOFF=PARTIAL
PYTHON_TESTS=651 passed; 2 failed; 0 skipped
NODE_TESTS=21 passed; 0 failed
BROWSER_TESTS=3 headless Chromium suites PASS; actual IAB BLOCKED
HOST_ISOLATION_TESTS=2 failed; live unrelated executable blocks trusted inventory
DECISION_EVIDENCE_CONSISTENCY=PASS
DEEPSEEK_ACTUAL_CALLS=0
DEEPSEEK_ACTUAL_RESULTS=NOT_RUN; no new genuine model observations
REAL_PAYPAL_NEW_REQUESTS=0 from Phase 4.7 executions
FAKEPAYPAL_DISPATCHES=9 in isolated presentation preview; other test stores separate
HISTORICAL_EVIDENCE_INTEGRITY=PASS
VIDEO_FILE=NOT_CREATED
VIDEO_DURATION=NOT_VERIFIED
VIDEO_RESOLUTION=NOT_VERIFIED
VIDEO_QA=NOT_RUN
VOICEOVER_SCRIPT=D:\workshop\oct\refund-sentinel-phase47-artifacts\20261030-030524\RefundSentinel_Phase47_Voiceover_EN.md
SUBTITLE_FILE=D:\workshop\oct\refund-sentinel-phase47-artifacts\20261030-030524\RefundSentinel_Phase47_Subtitles_EN.srt
FINAL_STATUS=PARTIAL
FINAL_RECOMMENDATION=NO_GO
USER_ACTION_REQUIRED=Restore IAB and obtain isolated Windows qualification; then complete gated filming/QA and owner narration
```

Gate 2's summary PARTIAL means the required IAB capability is **BLOCKED**, despite
separate automated coverage. Gate 4's summary PARTIAL means installed-tool discovery
only; actual recording preflight is **BLOCKED**. Neither permits final filming.
