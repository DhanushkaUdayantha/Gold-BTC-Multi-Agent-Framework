/**
 * Unit Test Matrix for formatConflictWeight (DEF-02)
 *
 * Case A: Authoritative numeric conflict weight exists -> display actual value
 * Case B: Numeric conflict weight is unavailable -> display "--"
 * Case C: Conflict is detected but no numeric weight exists -> do NOT display "0.0%", do NOT fabricate "25.0%"
 */

import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node ESM requires explicit .ts extension
import { formatConflictWeight } from "../format.ts";

test("formatConflictWeight - Case A: Authoritative numeric conflict weight exists", () => {
  // Decimal ratio format (<= 1.0)
  assert.strictEqual(formatConflictWeight(0.18), "18.0%");
  assert.strictEqual(formatConflictWeight(0.25), "25.0%");
  assert.strictEqual(formatConflictWeight(0.05), "5.0%");
  assert.strictEqual(formatConflictWeight(0.312), "31.2%");
  assert.strictEqual(formatConflictWeight(0), "0.0%");

  // Percentage format (> 1.0)
  assert.strictEqual(formatConflictWeight(18.5), "18.5%");
  assert.strictEqual(formatConflictWeight(25.0), "25.0%");
  assert.strictEqual(formatConflictWeight(30.2), "30.2%");
});

test("formatConflictWeight - Case B: Numeric conflict weight is unavailable -> display '--'", () => {
  assert.strictEqual(formatConflictWeight(null), "--");
  assert.strictEqual(formatConflictWeight(undefined), "--");
  assert.strictEqual(formatConflictWeight(""), "--");
  assert.strictEqual(formatConflictWeight("unknown"), "--");
  assert.strictEqual(formatConflictWeight(NaN), "--");
  assert.strictEqual(formatConflictWeight(Infinity), "--");
});

test("formatConflictWeight - Case C: Conflict detected without numeric weight -> NEVER fabricates '0.0%' or '25.0%'", () => {
  // When only boolean conflict_detected is known, value passed to formatter is null/undefined
  const rendered = formatConflictWeight(undefined);
  assert.strictEqual(rendered, "--");
  assert.notStrictEqual(rendered, "0.0%");
  assert.notStrictEqual(rendered, "25.0%");
  assert.notStrictEqual(rendered, ">= 25.0%");
  assert.notStrictEqual(rendered, "≥ 25.0%");
});
