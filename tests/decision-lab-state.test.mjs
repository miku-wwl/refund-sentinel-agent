import test from "node:test";
import assert from "node:assert/strict";
import {
  demoNext,
  commandBody,
  workflowProgress,
} from "../src/refund_sentinel/static/console-state.mjs";

for (const verdict of ["BLOCKED", "NOT_EVALUATED"]) {
  test(`${verdict} decision without a Run never offers generation or execution`, () => {
    const view = {
      decision: { policy_verdict: verdict },
      run: null,
      action: null,
    };
    assert.equal(demoNext(view), null);
    for (const op of ["approve", "authorize", "execute"]) {
      assert.throws(() => commandBody(view, op, "key"));
    }
  });
}
test("decision evidence grants no authority to an admitted Action", () => {
  const view = {
    decision: { policy_verdict: "PASS" },
    run: { state: "Approved" },
    action: { state: "Pending" },
  };
  assert.equal(demoNext(view), "authorize");
  assert.throws(() => commandBody(view, "execute", "key"));
});
test("policy denial stops the visual workflow", () => {
  const progress = workflowProgress({
    decision: { policy_verdict: "BLOCKED" },
  });
  assert.equal(progress.stopped, true);
  assert.equal(progress.complete, 0);
});
