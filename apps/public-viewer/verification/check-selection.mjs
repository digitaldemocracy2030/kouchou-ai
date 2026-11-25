import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolveChartSelection } from "../components/charts/plugins/selection.ts";

const examples = JSON.parse(readFileSync(0, "utf8"));
assert(examples.length > 0);
for (const { modes, requested, fallback, expected } of examples) {
  assert.equal(
    resolveChartSelection(modes, requested ?? undefined, fallback ?? undefined),
    expected ?? undefined,
    JSON.stringify({ modes, requested, fallback }),
  );
}
console.log(`Chart selection agrees with Lean in ${examples.length} cases.`);
