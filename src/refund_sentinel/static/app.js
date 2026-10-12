"use strict";
const $ = id => document.getElementById(id);
let token = "", current = null, busy = false;
const keys = new Map();
const actionButtons = ["approve", "reject", "admit", "authorize", "execute", "verify"];

async function api(path, body) {
  const response = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"Content-Type": "application/json", ...(token ? {"Authorization": "Bearer " + token} : {})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request rejected. Check the input and reload state.");
  return data;
}
function fact(container, label, value) {
  const div = document.createElement("div"); div.className = "fact";
  const span = document.createElement("span"); span.textContent = label;
  const strong = document.createElement("strong"); strong.textContent = value || "—";
  div.append(span, strong); container.append(div);
}
function render(data) {
  current = data; $("empty").hidden = true; $("incident").hidden = false;
  $("policy").textContent = data.policy || data.analysis_state;
  $("explanation").textContent = data.recommendation?.explanation || "Analysis could not produce an executable refund.";
  $("recommendation").textContent = data.recommendation ? `${data.modes.ai === "real" ? "Model" : "Test fixture"} recommendation: ${data.recommendation.recommendation} · uncertainty ${data.recommendation.uncertainty}` : data.policy;
  $("facts").replaceChildren();
  fact($("facts"), "Capture", data.capture_id);
  fact($("facts"), "Trusted captured amount", data.capture ? `${data.capture.currency} ${data.capture.amount}` : null);
  fact($("facts"), "Merchant", data.capture?.merchant_id);
  fact($("facts"), "Payment evidence", data.capture?.source);
  fact($("facts"), "Capture status", data.capture?.status);
  fact($("facts"), "Proposed refund", data.refund_arguments ? `${data.refund_arguments.currency} ${data.refund_arguments.amount}` : null);
  $("run-state").textContent = data.run?.state || "No plan";
  $("plan-summary").textContent = data.refund_arguments ? `Refund ${data.refund_arguments.currency} ${data.refund_arguments.amount} to the original payment ${data.capture_id}.` : "Policy requires manual review. No executable plan was created.";
  $("fingerprint").textContent = data.plan_digest || "—";
  $("plan").textContent = JSON.stringify(data.run?.plan || null, null, 2);
  $("action-state").textContent = data.action?.state || "No action";
  const isUnknown = data.action?.state === "Unknown";
  $("execution-note").textContent = isUnknown ? "Execution outcome is Unknown. No retry is available. Inspect the provider directly; a read-only status check will not authorize or execute another refund." : "Each control records a separate durable step. Only an authorized action can execute.";
  const evidence = data.evidence || [];
  const latest = [...evidence].reverse().find(row => row.data.refund_id)?.data;
  const fake = data.modes.payment === "offline";
  $("outcome").textContent = data.action?.state === "Succeeded" ? `${fake ? "SIMULATED" : "PayPal Sandbox"} refund verified COMPLETED. The Runtime persisted its receipt.` : isUnknown ? `Runtime: Unknown. Provider: ${latest?.provider_status || "unconfirmed"}. Completion is not established by the local action.` : data.action?.state === "Failed" ? "Execution failed with confirmed no-effect evidence. Inspect observations for the reason." : "No refund has been attempted.";
  $("result-facts").replaceChildren();
  fact($("result-facts"), "Provider refund ID", latest?.refund_id);
  fact($("result-facts"), "Provider status", latest?.provider_status);
  fact($("result-facts"), "Durable receipt", data.action?.result?.receipt_reference);
  fact($("result-facts"), "Local action state", data.action?.state);
  fact($("result-facts"), "Stable request / effect ID", data.action?.effect_key);
  fact($("result-facts"), "Evidence mode", fake ? "SIMULATED PAYMENT" : "PAYPAL SANDBOX");
  $("evidence").textContent = JSON.stringify({action: data.action || null, observations: evidence}, null, 2);
  updateButtons();
}
function updateButtons() {
  $("analyze").disabled = busy || !token;
  $("refresh").disabled = busy || !token;
  for (const id of actionButtons) $(id).disabled = true;
  if (!current || busy || !token) return;
  const run = current.run?.state, action = current.action?.state;
  $("approve").disabled = $("reject").disabled = run !== "AwaitingApproval";
  $("admit").disabled = run !== "Approved" || !!action;
  $("authorize").disabled = action !== "Pending";
  $("execute").disabled = action !== "Authorized";
  $("verify").disabled = !(current.evidence || []).some(row => row.data.refund_id);
}
async function work(task) {
  busy = true; $("error").hidden = true; updateButtons();
  try { await task(); }
  catch (error) { $("error").textContent = error.message; $("error").hidden = false; }
  finally { busy = false; updateButtons(); }
}
async function history() {
  const data = await api("/incidents"); $("history").replaceChildren();
  for (const row of data) {
    const button = document.createElement("button"); button.className = "secondary";
    button.textContent = `${row.capture_id} · ${row.analysis_state}`;
    button.addEventListener("click", () => work(async () => render(await api(`/incidents/${row.id}`))));
    $("history").append(button);
  }
}
$("capability").addEventListener("change", () => work(async () => {
  token = (await $("capability").files[0].text()).trim();
  if (!/^[0-9a-f]{64}$/.test(token)) { token = ""; throw new Error("Invalid capability file."); }
  try { await history(); $("session-status").textContent = "Merchant session unlocked"; }
  catch (error) { token = ""; $("session-status").textContent = "Session locked"; throw error; }
}));
$("request-form").addEventListener("submit", event => {
  event.preventDefault(); work(async () => { render(await api("/incidents", {capture_id: $("capture").value, message: $("message").value})); await history(); });
});
$("refresh").addEventListener("click", () => work(history));
for (const id of actionButtons) $(id).addEventListener("click", () => work(async () => {
  const base = `/incidents/${current.id}`;
  if (id === "verify") { render(await api(base + "/verify", {})); return; }
  const version = id === "approve" || id === "reject" || id === "admit" ? current.run.version : current.action.version;
  const command = {plan_digest: current.plan_digest, expected_version: version};
  if (id === "approve" || id === "reject") command.decision = id;
  else {
    const slot = `${current.id}:${id}:${version}`;
    if (!keys.has(slot)) keys.set(slot, crypto.randomUUID());
    command.idempotency_key = keys.get(slot);
  }
  try { render(await api(base + "/" + (id === "approve" || id === "reject" ? "decision" : id), command)); }
  catch (error) { render(await api(base)); throw error; }
}));
work(async () => {
  const config = await api("/config");
  $("modes").textContent = `Payment: ${config.payment_mode} · AI: ${config.ai_mode}`;
  $("mode-note").textContent = `${config.payment_mode === "offline" ? "Simulated provider. No PayPal payment occurs." : "Real PayPal Sandbox client."} ${config.ai_mode === "real" ? "Real model analysis enabled." : "Deterministic test analysis; no AI is called."}`;
  for (const id of config.capture_ids) { const option = document.createElement("option"); option.value = option.textContent = id; $("capture").append(option); }
});
