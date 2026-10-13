// Native ESM build verification: this frontend has no compilation or npm runtime dependency.
import { readFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const root = new URL("../", import.meta.url);
const asset = (name) => new URL("src/refund_sentinel/static/" + name, root);
for (const name of ["console.js", "console-state.mjs"]) {
  const result = spawnSync(
    process.execPath,
    ["--check", fileURLToPath(asset(name))],
    { encoding: "utf8" },
  );
  if (result.status !== 0) throw new Error(result.stderr);
}
const html = readFileSync(asset("console.html"), "utf8");
for (const match of html.matchAll(/(?:href|src)="\/assets\/([^"]+)"/g))
  if (!existsSync(asset(match[1])))
    throw new Error("Missing asset: " + match[1]);
const checksum = createHash("sha256")
  .update(readFileSync(asset("qualified-case.json")))
  .digest("hex");
const frozen = readFileSync(
  new URL("evidence/phase2-freeze/verified-refund.json", root),
);
if (checksum !== createHash("sha256").update(frozen).digest("hex"))
  throw new Error("Archived proof changed");
console.log(
  JSON.stringify({
    frontend: "Native browser ESM + CSS",
    syntax: "PASS",
    assets: "PASS",
    archived_proof_sha256: checksum,
    runtime_dependencies_added: 0,
  }),
);
