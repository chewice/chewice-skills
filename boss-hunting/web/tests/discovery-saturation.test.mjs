import assert from "node:assert/strict";
import test from "node:test";
import { saturationReached } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";

test("T26 saturation stops on zero new validated PIs, low growth without new structure, or the round cap", () => {
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 0, round: 1 }).reason, "pi_saturation");
  const engineering = saturationReached({ existingValidated: 20, newValidated: 1, newSubdirections: 0, round: 1 });
  assert.equal(engineering.stop, true);
  assert.equal(engineering.reason, "engineering_heuristic");
  assert.equal(engineering.growthRatio, 0.05);
  assert.match(engineering.note, /configurable engineering default/);
  const structural = saturationReached({ existingValidated: 20, newValidated: 1, newSubdirections: 1, round: 1 });
  assert.equal(structural.stop, false);
  assert.equal(structural.reason, "continue");
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 8, round: 2 }).reason, "max_rounds");
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 8, round: 1, ratio: 0.5 }).stop, true, "ratio is configurable");
});
