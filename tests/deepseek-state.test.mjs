import test from "node:test";
import assert from "node:assert/strict";
import {
  hasExecutablePlan,
  demoNext,
} from "../src/refund_sentinel/static/console-state.mjs";

test("a proposal or Plan-shaped projection without a persistent Run is never ready", () => {
  assert.equal(
    hasExecutablePlan({ plan: {}, plan_sha256: "a".repeat(64) }),
    false,
  );
  assert.equal(hasExecutablePlan({ run: {}, plan: null }), false);
  assert.equal(
    hasExecutablePlan({ run: {}, plan: {}, plan_sha256: "a".repeat(64) }),
    true,
  );
});
test("a cloud decision without a Run cannot offer an executable gate", () => {
  assert.equal(
    demoNext({
      planning_mode: "deepseek",
      decision: { policy_verdict: "PASS" },
    }),
    null,
  );
  assert.equal(
    demoNext({
      planning_mode: "deepseek",
      decision: { policy_verdict: "BLOCKED" },
    }),
    null,
  );
});
