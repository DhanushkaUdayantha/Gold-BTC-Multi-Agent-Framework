/**
 * Reusable Relative-Time Formatter Utility
 *
 * Formats real timestamps into human-readable relative strings:
 * - < 60s  -> "0s ago", "1s ago", "12s ago", "59s ago"
 * - 60-119s -> "1 min ago"
 * - 120s+  -> "2 mins ago", "5 mins ago", "59 mins ago"
 * - 60m+   -> "1 hr ago"
 * - 120m+  -> "2 hrs ago", "23 hrs ago"
 * - 24h+   -> "1 day ago"
 * - 48h+   -> "2 days ago"
 * - Fallback for missing/invalid: "--"
 */

import React, { useEffect, useMemo, useState } from "react";

export interface FormatRelativeTimeOptions {
  /** Deterministic reference time for testing or frozen displays */
  now?: number | Date | null;
  /** Fallback string when timestamp is missing or invalid. Defaults to "--" */
  fallback?: string;
  /** Optional prefix prepended to valid relative strings (e.g. "Updated ") */
  prefix?: string;
}

export function parseTimestampMs(timestamp: unknown, refNowMs = Date.now()): number | null {
  if (timestamp == null || timestamp === "") return null;
  if (timestamp instanceof Date) {
    const t = timestamp.getTime();
    return Number.isFinite(t) ? t : null;
  }
  if (typeof timestamp === "number") {
    if (!Number.isFinite(timestamp)) return null;
    // Epoch seconds (e.g. 10 digits < 1e11) vs epoch milliseconds
    return timestamp > 1e11 ? timestamp : timestamp * 1000;
  }
  if (typeof timestamp === "string") {
    const trimmed = timestamp.trim();
    if (!trimmed || trimmed === "--" || trimmed === "--:--:--") return null;

    // Numeric timestamp string
    if (/^\d+(\.\d+)?$/.test(trimmed)) {
      const num = parseFloat(trimmed);
      if (!Number.isFinite(num)) return null;
      return num > 1e11 ? num : num * 1000;
    }

    // Time-only string "HH:MM" or "HH:MM:SS"
    if (/^\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) {
      const parts = trimmed.split(":").map(Number);
      const d = new Date(refNowMs);
      d.setHours(parts[0], parts[1], parts[2] || 0, 0);
      let t = d.getTime();
      // If time is far in future due to day rollover, step back 24 hours
      if (t - refNowMs > 60000) {
        t -= 86400000;
      }
      return Number.isFinite(t) ? t : null;
    }

    // Full date/ISO string
    const d = new Date(trimmed);
    const t = d.getTime();
    return Number.isFinite(t) ? t : null;
  }
  return null;
}

/**
 * Pure, deterministic formatter for relative time.
 * Accepts any valid timestamp and formats according to the exact duration rules.
 */
export function formatRelativeTime(
  timestamp?: string | number | Date | null,
  optionsOrNow?: FormatRelativeTimeOptions | number | Date | null
): string {
  let nowVal: number | Date | null | undefined;
  let fallback = "--";
  let prefix = "";

  if (typeof optionsOrNow === "number" || optionsOrNow instanceof Date) {
    nowVal = optionsOrNow;
  } else if (optionsOrNow && typeof optionsOrNow === "object") {
    nowVal = optionsOrNow.now;
    if (optionsOrNow.fallback !== undefined) fallback = optionsOrNow.fallback;
    if (optionsOrNow.prefix !== undefined) prefix = optionsOrNow.prefix;
  }

  let nowMs: number;
  if (typeof nowVal === "number") {
    nowMs = nowVal > 1e11 ? nowVal : nowVal * 1000;
  } else if (nowVal instanceof Date) {
    nowMs = nowVal.getTime();
  } else {
    nowMs = Date.now();
  }

  const timeMs = parseTimestampMs(timestamp, nowMs);
  if (timeMs === null) {
    return prefix ? `${prefix}${fallback}` : fallback;
  }

  const diffMs = Math.max(0, nowMs - timeMs);
  const diffSec = Math.floor(diffMs / 1000);

  let rel: string;
  if (diffSec < 60) {
    rel = `${diffSec}s ago`;
  } else if (diffSec < 120) {
    rel = "1 min ago";
  } else if (diffSec < 3600) {
    const mins = Math.floor(diffSec / 60);
    rel = `${mins} mins ago`;
  } else if (diffSec < 7200) {
    rel = "1 hr ago";
  } else if (diffSec < 86400) {
    const hrs = Math.floor(diffSec / 3600);
    rel = `${hrs} hrs ago`;
  } else if (diffSec < 172800) {
    rel = "1 day ago";
  } else {
    const days = Math.floor(diffSec / 86400);
    rel = `${days} days ago`;
  }

  return prefix ? `${prefix}${rel}` : rel;
}

export interface UseRelativeTimeOptions {
  fallback?: string;
  prefix?: string;
  refreshIntervalMs?: number;
}

/**
 * React hook that refreshes the relative time string periodically (default 5s)
 * while keeping the real source timestamp intact. Does NOT trigger any API refetch.
 */
export function useRelativeTime(
  timestamp?: string | number | Date | null,
  options?: UseRelativeTimeOptions
): string {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!timestamp) return;
    const intervalMs = options?.refreshIntervalMs ?? 5000;
    const timer = setInterval(() => {
      setTick((t) => (t + 1) % 1000000);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [timestamp, options?.refreshIntervalMs]);

  return useMemo(() => {
    return formatRelativeTime(timestamp, {
      fallback: options?.fallback,
      prefix: options?.prefix,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timestamp, tick, options?.fallback, options?.prefix]);
}

/**
 * Component for displaying auto-refreshing relative timestamps inline.
 */
export function RelativeTime({
  timestamp,
  fallback = "--",
  prefix = "",
  className = "",
  refreshIntervalMs = 5000,
}: {
  timestamp?: string | number | Date | null;
  fallback?: string;
  prefix?: string;
  className?: string;
  refreshIntervalMs?: number;
}) {
  const text = useRelativeTime(timestamp, { fallback, prefix, refreshIntervalMs });
  return React.createElement("span", { className }, text);
}
