// Actual Chromium interactions. Live Ollama and deterministic scenarios are reported separately.
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { presentationReady } from "./presentation_ready.mjs";

const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
const base = process.env.SENTINEL_PRESENTATION_URL || "http://127.0.0.1:8880";
assert.equal(new URL(base).hostname, "127.0.0.1");
// New recording/production evidence must live outside the source tree.
assert.ok(
  process.env.SENTINEL_QA_OUTPUT_DIR,
  "Choose an external QA output directory",
);
const output = resolve(process.env.SENTINEL_QA_OUTPUT_DIR, "decision-lab");
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const report = {
  status: "RUNNING",
  browser: await browser.version(),
  scenarios: [],
  restart_cases: [],
  gates: [],
  screenshots: [],
  accessibility: [],
  layouts: [],
  unexpected_errors: [],
  external_browser_requests: 0,
  genuine_paypal_requests: 0,
  live_ollama: { status: "NOT RUN" },
};
await context.route("**/*", (route) => {
  const url = new URL(route.request().url());
  if (url.origin !== new URL(base).origin) {
    report.external_browser_requests++;
    return route.abort();
  }
  assert.ok(
    !url.pathname.startsWith("/api/"),
    "No financial operations routes",
  );
  return route.continue();
});
const page = await context.newPage();
page.on("pageerror", (error) => report.unexpected_errors.push(error.message));
const saved = async () =>
  (await page.request.get(base + "/presentation/demo")).json();

async function capture(name, modal = false) {
  await page.evaluate(() => window.scrollTo(0, 0));
  const ready = await presentationReady(page);
  assert.equal(ready.horizontal_overflow, false);
  await page.screenshot({
    path: resolve(output, name + ".png"),
    fullPage: !modal,
  });
  report.screenshots.push({
    name,
    source: page.url().endsWith("#evidence")
      ? "HISTORICAL_VERIFIED_PAYPAL_SANDBOX"
      : (await saved())?.analysis_source,
    ...ready,
  });
}
async function axe(label) {
  await page.evaluate(readFileSync(process.env.AXE_CORE_PATH, "utf8"));
  const result = await page.evaluate(() =>
    window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  const violations = result.violations.map((v) => ({
    id: v.id,
    targets: v.nodes.map((n) => n.target),
  }));
  report.accessibility.push({ label, violations });
  assert.equal(violations.length, 0, JSON.stringify(violations));
}
async function load(caseId, mode) {
  await page.locator("#scenario").selectOption(caseId);
  await page.locator("#planning-mode").selectOption(mode);
  await page.locator('[data-demo="load"]').first().click();
  if (await page.locator("#confirmation[open]").count())
    await page.locator("#confirm-accept").click();
  await page.locator('[data-demo="generate"]').waitFor();
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/demo/generate"),
    { timeout: 55000 },
  );
  await page.locator('[data-demo="generate"]').click();
  assert.equal((await response).status(), 200);
  await page.locator(".decision-evidence").waitFor();
  const view = await saved();
  report.scenarios.push({
    case: caseId,
    mode,
    source: view.analysis_source,
    decision: view.decision,
    plan_present: !!view.plan,
    action_present: !!view.action,
    dispatches: view.simulated_dispatches,
  });
  assert.equal(view.action, null);
  assert.equal(view.simulated_dispatches, 0);
  return view;
}
async function gate(operation, screenshot) {
  await page.locator(`[data-demo="${operation}"]`).click();
  await page.locator("#confirmation[open]").waitFor();
  if (screenshot) await capture(screenshot, true);
  const before = await saved();
  await page.locator("#confirm-accept").click();
  const target =
    operation === "approve"
      ? '[data-demo="authorize"]'
      : operation === "authorize"
        ? '[data-demo="execute"]'
        : ".receipt-strip,.callout.warning";
  await page.locator(target).first().waitFor();
  // Wait for the command response/state, not the earlier synthetic Plan projection.
  await page.waitForFunction(() => !document.querySelector(".processing"));
  const after = await saved();
  report.gates.push({
    operation,
    before: before.action?.state ?? before.run?.state,
    after: after.action?.state,
    dispatches: after.simulated_dispatches,
  });
  assert.equal(after.simulated_dispatches, operation === "execute" ? 1 : 0);
  return after;
}

try {
  await page.goto(base + "/#demo");
  await page.locator("#scenario").waitFor();
  let view = await load("valid_partial", "local_ai");
  report.live_ollama = {
    status: view.plan ? "PASS" : "PARTIAL",
    model: view.model,
    seconds: view.model_seconds,
    reason: view.decision.reason,
    source: view.analysis_source,
  };
  await capture("01-valid-ai-proposal");
  await axe("valid-local-ai-proposal");
  if (!view.plan) view = await load("valid_partial", "deterministic");
  assert.ok(view.plan);
  view = await gate("approve", "02-human-approval");
  assert.equal(view.action.authorized, false);
  view = await gate("authorize", "03-independent-authorization");
  view = await gate("execute", "04-execution-confirmation");
  assert.equal(view.action.state, "Succeeded");
  assert.equal(view.receipt.source, "SIMULATED_PROVIDER");
  report.restart_cases.push({
    session_id: view.session_id,
    action: view.action,
    receipt: view.receipt,
    decision: view.decision,
    simulated_dispatches: view.simulated_dispatches,
  });
  await page.locator('[data-receipt="simulation"]').click();
  await capture("05-simulated-receipt", true);
  await axe("simulated-receipt-dialog");
  await page.locator("#receipt-close").click();
  await page.reload();
  await page.locator(".receipt-strip").waitFor();
  assert.deepEqual((await saved()).receipt, view.receipt);
  assert.equal((await saved()).simulated_dispatches, 1);

  for (const caseId of ["ambiguous", "excessive", "injection"]) {
    view = await load(caseId, "local_ai");
    if (caseId !== "injection") {
      assert.equal(view.decision.policy_verdict, "BLOCKED");
      assert.equal(view.plan, null);
      assert.equal(await page.locator('[data-demo="approve"]').count(), 0);
    } else if (view.plan) {
      assert.equal(view.run.state, "AwaitingApproval");
      assert.equal(view.action, null); // A compliant proposal still cannot authorize itself.
    }
    await capture(
      {
        ambiguous: "06-ambiguous-request",
        excessive: "07-policy-denial",
        injection: "08-prompt-injection",
      }[caseId],
    );
    await axe(caseId);
    report.restart_cases.push({
      session_id: view.session_id,
      action: view.action,
      receipt: view.receipt,
      decision: view.decision,
      simulated_dispatches: view.simulated_dispatches,
    });
  }
  // Explicit adversarial fixture demonstrates deterministic containment even if a live model refuses.
  view = await load("injection", "deterministic");
  assert.equal(view.decision.reason, "AMOUNT_OUTSIDE_POLICY");
  await capture("09-injection-adversarial-fixture");

  view = await load("unknown_outcome", "deterministic");
  for (const op of ["approve", "authorize", "execute"]) view = await gate(op);
  assert.equal(view.action.state, "Unknown");
  assert.equal(view.receipt, null);
  report.restart_cases.push({
    session_id: view.session_id,
    action: view.action,
    receipt: view.receipt,
    decision: view.decision,
    simulated_dispatches: view.simulated_dispatches,
  });
  assert.equal(await page.locator('[data-demo="execute"]').count(), 0);
  await capture("10-unknown-terminal-outcome");
  await axe("unknown-terminal");
  await page.reload();
  await page.locator(".decision-evidence").waitFor();
  assert.equal((await saved()).action.state, "Unknown");
  assert.equal((await saved()).simulated_dispatches, 1);

  const downloading = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download synthetic evidence" }).click();
  const download = await downloading;
  await download.saveAs(resolve(output, "synthetic-evidence-export.json"));
  const exported = JSON.parse(
    readFileSync(resolve(output, "synthetic-evidence-export.json"), "utf8"),
  );
  assert.equal(exported.decision.evidence_kind, "SYNTHETIC_DECISION_EVIDENCE");
  assert.equal(exported.action.state, "Unknown");
  assert.equal(exported.receipt, null);
  assert.ok(!JSON.stringify(exported).includes("operator.capability"));
  report.export =
    "PASS · actual browser download of typed synthetic projection";

  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 900 });
    const state = await presentationReady(page);
    assert.equal(state.horizontal_overflow, false);
    report.layouts.push({ width, horizontal_overflow: false });
    await axe(`lab-${width}px`);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('nav a[data-screen="evidence"]').click();
  await page
    .getByRole("heading", { name: "A completed refund. A verifiable record." })
    .waitFor();
  await capture("11-historical-paypal-evidence");
  await axe("historical-evidence");
  assert.equal(report.external_browser_requests, 0);
  assert.equal(report.unexpected_errors.length, 0);
  report.status = report.live_ollama.status === "PASS" ? "PASS" : "PARTIAL";
} catch (error) {
  report.status = "FAIL";
  report.failure = error.message;
  throw error;
} finally {
  writeFileSync(
    resolve(output, "browser-report.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await browser.close();
  console.log(
    JSON.stringify({
      status: report.status,
      scenarios: report.scenarios.length,
      gates: report.gates.length,
      screenshots: report.screenshots.length,
      live_ollama: report.live_ollama,
      axe_scans: report.accessibility.length,
      unexpected_errors: report.unexpected_errors,
      output,
    }),
  );
}
