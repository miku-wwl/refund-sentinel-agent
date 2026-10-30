import test from "node:test";
import assert from "node:assert/strict";
import {
  demoNext,
  commandBody,
  workflowProgress,
  hasExecutablePlan,
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

for (const status of ["FAILED", "INTERRUPTED", "BLOCKED"]) {
  test(`${status} cannot expose controls even with a stale Run projection`, () => {
    const view = {
      decision: { workflow_status: status, policy_verdict: "PASS" },
      run: { state: "AwaitingApproval" },
      plan: { goal: "stale proposal" },
      plan_sha256: "a".repeat(64),
    };
    assert.equal(demoNext(view), null);
    assert.equal(hasExecutablePlan(view), false);
    assert.equal(workflowProgress(view).stopped, true);
    assert.equal(workflowProgress(view).complete, 0);
    assert.notEqual(workflowProgress(view).state, "AwaitingApproval");
    for (const op of ["approve", "admit", "authorize", "execute"]) {
      assert.throws(() => commandBody(view, op, "key"));
    }
  });
}
test("policy denial stops the visual workflow", () => {
  const progress = workflowProgress({
    decision: { policy_verdict: "BLOCKED" },
  });
  assert.equal(progress.stopped, true);
  assert.equal(progress.complete, 0);
});
