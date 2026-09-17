/**
 * Small Focused Test Matrix for formatRelativeTime
 *
 * Tests exact boundaries, singular vs plural rules, and fallback handling
 * using deterministic/frozen timestamps to avoid flakiness.
 */

import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node ESM requires explicit .ts extension
import { formatRelativeTime } from "../relativeTime.ts";

test("formatRelativeTime test matrix - exact boundaries and representative cases", async (t) => {
  // Deterministic fixed reference timestamp: 2026-09-04T12:00:00.000Z
  const frozenNow = new Date("2026-09-04T12:00:00.000Z").getTime();

  // Helper to create a timestamp offset from frozenNow by -seconds
  const offsetTime = (seconds: number) => new Date(frozenNow - seconds * 1000).toISOString();

  const testMatrix: Array<{ seconds: number; expected: string; label: string }> = [
    { seconds: 0, expected: "0s ago", label: "0s boundary" },
    { seconds: 1, expected: "1s ago", label: "1s elapsed" },
    { seconds: 12, expected: "12s ago", label: "12s elapsed" },
    { seconds: 45, expected: "45s ago", label: "45s elapsed" },
    { seconds: 59, expected: "59s ago", label: "59s upper boundary for seconds" },
    { seconds: 60, expected: "1 min ago", label: "60s transition to 1 min" },
    { seconds: 61, expected: "1 min ago", label: "61s within 1 min bucket" },
    { seconds: 119, expected: "1 min ago", label: "119s upper boundary for 1 min" },
    { seconds: 120, expected: "2 mins ago", label: "120s transition to 2 mins" },
    { seconds: 5 * 60, expected: "5 mins ago", label: "5 min elapsed" },
    { seconds: 59 * 60, expected: "59 mins ago", label: "59 min upper boundary for mins" },
    { seconds: 60 * 60, expected: "1 hr ago", label: "60 min transition to 1 hr" },
    { seconds: 2 * 3600, expected: "2 hrs ago", label: "2 hr elapsed" },
    { seconds: 23 * 3600, expected: "23 hrs ago", label: "23 hr upper boundary for hrs" },
    { seconds: 24 * 3600, expected: "1 day ago", label: "24 hr transition to 1 day" },
    { seconds: 2 * 86400, expected: "2 days ago", label: "2 days elapsed" },
  ];

  for (const item of testMatrix) {
    const inputTs = offsetTime(item.seconds);
    const result = formatRelativeTime(inputTs, frozenNow);
    assert.strictEqual(
      result,
      item.expected,
      `Failed for ${item.label} (${item.seconds}s): expected "${item.expected}", got "${result}"`
    );
  }
});

test("formatRelativeTime - invalid, missing, and malformed inputs", () => {
  const frozenNow = new Date("2026-09-04T12:00:00.000Z").getTime();

  // null
  assert.strictEqual(formatRelativeTime(null, frozenNow), "--");

  // undefined
  assert.strictEqual(formatRelativeTime(undefined, frozenNow), "--");

  // empty string
  assert.strictEqual(formatRelativeTime("", frozenNow), "--");

  // invalid timestamp string
  assert.strictEqual(formatRelativeTime("invalid-timestamp-xyz", frozenNow), "--");

  // custom fallback option
  assert.strictEqual(
    formatRelativeTime(null, { now: frozenNow, fallback: "N/A" }),
    "N/A"
  );
});

test("formatRelativeTime - exact boundary transitions", () => {
  const frozenNow = 1700000000000;

  // 59s -> 1 min
  assert.strictEqual(formatRelativeTime(frozenNow - 59 * 1000, frozenNow), "59s ago");
  assert.strictEqual(formatRelativeTime(frozenNow - 60 * 1000, frozenNow), "1 min ago");

  // 119s -> 2 mins
  assert.strictEqual(formatRelativeTime(frozenNow - 119 * 1000, frozenNow), "1 min ago");
  assert.strictEqual(formatRelativeTime(frozenNow - 120 * 1000, frozenNow), "2 mins ago");

  // 59m (3540s) / 3599s -> 60m (3600s = 1 hr)
  assert.strictEqual(formatRelativeTime(frozenNow - 3599 * 1000, frozenNow), "59 mins ago");
  assert.strictEqual(formatRelativeTime(frozenNow - 3600 * 1000, frozenNow), "1 hr ago");

  // 23h (82800s) / 86399s -> 24h (86400s = 1 day)
  assert.strictEqual(formatRelativeTime(frozenNow - 86399 * 1000, frozenNow), "23 hrs ago");
  assert.strictEqual(formatRelativeTime(frozenNow - 86400 * 1000, frozenNow), "1 day ago");

  // 47h59m / 172799s -> 48h (172800s = 2 days)
  assert.strictEqual(formatRelativeTime(frozenNow - 172799 * 1000, frozenNow), "1 day ago");
  assert.strictEqual(formatRelativeTime(frozenNow - 172800 * 1000, frozenNow), "2 days ago");
});

test("formatRelativeTime - prefix option support", () => {
  const frozenNow = 1700000000000;
  const ts = frozenNow - 12 * 1000;
  assert.strictEqual(
    formatRelativeTime(ts, { now: frozenNow, prefix: "Updated " }),
    "Updated 12s ago"
  );
  assert.strictEqual(
    formatRelativeTime(null, { now: frozenNow, prefix: "Updated " }),
    "Updated --"
  );
});
