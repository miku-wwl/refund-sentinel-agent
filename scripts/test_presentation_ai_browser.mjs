// Genuine loopback Ollama qualification is distinct from mocked failure UI checks.
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { presentationReady } from "./presentation_ready.mjs";
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
const base = process.env.SENTINEL_PRESENTATION_URL || "http://127.0.0.1:8880";
assert.equal(new URL(base).hostname, "127.0.0.1");
const output = resolve(
  process.env.SENTINEL_QA_OUTPUT_DIR || ".state-qa",
  "presentation",
);
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const report = {
  status: "PASS",
  browser: await browser.version(),
  live_ollama: { status: "NOT RUN" },
  negative_ui: [],
  visuals: [],
  accessibility: [],
  unexpected_errors: [],
  external_browser_requests: 0,
  genuine_paypal_requests: 0,
};
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
});
await context.route("**/*", (route) => {
  if (new URL(route.request().url()).origin !== new URL(base).origin) {
    report.external_browser_requests++;
    return route.abort();
  }
  assert.ok(!new URL(route.request().url()).pathname.startsWith("/api/"));
  return route.continue();
});
const page = await context.newPage();
page.on("pageerror", (error) => report.unexpected_errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") report.unexpected_errors.push(message.text());
});
const saved = async () =>
  (await page.request.get(base + "/presentation/demo")).json();
async function gate(operation) {
  await page.locator(`[data-demo="${operation}"]`).click();
  await page.locator("#confirm-accept").click();
}
async function screenshot(name) {
  await page.evaluate(() => window.scrollTo(0, 0));
  const ready = await presentationReady(page);
  assert.equal(ready.opacity, 1);
  assert.equal(ready.horizontal_overflow, false);
  await page.screenshot({
    path: resolve(output, name + ".png"),
    fullPage: true,
  });
  return ready;
}
async function axe(label) {
  await page.evaluate(readFileSync(process.env.AXE_CORE_PATH, "utf8"));
  const result = await page.evaluate(() =>
    window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  report.accessibility.push({
    screen: label,
    violations: result.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  });
  assert.equal(
    result.violations.length,
    0,
    JSON.stringify(report.accessibility.at(-1)),
  );
}
try {
  await page.goto(base + "/#demo");
  await page.locator("#planning-mode").waitFor();
  assert.equal(
    await page.locator("#planning-mode").inputValue(),
    "deterministic",
  );
  await page.locator("#planning-mode").selectOption("local_ai");
  await page.locator('[data-demo="load"]').first().click();
  await page
    .getByRole("button", { name: "Generate Live Ollama Plan", exact: true })
    .waitFor();
  const empty = await saved();
  assert.equal(empty.analysis_source, "NOT_GENERATED");
  const started = performance.now();
  const generation = page.waitForResponse(
    (response) => response.url().endsWith("/demo/generate"),
    { timeout: 55000 },
  );
  await page.locator('[data-demo="generate"]').click();
  const response = await generation;
  const result = await response.json();
  if (response.status() !== 200) {
    report.status = "PARTIAL";
    report.live_ollama = {
      status: "BLOCKED",
      http: response.status(),
      error: result.error,
      browser_seconds: (performance.now() - started) / 1000,
    };
    assert.deepEqual(await saved(), empty);
    await screenshot("16-local-ai-unavailable");
  } else {
    await page.locator('[data-demo="approve"]').waitFor();
    assert.equal(result.analysis_source, "REAL_LOCAL_OLLAMA");
    assert.equal(result.model, "phi4-mini:latest");
    assert.equal(result.action, null);
    assert.equal(result.simulated_dispatches, 0);
    assert.equal(
      result.plan.steps[0].arguments.capture_id,
      "DEMO0000000000001",
    );
    assert.equal(result.plan.steps[0].arguments.amount, "25.00");
    assert.match(
      await page.locator(".model-result").innerText(),
      /REAL LOCAL OLLAMA/,
    );
    await screenshot("16-live-ollama-plan");
    await axe("live-ollama-awaiting-approval");
    // Exercise stale Plan, wrong Approval and wrong Authorization without new dispatches.
    for (const [operation, state, override, expected] of [
      ["approve", result, { expected_version: 3 }, 409],
      ["approve", result, { plan_digest: "0".repeat(64) }, 409],
    ]) {
      const invalid = await page.request.post(
        base + "/presentation/demo/command",
        {
          headers: { "X-Sentinel-Demo": "simulation" },
          data: {
            operation,
            expected_version: state.run.version,
            plan_digest: state.plan_sha256,
            idempotency_key: crypto.randomUUID(),
            confirmed: true,
            ...override,
          },
        },
      );
      assert.equal(invalid.status(), expected);
    }
    await gate("approve");
    await page.locator('[data-demo="authorize"]').waitFor();
    const pending = await saved();
    assert.equal(pending.action.state, "Pending");
    assert.equal(pending.action.authorized, false);
    const mismatch = await page.request.post(
      base + "/presentation/demo/command",
      {
        headers: { "X-Sentinel-Demo": "simulation" },
        data: {
          operation: "authorize",
          expected_version: 1,
          plan_digest: "0".repeat(64),
          idempotency_key: crypto.randomUUID(),
          confirmed: true,
        },
      },
    );
    assert.equal(mismatch.status(), 409);
    await gate("authorize");
    await page.locator('[data-demo="execute"]').waitFor();
    assert.equal((await saved()).simulated_dispatches, 0);
    await gate("execute");
    await page
      .getByText("Simulation verified COMPLETED", { exact: false })
      .waitFor();
    const completed = await saved();
    assert.equal(completed.action.state, "Succeeded");
    assert.equal(completed.action.version, 4);
    assert.equal(completed.simulated_dispatches, 1);
    assert.equal(completed.receipt.source, "SIMULATED_PROVIDER");
    await screenshot("17-live-ai-simulation-completed");
    await axe("live-ai-synthetic-receipt");
    await page.reload();
    await page
      .getByText("Simulation verified COMPLETED", { exact: false })
      .waitFor();
    assert.equal((await saved()).receipt.id, completed.receipt.id);
    report.live_ollama = {
      status: "PASS",
      inference_http: 200,
      model: result.model,
      inference_seconds: result.model_seconds,
      source: result.analysis_source,
      synthetic_capture: completed.capture_id,
      plan_sha256: result.plan_sha256,
      run_id: result.run.id,
      action_id: completed.action.id,
      final_state: "Succeeded v4",
      receipt_id: completed.receipt.id,
      receipt_source: "SIMULATED_PROVIDER",
      synthetic_dispatches: 1,
      real_paypal_dispatches: 0,
      gates: "Three separate browser confirmations",
      reload_receipt_preserved: true,
      negative_binding_checks: 3,
    };
  }
  // All screens at all requested recording sizes; actual rendering and axe, no API mocks.
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    for (const screen of ["overview", "review", "trust", "evidence", "demo"]) {
      await page.locator(`nav a[data-screen="${screen}"]`).click();
      await page
        .locator(`nav a[data-screen="${screen}"][aria-current="page"]`)
        .waitFor();
      const name = `quality-${viewport.width}-${screen}`;
      const ready = await screenshot(name);
      const sizes = await page.evaluate(() => ({
        title: getComputedStyle(document.querySelector("h1")).fontSize,
        button: document.querySelector("#main .button")
          ? getComputedStyle(document.querySelector("#main .button")).fontSize
          : null,
        evidence_row: document.querySelector(".data-row")
          ? getComputedStyle(document.querySelector(".data-row")).fontSize
          : null,
      }));
      const clipped = await page.evaluate(() => {
        const selectors =
          "#main h1,#main h2,#main h3,#main .button,#main label,#main .data-row dd,#main .badge";
        return [...document.querySelectorAll(selectors)]
          .filter(
            (node) =>
              node.clientWidth > 0 &&
              node.getBoundingClientRect().height > 0 &&
              node.scrollWidth > node.clientWidth + 1,
          )
          .map((node) => ({
            tag: node.tagName,
            text: node.textContent.slice(0, 80),
          }));
      });
      assert.deepEqual(
        clipped,
        [],
        `${viewport.width}/${screen}: ${JSON.stringify(clipped)}`,
      );
      report.visuals.push({
        screen,
        viewport,
        ...ready,
        sizes,
        clipped_critical_elements: clipped,
      });
      await axe(name);
    }
  }
  await page.locator('nav a[data-screen="evidence"]').click();
  await page.getByRole("heading", { name: "Evidence provenance" }).waitFor();
  const references = await page
    .locator(".evidence-links a")
    .evaluateAll((links) => links.map((a) => a.href));
  assert.equal(references.length, 2);
  assert.ok(
    references.every((url) =>
      url.includes("04fac090b6aa0a77ef1c50b9e6b451404fccc58f"),
    ),
  );
  report.public_evidence_references = references;
  // Synthetic HTTP errors qualify UI handling only; real parser negatives are pytest contracts.
  for (const [label, code, status] of [
    ["invalid-output", "INVALID_MODEL_RESPONSE", 400],
    ["unavailable", "MODEL_UNAVAILABLE", 502],
    ["expired", "LOCAL_AI_REQUEST_EXPIRED", 504],
    ["unapproved-proposal", "MANUAL_REVIEW_REQUIRED", 400],
  ]) {
    const negative = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    await negative.route("**/presentation/demo/generate", (route) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify({ error: code }),
      }),
    );
    const p = await negative.newPage();
    await p.goto(base + "/#demo");
    await p.locator("#planning-mode").selectOption("local_ai");
    await p.locator('[data-demo="load"]').first().click();
    await p.locator('[data-demo="generate"]').waitFor();
    const before = await (
      await p.request.get(base + "/presentation/demo")
    ).json();
    await p.locator('[data-demo="generate"]').click();
    await p.locator("#notice").filter({ hasText: code }).waitFor();
    assert.deepEqual(
      await (await p.request.get(base + "/presentation/demo")).json(),
      before,
    );
    assert.equal(await p.locator('[data-demo="approve"]').count(), 0);
    assert.match(
      await p.locator(".mode-hint").innerText(),
      /no automatic fallback/,
    );
    await p.locator('[data-demo="fallback"]').click();
    await p.locator("#confirm-accept").click();
    await p
      .getByRole("button", { name: "Generate simulated Plan", exact: true })
      .waitFor();
    assert.equal(
      (await (await p.request.get(base + "/presentation/demo")).json())
        .planning_mode,
      "deterministic",
    );
    report.negative_ui.push({
      case: label,
      transport: "MOCKED_BROWSER_HTTP",
      state_preserved: true,
      manual_fallback: true,
      automatic_gates: 0,
      financial_dispatches: 0,
    });
    await negative.close();
  }
  assert.equal(report.unexpected_errors.length, 0);
  assert.equal(report.external_browser_requests, 0);
  console.log(
    JSON.stringify({
      status: report.status,
      live_ollama: report.live_ollama,
      visual_checks: report.visuals.length,
      accessibility: report.accessibility.length,
      negative_ui: report.negative_ui.length,
    }),
  );
} catch (error) {
  report.status = "FAIL";
  report.failure = String(error).slice(0, 1000);
  throw error;
} finally {
  writeFileSync(
    resolve(output, "phase31-browser-verification.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await context.close();
  await browser.close();
}
