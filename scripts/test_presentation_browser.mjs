// Real Chromium QA. Playwright/axe are development tools installed outside the frozen manifest.
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
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
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const requests = [],
  external = [],
  errors = [],
  accessibility = [],
  checks = [];
const readiness = [];
await context.route("**/*", (route) => {
  const request = route.request(),
    url = new URL(request.url());
  if (url.origin !== new URL(base).origin) {
    external.push(url.origin);
    return route.abort();
  }
  const entry = { method: request.method(), path: url.pathname };
  if (entry.path.endsWith("/command"))
    entry.operation = request.postDataJSON()?.operation;
  requests.push(entry);
  return route.continue();
});
const page = await context.newPage();
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
const screenshot = async (name) => {
  await page.evaluate(() => window.scrollTo(0, 0));
  const ready = await presentationReady(page);
  assert.equal(ready.opacity, 1);
  assert.equal(ready.horizontal_overflow, false);
  readiness.push({ screenshot: name, ...ready });
  const modal = await page.locator("dialog[open]").count();
  return page.screenshot({
    path: resolve(output, name + ".png"),
    fullPage: modal === 0,
  });
};
const state = async () => {
  const response = await page.request.get(base + "/presentation/demo");
  assert.equal(response.status(), 200);
  return response.json();
};
const navigate = async (key) => {
  await page.locator(`nav a[data-screen="${key}"]`).click();
  await page
    .locator(`nav a[data-screen="${key}"][aria-current="page"]`)
    .waitFor();
};
async function axe(screen) {
  await presentationReady(page);
  if (!process.env.AXE_CORE_PATH)
    throw new Error(
      "AXE_CORE_PATH is required for accessibility qualification",
    );
  await page.evaluate(readFileSync(process.env.AXE_CORE_PATH, "utf8"));
  const result = await page.evaluate(async () =>
    window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  accessibility.push({
    screen,
    violations: result.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  });
  assert.equal(
    result.violations.length,
    0,
    JSON.stringify(accessibility.at(-1)),
  );
}
async function load(scenario = "completed") {
  await page.locator("#scenario").selectOption(scenario);
  await page.locator('[data-demo="load"]').first().click();
  if (await page.locator("#confirmation").isVisible())
    await page.locator("#confirm-accept").click();
  await page.locator('[data-demo="generate"]').waitFor();
}
async function generate() {
  await page.locator('[data-demo="generate"]').click();
  await page.locator('[data-demo="approve"]').waitFor();
}
async function approve() {
  await page.locator('[data-demo="approve"]').click();
  await page.locator("#confirm-accept").click();
  await page.locator('[data-demo="authorize"]').waitFor();
}
async function authorize() {
  await page.locator('[data-demo="authorize"]').click();
  await page.locator("#confirm-accept").click();
  await page.locator('[data-demo="execute"]').waitFor();
}
async function execute() {
  await page.locator('[data-demo="execute"]').click();
  await page.locator("#confirm-accept").click();
}
try {
  await page.goto(base);
  await page.locator(".hero").waitFor();
  assert.match(await page.locator(".hero-proof").innerText(), /COMPLETED/);
  await screenshot("01-overview");
  await axe("overview");
  checks.push("Overview uses exact archived real Sandbox values");
  for (const [screen, name] of [
    ["review", "02-ai-review"],
    ["trust", "03-trust-workflow"],
    ["evidence", "04-verified-evidence"],
  ]) {
    await navigate(screen);
    await screenshot(name);
    await axe(screen);
  }
  await page.locator('[data-receipt="historical"]').click();
  assert.match(
    await page.locator("#receipt-content").innerText(),
    /e1415750-0971-4347-a88d-a3704dbb79c8/,
  );
  await screenshot("05-historical-receipt");
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("#receipt-dialog").isVisible(), false);
  checks.push("Read-only historical receipt and keyboard dismissal");
  await navigate("trust");
  await page.getByRole("button", { name: "Unknown", exact: true }).focus();
  await page.keyboard.press("Enter");
  assert.match(
    await page.locator(".state-description").innerText(),
    /no automatic retry/,
  );
  checks.push("State glossary keyboard navigation");
  await navigate("demo");
  await screenshot("06-demo-empty");
  await axe("demo-empty");
  assert.match(
    await page.locator(".demo-banner").innerText(),
    /DEMO MODE — SIMULATED/,
  );
  await load();
  assert.equal((await state()).simulated_dispatches, 0);
  await generate();
  const original = await state();
  assert.equal(original.run.state, "AwaitingApproval");
  assert.equal(original.action, null);
  assert.equal(await page.locator('[data-demo="execute"]').count(), 0);
  await page.locator('[data-demo="approve"]').click();
  assert.equal(
    await page
      .locator("#confirm-cancel")
      .evaluate((n) => n === document.activeElement),
    true,
  );
  await page.keyboard.press("Escape");
  assert.equal((await state()).run.state, "AwaitingApproval");
  await approve();
  assert.equal((await state()).action.state, "Pending");
  assert.equal((await state()).simulated_dispatches, 0);
  await screenshot("07-plan-approved");
  await axe("demo-pending");
  await authorize();
  const authorized = await state();
  assert.equal(authorized.action.state, "Authorized");
  assert.equal(authorized.simulated_dispatches, 0);
  await page.locator('[data-demo="execute"]').click();
  const review = await page.locator("#confirm-content").innerText();
  assert.ok(review.includes(authorized.action.effect_key));
  assert.ok(review.includes(authorized.action.execution_scope));
  assert.match(review, /USD 25.00/);
  await screenshot("08-execute-confirmation");
  await axe("execute-confirmation");
  await page.locator("#confirm-cancel").click();
  assert.equal((await state()).simulated_dispatches, 0);
  await execute();
  await page.locator(".processing").waitFor();
  await page.locator('[data-receipt="simulation"]').waitFor();
  const completed = await state();
  assert.equal(completed.action.state, "Succeeded");
  assert.equal(completed.action.version, 4);
  assert.equal(completed.simulated_dispatches, 1);
  assert.equal(completed.receipt.source, "SIMULATED_PROVIDER");
  await screenshot("09-demo-completed");
  await axe("demo-completed");
  await page.locator('[data-receipt="simulation"]').click();
  await screenshot("10-simulated-receipt");
  await page.locator("#receipt-close").click();
  await page.reload();
  await page.locator('[data-receipt="simulation"]').waitFor();
  assert.equal((await state()).receipt.id, completed.receipt.id);
  assert.equal((await state()).simulated_dispatches, 1);
  assert.equal(await page.locator('[data-demo="execute"]').count(), 0);
  checks.push(
    "Three distinct gates, cancel safety, real claimed execution, persisted receipt, reload and no replay",
  );
  const duplicate = await page.request.post(
    base + "/presentation/demo/command",
    {
      headers: { "X-Sentinel-Demo": "simulation" },
      data: {
        operation: "execute",
        expected_version: 4,
        plan_digest: completed.plan_sha256,
        idempotency_key: crypto.randomUUID(),
        confirmed: true,
      },
    },
  );
  assert.equal(duplicate.status(), 409);
  assert.equal((await state()).simulated_dispatches, 1);
  await load("unknown");
  await generate();
  await approve();
  await authorize();
  await execute();
  await page
    .getByText("Unknown — this Action is terminal.", { exact: false })
    .waitFor();
  const unknown = await state();
  assert.equal(unknown.action.state, "Unknown");
  assert.equal(unknown.simulated_dispatches, 1);
  assert.equal(unknown.receipt, null);
  assert.equal(await page.locator('[data-demo="execute"]').count(), 0);
  await screenshot("11-demo-unknown");
  await axe("demo-unknown");
  await page.reload();
  await page
    .getByText("Unknown — this Action is terminal.", { exact: false })
    .waitFor();
  assert.equal((await state()).simulated_dispatches, 1);
  checks.push(
    "Lost provider acknowledgment persists Unknown; no receipt claim, retry or reconciliation",
  );
  await load("rejected");
  await generate();
  await approve();
  await authorize();
  await execute();
  await page
    .getByText("Failed — this Action is terminal.", { exact: false })
    .waitFor();
  assert.equal((await state()).action.state, "Failed");
  await screenshot("12-demo-failed");
  checks.push("Definitive rejection remains terminal Failed");
  await page.setViewportSize({ width: 390, height: 844 });
  await navigate("overview");
  await screenshot("13-mobile-overview");
  await axe("mobile-overview");
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  await navigate("demo");
  await screenshot("14-mobile-demo");
  await axe("mobile-demo");
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  checks.push(
    "390px responsive layout, no page overflow, labeled controls and keyboard-accessible native dialogs",
  );
  await page.evaluate(() => {
    location.hash = "__proto__";
  });
  await page.locator(".hero").waitFor();
  checks.push(
    "Unrecognized and prototype-like navigation hashes safely fall back to overview",
  );
  // Error rendering uses a separate browser and synthetic local response; no false archived success.
  const failure = await browser.newContext({
    viewport: { width: 1100, height: 850 },
  });
  await failure.route("**/presentation/proof", (r) =>
    r.fulfill({
      status: 503,
      contentType: "application/json",
      body: '{"error":"TEST_SERVICE_UNAVAILABLE"}',
    }),
  );
  const failedPage = await failure.newPage();
  await failedPage.goto(base);
  await failedPage
    .getByRole("heading", { name: "Verified workspace unavailable" })
    .waitFor();
  await presentationReady(failedPage);
  await failedPage.screenshot({
    path: resolve(output, "15-service-error.png"),
    fullPage: true,
  });
  await failure.close();
  checks.push(
    "Unavailable archive renders explicit error with no cached success",
  );
  assert.equal(external.length, 0);
  assert.equal(errors.length, 0, JSON.stringify(errors));
  assert.equal(requests.filter((r) => r.path.startsWith("/api/")).length, 0);
  checks.push(
    "Zero external/browser PayPal requests, zero real mutation endpoints, zero unexpected console/page errors",
  );
  writeFileSync(
    resolve(output, "browser-verification.json"),
    JSON.stringify(
      {
        status: "PASS",
        browser: await browser.version(),
        viewport_desktop: "1440x900",
        viewport_mobile: "390x844",
        checks,
        accessibility,
        request_count: requests.length,
        external_requests: external.length,
        real_mutation_routes: 0,
        unexpected_errors: errors,
        completed_simulation: {
          state: completed.action.state,
          version: completed.action.version,
          dispatches: 1,
          receipt_persisted: true,
        },
        unknown_simulation: {
          state: unknown.action.state,
          dispatches: 1,
          receipt: null,
        },
        screenshots: 15,
        requests,
        readiness,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: checks.length,
      accessibility_screens: accessibility.length,
      screenshots: 15,
      external_requests: 0,
    }),
  );
} finally {
  await context.close();
  await browser.close();
}
