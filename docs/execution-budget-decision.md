# Execution budget decision

**Recommend B: a separately released Runtime API with an explicit Sandbox-only
15-second adapter profile. Current pilot: NO-GO.** Five seconds is a fast-path
budget, not a defensible general success budget for this payment chain. No upgrade,
new candidate, Gateway execution or genuine PayPal request occurred in this review.

## Critical path

```text
Outside adapter timer: human gates → external preflight → durable Gateway claim
Inside timer:          Capture GET || Order GET → dispatch commit/checkpoint
                       → Refund POST → response commit → Refund GET → receipt commit
Outside adapter timer: durable Gateway finish
```

Cold OAuth precedes authenticated reads; warm OAuth is a cache hit. Both parallel
reads share one token/cache, and the same AsyncClient/pool survives preflight into
execution. No client-recreation defect was found. Actual TCP/TLS reuse was not
traced; removing preflight also removes its potential connection-warming benefit.
[HTTPX pooling](https://www.python-httpx.org/advanced/clients/).

| Stage | Preserved genuine/local evidence | Implication |
|---|---|---|
| Cold OAuth | 0.801505–0.951288 s genuine | Serial prefix if cold inside timer |
| External preflight | 1.736210–2.099275 s genuine, including OAuth | Duplicate reads, outside adapter timer |
| Internal parallel revalidation | Capture 1.135218 s; Order ReadTimeout at 1.136642 s under old 1.1 s ceiling | Critical-path prefix |
| Later read qualification | Capture up to 1.502033 s; Order no response at 2.007682 s | Tail reaches/exceeds current 2 s ceiling |
| Refund POST / GET / financial receipt | **Never genuinely measured** | Mandatory serial suffix |
| Claim / finish | Prior mocks: 0.103–0.190 / 0.107–0.171 s | Outside adapter timer |

`T_adapter = OAuth_if_cold + max(Capture, Order) + POST_ack + Refund_GET + local_IO`.
POST must precede GET because GET needs the real refund ID; receipt follows verified
COMPLETED evidence. A read tail of 2.8 s plus assumed POST/GET of 2.2/1.8 s needs
about seven seconds even warm. Sparse/censored real observations establish no p95
or p99, and no real refund latency has been measured.

## Compare A and B

| Approach | Smallest safe change | Assessment |
|---|---|---|
| A: retain five seconds | Reuse token/client and parallel reads; remove external duplicate reads only after moving all their checks internally | Saves total workflow time, not a mandatory in-budget stage. Fast-path only; slow ACK/GET still becomes Unknown |
| B: explicit 15-second Sandbox profile | Versioned public Runtime limit, consumer configuration bound to trusted identity, existing validation retained | Accommodates modeled tails without weakening payment facts. More headroom, never a success/exactly-once guarantee |

A cannot use cached external facts or drop Order GET without proving equivalence.
The outer pilot checks CAPTURE intent, exactly one purchase unit/capture, unit gross
amount and original buyer; current internal validation does not enforce all those
predicates. Deduplication requires their identical trusted expectations and negative
contract tests inside the Executor. TTL alone is insufficient. Keep independent
Refund GET. **No validation was removed here.**

## Recommended implementation — proposed, not enabled

1. Review/release a **v0.2.0 candidate** Runtime; this version is proposed, not claimed
   published. Add immutable validated execution limits to public `open_runtime`,
   forwarded to the Gateway: default five, trusted opt-in maximum 15, finite/positive,
   rejecting booleans/NaN/infinity. Caller deadlines only shorten. Preserve claim,
   cancellation, finish, CAS, receipts and terminal Unknown/no-blind-retry behavior.
2. Verify its annotated tag and pin its peeled full commit SHA; update exact consumer
   version/commit verification. Current v0.1.0 rejects constructor limits above five;
   `open_runtime` exposes no limit option and later caller deadlines cannot extend
   five. **Never patch the installed pin or assign its timeout attribute.**
3. Consumer opt-in: Sandbox environment/base URL only, explicit 15 s in persisted
   configuration, fresh scope/binding revision tied to that profile. Verify configuration
   before admission/authorization/execution; never inherit another binding's Approval
   or grant. Preserve old state and require separately instructed new candidacy.
4. First pilot retains full external preflight and internal revalidation, one warmed
   client, new Action-derived effect-key request-id and durable one-POST fence.
   Qualify read 4 s / connect-write-pool 1.1 s, each capped by remaining budget; this
   profile was **model-only**, not enabled in production. Replace old hardcoded audit
   identity with parameters from the new admitted Action.
5. Check a documented verification/persistence reserve before POST; insufficient time
   stops before dispatch. Keep post-sync-write and transport-entry deadline checks.
   No extension after claim/dispatch; any dispatched ambiguity stays Unknown without
   retry or reconciliation. A reserve cannot guarantee remote latency.

Engineering target: OAuth ~1 + reads ~3.5 + ACK ~3.2 + GET ~3.2 + local/headroom ~2:
roughly 13 s. Fifteen gives more room than twelve. HTTPX read limits bound chunk
inactivity, not total request time; the Runtime total deadline remains authoritative.
[HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/).

## Safety evidence and limitations

**16 review tests passed in 78.45 s; 11 stateless SDK regression tests in 0.38 s.**
MockTransport and isolated product/provider databases only. Tests invoke the consumer
Executor/transport, **not Gateway**, and create no Run/Plan/Action. Twelve/fifteen-second
results use public AttemptContext plus a local timer model: they do not qualify a
new Runtime composition.

| Modeled path | Budget s | Executor s | Category / mock POSTs |
|---|---:|---:|---|
| Warm: read 2.8, ACK 2.2, GET 1.8 | 5 | 5.008591 | Unknown / 1 |
| Same warm path | 12 / 15 | 7.027586 / 7.010918 | Success / 1 |
| Cold: OAuth 0.9, read 3.2, ACK 3.0, GET 2.4 | 12 / 15 | 9.797718 / 9.760728 | Success / 1 |
| Cold tail: 3.2 + 3.5 + 3.2 + 3.2 | 12 / 15 | 12.008782 / 13.327986 | Unknown / Success; 1 each |
| Read exceeds phase limit | 15 | 4.062857 | Confirmed failure / 0 |
| Remote mock commits, ACK lost | 12 | 2.406616 | Unknown / 1 |
| Cancellation / sync-write deadline crossing | 15 / 5 | 1.893182 / 5.073694 | Unknown / 0 |

Exact request/phase/persistence timings (private local diagnostic; not published).
The one-POST fence rejected duplicates and restart before mock wire entry. No
ambiguous Executor was retried. Prior **420-test** Gateway regression remains the
baseline; it was not rerun under this review's no-Gateway restriction.

The only production change records allowlisted underlying HTTPX timeout and
cancellation types in `_roundtrip` before exception folding, without messages,
URLs/headers/locals. Tests verify redaction. This cannot recover the unrecorded
Phase 2.3.4 subtype. Defaults and financial behavior are unchanged. Lint, format and
dependency checks pass. Review tests (private local diagnostic; not published),
SDK regression (private local diagnostic; not published).

## Pilot decision

**NO-GO now.** GO requires the released/pinned extension's actual public Gateway
qualification: default/opt-in limits, scope/config binding, separate Approval and
Authorization, pre-POST expiry, Unknown, restart and duplicate protection. Then
qualify the consumer profile/fence and separately permitted fresh payment reads,
create a new real-model Plan, and obtain all three distinct human gates. Any failed
safety test, uncertain prior effect or identity mismatch is NO-GO. Success requires
genuine matching COMPLETED Refund GET and durable Receipt; ledger uncertainty must
still be disclosed.

All **3979** historical private files and **54** Runtime files remain unchanged;
original Action stays **Failed v4**, one historical attempt. Review totals: **0 genuine
PayPal requests, 0 Gateway calls, 0 real Refund POSTs**, no candidate/state/secret
changes or commit/push. Integrity (private local diagnostic; not published).
**STOP after review.**
