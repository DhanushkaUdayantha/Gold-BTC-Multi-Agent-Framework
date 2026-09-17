/**
 * Unit Test Matrix for computeOverallInsightPercentage
 * (H + N) / 2 Combination Rules & Fallbacks
 */

import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node ESM requires explicit .ts extension
import { computeOverallInsightPercentage } from "../format.ts";

test("computeOverallInsightPercentage - valid numeric calculations and rounding", () => {
  // Exact averages
  assert.strictEqual(computeOverallInsightPercentage(64, 82), 73);
  assert.strictEqual(computeOverallInsightPercentage(50, 50), 50);
  assert.strictEqual(computeOverallInsightPercentage(0, 0), 0);
  assert.strictEqual(computeOverallInsightPercentage(100, 100), 100);
  assert.strictEqual(computeOverallInsightPercentage(0, 100), 50);

  // Half-integers round to nearest whole integer (standard Math.round)
  assert.strictEqual(computeOverallInsightPercentage(65, 80), 73); // 145 / 2 = 72.5 -> 73
  assert.strictEqual(computeOverallInsightPercentage(60, 61), 61); // 121 / 2 = 60.5 -> 61
  assert.strictEqual(computeOverallInsightPercentage(60, 63), 62); // 123 / 2 = 61.5 -> 62
});

test("computeOverallInsightPercentage - string inputs and decimals", () => {
  assert.strictEqual(computeOverallInsightPercentage("64", "82"), 73);
  assert.strictEqual(computeOverallInsightPercentage("65.4", "80.2"), 73);
  assert.strictEqual(computeOverallInsightPercentage(70.2, 79.8), 75);
});

test("computeOverallInsightPercentage - clamps values to [0, 100]", () => {
  assert.strictEqual(computeOverallInsightPercentage(120, 80), 90); // clamped 100, 80 -> 90
  assert.strictEqual(computeOverallInsightPercentage(-20, 80), 40); // clamped 0, 80 -> 40
});

test("computeOverallInsightPercentage - null, undefined, empty, and NaN handling (NEVER returns 0)", () => {
  // Either value missing returns null
  assert.strictEqual(computeOverallInsightPercentage(null, 80), null);
  assert.strictEqual(computeOverallInsightPercentage(60, null), null);
  assert.strictEqual(computeOverallInsightPercentage(undefined, 80), null);
  assert.strictEqual(computeOverallInsightPercentage(60, undefined), null);
  assert.strictEqual(computeOverallInsightPercentage(null, null), null);
  assert.strictEqual(computeOverallInsightPercentage(undefined, undefined), null);
  assert.strictEqual(computeOverallInsightPercentage("", 80), null);
  assert.strictEqual(computeOverallInsightPercentage(60, ""), null);

  // Non-numeric strings / NaN return null
  assert.strictEqual(computeOverallInsightPercentage("abc", 80), null);
  assert.strictEqual(computeOverallInsightPercentage(60, "xyz"), null);
  assert.strictEqual(computeOverallInsightPercentage(NaN, 80), null);
  assert.strictEqual(computeOverallInsightPercentage(60, NaN), null);

  // Assert explicitly that missing inputs NEVER evaluate to 0
  assert.notStrictEqual(computeOverallInsightPercentage(null, 80), 0);
  assert.notStrictEqual(computeOverallInsightPercentage(60, null), 0);
  assert.notStrictEqual(computeOverallInsightPercentage(null, null), 0);
});
