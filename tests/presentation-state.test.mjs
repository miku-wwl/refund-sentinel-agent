import test from "node:test";
import assert from "node:assert/strict";
import {
  escapeHTML,
  demoNext,
  commandBody,
  workflowProgress,
  money,
  seconds,
} from "../src/refund_sentinel/static/console-state.mjs";

const awaiting = {
  run: { state: "AwaitingApproval", version: 4 },
  plan_sha256: "a".repeat(64),
};
const pending = {
  ...awaiting,
  run: { state: "Approved", version: 5 },
  action: { state: "Pending", version: 1, authorized: false },
};
const authorized = {
  ...pending,
  action: { state: "Authorized", version: 2, authorized: true },
};
test("untrusted strings cannot introduce browser markup", () =>
  assert.equal(
    escapeHTML('<img src=x onerror="steal()">&\''),
    "&lt;img src=x onerror=&quot;steal()&quot;&gt;&amp;&#39;",
  ));
test("empty and loaded samples have no execution authority", () => {
  assert.equal(demoNext(null), "load");
  assert.equal(demoNext({}), "generate");
});
test("Approval does not grant Authorization or execution", () => {
  assert.equal(demoNext(awaiting), "approve");
  assert.equal(demoNext(pending), "authorize");
  assert.throws(() => commandBody(pending, "execute", "key"));
});
test("approved admission can resume independently", () =>
  assert.equal(
    demoNext({ ...awaiting, run: { state: "Approved", version: 5 } }),
    "admit",
  ));
test("authorization and execute use exact Action version and Plan fingerprint", () =>
  assert.deepEqual(commandBody(authorized, "execute", "command-key"), {
    operation: "execute",
    confirmed: true,
    expected_version: 2,
    plan_digest: "a".repeat(64),
    idempotency_key: "command-key",
  }));
for (const state of ["Executing", "Succeeded", "Failed", "Unknown"])
  test(`${state} never offers another dispatch`, () => {
    assert.equal(
      demoNext({ ...authorized, action: { ...authorized.action, state } }),
      null,
    );
    assert.throws(() =>
      commandBody(
        { ...authorized, action: { ...authorized.action, state } },
        "execute",
        "key",
      ),
    );
  });
test("Unknown stops progress before verification or receipt", () => {
  const p = workflowProgress({
    ...authorized,
    action: { ...authorized.action, state: "Unknown" },
  });
  assert.equal(p.complete, 6);
  assert.equal(p.stopped, true);
});
test("completed receipt independently controls completion display", () => {
  const v = {
    ...authorized,
    action: { ...authorized.action, state: "Succeeded" },
  };
  assert.notEqual(workflowProgress(v).complete, 9);
  assert.equal(
    workflowProgress({ ...v, receipt: { id: "simulated" } }).complete,
    9,
  );
});
test("money and timing retain units and meaningful precision", () => {
  assert.equal(money("5.00", "NZD"), "NZD 5.00");
  assert.equal(seconds(2.148422), "2.148 s");
});
