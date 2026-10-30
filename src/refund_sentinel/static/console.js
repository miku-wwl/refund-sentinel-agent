import {
  escapeHTML as e,
  demoNext,
  commandBody,
  workflowProgress,
  hasExecutablePlan,
  money,
  seconds,
} from "./console-state.mjs";

const paths = {
  shield: "M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z M8 12l3 3 5-6",
  grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  brain:
    "M9 4a3 3 0 0 0-5 3 4 4 0 0 0-1 7 4 4 0 0 0 6 5V4Z M15 4a3 3 0 0 1 5 3 4 4 0 0 1 1 7 4 4 0 0 1-6 5V4Z M7 9l2 2 M17 9l-2 2 M6 15h3 M18 15h-3",
  layers: "M12 3 2 8l10 5 10-5-10-5Z M2 12l10 5 10-5 M2 16l10 5 10-5",
  receipt: "M5 3h14v18l-3-2-4 2-4-2-3 2V3Z M8 7h8 M8 11h8 M8 15h4",
  play: "m9 5 11 7-11 7V5Z",
  check: "m5 12 4 4 10-10",
  arrow: "M4 12h16 m-6-6 6 6-6 6",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 7v5l3 2",
  lock: "M6 10h12v11H6z M8 10V7a4 4 0 0 1 8 0v3 M12 14v3",
  bolt: "m13 2-8 12h6l-1 8 9-12h-6l0-8Z",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 11v6 M12 7h.01",
  refresh: "M20 11a8 8 0 1 0-2 6 M20 4v7h-7",
  dollar: "M12 2v20 M17 6H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H7",
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.shield}"/></svg>`;
document.querySelectorAll("[data-icon]").forEach((node) => {
  node.innerHTML = icon(node.dataset.icon);
});
const names = {
  overview: "Operations overview",
  review: "AI refund review",
  trust: "Trust workflow",
  evidence: "Verified execution evidence",
  demo: "Interactive demo",
};
const main = document.querySelector("#main");
let proof = null,
  demo = null,
  busy = false,
  busyOperation = null,
  uncertain = false,
  selectedState = "Awaiting Approval";
let modalResolve = null;
const titles = [
  "AI Plan",
  "Validation",
  "Human Approval",
  "Action Admission",
  "Authorization",
  "Execute Once",
  "Provider",
  "Verification",
  "Receipt",
];
const explanations = [
  "Structured proposal",
  "Trusted constraints",
  "Exact Plan binding",
  "Durable Action",
  "Independent grant",
  "Separate permission",
  "Original capture",
  "Independent GET",
  "Persisted evidence",
];
const glossary = {
  "Awaiting Approval":
    "A validated Plan is ready for human review. No Action has been authorized and no refund is dispatched.",
  Approved:
    "The human approved the exact immutable Plan. Approval alone grants no execution authority.",
  Pending:
    "The approved Plan has been admitted as a durable Action. Independent Authorization is still required.",
  Authorized:
    "A separate grant binds this Action and its execution scope. A further one-time permission precedes dispatch.",
  Executing:
    "The Runtime durably claimed an attempt. Provider acknowledgment and independent verification may still fail.",
  Succeeded:
    "The effect is independently verified and a durable receipt references the completed refund.",
  Failed:
    "A definitive failure was recorded. This terminal Action cannot be reused.",
  Unknown:
    "An effect may have happened remotely. Stop with no automatic retry or reconciliation.",
};
const badge = (text, tone = "info") =>
  `<span class="badge ${tone}">${e(text)}</span>`;
const row = (label, value, mono = false) =>
  `<div class="data-row"><dt>${e(label)}</dt><dd${mono ? ' class="mono"' : ""}>${e(value)}</dd></div>`;
const rows = (values) =>
  `<dl class="data-list">${values.map((v) => row(...v)).join("")}</dl>`;
const button = (label, attributes = "", kind = "", glyph = "arrow") =>
  `<button type="button" class="button ${kind}" ${attributes}>${icon(glyph)}${e(label)}</button>`;
const intro = (title, description, marker = badge("HISTORICAL · READ ONLY")) =>
  `<div class="page-intro"><div><div class="eyebrow">REFUND SENTINEL / ${e(names[currentScreen()].toUpperCase())}</div><h1>${e(title)}</h1><p>${e(description)}</p></div>${marker}</div>`;
const note = () =>
  `<div class="archived-note">${icon("info")}Archived genuine Sandbox evidence · observed ${e(new Date(proof.observed_at).toLocaleString("en-NZ", { timeZone: "UTC" }))} UTC · no live API query.</div>`;
function flow(complete = 9, stopped = false) {
  return `<div class="flow" aria-label="Trust workflow">${titles.map((label, i) => `<div class="flow-step ${i < complete ? "done" : i === complete ? (stopped ? "stopped" : "current") : ""}"><span class="flow-dot">${i < complete ? "✓" : String(i + 1).padStart(2, "0")}</span><strong>${e(label)}</strong><small>${e(explanations[i])}</small></div>`).join("")}</div>`;
}
const checklist = (items) =>
  `<ul class="check-list">${items.map(([title, desc]) => `<li>${icon("check")}<div><strong>${e(title)}</strong><p>${e(desc)}</p></div></li>`).join("")}</ul>`;
function overview() {
  const x = proof.execution;
  return `<div class="hero"><div><div class="eyebrow">AI-POWERED REFUND OPERATIONS</div><h1>A refund.<br><em>With a chain of trust.</em></h1><p>From an AI proposal to a verified payment result. Keep humans in control of every consequential decision.</p><div class="hero-actions"><a class="button" href="#demo">${icon("play")}Start guided demo</a><a class="button secondary" href="#evidence">${icon("receipt")}Inspect real evidence</a></div></div><div class="hero-proof"><div class="proof-head"><span class="icon-box">${icon("shield")}</span><div><small>VERIFIED SANDBOX REFUND</small><strong>One reviewed partial refund</strong></div>${badge("COMPLETED", "success")}</div><div class="proof-money"><span>NZD</span><strong>5.00</strong><span>of NZD 20.00</span></div><div class="proof-line">${icon("check")}Independently verified. Receipt persisted.</div></div></div>
  <div class="metric-grid">${[
    [
      "Original payment",
      "20.00",
      "NZD",
      "Completed capture · historical",
      "dollar",
    ],
    [
      "Verified partial refund",
      "5.00",
      "NZD",
      "PayPal Sandbox · COMPLETED",
      "check",
    ],
    [
      "Financial requests",
      "1",
      "",
      "Exactly one observed Refund POST",
      "shield",
    ],
    [
      "Gateway elapsed",
      "4.767",
      "s",
      "Measured against a 15-second profile",
      "clock",
    ],
  ]
    .map(
      ([label, value, unit, desc, glyph]) =>
        `<div class="metric"><div class="metric-label">${e(label)}${icon(glyph)}</div><div class="metric-value"><span class="unit">${e(unit)}</span>${e(value)}</div><div class="metric-note">${e(desc)}</div></div>`,
    )
    .join("")}</div>
  <div class="grid-two"><section class="panel"><div class="panel-head"><h2>Latest qualified execution</h2>${badge("SUCCEEDED v4", "success")}</div><div class="record-header"><span class="icon-box">${icon("receipt")}</span><div><strong>Human-gated Sandbox pilot</strong><p>A real provider result, preserved for review.</p></div></div>${rows(
    [
      ["Refund ID", x.refund_id, true],
      ["Action", x.action_id, true],
      ["Durable receipt", "Available · independently reopened"],
      ["Execution profile", proof.runtime.profile, true],
    ],
  )}<div class="step-actions">${button("View receipt", 'data-receipt="historical"', "secondary", "receipt")}</div></section>
  <section class="panel"><div class="panel-head"><h2>Trust & policy controls</h2>${icon("lock")}</div>${checklist(
    [
      [
        "Payment identity verified",
        "Original Capture, Order, merchant, amount and currency were cross-checked.",
      ],
      [
        "Three separate human gates",
        "Plan Approval, independent Authorization, then Execute Once permission.",
      ],
      [
        "Immutable execution scope",
        "Pinned Runtime, trusted tool binding and durable effect protection.",
      ],
      [
        "Unknown stops the workflow",
        "No blind retries or automatic reconciliation of an ambiguous effect.",
      ],
    ],
  )}</section></div><div class="section-label"><h2>The verified execution trail</h2><small>Archived evidence · all nine stages completed</small></div>${flow()}${note()}`;
}
function review() {
  const a = proof.analysis;
  return (
    intro(
      "AI recommends. You decide.",
      "Review the original qualified proposal and the exact Plan that humans approved.",
    ) +
    `<div class="grid-two"><section class="panel"><div class="panel-head"><h2>Customer incident</h2><span class="tag">SYNTHETIC TEST DESCRIPTION</span></div><div class="sample-bubble">${e(a.incident_description)}</div>${rows(
      [
        ["Original completed payment", "NZD 20.00"],
        ["Trusted Capture", proof.payment.capture_id, true],
        ["Reason", "Damaged item · partial refund request"],
      ],
    )}<div class="section-label"><h2>Archived AI recommendation</h2>${badge("REAL LOCAL OLLAMA")}</div><div class="quote">${e(a.recommendation.explanation)}</div><div class="review-amount"><span>NZD</span>5.00</div><p>A partial refund of the requested amount. The proposal stays below the original NZD 20.00 payment.</p>${rows(
      [
        ["Model", a.model, true],
        ["Uncertainty", a.recommendation.uncertainty],
        ["Approval", "Exact Plan approved · historical"],
      ],
    )}<div class="callout">This is the preserved <strong>genuine local-model proposal</strong>. Opening this page makes no new model or payment request.</div></section>
  <section class="panel"><div class="panel-head"><h2>Validated execution Plan</h2>${badge("SIDE_EFFECT", "warning")}</div><div class="plan-box"><div class="code-head"><span>IMMUTABLE STRUCTURED PLAN</span><span>VALIDATED</span></div><pre>${e(JSON.stringify(a.plan, null, 2))}</pre></div><div class="fingerprint">Plan review SHA-256<code>${e(a.plan_review_sha256)}</code></div><div class="callout"><strong>Why NZD 5.00?</strong> The customer requested that exact amount. Trusted payment facts and deterministic policy checked currency, merchant, capture eligibility and a bounded partial amount. The model cannot grant authority.</div><div class="step-actions"><a class="button secondary" href="#trust">${icon("layers")}Explore the human gates</a></div></section></div>${note()}`
  );
}
function trust() {
  return (
    intro(
      "Three decisions. One protected effect.",
      "Approval, Authorization and Execute Once permission remain separate.",
    ) +
    `<section class="panel"><div class="panel-head"><h2>From proposal to durable proof</h2>${badge("ARCHIVED SUCCESS", "success")}</div>${flow()}<div class="callout">The shared <strong>Agentic Intent Gate v0.2.0</strong> owns validation, exact Plan binding, grants, durable Action claiming and terminal states. The consumer host records the separate third Execute Once permission.</div></section>
  <div class="gate-grid">${[
    [
      "GATE 01",
      "APPROVE",
      "I approve this exact Plan.",
      "Binds human review to the immutable Plan. It does not authorize payment execution.",
    ],
    [
      "GATE 02",
      "AUTHORIZE",
      "I authorize this specific Action.",
      "A separate grant binds the admitted Action, trusted tool identity and execution scope.",
    ],
    [
      "GATE 03",
      "EXECUTE ONCE",
      "I permit one specific dispatch.",
      "Fresh payment facts must pass. An ambiguous outcome means stop with no automatic retry.",
    ],
  ]
    .map(
      ([gate, title, quote, desc]) =>
        `<section class="gate-card"><span class="gate-number">${gate}</span><h3>${title}</h3><strong>${e(quote)}</strong><p>${e(desc)}</p></section>`,
    )
    .join("")}</div>
  <section class="panel"><div class="panel-head"><h2>Understand the states</h2><small>Explanation only · no state changes</small></div><div class="glossary">${Object.keys(
    glossary,
  )
    .map(
      (state) =>
        `<button type="button" data-state="${e(state)}" aria-pressed="${state === selectedState}">${e(state)}</button>`,
    )
    .join(
      "",
    )}</div><p class="state-description">${e(glossary[selectedState])}</p></section>
  <div class="callout warning"><strong>Unknown is a safety outcome.</strong> A provider may complete the refund while its acknowledgment or verification is lost. Never automatically resend the mutation. The original failed and successful financial Actions are terminal and inaccessible from this demo.</div>${note()}`
  );
}
function evidence() {
  const x = proof.execution;
  return (
    intro(
      "A completed refund. A verifiable record.",
      "Read-only proof of the original genuine PayPal Sandbox transaction.",
    ) +
    `<div class="evidence-banner"><div><span class="inline-label">GENUINE PAYPAL SANDBOX · HISTORICAL</span><h2>NZD 5.00 <span class="green">COMPLETED</span></h2><p>Independent Refund GET matched the returned ID, exact amount, currency and Capture association.</p></div><span class="evidence-mark">${icon("check")}</span></div>
  <div class="grid-two"><section class="panel"><div class="panel-head"><h2>Provider & Runtime identity</h2>${badge("SUCCEEDED v4", "success")}</div>${rows(
    [
      ["Genuine Refund ID", x.refund_id, true],
      ["Original Capture", proof.payment.capture_id, true],
      ["Original Order", proof.payment.order_id, true],
      ["Sandbox merchant", proof.payment.merchant_id, true],
      ["Action ID", x.action_id, true],
      ["Run ID", x.run_id, true],
      ["Refund amount", "NZD 5.00"],
      ["Observed Refund POST count", "Exactly 1"],
    ],
  )}</section>
  <section class="panel"><div class="panel-head"><h2>Measured execution evidence</h2>${icon("clock")}</div><div class="table-wrap" role="region" aria-label="Measured execution evidence table" tabindex="0"><table><thead><tr><th>Operation</th><th>HTTP</th><th>Elapsed</th><th>Result</th></tr></thead><tbody><tr><td>Refund POST</td><td>201</td><td>${seconds(x.post_seconds)}</td><td>COMPLETED</td></tr><tr><td>Independent Refund GET</td><td>200</td><td>${seconds(x.verification_seconds)}</td><td>VERIFIED</td></tr><tr><td>Public Runtime Gateway</td><td>—</td><td>${seconds(x.gateway_seconds)}</td><td>SUCCEEDED</td></tr></tbody></table></div><div class="callout"><strong>15-second trusted Sandbox profile.</strong> This genuine sample finished in 4.766604 seconds. One sample establishes neither p95 latency nor a universal exactly-once guarantee.</div><div class="section-label"><h2>Durable receipt</h2>${badge("PERSISTED", "success")}</div><p class="mono">${e(x.receipt_id)}</p><p>Reopened and independently checked in a new process after execution.</p>${button("Inspect receipt", 'data-receipt="historical"', "secondary", "receipt")}</section></div>
  <section class="panel provenance"><div class="panel-head"><h2>Evidence provenance</h2>${badge("VERIFIED SANDBOX EVIDENCE", "success")}</div><p>The original transaction used genuine PayPal Sandbox APIs. This dashboard presents sanitized recorded evidence; viewing it makes <strong>no current live PayPal query</strong>.</p>${rows(
    [
      [
        "Archived observation (UTC)",
        new Date(proof.observed_at).toISOString(),
        true,
      ],
      [
        "Provider verification",
        "Refund POST HTTP 201 → independent Refund GET HTTP 200 · COMPLETED",
      ],
      [
        "Durable verification",
        "Succeeded v4 · receipt reopened read-only in a separate process",
      ],
      ["Observed genuine dispatches", "Exactly one Refund POST"],
    ],
  )}<div class="evidence-links"><a href="https://github.com/miku-wwl/refund-sentinel-agent/blob/04fac090b6aa0a77ef1c50b9e6b451404fccc58f/evidence/phase2-freeze/verified-refund.json" target="_blank" rel="noopener noreferrer">Sanitized provider evidence ↗</a><a href="https://github.com/miku-wwl/refund-sentinel-agent/blob/04fac090b6aa0a77ef1c50b9e6b451404fccc58f/docs/PHASE2-BACKEND-FREEZE.md" target="_blank" rel="noopener noreferrer">Published backend qualification ↗</a></div><p class="provenance-note">References are pinned to the published Phase 2 freeze. These records describe one historical sample; they do not establish today's refund balance.</p></section>
  <section class="panel"><div class="panel-head"><h2>Evidence boundaries</h2><span class="tag">NO EXECUTABLE CONTROLS</span></div>${checklist(
    [
      [
        "Archived, not a current balance lookup",
        "No new provider requests occur. The archived Order observation is not a complete refund-balance ledger.",
      ],
      [
        "Merchant and relationship validation",
        "The original Capture/Order observations verify merchant identity; Refund GET verifies its up relationship.",
      ],
      [
        "Private records stay private",
        "Only whitelisted facts are shown. No credentials, raw provider payloads, buyer personal data or private ledgers.",
      ],
    ],
  )}<details><summary>Expand technical qualification details</summary><pre>${e(JSON.stringify({ runtime: proof.runtime, plan_review_sha256: proof.analysis.plan_review_sha256, receipt_id: x.receipt_id, three_separate_human_gates_recorded: true }, null, 2))}</pre></details></section>${note()}`
  );
}
const labCases = [
  ["valid_partial", "A · Valid partial refund"],
  ["ambiguous", "B · Ambiguous request"],
  ["excessive", "C · Excessive refund"],
  ["injection", "D · Prompt injection"],
  ["unknown_outcome", "E · Lost acknowledgment → Unknown"],
];
const decisionReasons = {
  DEEPSEEK_KEY_NOT_CONFIGURED:
    "Configure REFUND_SENTINEL_DEEPSEEK_API_KEY or DEEPSEEK_API_KEY in the server environment, then explicitly start a new case. No .env is read.",
  DEEPSEEK_AUTHENTICATION_FAILED:
    "DeepSeek rejected server authentication. No automatic retry or fallback was performed.",
  DEEPSEEK_REQUEST_EXPIRED:
    "The cloud request exceeded its bounded deadline. No executable Plan was created.",
  DEEPSEEK_CASE_NOT_SUPPORTED:
    "DeepSeek supports synthetic cases A–D. Explicitly select Deterministic Demo for the lost-acknowledgment case E.",
  CASE_AMOUNT_UNSPECIFIED:
    "The customer did not specify an amount. A model-invented amount cannot become an executable refund.",
  AMOUNT_OUTSIDE_POLICY:
    "The requested refund exceeds the payment or the USD 100.00 policy maximum. No executable Action was created.",
  CASE_AMOUNT_UNSUPPORTED:
    "The recommendation does not match the amount supported by this synthetic customer case.",
  MANUAL_REVIEW_REQUIRED:
    "The recommendation requires manual review. It cannot become an executable refund.",
  INVALID_MODEL_RESPONSE:
    "The actual response failed strict schema validation. No executable Plan was created.",
  ANALYSIS_INTERRUPTED:
    "Analysis did not finish. This case cannot be regenerated; start a new synthetic case explicitly.",
  DEMO_RUN_NOT_PERSISTED:
    "Policy eligibility alone is insufficient. No matching persistent Runtime Plan was verified; this case cannot proceed.",
  DEMO_PLAN_FINGERPRINT_MISMATCH:
    "The analysis result does not match the persistent Plan fingerprint. This case cannot proceed.",
  DEMO_RUNTIME_PROCESSING_FAILED:
    "Runtime processing failed after policy eligibility. No executable authority is exposed; this case cannot be retried.",
  DEMO_PERSISTENT_PLAN_UNVERIFIABLE:
    "The saved Run and Plan fingerprint cannot be verified. Approval and execution are unavailable.",
  REQUEST_SUPPORTED_POLICY_PASS:
    "The recommendation matches the supported request and passes trusted payment policy. Human Approval and independent Authorization remain mandatory.",
};
function decisionEvidence() {
  const d = demo?.decision;
  if (!d) return "";
  const pass = d.policy_verdict === "PASS" && hasExecutablePlan(demo);
  const human = demo.run?.state === "Approved";
  const stopped =
    d.workflow_status === "FAILED"
      ? "RUNTIME FAILED"
      : d.workflow_status === "INTERRUPTED"
        ? "INTERRUPTED"
        : "BLOCKED";
  return `<section class="panel decision-evidence" aria-label="Decision explanation"><div class="panel-head"><h2>Explain this decision</h2>${badge(pass ? "POLICY PASS · HUMAN GATES REQUIRED" : `${stopped} · NO EXECUTABLE ACTION`, pass ? "info" : "warning")}</div>
    <div class="decision-grid"><div><h3>AI PROPOSAL — UNTRUSTED</h3>${rows([
      ["Actual source", d.source],
      ["Provider", d.provider ?? "Legacy evidence"],
      ["Requested model", d.requested_model ?? "No model"],
      ["Returned model", d.returned_model ?? "Not supplied"],
      ["Finish reason", d.finish_reason ?? "Not supplied"],
      [
        "Refused / truncated",
        `${d.refused ? "Yes" : "No"} / ${d.output_truncated ? "Yes" : "No"}`,
      ],
      ["Schema verdict", d.schema_verdict],
      [
        "Model uncertainty",
        demo.recommendation?.uncertainty ?? "No valid recommendation",
      ],
      [
        "Model duration",
        d.model_seconds == null
          ? "No model duration"
          : seconds(d.model_seconds),
      ],
    ])}<p>Source labels describe this run. A deterministic fixture is not AI inference. Model behavior can vary; injection resistance is not guaranteed.</p><details open><summary>Actual model output / labeled fixture</summary><pre class="decision-output">${e(d.model_output ?? "No usable model text was retained. The failure code below is the actual observed result.")}</pre>${d.output_truncated ? "<p>Output exceeded the evidence limit; the displayed prefix is explicitly truncated.</p>" : ""}</details></div>
    <div><h3>POLICY VERDICT — DETERMINISTIC</h3>${rows([
      ["Trusted source", "Server-owned synthetic case"],
      [
        "Payment",
        `${d.facts.currency} ${d.facts.payment_amount} · ${d.facts.payment_status}`,
      ],
      [
        "Supported request",
        d.facts.requested_amount
          ? `USD ${d.facts.requested_amount}`
          : "Amount unspecified",
      ],
      ["Policy maximum", `USD ${d.facts.policy_maximum}`],
      [
        "Policy eligibility",
        d.policy_eligibility ?? "Legacy record — not recorded",
      ],
      ["Verdict", d.policy_verdict],
      [
        "Runtime readiness",
        d.workflow_status ?? "Legacy record — not recorded",
      ],
      ["Reason code", d.reason],
    ])}<p>${e(decisionReasons[d.reason] ?? "The trusted boundary did not accept this recommendation. No automatic fallback or retry is performed.")}</p>
    <h3>HUMAN AUTHORIZATION — REQUIRED</h3>${rows([
      [
        "Exact Plan Approval",
        human ? "Recorded for this Plan" : "Not recorded",
      ],
      [
        "Independent Authorization",
        demo.action?.authorized ? "Recorded for this Action" : "Not granted",
      ],
      [
        "Execution confirmation",
        ["Executing", "Succeeded", "Failed", "Unknown"].includes(
          demo.action?.state,
        )
          ? "Separate execution attempt recorded"
          : "Not submitted",
      ],
      [
        "Plan / Action",
        d.workflow_status && d.workflow_status !== "READY"
          ? "No executable authority"
          : `${demo.run?.state ?? "No Run"} / ${demo.action?.state ?? "No Action"}`,
      ],
    ])}<h3>PAYMENT EXECUTION — SIMULATED</h3><p>${e(d.workflow_status && d.workflow_status !== "READY" ? "Workflow unavailable. No executable authority. No automatic retry." : demo.action?.state === "Unknown" ? "Unknown: an effect may exist, but completion is unconfirmed. Terminal; no blind retry." : demo.receipt ? "Completed and verified by local FakePayPal; durable simulated Receipt available." : !demo.run ? "Blocked before execution. Zero provider dispatches; no financial Action." : "Waiting for the separate human gates. This provider is local FakePayPal.")}</p><strong>Simulated dispatches: ${e(demo.simulated_dispatches)}</strong></div></div>
    <div class="step-actions"><a class="button secondary" href="/presentation/demo/export" download>Download synthetic evidence</a><small>Sanitized projection only. SHA-256 fingerprints support comparison; no signature or independent authenticity claim.</small></div></section>`;
}
function demoScreen() {
  const cloud = demo?.planning_mode === "deepseek";
  const live = cloud || demo?.planning_mode === "local_ai";
  const inferred = ["REAL_LOCAL_OLLAMA", "REAL_DEEPSEEK_API"].includes(
    demo?.analysis_source,
  );
  const providerLabel = cloud
    ? "DeepSeek Flash — Live Cloud AI"
    : "Local AI Demo — Live Ollama";
  const sourceLabel = cloud ? "REAL DEEPSEEK API" : "REAL LOCAL OLLAMA";
  const planReady = hasExecutablePlan(demo);
  const next = demoNext(demo),
    progress = workflowProgress(demo, busy);
  const state =
    demo?.decision?.workflow_status && demo.decision.workflow_status !== "READY"
      ? progress.state
      : (demo?.action?.state ??
        (demo?.run
          ? "Awaiting Approval"
          : demo?.decision
            ? "Decision blocked"
            : "Sample ready"));
  const gateLabel = {
    generate: cloud
      ? "Generate Live DeepSeek Plan"
      : live
        ? "Generate Live Ollama Plan"
        : "Generate simulated Plan",
    approve: "Approve Plan",
    admit: "Admit approved Action",
    authorize: "Authorize Action",
    execute: "Execute Simulation",
  };
  const instructions = {
    generate: cloud
      ? "Send this server-owned synthetic case to DeepSeek Flash. Validate before creating a persistent Run. No payment dispatch."
      : live
        ? "Call phi4-mini:latest locally. Validate before creating a Plan. No payment dispatch."
        : "The simulated recommendation is deterministic. No live AI or PayPal call.",
    approve: "Review the exact Plan. This gate cannot execute a refund.",
    admit: "Complete admission of the previously approved Plan.",
    authorize:
      "Admission alone cannot execute. Grant independent Authorization.",
    execute:
      "Review the synthetic effect, then separately permit one simulation.",
  };
  return (
    intro(
      "AI Decision Lab. Authority stays verified.",
      "Choose genuine DeepSeek cloud AI, local Ollama or an offline fixture. Payments stay synthetic.",
      badge("DEMO MODE — SIMULATED", "warning"),
    ) +
    `<div class="demo-banner"><strong>DEMO MODE — SIMULATED PAYMENTS</strong><span>Synthetic USD 120.00 payment · Refund bounded by case and policy · No real PayPal requests · ${cloud ? "Cloud AI proposal / fake execution" : live ? "Local AI proposal / fake execution" : "Deterministic Demo / no AI call"}</span></div>
  <div class="demo-controls"><div class="control-field"><label for="planning-mode">Proposal mode</label><select id="planning-mode" ${busy ? "disabled" : ""}><option value="deepseek" ${cloud ? "selected" : ""}>DeepSeek Flash — Live Cloud AI (preferred live)</option><option value="local_ai" ${live && !cloud ? "selected" : ""}>Local AI Demo — Live Ollama</option><option value="deterministic" ${!live ? "selected" : ""}>Deterministic Demo — offline</option></select></div><div class="control-field"><label for="scenario">Synthetic case</label><select id="scenario" ${busy ? "disabled" : ""}><optgroup label="AI Decision Lab — preserved decision evidence">${labCases.map(([id, label]) => `<option value="${id}" ${demo?.scenario === id ? "selected" : ""}>${e(label)}</option>`).join("")}</optgroup><optgroup label="Original demonstrations"><option value="completed" ${demo?.scenario === "completed" ? "selected" : ""}>Completed + verified</option><option value="unknown" ${demo?.scenario === "unknown" ? "selected" : ""}>Lost acknowledgment → Unknown</option><option value="rejected" ${demo?.scenario === "rejected" ? "selected" : ""}>Definitive rejection → Failed</option></optgroup></select></div>${button(demo ? "Start new simulation" : "Load sample incident", 'data-demo="load" ' + (busy ? "disabled" : ""), "secondary", "refresh")}${button("Refresh saved state", 'data-demo="refresh" ' + (busy ? "disabled" : ""), "ghost", "refresh")}</div><p class="mode-hint">Mode applies to a new simulation. ${cloud ? "Current case: DeepSeek V4.1 Flash 1017 (official alias mapping). Cloud inference has a 30-second total limit. The returned model ID does not independently attest to an immutable build." : live ? "Current case: Local AI Demo. Inference has a 45-second total limit." : "Deterministic Demo starts offline; select DeepSeek for the preferred live demonstration."} There is no automatic fallback. Case E uses an explicitly selected deterministic fixture. <a href="#evidence">Inspect historical PayPal evidence</a>.</p>
  <div class="demo-stage"><div><h2>${demo ? e(state) : "Open a synthetic incident"}</h2><p>${demo ? "Fresh synthetic scope. Original financial Actions remain untouched." : "Load the sample to begin. Each decision is explicit."}</p></div>${demo ? badge(state, progress.stopped ? "warning" : state === "Succeeded" ? "success" : "info") : ""}</div>
  ${demo && next && !uncertain ? `<section class="demo-next-step" aria-label="Next simulation step"><div><strong>Your next decision</strong><p>${e(instructions[next])}</p></div>${button(gateLabel[next], `data-demo="${next}" ${busy ? "disabled" : ""}`, next === "execute" ? "amber" : "", next === "generate" ? "brain" : next === "execute" ? "play" : "lock")}</section>` : ""}
  ${demo ? flow(progress.complete, progress.stopped) : ""}
  ${busy ? `<div class="processing" role="status"><span class="spinner"></span><div><strong>${busyOperation === "execute" ? "Executing synthetic refund through the public Runtime" : busyOperation === "generate" && live ? `Generating a genuine ${cloud ? "DeepSeek cloud" : "local Ollama"} proposal` : "Recording the simulation step"}</strong><p>${busyOperation === "generate" && live ? `${cloud ? "deepseek-flash" : "phi4-mini:latest"} · synthetic incident only · bounded output · no gate is automatically approved` : "Durable claiming and verification use the pinned Runtime. This payment provider is entirely local."}</p></div></div>` : ""}
  ${uncertain ? '<div class="callout warning"><strong>Response unavailable.</strong> No automatic resend. Refresh saved state to inspect the simulation before taking another step.</div>' : ""}
  <div class="demo-grid"><section class="panel"><div class="panel-head"><h2>Synthetic refund incident</h2><span class="tag">SAMPLE DATA</span></div><div class="sample-meta"><span>Original payment <strong>USD 120.00</strong></span><span>Requested <strong>${e(demo?.decision ? (demo.decision.facts.requested_amount ? `USD ${demo.decision.facts.requested_amount}` : "Amount unspecified") : demo?.scenario === "ambiguous" ? "Amount unspecified" : demo?.scenario === "excessive" ? "USD 150.00" : "USD 25.00")}</strong></span></div><div class="sample-bubble">${e(demo?.incident_description ?? "Synthetic customer: my item arrived damaged. Please refund USD 25.00.")}</div>${rows(
    [
      ["Capture", "DEMO0000000000001", true],
      ["Merchant", "DEMO-MERCHANT"],
      ["Provider", "Persisted local fake · no HTTP"],
      [
        "Recommendation",
        live
          ? inferred
            ? `Genuine ${cloud ? "DeepSeek cloud" : "local Ollama"} inference`
            : `${providerLabel} selected · not yet accepted`
          : "Simulated deterministic fixture",
      ],
    ],
  )}
  ${demo?.recommendation ? `<div class="callout model-result" data-source="${e(demo.analysis_source)}">${badge(inferred ? sourceLabel : "DETERMINISTIC FIXTURE", inferred ? "success" : "info")}<h3>Recommendation: ${e(demo.recommendation.recommendation)} ${e(demo.recommendation.currency ?? "")} ${e(demo.recommendation.requested_amount ?? "Amount unspecified")}</h3><p>${e(demo.recommendation.explanation)}</p>${inferred ? `<p>Requested model: <strong>${e(demo.model)}</strong> · inference ${seconds(demo.model_seconds)} · ${demo.decision?.policy_verdict === "BLOCKED" ? "trusted boundary blocked execution" : planReady ? "schema and trusted policy passed" : "proposal has no executable authority"}</p>` : ""}</div>` : ""}
  ${live ? `<div class="step-actions">${button("Switch to Deterministic Demo", 'data-demo="fallback" ' + (busy ? "disabled" : ""), "ghost", "refresh")}<small>Manual fallback creates a new synthetic case and retains this record.</small></div>` : ""}
  ${!demo ? `<div class="step-actions">${button("Load sample incident", 'data-demo="load" ' + (busy ? "disabled" : ""), "", "play")}</div>` : ""}
  </section><section class="panel"><div class="panel-head"><h2>${planReady ? "Exact synthetic Plan" : "Your Plan will appear here"}</h2>${planReady ? badge("VALIDATED", "success") : icon("brain")}</div>
  ${
    planReady
      ? `<div class="plan-box"><div class="code-head"><span>${inferred ? sourceLabel : "DETERMINISTIC FIXTURE"} / REAL VALIDATION</span><span>SIDE_EFFECT</span></div><pre>${e(JSON.stringify(demo.plan, null, 2))}</pre></div><div class="fingerprint">Exact Plan SHA-256<code>${e(demo.plan_sha256)}</code></div>${rows(
          [
            ["Run", demo.run.id, true],
            ["Run state", `${demo.run.state} v${demo.run.version}`],
            ["Action", demo.action?.id ?? "Not admitted", true],
            [
              "Authorization",
              demo.action?.authorized
                ? "Independent grant recorded"
                : "Not granted",
            ],
            ["Synthetic dispatches", String(demo.simulated_dispatches)],
          ],
        )}`
      : `<div class="empty-card"><span class="icon-box">${icon("layers")}</span><h3>${demo?.decision ? "No executable refund" : "Begin with a proposal"}</h3><p>${demo?.decision ? e(decisionReasons[demo.decision.reason] ?? "The observed response did not produce an executable Plan. Review the decision evidence below.") : live ? `Generate a genuine ${cloud ? "DeepSeek cloud" : "local Ollama"} recommendation for this synthetic incident. Payment execution remains simulated.` : "Load the sample and generate a deterministic recommendation. No model is called; payment execution remains simulated."}</p><span class="tag">NO FINANCIAL AUTHORITY</span></div>`
  }
  </section></div>${decisionEvidence()}
  ${demo?.action && ["Unknown", "Failed"].includes(demo.action.state) ? `<div class="callout warning"><strong>${e(demo.action.state)} — this Action is terminal.</strong> ${demo.action.state === "Unknown" ? "An effect may exist, but the Runtime outcome was not confirmed as successful. No successful receipt is claimed." : "A definitive failure was recorded. No completed effect is claimed."} No retry, reauthorization or automatic reconciliation is offered. A new simulation creates a different synthetic scope and retains this record.</div>` : ""}
  ${demo?.receipt ? `<div class="receipt-strip"><div><h3>${icon("check")} Simulation verified COMPLETED</h3><p>USD 25.00 · ${e(demo.action.state)} v${demo.action.version} · one local fake dispatch · durable receipt</p></div>${button("Open simulated receipt", 'data-receipt="simulation"', "secondary", "receipt")}</div>` : ""}
  ${demo?.action ? `<details><summary>Show synthetic Action identity and scope</summary><pre>${e(JSON.stringify(demo.action, null, 2))}</pre></details>` : ""}
  <div class="archived-note">${icon("shield")}This page uses isolated synthetic state and the default five-second adapter budget. Reset retains earlier simulations and creates a fresh scope.</div>`
  );
}
function currentScreen() {
  const key = location.hash.slice(1);
  return Object.hasOwn(names, key) ? key : "overview";
}
function render() {
  if (!proof) return;
  const screen = currentScreen();
  document.querySelector("#page-name").textContent = names[screen];
  document.title = `${names[screen]} — Refund Sentinel`;
  const environment = document.querySelector(".environment");
  environment.classList.toggle("simulated", screen === "demo");
  environment.innerHTML =
    screen === "demo"
      ? "<i></i>SIMULATED PAYMENTS <span>NO PAYPAL REQUESTS</span>"
      : "<i></i>PAYPAL SANDBOX <span>ARCHIVED PROOF</span>";
  document.querySelectorAll("nav a").forEach((a) => {
    if (a.dataset.screen === screen) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  main.innerHTML = `<div class="screen-fade">${{ overview, review, trust, evidence, demo: demoScreen }[screen]()}</div>`;
}
function notice(message) {
  const node = document.querySelector("#notice");
  node.innerHTML = `${e(message)} <button type="button" data-dismiss>Dismiss</button>`;
  node.classList.remove("hidden");
}
async function api(path, body, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`/presentation/${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers:
        body === undefined
          ? {}
          : {
              "Content-Type": "application/json",
              "X-Sentinel-Demo": "simulation",
            },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(
        "The presentation service returned an unreadable response.",
      );
    }
    if (!response.ok)
      throw new Error(
        `${data.error || "Presentation request failed"} (${response.status}). No automatic retry was sent.`,
      );
    return data;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error("The response timed out. No automatic retry was sent.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
function confirmGate(operation) {
  const dialog = document.querySelector("#confirmation");
  const copy = {
    approve: [
      "GATE 1 / SIMULATION ONLY",
      "Approve this exact synthetic Plan?",
      "Approve Plan",
      "Approval binds this immutable Plan. It does not grant Authorization or execute the synthetic effect.",
    ],
    admit: [
      "ADMISSION / SIMULATION ONLY",
      "Admit the approved synthetic Plan?",
      "Admit Action",
      "The Plan is already approved. Admission creates a Pending Action and grants no execution authority.",
    ],
    authorize: [
      "GATE 2 / SIMULATION ONLY",
      "Authorize this synthetic Action?",
      "Authorize Action",
      "This independent grant applies only to the displayed admitted Action and its original scope. It does not execute yet.",
    ],
    execute: [
      "GATE 3 / SIMULATION ONLY",
      "Permit exactly one synthetic dispatch?",
      "Execute Simulation",
      "The default Runtime adapter limit is five seconds. Unknown means stop, with no automatic retry. This is a local fake provider; no PayPal HTTP request is possible.",
    ],
    load: [
      "NEW ISOLATED SIMULATION",
      "Start a new synthetic simulation?",
      "Start new simulation",
      "The current record is retained. A fresh synthetic scope is created; no historical payment state is reset.",
    ],
  };
  const [kind, title, accept, description] = copy[operation];
  document.querySelector("#confirm-kind").textContent = kind;
  document.querySelector("#confirm-title").textContent = title;
  document.querySelector("#confirm-accept").textContent = accept;
  document.querySelector("#confirm-content").innerHTML =
    `<p>${e(description)}</p>${
      operation === "load"
        ? ""
        : rows([
            ["Amount", "USD 25.00 (SIMULATED)"],
            ["Capture", "DEMO0000000000001", true],
            ["Merchant", "DEMO-MERCHANT"],
            ["Plan SHA-256", demo.plan_sha256, true],
            ...(demo.action
              ? [
                  ["Action", demo.action.id, true],
                  ["Effect key", demo.action.effect_key, true],
                  ["Scope", demo.action.execution_scope, true],
                ]
              : []),
          ])
    }`;
  dialog.showModal();
  document.querySelector("#confirm-cancel").focus();
  return new Promise((resolve) => {
    modalResolve = resolve;
  });
}
function settleConfirmation(accepted) {
  document.querySelector("#confirmation").close();
  if (modalResolve) {
    modalResolve(accepted);
    modalResolve = null;
  }
}
document
  .querySelector("#confirm-cancel")
  .addEventListener("click", () => settleConfirmation(false));
document
  .querySelector("#confirm-accept")
  .addEventListener("click", () => settleConfirmation(true));
document.querySelector("#confirmation").addEventListener("cancel", (event) => {
  event.preventDefault();
  settleConfirmation(false);
});
function openReceipt(type) {
  const historical = type === "historical",
    x = historical ? proof.execution : demo?.receipt;
  if (!x) return;
  document.querySelector("#receipt-title").textContent = historical
    ? "Verified historical receipt"
    : "Simulated durable receipt";
  document.querySelector("#receipt-content").innerHTML =
    `${badge(historical ? "GENUINE SANDBOX · HISTORICAL" : "DEMO MODE — SIMULATED", historical ? "success" : "warning")}<div class="receipt-details">${rows(
      [
        ["Receipt", historical ? x.receipt_id : x.id, true],
        ["Refund", x.refund_id, true],
        ["Amount", money(x.amount, x.currency)],
        ["Status", historical ? x.refund_status : x.status],
        ["Action", historical ? x.action_id : demo.action.id, true],
        ["Persisted", "Yes"],
        [
          "Verification",
          historical
            ? "Independent provider GET + new-process receipt check"
            : "Independent local fake lookup",
        ],
        [
          "Evidence source",
          historical
            ? "Archived genuine PayPal Sandbox"
            : "Local simulated provider",
        ],
      ],
    )}</div><div class="callout">${historical ? "This immutable proof view cannot dispatch or replay the original Action." : "This receipt is persisted by the actual consumer and Runtime integration in an isolated synthetic directory. It is not another PayPal transaction."}</div>`;
  document.querySelector("#receipt-dialog").showModal();
  document.querySelector("#receipt-close").focus();
}
document
  .querySelector("#receipt-close")
  .addEventListener("click", () =>
    document.querySelector("#receipt-dialog").close(),
  );
async function runDemo(operation) {
  if (busy) return;
  const planning_mode =
    operation === "fallback"
      ? "deterministic"
      : document.querySelector("#planning-mode")?.value ||
        demo?.planning_mode ||
        "deterministic";
  if (operation === "fallback") operation = "load";
  const scenario =
    document.querySelector("#scenario")?.value || demo?.scenario || "completed";
  if (
    (["approve", "admit", "authorize", "execute"].includes(operation) ||
      (operation === "load" && demo)) &&
    !(await confirmGate(operation))
  )
    return;
  busy = true;
  busyOperation = operation;
  render();
  let poll;
  try {
    if (operation === "load")
      demo = await api("demo", { scenario, planning_mode });
    else if (operation === "refresh") demo = await api("demo");
    else if (operation === "generate")
      demo = await api(
        "demo/generate",
        { scenario: demo.scenario, planning_mode: demo.planning_mode },
        demo.planning_mode === "deepseek"
          ? 35000
          : demo.planning_mode === "local_ai"
            ? 50000
            : 12000,
      );
    else {
      const body = commandBody(demo, operation, crypto.randomUUID());
      const sessionId = demo.session_id;
      const result = api("demo/command", body);
      if (operation === "execute")
        poll = setInterval(async () => {
          try {
            const current = await api("demo");
            if (busy && current?.session_id === sessionId) {
              demo = current;
              render();
            }
          } catch {} // Observe local Runtime state only. Never resend or query a provider.
        }, 250);
      demo = await result;
    }
    uncertain = false;
  } catch (error) {
    notice(error.message);
    if (operation === "execute") uncertain = true;
  } finally {
    clearInterval(poll);
    busy = false;
    busyOperation = null;
    render();
    const next = demoNext(demo);
    (
      main.querySelector(`[data-demo="${next}"]`) ||
      main.querySelector('[data-receipt="simulation"]')
    )?.focus({ preventScroll: true });
  }
}
document.querySelector(".skip-link").addEventListener("click", (event) => {
  // Native anchor Enter activation also emits click. Keep the screen/history intact.
  event.preventDefault();
  main.focus({ preventScroll: true });
  main.scrollIntoView({ block: "start", behavior: "instant" });
});
document.addEventListener("click", (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.hasAttribute("data-dismiss"))
    document.querySelector("#notice").classList.add("hidden");
  else if (target.dataset.state) {
    selectedState = target.dataset.state;
    render();
    document
      .querySelector(`[data-state="${CSS.escape(selectedState)}"]`)
      ?.focus();
  } else if (target.dataset.receipt) openReceipt(target.dataset.receipt);
  else if (target.dataset.demo) void runDemo(target.dataset.demo);
});
window.addEventListener("hashchange", () => {
  render();
  main.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
});
async function start() {
  try {
    proof = await api("proof");
    try {
      demo = await api("demo");
    } catch (error) {
      notice(error.message);
    }
    render();
  } catch (error) {
    main.innerHTML = `<section class="panel empty-card"><span class="icon-box">${icon("info")}</span><h1>Verified workspace unavailable</h1><p>${e(error.message)}</p><p>The app has no cached claim of success. Reload when the local presentation server is available.</p><button type="button" id="reload" class="button secondary">Reload workspace</button></section>`;
    document
      .querySelector("#reload")
      .addEventListener("click", () => location.reload());
  }
}
void start();
