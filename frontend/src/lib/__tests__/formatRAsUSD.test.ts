/**
 * Unit Test Matrix for formatRAsUSD (1R = $1 Equivalence)
 */

import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node ESM requires explicit .ts extension
import { formatRAsUSD } from "../format.ts";

test("formatRAsUSD - prompt required examples and exact values", () => {
  // 1R -> $1.00
  assert.strictEqual(formatRAsUSD(1), "$1.00");
  // 2R -> $2.00
  assert.strictEqual(formatRAsUSD(2), "$2.00");
  // 5R -> $5.00
  assert.strictEqual(formatRAsUSD(5), "$5.00");
  // -1R -> -$1.00
  assert.strictEqual(formatRAsUSD(-1), "-$1.00");
  // -2.5R -> -$2.50
  assert.strictEqual(formatRAsUSD(-2.5), "-$2.50");
  // +3R -> +$3.00
  assert.strictEqual(formatRAsUSD(3, { showSign: true }), "+$3.00");
  // +4.25R -> +$4.25
  assert.strictEqual(formatRAsUSD(4.25, { showSign: true }), "+$4.25");
  // 0.47R -> $0.47 / +$0.47
  assert.strictEqual(formatRAsUSD(0.47), "$0.47");
  assert.strictEqual(formatRAsUSD(0.47, { showSign: true }), "+$0.47");
  // Zero -> $0.00
  assert.strictEqual(formatRAsUSD(0), "$0.00");
  assert.strictEqual(formatRAsUSD(0, { showSign: true }), "$0.00");
  assert.strictEqual(formatRAsUSD(-0), "$0.00");
});

test("formatRAsUSD - string inputs and custom precision", () => {
  // String numeric inputs
  assert.strictEqual(formatRAsUSD("1.5"), "$1.50");
  assert.strictEqual(formatRAsUSD("+0.42", { showSign: true }), "+$0.42");
  assert.strictEqual(formatRAsUSD("-3.75"), "-$3.75");

  // Higher precision (3 or 4 decimals for EV and expectancy models)
  assert.strictEqual(formatRAsUSD(0.0444, { showSign: true, digits: 4 }), "+$0.0444");
  assert.strictEqual(formatRAsUSD(0.365, { showSign: true, digits: 4 }), "+$0.3650");
  assert.strictEqual(formatRAsUSD(0.42, { showSign: true, digits: 3 }), "+$0.420");
});

test("formatRAsUSD - invalid and fallback handling", () => {
  // Default fallback is "--"
  assert.strictEqual(formatRAsUSD(null), "--");
  assert.strictEqual(formatRAsUSD(undefined), "--");
  assert.strictEqual(formatRAsUSD(""), "--");
  assert.strictEqual(formatRAsUSD("invalid-string"), "--");
  assert.strictEqual(formatRAsUSD(NaN), "--");

  // Custom fallback
  assert.strictEqual(formatRAsUSD(null, { fallback: "N/A" }), "N/A");
  assert.strictEqual(formatRAsUSD(undefined, { fallback: "—" }), "—");
});
