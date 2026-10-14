// Await explicit rendered state, finite transitions, fonts and stable geometry.
export async function presentationReady(page) {
  await page.locator("#main > *").first().waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      document
        .getAnimations()
        .filter(
          (animation) =>
            animation.effect?.getComputedTiming().iterations !== Infinity,
        )
        .map((animation) => animation.finished.catch(() => {})),
    );
  });
  await page.waitForFunction(() => {
    const node = document.querySelector(".screen-fade");
    return (
      (!node || Number(getComputedStyle(node).opacity) >= 0.999) &&
      !document
        .getAnimations()
        .some(
          (animation) =>
            animation.playState === "running" &&
            animation.effect?.getComputedTiming().iterations !== Infinity,
        )
    );
  });
  return page.evaluate(async () => {
    let previous = "",
      stable = 0;
    const deadline = performance.now() + 2500;
    while (performance.now() < deadline) {
      await new Promise(requestAnimationFrame);
      const nodes = [
        ...document.querySelectorAll("#main > *, .panel, dialog[open]"),
      ];
      const geometry = JSON.stringify(
        nodes.map((node) => {
          const { x, y, width, height } = node.getBoundingClientRect();
          return [x, y, width, height, node.textContent];
        }),
      );
      stable = geometry === previous ? stable + 1 : 0;
      previous = geometry;
      if (stable >= 3)
        return {
          opacity: Number(
            getComputedStyle(
              document.querySelector(".screen-fade") ||
                document.querySelector("#main"),
            ).opacity,
          ),
          fonts: document.fonts.status,
          stable_frames: stable,
          horizontal_overflow:
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth + 1,
        };
    }
    throw new Error("Presentation geometry did not stabilize");
  });
}
