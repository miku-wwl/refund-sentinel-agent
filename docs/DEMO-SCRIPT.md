# Refund Sentinel demo script

Run `python -m refund_sentinel.presentation --port 8880` and open
`http://127.0.0.1:8880`. This presentation ignores `.env`; it needs no payment
credentials. Record at 1920×1080. Keep the simulation banner visible, choose
**A · Valid partial refund**, and start a fresh case. Configure the server's
DeepSeek API key through its explicit environment variable before startup; no key
is entered in the browser. DeepSeek is the preferred live provider. Ollama
`phi4-mini:latest` remains an optional local alternative. Rehearse first: the
qualified inference times vary; allow for the genuine model's bounded wait and
rehearse the complete sequence before recording.

## 2–3 minute demonstration

**0:00–0:20 — Overview, then Interactive demo**

“Refund Sentinel turns a customer refund request into a bounded proposal, explicit
human decisions and verifiable execution. An AI suggestion should never be enough
to move money. The overview shows one completed historical PayPal Sandbox pilot.”

Select **DeepSeek Flash — Live Cloud AI (preferred live)**, load case A, then click
**Generate Live DeepSeek Plan**. Keep the loading indicator visible.

**0:20–0:55 — Genuine cloud inference and local validation**

"This incident and payment are synthetic. We are calling the genuine DeepSeek
cloud API to interpret the damaged-item request for twenty-five US dollars. The model
only recommends. It cannot choose credentials, tools, scope or permission.

Here is its recommendation and measured inference time. Strict schema and merchant
policy validate the amount and currency before the pinned Runtime validates this
structured Plan. The exact Plan has a fingerprint.”

Show the recommendation, Plan and visible next-decision control. If the model fails, show its
actual error and click **Switch to Deterministic Demo**. Say: “The live proposal
was unavailable or rejected. I am explicitly switching to an offline fixture.”
Never call that fallback genuine AI.

**0:55–1:45 — Three separate decisions and synthetic receipt**

Click **Approve Plan**, read and confirm the first dialog; show Pending.

“I approve this exact Plan. The admitted Action is Pending, with no execution grant.”

Click **Authorize Action** and separately confirm; show Authorized.

“I separately authorize this specific Action. No provider dispatch has happened.”

Click **Execute Simulation**, review the third dialog and confirm once.
Open the simulated receipt, then reload.

“Now I permit one simulation. The real Runtime claims the Action, a local fake
provider performs the effect, and independent lookup produces a durable receipt.
Reloading preserves it. This sends no genuine PayPal refund. An Unknown result
means stop, with no automatic retry.”

**1:45–2:45 — Genuine historical evidence and provenance**

Open **Verified evidence**, show COMPLETED, the HTTP table, provenance and historical
receipt. Follow public references only if needed after recording.

“This separate screen records the genuine historical Sandbox transaction: five
New Zealand dollars from a twenty-dollar payment. Refund POST returned 201;
independent Refund GET returned 200 and COMPLETED. The Action is Succeeded version
four, with exactly one observed POST. Its receipt was reopened from a separate
process. Public references identify the frozen sanitized evidence.

Viewing this archive performs no new PayPal verification. It proves one historical
Sandbox sample, not production readiness or universal exactly-once delivery.
AI proposes. Humans decide. Receipts prove.”

Timing marks are rehearsal targets and include model waiting plus human gate/scrolling time. Actual
duration depends on inference and review. No completed recording duration is claimed.
The displayed requested alias is `deepseek-flash`. Official documentation currently
maps it to DeepSeek-V4.1-Flash-1017; returned metadata does not independently attest
to an immutable build. Do not describe this live cloud inference as local execution.
The historical Sandbox proposal retains its original local Ollama provenance.

For an additional decision example, explicitly load B, C or D in cloud mode and
show its actual output. Do not promise that injection makes the model fail. B and C
are blocked by trusted request/policy checks; a compliant D proposal may reach
AwaitingApproval, with no Action or dispatch. E must be explicitly loaded in
deterministic mode to demonstrate FakePayPal's terminal Unknown, without another
cloud inference or a real financial request.

## 60-second pitch

“Refund Sentinel makes AI-assisted refunds understandable and controllable.
A cloud or local model proposes a bounded partial refund. Trusted payment facts and policy
validate it. A human approves the exact Plan, separately authorizes its admitted
Action, then permits one execution.

We reuse the pinned Agentic Intent Gate Runtime for durable claiming, scope binding
and terminal-state protection. A genuine PayPal Sandbox pilot refunded five New
Zealand dollars, independently verified COMPLETED, with one observed Refund POST
and a durable receipt.

The interactive UI can run genuine DeepSeek cloud or optional local Ollama inference, but its payment execution
is always simulated. A clearly labeled deterministic mode supports offline demos.
The historical provider evidence stays read-only. Unknown means stop without an
automatic retry.

This is a local Sandbox MVP. AI proposes. Humans decide. Receipts prove.”

## Recording boundary

The [curated qualification](../evidence/submission/qa-summary.json) records actual
browser/model verification. UI acceptance defects were corrected and revalidated.
Timed narrated recording, video, upload and competition submission are **NOT RUN**.
Use the simulation for recording; do not perform another genuine refund.
