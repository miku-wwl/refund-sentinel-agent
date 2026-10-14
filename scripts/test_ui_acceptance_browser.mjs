// Consumer UI regression only. All payment operations remain in the local simulation.
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
  "ui-acceptance",
);
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ignoreDefaultArgs: ["--hide-scrollbars"],
  args: ["--disable-features=OverlayScrollbar,FluentOverlayScrollbar"],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
});
const report = {
  status: "RUNNING",
  browser: await browser.version(),
  navigation: [],
  unknown_routes: [],
  layouts: [],
  next_actions: [],
  accessibility: [],
  requests: [],
  unexpected_errors: [],
  external_requests: 0,
  forbidden_routes: 0,
  text_zoom_method:
    "QA-only doubling of snapshotted computed text sizes; not native Firefox text zoom",
};
await context.route("**/*", (route) => {
  const url = new URL(route.request().url());
  if (url.origin !== new URL(base).origin) {
    report.external_requests++;
    return route.abort();
  }
  if (url.pathname.startsWith("/api/")) {
    report.forbidden_routes++;
    return route.abort();
  }
  report.requests.push({
    method: route.request().method(),
    path: url.pathname,
  });
  return route.continue();
});
const page = await context.newPage();
page.on("pageerror", (error) => report.unexpected_errors.push(error.message));
page.on("console", (entry) => {
  if (entry.type() === "error") report.unexpected_errors.push(entry.text());
});
const screens = ["overview", "review", "trust", "evidence", "demo"];
async function active(screen) {
  await page
    .locator(`nav [data-screen="${screen}"][aria-current="page"]`)
    .waitFor();
  await presentationReady(page);
}
async function navigate(screen) {
  await page.locator(`nav [data-screen="${screen}"]`).click();
  await active(screen);
}
async function axe(label) {
  assert.ok(process.env.AXE_CORE_PATH, "AXE_CORE_PATH required");
  await page.evaluate(readFileSync(process.env.AXE_CORE_PATH, "utf8"));
  const result = await page.evaluate(() =>
    window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  const violations = result.violations.map((entry) => ({
    id: entry.id,
    targets: entry.nodes.map((node) => node.target),
  }));
  report.accessibility.push({ screen: label, violations });
  assert.deepEqual(violations, [], label);
}
async function capture(name) {
  await presentationReady(page);
  await page.screenshot({
    path: resolve(output, name + ".png"),
    fullPage: true,
  });
}
try {
  // Real native anchor keyboard activation must not create a route/history entry.
  for (const screen of screens) {
    const previous = screen === "overview" ? "demo" : "overview";
    await page.goto(base + "/#" + previous);
    await active(previous);
    await navigate(screen);
    const before = await page.evaluate(() => ({
      hash: location.hash,
      title: document.title,
      history: history.length,
      content: document.querySelector("main").innerHTML,
    }));
    await page.locator(".skip-link").focus();
    await page.keyboard.press("Enter");
    const after = await page.evaluate(() => ({
      hash: location.hash,
      title: document.title,
      history: history.length,
      content: document.querySelector("main").innerHTML,
      focus: document.activeElement.id,
    }));
    assert.equal(after.focus, "main");
    for (const key of ["hash", "title", "history", "content"])
      assert.equal(after[key], before[key], `${screen} skip ${key}`);
    await page.keyboard.press("Tab");
    assert.ok(
      await page.evaluate(() =>
        document.querySelector("main").contains(document.activeElement),
      ),
    );
    await page.reload();
    await active(screen);
    assert.equal(await page.title(), before.title);
    await page.goBack();
    await active(previous);
    await page.goForward();
    await active(screen);
    report.navigation.push({
      screen,
      keyboard_enter: true,
      focus: "main",
      route_preserved: true,
      history_entry_added: false,
      reload: true,
      back_forward: true,
    });
    await capture("skip-" + screen);
    await axe("skip-" + screen);
  }
  for (const hash of ["not-a-screen", "__proto__", "constructor"]) {
    await page.goto(base + "/#" + hash);
    await active("overview");
    report.unknown_routes.push({ hash, displayed: "overview" });
  }

  // Classic scrollbars consume layout width. Check clientWidth, not innerWidth.
  for (const width of [320, 360, 390]) {
    for (const textScale of [1, 2]) {
      for (const screen of screens) {
        await page.setViewportSize({ width, height: 844 });
        await page.goto(base + "/#" + screen);
        // Hash-only navigation retains the document: clear QA text sizing before each case.
        await page.reload();
        await active(screen);
        await page.evaluate(() => {
          document.documentElement.style.overflowY = "scroll";
          document.documentElement.style.scrollbarGutter = "stable";
        });
        if (textScale === 2)
          await page.evaluate(() => {
            const sizes = [...document.querySelectorAll("body, body *")].map(
              (el) => [el, Number.parseFloat(getComputedStyle(el).fontSize)],
            );
            for (const [el, size] of sizes) el.style.fontSize = `${size * 2}px`;
          });
        await presentationReady(page);
        const measurement = await page.evaluate(() => {
          const client = document.documentElement.clientWidth;
          return {
            width: innerWidth,
            client_width: client,
            scrollbar_gutter: innerWidth - client,
            scroll_width: document.documentElement.scrollWidth,
            clipped_facts: [
              ...document.querySelectorAll("main .data-row, main .panel-head"),
            ]
              .map((el) => ({
                text: el.textContent,
                left: el.getBoundingClientRect().left,
                right: el.getBoundingClientRect().right,
              }))
              .filter((entry) => entry.left < -1 || entry.right > client + 1),
          };
        });
        const label = `${width}-${textScale * 100}-${screen}`;
        report.layouts.push({ screen, text_scale: textScale, ...measurement });
        await capture("mobile-" + label);
        assert.ok(
          measurement.scrollbar_gutter > 0,
          "Classic scrollbar qualification unavailable",
        );
        assert.ok(
          measurement.scroll_width <= measurement.client_width + 1,
          label + " document overflow",
        );
        assert.deepEqual(
          measurement.clipped_facts,
          [],
          label + " clipped facts",
        );
        if (screen === "review") {
          assert.match(
            await page.locator("main").innerText(),
            /1YA65594665951620/,
          );
          assert.match(await page.locator("main").innerText(), /NZD 20\.00/);
        }
        await axe(label);
      }
    }
  }

  for (const width of [1440, 1920]) {
    for (const mode of ["deterministic", "local_ai"]) {
      await page.setViewportSize({
        width,
        height: width === 1440 ? 900 : 1080,
      });
      await page.goto(base + "/#demo");
      await page.reload();
      await active("demo");
      await page.locator("#planning-mode").selectOption(mode);
      const resetRequired =
        (await page
          .getByRole("button", { name: "Start new simulation", exact: true })
          .count()) > 0;
      const loaded = page.waitForResponse(
        (response) =>
          response.url().endsWith("/presentation/demo") &&
          response.request().method() === "POST",
      );
      await page.locator('[data-demo="load"]').first().click();
      if (resetRequired) {
        await page.locator("#confirmation[open]").waitFor();
        await page.locator("#confirm-accept").click();
      }
      const response = await loaded;
      assert.equal(response.status(), 200);
      const sample = await response.json();
      assert.equal(sample.planning_mode, mode);
      assert.equal(sample.simulated_dispatches, 0);
      await page
        .getByRole("button", {
          name:
            mode === "local_ai"
              ? "Generate Live Ollama Plan"
              : "Generate simulated Plan",
          exact: true,
        })
        .waitFor();
      await page.waitForFunction(
        () => !document.querySelector('[data-demo="generate"]').disabled,
      );
      await presentationReady(page);
      assert.match(
        await page.locator(".environment").innerText(),
        /SIMULATED PAYMENTS/,
      );
      const empty = await page.locator(".empty-card").innerText();
      assert.match(
        empty,
        mode === "local_ai"
          ? /genuine local Ollama recommendation/
          : /deterministic recommendation/,
      );
      assert.match(empty, /execution remains simulated/);
      if (mode === "local_ai")
        assert.doesNotMatch(empty, /simulated recommendation/);
      const button = await page.locator('[data-demo="generate"]').boundingBox();
      assert.ok(
        button.y >= 0 &&
          button.y + button.height <= (width === 1440 ? 900 : 1080),
      );
      assert.equal(await page.locator('[data-demo="generate"]').count(), 1);
      report.next_actions.push({
        width,
        mode,
        button,
        visible_without_scroll: true,
      });
      await capture(`desktop-${width}-${mode}`);
      await axe(`desktop-${width}-${mode}`);
    }
  }
  assert.equal(report.external_requests, 0);
  assert.equal(report.forbidden_routes, 0);
  assert.deepEqual(report.unexpected_errors, []);
  report.status = "PASS";
  console.log(
    JSON.stringify({
      status: report.status,
      navigation: report.navigation.length,
      layouts: report.layouts.length,
      next_actions: report.next_actions.length,
      axe_scans: report.accessibility.length,
    }),
  );
} catch (error) {
  report.status = "FAIL";
  report.failure = String(error).slice(0, 1500);
  throw error;
} finally {
  writeFileSync(
    resolve(output, "browser-regression.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await context.close();
  await browser.close();
}
