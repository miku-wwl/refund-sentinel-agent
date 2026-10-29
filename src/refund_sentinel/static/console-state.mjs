// Presentation helpers only. The installed Runtime owns all durable state transitions.
export const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export function demoNext(view) {
  if (!view) return "load";
  if (view.decision && !view.run) return null;
  if (!view.run) return "generate";
  if (view.run.state === "AwaitingApproval") return "approve";
  if (view.run.state === "Approved" && !view.action) return "admit";
  if (view.action?.state === "Pending") return "authorize";
  if (view.action?.state === "Authorized") return "execute";
  return null;
}
export function commandBody(view, operation, key) {
  if (demoNext(view) !== operation)
    throw new Error("The simulation is not at this gate.");
  return {
    operation,
    confirmed: true,
    expected_version: (["approve", "admit"].includes(operation)
      ? view.run
      : view.action
    ).version,
    plan_digest: view.plan_sha256,
    idempotency_key: key,
  };
}
export function workflowProgress(view, busy = false) {
  const state = view?.action?.state;
  let complete = 0;
  if (view?.run) complete = 2;
  if (view?.run?.state === "Approved") complete = 3;
  if (view?.action) complete = 4;
  if (view?.action?.authorized) complete = 5;
  if (state === "Executing" || (busy && state === "Authorized")) complete = 6;
  if (["Failed", "Unknown"].includes(state)) complete = 6;
  if (state === "Succeeded" && view?.receipt) complete = 9;
  return {
    complete,
    terminal: ["Succeeded", "Failed", "Unknown"].includes(state),
    stopped:
      ["Unknown", "Failed"].includes(state) ||
      view?.decision?.policy_verdict === "BLOCKED",
    state:
      state ??
      view?.run?.state ??
      (view?.decision ? "Decision blocked" : "Sample loaded"),
  };
}
export const money = (value, currency) =>
  `${currency} ${Number(value).toFixed(2)}`;
export const seconds = (value) => `${Number(value).toFixed(3)} s`;
