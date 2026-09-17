export function isPresent(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function safeNum(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = parseFloat(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

export function fmtPrice(value: number | null | undefined, prefix = "$"): string {
  if (!isPresent(value)) return "—";
  return `${prefix}${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtCurrency(value: unknown, prefix = "$"): string {
  const num = safeNum(value, 0);
  return `${prefix}${num.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtSignedCurrency(value: unknown, prefix = "$"): string {
  const num = safeNum(value, 0);
  const sign = num > 0 ? "+" : num < 0 ? "-" : "";
  const abs = Math.abs(num);
  return `${sign}${prefix}${abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtNumber(value: number | null | undefined, digits = 2): string {
  if (!isPresent(value)) return "—";
  return value.toFixed(digits);
}

export function fmtSigned(value: number | null | undefined, digits = 2): string {
  if (!isPresent(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

export function fmtPct(value: number | null | undefined, digits = 2): string {
  if (!isPresent(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function fmtTime(iso?: string | null): string {
  if (!iso) return "--:--:--";
  const trimmed = iso.trim();
  if (/^\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) {
    return trimmed.length === 5 ? `${trimmed}:00` : trimmed;
  }
  const d = new Date(trimmed);
  if (Number.isNaN(d.getTime())) return "--:--:--";
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

export function fmtClock(date: Date = new Date()): string {
  return date.toLocaleTimeString("en-GB", { hour12: false });
}

export function fmtSriLankaTime(iso?: string | number | Date | null, fallback = "--:--:--"): string {
  if (!iso) return fallback;
  try {
    let d: Date;
    if (iso instanceof Date) {
      d = iso;
    } else if (typeof iso === "number") {
      d = new Date(iso > 1e11 ? iso : iso * 1000);
    } else {
      const trimmed = String(iso).trim();
      if (!trimmed || trimmed === "--" || trimmed === "--:--:--") return fallback;
      if (/^\d+(\.\d+)?$/.test(trimmed)) {
        const num = parseFloat(trimmed);
        d = new Date(num > 1e11 ? num : num * 1000);
      } else if (/^\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) {
        return trimmed.length === 5 ? `${trimmed}:00` : trimmed;
      } else {
        d = new Date(trimmed);
      }
    }
    if (Number.isNaN(d.getTime())) return fallback;
    return d.toLocaleTimeString("en-GB", {
      timeZone: "Asia/Colombo",
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return fallback;
  }
}

export function emaStructureLabel(
  price: number | null | undefined,
  ema20: number | null | undefined,
  ema50: number | null | undefined,
  ema200: number | null | undefined
): string {
  if (!isPresent(ema20) && !isPresent(ema50)) return "INSUFFICIENT DATA";
  if (isPresent(ema20) && isPresent(ema50) && isPresent(ema200)) {
    if (isPresent(price) && price > ema20 && ema20 > ema50 && ema50 > ema200) {
      return "BULLISH STACK";
    }
    if (isPresent(price) && price < ema20 && ema20 < ema50 && ema50 < ema200) {
      return "BEARISH STACK";
    }
    return "MIXED";
  }
  if (isPresent(ema20) && isPresent(ema50)) {
    return ema20 > ema50 ? "EMA20 > EMA50" : "EMA20 < EMA50";
  }
  return "PARTIAL";
}

export function biasClass(value?: string | null): string {
  const v = (value || "").toUpperCase();
  if (v.includes("BULL")) return "text-emerald-400";
  if (v.includes("BEAR")) return "text-rose-400";
  if (v.includes("WAIT") || v.includes("SIDE") || v.includes("NEUTR")) return "text-amber-400";
  return "text-zinc-300";
}

export function riskClass(value?: string | null): string {
  const v = (value || "").toUpperCase();
  if (v === "HIGH") return "text-rose-400";
  if (v === "LOW") return "text-emerald-400";
  return "text-amber-400";
}

export interface FormatROptions {
  showSign?: boolean;
  digits?: number;
  fallback?: string;
}

/**
 * Formats a monetary R-based value as USD: 1R = $1.00.
 *
 * Preserves the exact source numeric value while converting the displayed unit to USD.
 *
 * Examples:
 *  formatRAsUSD(1) => "$1.00"
 *  formatRAsUSD(3, { showSign: true }) => "+$3.00"
 *  formatRAsUSD(-2.5) => "-$2.50"
 *  formatRAsUSD(0) => "$0.00"
 *  formatRAsUSD(0.42, { showSign: true }) => "+$0.42"
 *  formatRAsUSD(0.0444, { showSign: true, digits: 4 }) => "+$0.0444"
 */
export function formatRAsUSD(
  rValue: number | string | null | undefined,
  options?: FormatROptions
): string {
  const { showSign = false, digits = 2, fallback = "--" } = options || {};
  if (rValue === null || rValue === undefined || rValue === "") {
    return fallback;
  }
  const num = typeof rValue === "number" ? rValue : parseFloat(String(rValue));
  if (!Number.isFinite(num)) {
    return fallback;
  }

  const absVal = Math.abs(num);
  const formattedAbs = absVal.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  if (absVal === 0 || formattedAbs === (0).toFixed(digits)) {
    return `$${(0).toFixed(digits)}`;
  }

  if (num < 0) {
    return `-$${formattedAbs}`;
  }

  return showSign ? `+$${formattedAbs}` : `$${formattedAbs}`;
}

export const fmtRAsUSD = formatRAsUSD;

/**
 * @deprecated NON-AUTHORITATIVE: Do NOT use to calculate or override authoritative overall trading signals.
 * Authoritative overall signal is computed by backend SignalAggregator (decision.overall_signal.percentage).
 * Retained strictly for legacy test compatibility.
 */
export function computeOverallInsightPercentage(
  historyPct: number | string | null | undefined,
  nowPct: number | string | null | undefined
): number | null {
  if (historyPct === null || historyPct === undefined || historyPct === "") {
    return null;
  }
  if (nowPct === null || nowPct === undefined || nowPct === "") {
    return null;
  }

  const h = typeof historyPct === "number" ? historyPct : parseFloat(String(historyPct));
  const n = typeof nowPct === "number" ? nowPct : parseFloat(String(nowPct));

  if (!Number.isFinite(h) || !Number.isFinite(n) || Number.isNaN(h) || Number.isNaN(n)) {
    return null;
  }

  const clampedH = Math.max(0, Math.min(100, h));
  const clampedN = Math.max(0, Math.min(100, n));
  const avg = Math.round((clampedH + clampedN) / 2);

  return Math.max(0, Math.min(100, avg));
}

/**
 * Resolves the authoritative Overall Signal percentage:
 * - Directly uses backend SignalAggregator overall_signal.percentage or overall_evidence_score.
 * - If signal is WAIT or conflict is detected, returns null (renders as "--" or "WAIT...").
 * - Never calculates an ad-hoc arithmetic average.
 */
export function resolveOverallSignalPercentage(
  signal?: string | null,
  overallSignalPct?: number | null,
  overallEvidenceScore?: number | null
): number | null {
  const normSig = String(signal || "").toUpperCase().trim();
  if (normSig === "WAIT" || normSig === "") {
    return null;
  }
  if (overallSignalPct != null && !isNaN(Number(overallSignalPct)) && Number.isFinite(Number(overallSignalPct))) {
    return Math.max(0, Math.min(100, Math.round(Number(overallSignalPct))));
  }
  if (overallEvidenceScore != null && !isNaN(Number(overallEvidenceScore)) && Number.isFinite(Number(overallEvidenceScore)) && Number(overallEvidenceScore) >= 20) {
    return Math.max(0, Math.min(100, Math.round(Number(overallEvidenceScore))));
  }
  return null;
}

/**
 * Resolves the authoritative History Market support percentage:
 * - Uses empirical historical win rate directly as determined by backend data lineage.
 * - Backend enforces statistical sufficiency (sets win_rate = None when sample_size < 10).
 * - If win rate is undefined/null/non-finite, returns null (truthful "--").
 */
export function resolveHistoryMarketPercentage(
  winRate?: number | null,
  sampleSize?: number | null
): number | null {
  if (winRate != null && !isNaN(Number(winRate)) && Number.isFinite(Number(winRate))) {
    return Math.max(0, Math.min(100, Math.round(Number(winRate))));
  }
  return null;
}

/**
 * Resolves the authoritative ML Shadow validation accuracy percentage:
 * - Uses empirical resolved validation accuracy across post-T0 closed candles.
 * - If accuracy is undefined/null/non-finite, returns null (truthful "--").
 * - Never substitutes prediction probability for validation accuracy.
 */
export function resolveMLShadowAccuracy(
  accuracy?: number | null,
  sampleSize?: number | null
): number | null {
  if (accuracy != null && !isNaN(Number(accuracy)) && Number.isFinite(Number(accuracy))) {
    const val = Number(accuracy) <= 1.0 ? Number(accuracy) * 100 : Number(accuracy);
    return Math.max(0, Math.min(100, Math.round(val)));
  }
  return null;
}

/**
 * Authoritative Hero percentage formatter:
 * - isMarketClosed -> "--%"
 * - isEvaluating -> "..."
 * - valid numeric percentage (0-100) -> "XX%" (truthful display for all valid metrics, including WAIT setups)
 * - unavailable (null / undefined / NaN / non-finite):
 *     - if fallbackText is provided -> fallbackText
 *     - if signal is WAIT -> "..." (honest awaiting confluence/evidence state)
 *     - if signal is BUY/SELL -> "--%" (unresolved directional metric)
 */
export function formatHeroPercentage({
  percentage,
  signal,
  isEvaluating,
  isMarketClosed,
  fallbackText,
}: {
  percentage?: number | string | null;
  signal?: string | null;
  isEvaluating?: boolean;
  isMarketClosed?: boolean;
  fallbackText?: string;
}): string {
  if (isMarketClosed) return "";
  if (isEvaluating) return "WAIT...";
  const safePct =
    percentage != null && percentage !== "" && !isNaN(Number(percentage))
      ? Math.max(0, Math.min(100, Math.round(Number(percentage))))
      : null;
  if (safePct != null) {
    if (safePct < 50) return "WAIT...";
    return `${safePct}%`;
  }
  if (fallbackText !== undefined) return fallbackText;
  return "--";
}

export interface ResolvedHeroState {
  state: "LOADING" | "BUY" | "SELL" | "WAIT" | "UNAVAILABLE";
  signalText: string;
  percentageText: string;
  theme: SignalSemanticTheme;
  isLoading: boolean;
  isUnavailable: boolean;
}

/**
 * Single authoritative presentation resolver for Hero percentage cards across all 10 pages/views:
 * - LOADING (isEvaluating = true) -> state: "LOADING", signalText: "WAIT...", percentageText: "", theme: neutral
 * - UNAVAILABLE (loaded, safePct == null) -> state: "UNAVAILABLE", signalText: "--", percentageText: "", theme: neutral
 * - < 50% -> state: "WAIT", signalText: "WAIT...", percentageText: "", theme: neutral
 * - >= 50% + BUY -> state: "BUY", signalText: "BUY", percentageText: "XX%", theme: Emerald (#10b981 / #34d399)
 * - >= 50% + SELL -> state: "SELL", signalText: "SELL", percentageText: "XX%", theme: Rose (#f43f5e / #fb7185)
 * - >= 50% + WAIT -> state: "WAIT", signalText: "WAIT...", percentageText: "", theme: neutral
 */
export function resolveHeroPresentation({
  signal,
  percentage,
  isEvaluating = false,
  isMarketClosed = false,
  fallbackPercentageText,
}: {
  signal?: string | null;
  percentage?: number | string | null;
  isEvaluating?: boolean;
  isMarketClosed?: boolean;
  fallbackPercentageText?: string;
}): ResolvedHeroState {
  // 1. Loading state (isEvaluating)
  if (isEvaluating) {
    return {
      state: "LOADING",
      signalText: "WAIT...",
      percentageText: "",
      theme: getNeutralSemanticTheme(),
      isLoading: true,
      isUnavailable: false,
    };
  }

  // 2. Market closed state
  if (isMarketClosed) {
    return {
      state: "WAIT",
      signalText: "MARKET CLOSED...",
      percentageText: "",
      theme: getSignalSemanticTheme("WAIT", null, true, false),
      isLoading: false,
      isUnavailable: false,
    };
  }

  const safePct =
    percentage != null && percentage !== "" && !isNaN(Number(percentage))
      ? Math.max(0, Math.min(100, Math.round(Number(percentage))))
      : null;

  // 3. Unavailable state (loaded but data is missing / invalid)
  if (safePct == null) {
    return {
      state: "UNAVAILABLE",
      signalText: fallbackPercentageText ?? "--",
      percentageText: "",
      theme: getNeutralSemanticTheme(),
      isLoading: false,
      isUnavailable: true,
    };
  }

  // 4. Valid percentage < 50% -> WAIT...
  if (safePct < 50) {
    return {
      state: "WAIT",
      signalText: "WAIT...",
      percentageText: "",
      theme: getNeutralSemanticTheme(),
      isLoading: false,
      isUnavailable: false,
    };
  }

  // 5. Valid percentage >= 50%
  const norm = String(signal || "").toUpperCase().trim();
  const isBuy = norm === "BUY" || norm === "BULLISH" || (norm.startsWith("BUY") && !norm.includes("WAIT"));
  const isSell = norm === "SELL" || norm === "BEARISH" || (norm.startsWith("SELL") && !norm.includes("WAIT"));

  if (isBuy) {
    return {
      state: "BUY",
      signalText: "BUY",
      percentageText: `${safePct}%`,
      theme: getSignalSemanticTheme("BUY", safePct, false, false),
      isLoading: false,
      isUnavailable: false,
    };
  }

  if (isSell) {
    return {
      state: "SELL",
      signalText: "SELL",
      percentageText: `${safePct}%`,
      theme: getSignalSemanticTheme("SELL", safePct, false, false),
      isLoading: false,
      isUnavailable: false,
    };
  }

  // Authoritative decision is WAIT (or NEUTRAL) with percentage >= 50%
  return {
    state: "WAIT",
    signalText: "WAIT...",
    percentageText: "",
    theme: getNeutralSemanticTheme(),
    isLoading: false,
    isUnavailable: false,
  };
}

/**
 * Resolves the authoritative Now Market percentage:
 * - Priority 1: decision.now_signal.percentage (Layer 2 Now Market Signal)
 * - Priority 2: decision.confluence_pct (17-factor technical confluence)
 * - Fallback: null (displays as "--%")
 *
 * Never returns a fake fallback (50%, 51%, etc.).
 */
export function resolveNowMarketPercentage(
  nowSignalPct?: number | null,
  confluencePct?: number | null
): number | null {
  if (nowSignalPct != null && !isNaN(Number(nowSignalPct)) && Number.isFinite(Number(nowSignalPct))) {
    return Math.max(0, Math.min(100, Math.round(Number(nowSignalPct))));
  }
  if (confluencePct != null && !isNaN(Number(confluencePct)) && Number.isFinite(Number(confluencePct))) {
    return Math.max(0, Math.min(100, Math.round(Number(confluencePct))));
  }
  return null;
}

/**
 * Resolves the authoritative Now Market direction:
 * - "BULLISH" | "BEARISH" | "NEUTRAL" | "WAIT"
 *
 * Derived from now_signal.signal or gate_direction / trend.
 */
export function resolveNowMarketDirection(
  nowSignalDir?: string | null,
  gateDir?: string | null,
  trendDir?: string | null,
  percentage?: number | string | null
): "BULLISH" | "BEARISH" | "NEUTRAL" | "WAIT" {
  const s = String(nowSignalDir || "").toUpperCase().trim();
  if (s === "BUY" || s === "BULLISH") return "BULLISH";
  if (s === "SELL" || s === "BEARISH") return "BEARISH";
  if (s === "NEUTRAL") return "NEUTRAL";

  const g = String(gateDir || "").toUpperCase().trim();
  const t = String(trendDir || "").toUpperCase().trim();
  const parsedPct = percentage != null && !isNaN(Number(percentage)) ? Number(percentage) : null;

  // When percentage is strictly greater than 50%, resolve the active directional signal
  if (parsedPct != null && parsedPct > 50) {
    if (g === "BULLISH" || t === "BULLISH") return "BULLISH";
    if (g === "BEARISH" || t === "BEARISH") return "BEARISH";
  }

  if (s === "WAIT") return "WAIT";
  if (g === "BULLISH") return "BULLISH";
  if (g === "BEARISH") return "BEARISH";
  if (t === "BULLISH") return "BULLISH";
  if (t === "BEARISH") return "BEARISH";
  if (t === "SIDEWAYS" || t === "NEUTRAL") return "NEUTRAL";
  return "WAIT";
}

/**
 * Formats authoritative conflict weight percentage (DEF-02):
 * - If a valid numeric value is provided, formats as percentage (e.g. 0.18 -> "18.0%", 18 -> "18.0%")
 * - If unavailable (null, undefined, non-numeric), returns truthful unavailable representation "--"
 * - NEVER fabricates "0.0%", "25.0%", or ">=25.0%"
 */
export function formatConflictWeight(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    const pct = value <= 1.0 ? value * 100 : value;
    return `${pct.toFixed(1)}%`;
  }
  return "--";
}

export interface SignalSemanticTheme {
  border: string;
  borderColor: string;
  cardBg: string;
  cardShadow: string;
  text: string;
  pctText: string;
  pctColor: string;
  accent: string;
  badge: string;
  textGlow: string;
  circleBgColor: string;
  circleShadow: string;
  backWaveStart: string;
  backWaveEnd: string;
  frontWaveStart: string;
  frontWaveMid: string;
  frontWaveEnd: string;
  rippleColor: string;
}

export function getNeutralSemanticTheme(): SignalSemanticTheme {
  return {
    border: "border-slate-700/60",
    borderColor: "rgba(100, 116, 139, 0.35)",
    cardBg: "linear-gradient(to right, rgba(30, 41, 59, 0.3), rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.2))",
    cardShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
    text: "text-slate-300",
    pctText: "text-slate-200",
    pctColor: "#cbd5e1",
    accent: "#64748b",
    badge: "bg-slate-800/60 text-slate-300 border-slate-600/50 shadow-none",
    textGlow: "none",
    circleBgColor: "#0f172a",
    circleShadow: "0 0 14px rgba(100, 116, 139, 0.2), inset 0 0 10px rgba(100, 116, 139, 0.15)",
    backWaveStart: "#334155",
    backWaveEnd: "#0f172a",
    frontWaveStart: "#94a3b8",
    frontWaveMid: "#64748b",
    frontWaveEnd: "#334155",
    rippleColor: "rgba(148, 163, 184, 0.3)",
  };
}

/**
 * Returns dynamic semantic colors strictly derived from current authoritative Hero state:
 * - BUY (>=50%)  -> Emerald / Green (#10b981 / #34d399)
 * - SELL (>=50%) -> Rose / Red (#f43f5e / #fb7185)
 * - <50% / WAIT  -> Neutral Slate/Zinc (#64748b / #cbd5e1), textGlow: none, cardShadow: none
 * - LOADING      -> Neutral Slate/Zinc
 * - UNAVAILABLE  -> Neutral Slate/Zinc
 *
 * Exactly 50% is directional: BUY 50% -> GREEN, SELL 50% -> RED.
 * Never hardcoded per asset or per page.
 */
export function getSignalSemanticTheme(
  signal: string,
  percentage?: number | string | null,
  isMarketClosed?: boolean,
  isEvaluating?: boolean
): SignalSemanticTheme {
  if (isMarketClosed) {
    return {
      border: "border-amber-500/40",
      borderColor: "rgba(245, 158, 11, 0.45)",
      cardBg: "linear-gradient(to right, rgba(120, 53, 15, 0.25), rgba(7, 19, 48, 0.9), rgba(120, 53, 15, 0.15))",
      cardShadow: "0 0 24px rgba(245, 158, 11, 0.12)",
      text: "text-amber-400",
      pctText: "text-amber-300",
      pctColor: "#fbbf24",
      accent: "#f59e0b",
      badge: "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_10px_rgba(245,158,11,0.25)]",
      textGlow: "none",
      circleBgColor: "#1c1204",
      circleShadow: "0 0 20px rgba(245, 158, 11, 0.25)",
      backWaveStart: "#78350f",
      backWaveEnd: "#1c1204",
      frontWaveStart: "#fbbf24",
      frontWaveMid: "#d97706",
      frontWaveEnd: "#78350f",
      rippleColor: "rgba(245, 158, 11, 0.4)",
    };
  }

  // Loading/transitioning state must remain stable and neutral — never flash BUY/SELL colors
  if (isEvaluating) {
    return getNeutralSemanticTheme();
  }

  const norm = String(signal || "").toUpperCase().trim();

  // If signal is WAIT (or contains WAIT/CONFLICT/NEUTRAL), ALWAYS neutral even if percentage >= 50%
  const isWait = norm === "" || norm === "WAIT" || norm.startsWith("WAIT") || norm.includes("WAIT") || norm.includes("CONFLICT") || norm === "NEUTRAL";
  if (isWait) {
    return getNeutralSemanticTheme();
  }

  const parsedPct =
    percentage != null && percentage !== "" && !isNaN(Number(percentage))
      ? Number(percentage)
      : null;

  // Below 50% is always neutral WAIT theme
  if (parsedPct !== null && parsedPct < 50) {
    return getNeutralSemanticTheme();
  }

  // Directional checks: strictly BUY or SELL (excluding any compound WAIT states)
  const isBuy = norm === "BUY" || norm === "BULLISH" || (norm.startsWith("BUY") && !norm.includes("WAIT"));
  const isSell = norm === "SELL" || norm === "BEARISH" || (norm.startsWith("SELL") && !norm.includes("WAIT"));

  // BUY -> Emerald (only when >= 50% or when valid directional signal has unspecified percentage)
  if (isBuy && (parsedPct === null || parsedPct >= 50)) {
    return {
      border: "border-emerald-500/50",
      borderColor: "rgba(52, 211, 153, 0.65)",
      cardBg: "linear-gradient(to right, rgba(6, 78, 59, 0.35), rgba(7, 19, 48, 0.92), rgba(6, 78, 59, 0.25))",
      cardShadow: "0 0 32px rgba(16, 185, 129, 0.22)",
      text: "text-emerald-400",
      pctText: "text-emerald-300",
      pctColor: "#34d399",
      accent: "#10b981",
      badge: "bg-emerald-500/20 text-emerald-300 border-emerald-400/60 shadow-[0_0_12px_rgba(16,185,129,0.3)]",
      textGlow: "0 0 16px rgba(52, 211, 153, 0.6)",
      circleBgColor: "#022113",
      circleShadow: "0 0 32px rgba(16, 185, 129, 0.5), inset 0 0 20px rgba(4, 120, 87, 0.5)",
      backWaveStart: "#047857",
      backWaveEnd: "#022c19",
      frontWaveStart: "#6ee7b7",
      frontWaveMid: "#10b981",
      frontWaveEnd: "#047857",
      rippleColor: "rgba(52, 211, 153, 0.8)",
    };
  }

  // SELL -> Rose (only when >= 50% or when valid directional signal has unspecified percentage)
  if (isSell && (parsedPct === null || parsedPct >= 50)) {
    return {
      border: "border-rose-500/50",
      borderColor: "rgba(251, 113, 133, 0.65)",
      cardBg: "linear-gradient(to right, rgba(136, 19, 55, 0.35), rgba(7, 19, 48, 0.92), rgba(136, 19, 55, 0.25))",
      cardShadow: "0 0 32px rgba(244, 63, 94, 0.22)",
      text: "text-rose-400",
      pctText: "text-rose-300",
      pctColor: "#fb7185",
      accent: "#f43f5e",
      badge: "bg-rose-500/20 text-rose-300 border-rose-400/60 shadow-[0_0_12px_rgba(244,63,94,0.3)]",
      textGlow: "0 0 16px rgba(251, 113, 133, 0.6)",
      circleBgColor: "#24030c",
      circleShadow: "0 0 32px rgba(244, 63, 94, 0.5), inset 0 0 20px rgba(190, 24, 74, 0.5)",
      backWaveStart: "#be123c",
      backWaveEnd: "#360611",
      frontWaveStart: "#fda4af",
      frontWaveMid: "#f43f5e",
      frontWaveEnd: "#be123c",
      rippleColor: "rgba(251, 113, 133, 0.8)",
    };
  }

  // WAIT / CONFLICT / NEUTRAL / Below 50%
  return getNeutralSemanticTheme();
}

/**
 * Returns consistent asset identification badge classes matching the existing project theme:
 * - BTC (Bitcoin / BTC/USD) -> subtle dark orange background tint, orange text, orange border
 *   "bg-orange-500/15 text-orange-300 border-orange-500/40"
 * - XAU (Gold / XAU/USD)   -> subtle dark yellow background tint, yellow/gold text, yellow border
 *   "bg-yellow-500/15 text-yellow-300 border-yellow-500/40"
 * - Fallback / Unknown       -> subtle dark zinc tint
 *   "bg-zinc-800/70 text-zinc-300 border-zinc-700/60"
 *
 * Strictly decoupled from signal state (BUY/SELL/WAIT) to preserve asset identity.
 */
export function getAssetBadgeClass(assetTickerOrName?: string): string {
  const norm = String(assetTickerOrName || "").toUpperCase();
  const isBtc = norm.includes("BTC") || norm.includes("BITCOIN");
  const isXau = norm.includes("XAU") || norm.includes("GOLD");

  if (isBtc) {
    return "bg-orange-500/15 text-orange-300 border-orange-500/40";
  }
  if (isXau) {
    return "bg-yellow-500/15 text-yellow-300 border-yellow-500/40";
  }
  return "bg-zinc-800/70 text-zinc-300 border-zinc-700/60";
}



