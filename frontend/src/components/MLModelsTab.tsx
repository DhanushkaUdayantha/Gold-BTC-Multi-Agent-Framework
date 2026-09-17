"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Brain,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Info,
  Check,
  Zap,
  Radio,
  FileText,
  Activity,
  Award,
} from "lucide-react";
import {
  ApiClient,
  MLShadowStatusResponse,
  MLShadowMetricsResponse,
  MLShadowObservation,
  MLShadowModelInfo,
} from "@/services/api";
import { SignalHeroCard, AnimatedWaitDots } from "./SignalHeroCard";
import {
  fmtPrice,
  fmtPct,
  fmtNumber,
  safeNum,
  formatRAsUSD,
  getNeutralSemanticTheme,
  getSignalSemanticTheme,
} from "@/lib/format";

interface MLModelsTabProps {
  currentAssetSymbol?: string;
}

/**
 * Reusable helper mapping signal and percentage to the dashboard visual theme.
 * BUY -> Green (Emerald), SELL -> Red (Rose), WAIT -> Blue (Sky)
 */
function getMLNeutralTheme() {
  return {
    text: "text-slate-300",
    pctText: "text-slate-200",
    pctColor: "#cbd5e1",
    accent: "#64748b",
    textGlow: "none",
    borderColor: "rgba(100, 116, 139, 0.35)",
    circleBgColor: "#0f172a",
    circleShadow: "0 0 14px rgba(100, 116, 139, 0.2), inset 0 0 10px rgba(100, 116, 139, 0.15)",
    cardBg: "linear-gradient(to right, rgba(30, 41, 59, 0.3), rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.2))",
    cardShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
    waterFill: "bg-gradient-to-t from-[#334155]/70 via-[#475569]/55 to-[#94a3b8]/40",
    backWaveStart: "#334155",
    backWaveEnd: "#0f172a",
    frontWaveStart: "#94a3b8",
    frontWaveMid: "#64748b",
    frontWaveEnd: "#334155",
    rippleColor: "rgba(148, 163, 184, 0.3)",
    badge: "bg-slate-800/60 text-slate-300 border-slate-600/50 shadow-none",
    bar: "bg-slate-500",
  };
}

function signalTheme(decision: string, percentage?: number | string | null) {
  const parsed = percentage != null && percentage !== "" && !isNaN(Number(percentage)) ? Number(percentage) : null;
  const safeP = parsed != null ? Math.max(0, Math.min(100, Math.round(parsed))) : null;
  const normDec = String(decision || "").toUpperCase().trim();
  const isBuy = normDec === "BUY" || normDec.startsWith("BUY") || normDec.includes("BULL");
  const isSell = normDec === "SELL" || normDec.startsWith("SELL") || normDec.includes("BEAR");

  // Rule 18: If percentage is 50%, do not treat as strong bullish/bearish -> neutral styling
  if (safeP !== null && safeP === 50) {
    return getMLNeutralTheme();
  }

  // BUY -> GREEN / EMERALD (> 50% only)
  if (isBuy && (safeP === null || safeP > 50)) {
    return {
      text: "text-emerald-400",
      pctText: "text-emerald-300",
      pctColor: "#34d399",
      accent: "#10b981",
      textGlow: "0 0 18px rgba(52, 211, 153, 0.75)",
      borderColor: "rgba(52, 211, 153, 0.75)",
      circleBgColor: "#022113",
      circleShadow: "0 0 40px rgba(16, 185, 129, 0.6), inset 0 0 25px rgba(4, 120, 87, 0.6)",
      cardBg: "linear-gradient(to right, rgba(6, 78, 59, 0.4), rgba(7, 19, 48, 0.9), rgba(6, 78, 59, 0.3))",
      cardShadow: "0 0 40px rgba(16, 185, 129, 0.3), inset 0 0 30px rgba(16, 185, 129, 0.1)",
      waterFill: "bg-gradient-to-t from-[#047857] via-[#059669]/90 to-[#34d399]/70",
      backWaveStart: "#047857",
      backWaveEnd: "#022c19",
      frontWaveStart: "#6ee7b7",
      frontWaveMid: "#10b981",
      frontWaveEnd: "#047857",
      rippleColor: "rgba(52, 211, 153, 0.9)",
      badge: "bg-emerald-500/25 text-emerald-300 border-emerald-400/70 shadow-[0_0_14px_rgba(16,185,129,0.4)]",
      bar: "bg-emerald-500",
    };
  }

  // SELL -> RED / ROSE (> 50% only)
  if (isSell && (safeP === null || safeP > 50)) {
    return {
      text: "text-rose-400",
      pctText: "text-rose-300",
      pctColor: "#fb7185",
      accent: "#f43f5e",
      textGlow: "0 0 18px rgba(251, 113, 133, 0.75)",
      borderColor: "rgba(251, 113, 133, 0.75)",
      circleBgColor: "#24030c",
      circleShadow: "0 0 40px rgba(244, 63, 94, 0.6), inset 0 0 25px rgba(190, 24, 74, 0.6)",
      cardBg: "linear-gradient(to right, rgba(136, 19, 55, 0.4), rgba(7, 19, 48, 0.9), rgba(136, 19, 55, 0.3))",
      cardShadow: "0 0 40px rgba(244, 63, 94, 0.3), inset 0 0 30px rgba(244, 63, 94, 0.1)",
      waterFill: "bg-gradient-to-t from-[#be123c] via-[#e11d48]/90 to-[#fb7185]/70",
      backWaveStart: "#be123c",
      backWaveEnd: "#360611",
      frontWaveStart: "#fda4af",
      frontWaveMid: "#f43f5e",
      frontWaveEnd: "#be123c",
      rippleColor: "rgba(251, 113, 133, 0.9)",
      badge: "bg-rose-500/25 text-rose-300 border-rose-400/70 shadow-[0_0_14px_rgba(244,63,94,0.4)]",
      bar: "bg-rose-500",
    };
  }

  // WAIT / Neutral / Below 50%
  return getMLNeutralTheme();
}

/**
 * Exact ML Hero Signal computation:
 * Single source of truth: ML API -> ml_probability -> UI
 *
 * Case 1: prob == null -> WAIT (Display: "...", SignalText: "WAIT", No fake fallback)
 * Case 2: ML probability < 50% -> WAIT XX%
 * Case 3: ML probability > 50% + BULLISH -> BUY XX% (Emerald theme)
 * Case 4: ML probability > 50% + BEARISH -> SELL XX% (Rose theme)
 */
function computeMLHeroSignal(prob: number | null | undefined, predStr: string | null | undefined) {
  if (prob == null || isNaN(Number(prob))) {
    return {
      signal: "WAIT",
      percentage: null,
      displayPct: "--",
      displaySignalText: "--",
      theme: getNeutralSemanticTheme(),
    };
  }

  const rawPct = prob * 100;
  const roundedPct = Math.round(rawPct);
  const clampedPct = Math.max(0, Math.min(100, roundedPct));
  const normPred = (predStr || "").toUpperCase().trim();

  // Case 2: ML probability < 50% -> WAIT...
  if (rawPct < 50) {
    return {
      signal: "WAIT",
      percentage: clampedPct,
      displayPct: "WAIT...",
      displaySignalText: "WAIT...",
      theme: getNeutralSemanticTheme(),
    };
  }

  // Case 3: ML probability >= 50% + BULLISH -> BUY XX%
  if ((normPred === "BULLISH" || normPred === "BUY") && rawPct >= 50) {
    return {
      signal: "BUY",
      percentage: clampedPct,
      displayPct: `${clampedPct}%`,
      displaySignalText: `BUY ${clampedPct}%`,
      theme: getSignalSemanticTheme("BUY", clampedPct),
    };
  }

  // Case 4: ML probability >= 50% + BEARISH -> SELL XX%
  if ((normPred === "BEARISH" || normPred === "SELL") && rawPct >= 50) {
    return {
      signal: "SELL",
      percentage: clampedPct,
      displayPct: `${clampedPct}%`,
      displaySignalText: `SELL ${clampedPct}%`,
      theme: getSignalSemanticTheme("SELL", clampedPct),
    };
  }

  // Fallback: WAIT...
  return {
    signal: "WAIT",
    percentage: clampedPct,
    displayPct: "WAIT...",
    displaySignalText: "WAIT...",
    theme: getNeutralSemanticTheme(),
  };
}

/**
 * Animated Concentric Water-Wave Circular Gauge
 */
function WaterSignalCircle({
  signal,
  percentage,
  subLabel,
  isEvaluating,
  uniqueId = "heroWave",
}: {
  signal: string;
  percentage?: number | string | null;
  subLabel?: string;
  isEvaluating?: boolean;
  uniqueId?: string;
}) {
  const safePct =
    percentage != null && percentage !== "" && !isNaN(Number(percentage))
      ? Math.max(0, Math.min(100, Math.round(Number(percentage))))
      : null;
  const theme = signalTheme(signal, safePct);
  const normSig = String(signal || "").toUpperCase().trim();
  const isStrong = safePct !== null && safePct >= 50 && (normSig === "BUY" || normSig.startsWith("BUY") || normSig === "SELL" || normSig.startsWith("SELL"));
  const waterHeight = isEvaluating || safePct === null ? 35 : Math.max(8, Math.min(100, safePct));

  return (
    <div
      className="relative w-28 h-28 rounded-full overflow-hidden border-2 flex items-center justify-center shrink-0 select-none transition-all duration-500"
      style={{
        borderColor: theme.borderColor,
        backgroundColor: theme.circleBgColor,
        boxShadow: theme.circleShadow,
        opacity: isStrong ? 1 : 0.85,
        filter: isStrong ? "saturate(1.25) brightness(1.1)" : "saturate(0.9) brightness(0.95)",
      }}
    >
      {/* Animated Concentric Water-Wave Ripple Ring (Active when >= 50% and directional) */}
      {!isEvaluating && isStrong && (
        <div
          className="absolute -inset-2 rounded-full pointer-events-none"
          style={{
            border: `2px solid ${theme.accent}`,
            animation: "waterWaveRipple 2.5s cubic-bezier(0.25, 1, 0.5, 1) infinite",
            opacity: 0.9,
          }}
        />
      )}

      {/* Water Fill Rising from BOTTOM to TOP */}
      <div
        className="absolute inset-x-0 bottom-0 transition-all duration-1000 ease-in-out"
        style={{
          height: `${waterHeight}%`,
          opacity: isStrong ? 1 : 0.75,
        }}
      >
        {/* Bottom-to-Top Vertical Gradient */}
        <div className={`w-full h-full ${theme.waterFill}`} />

        {/* Dual Continuous SVG Surface Waves */}
        <div className="absolute -top-[47px] left-0 w-[200%] h-[160px] opacity-60 liquid-wave-back pointer-events-none">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none" className="w-full h-full">
            <defs>
              <linearGradient id={`${uniqueId}_back`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={theme.backWaveStart} />
                <stop offset="100%" stopColor={theme.backWaveEnd} />
              </linearGradient>
            </defs>
            <path
              d="M 0,35 C 100,41 200,29 300,35 C 400,41 500,29 600,35 C 700,41 800,29 900,35 C 1000,41 1100,29 1200,35 L 1200,120 L 0,120 Z"
              fill={`url(#${uniqueId}_back)`}
            />
          </svg>
        </div>

        <div className="absolute -top-[46px] left-0 w-[200%] h-[160px] opacity-90 liquid-wave-front pointer-events-none">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none" className="w-full h-full">
            <defs>
              <linearGradient id={`${uniqueId}_front`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={theme.frontWaveStart} />
                <stop offset="40%" stopColor={theme.frontWaveMid} />
                <stop offset="100%" stopColor={theme.frontWaveEnd} />
              </linearGradient>
            </defs>
            <path
              d="M 0,35 C 100,29 200,41 300,35 C 400,29 500,41 600,35 C 700,29 800,41 900,35 C 1000,29 1100,41 1200,35 L 1200,120 L 0,120 Z"
              fill={`url(#${uniqueId}_front)`}
            />
          </svg>
        </div>
      </div>

      {/* Spherical Inner Rim Reflection */}
      <div className="absolute inset-0 rounded-full border border-white/15 pointer-events-none shadow-[inset_0_1px_2px_rgba(255,255,255,0.3)]" />

      {/* Center Percentage & Status Label */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center select-none px-1">
        {isEvaluating ? (
          <RefreshCw size={22} className="animate-spin text-sky-300 drop-shadow-[0_2px_10px_rgba(56,189,248,0.8)]" />
        ) : safePct === null ? (
          <AnimatedWaitDots className="text-xl" />
        ) : (
          <span
            className="text-2xl font-black font-mono tracking-tight"
            style={{
              color: theme.pctColor,
              textShadow: theme.textGlow !== "none" ? `${theme.textGlow}, 0 2px 8px rgba(0,0,0,0.9)` : "0 2px 8px rgba(0,0,0,0.9)",
            }}
          >
            {safePct}%
          </span>
        )}
        <span
          className="text-[9px] font-mono font-bold uppercase tracking-widest mt-0.5"
          style={{
            color: theme.pctColor,
            textShadow: "0 1px 4px rgba(0,0,0,0.9)",
            opacity: isStrong ? 1 : 0.8,
          }}
        >
          {subLabel || normSig}
        </span>
      </div>
    </div>
  );
}

export function MLModelsTab({ currentAssetSymbol = "XAU-USD-SPOT" }: MLModelsTabProps) {
  const [statusData, setStatusData] = useState<MLShadowStatusResponse | null>(null);
  const [metrics, setMetrics] = useState<MLShadowMetricsResponse | null>(null);
  const [observations, setObservations] = useState<MLShadowObservation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);

  // Active asset determination strictly from dashboard context
  const isBtc = currentAssetSymbol.toUpperCase().includes("BTC");
  const targetSymbol = isBtc ? "BTC/USD" : "XAU/USD";
  const targetAsset = isBtc ? "BTC" : "XAU";
  const targetAssetName = isBtc ? "Bitcoin" : "Gold";

  // Request ID ref for stale-response protection
  const activeRequestIdRef = useRef(0);

  const loadMLData = useCallback(async (isUserTriggered = false) => {
    const requestId = ++activeRequestIdRef.current;
    if (isUserTriggered) setRefreshing(true);
    setError(null);

    try {
      // Parallel fetch strictly scoped to targetSymbol — ZERO cross-asset leakage
      const [statusRes, metRes, obsRes] = await Promise.allSettled([
        ApiClient.getMLShadowStatus(),
        ApiClient.getMLShadowMetrics(targetSymbol),
        ApiClient.getMLShadowObservations(targetSymbol, 50),
      ]);

      // Check for stale response / race condition
      if (requestId !== activeRequestIdRef.current) return;

      if (statusRes.status === "fulfilled") {
        setStatusData(statusRes.value);
      }

      if (metRes.status === "fulfilled") {
        const val = metRes.value;
        if (val && (val.symbol === targetSymbol || val.symbol.toUpperCase().includes(targetAsset))) {
          setMetrics(val);
        }
      }

      if (obsRes.status === "fulfilled") {
        const list = obsRes.value || [];
        // Strict filtering to ensure only active asset observations are present
        const strictlyScoped = list.filter(
          (o) => o.symbol === targetSymbol || o.symbol.toUpperCase().includes(targetAsset)
        );
        setObservations(strictlyScoped);
      }

      setLastSyncAt(new Date().toISOString());
    } catch (err) {
      if (requestId !== activeRequestIdRef.current) return;
      console.error("Failed to load ML Shadow data:", err);
      setError(err instanceof Error ? err.message : "ML data temporarily unavailable");
    } finally {
      if (requestId === activeRequestIdRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [targetSymbol, targetAsset]);

  const formatModelVersion = (v?: string | null) => {
    if (!v) return "V1.0.0-Research";
    return v.replace(/v1\.0\.0-research/i, "V1.0.0-Research");
  };

  useEffect(() => {
    // Invalidate stale asset data immediately to prevent cross-asset leakage
    setLoading(true);
    setMetrics(null);
    setObservations([]);
    loadMLData(false);
    // Periodic polling every 30s
    const interval = setInterval(() => {
      loadMLData(false);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadMLData, currentAssetSymbol]);

  const formatIsoDate = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    } catch {
      return isoStr;
    }
  };

  const formatDateShort = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return (
        d.toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          timeZone: "UTC",
        }) + " UTC"
      );
    } catch {
      return isoStr;
    }
  };

  // Strictly asset-isolated extraction helper
  const getAssetLatestML = (obsList: MLShadowObservation[]) => {
    if (!obsList || obsList.length === 0) {
      return { prob: null, pred: null, lastObs: null };
    }
    const latest = obsList[obsList.length - 1];
    const predStr = latest.ml_predicted_class === 1 ? "BULLISH" : "BEARISH";
    return {
      prob: latest.ml_probability,
      pred: predStr,
      lastObs: latest,
    };
  };

  // Model details strictly from target asset store
  const modelInfo = statusData?.models?.[targetSymbol];
  const ml = getAssetLatestML(observations);
  const heroSignal = computeMLHeroSignal(ml.prob, ml.pred);

  return (
    <div className="space-y-6 font-mono">
      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 1. TOP HERO CARD: ML MODEL RELIABILITY (WITH WATER WAVE CIRCLE)       */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="space-y-4">
        {/* Separation Notice */}
        <div className="p-3.5 bg-[#08152e]/85 border border-sky-500/30 rounded-xl flex items-center gap-3 text-xs text-sky-200 backdrop-blur-md">
          <Info size={16} className="text-cyan-400 shrink-0" />
          <p className="leading-relaxed">
            <strong className="text-white font-bold tracking-wide">ML ARCHITECTURE NOTICE:</strong>{" "}
            ML is one supporting component of the final decision. It does not independently determine or execute trades.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <SignalHeroCard
            pageTitle="ML MODEL RELIABILITY & SHADOW VALIDATION"
            icon={Brain}
            assetName={targetAssetName}
            assetTicker={targetSymbol}
            signal={heroSignal.signal}
            percentage={heroSignal.percentage}
            statusBadge="SHADOW ACTIVE"
            isEvaluating={loading}
            timeChangeText={`${observations.length} Observations Recorded`}
            lastUpdatedText={ml.lastObs?.timestamp_t0 || lastSyncAt || undefined}
            supportingPills={
              <>
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-cyan-400">ML Model Prob:</span>
                  <span className="font-bold tabular-nums text-cyan-300">
                    {heroSignal.displayPct}
                  </span>
                </div>
                <span className="text-zinc-600 font-bold">&middot;</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-400">Model:</span>
                  <strong className="text-zinc-200">{modelInfo?.model_name || (isBtc ? "Logistic Regression" : "Random Forest")}</strong>
                </div>
                <span className="text-zinc-600 font-bold">&middot;</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Impact:</span>
                  <strong className="text-emerald-400 font-bold">NONE</strong>
                </div>
              </>
            }
            reasoning="Observational machine learning shadow model tracking forward out-of-sample prediction accuracy and probability calibration without altering live decision rules."
            uniqueId={`ml${targetAsset}HeroWave`}
          />
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 2. SECOND HERO CARD: ML SHADOW MODE                                   */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="bg-[#0c101d]/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg backdrop-blur-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.25)]">
              <Brain size={18} className="text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  ML SHADOW MODE &mdash; {targetSymbol}
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">
                  SHADOW OBSERVER LAYER
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  SHADOW VALIDATION IN PROGRESS
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-zinc-400 mt-0.5">
                Downstream machine learning shadow observer tracking forward out-of-sample predictions and calibration for {targetAssetName}.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 font-mono text-xs self-start sm:self-auto">
            {lastSyncAt && (
              <span className="hidden md:inline-block text-[10px] text-zinc-400">
                Synced: <strong className="text-zinc-300">{formatDateShort(lastSyncAt)}</strong>
              </span>
            )}
            <button
              type="button"
              onClick={() => loadMLData(true)}
              disabled={refreshing || loading}
              className="px-3 py-1.5 rounded-lg bg-sky-950/50 hover:bg-sky-900/60 border border-sky-500/30 hover:border-sky-400/50 text-sky-200 font-bold text-xs flex items-center gap-1.5 transition-all duration-300 disabled:opacity-50 shadow-[0_0_12px_rgba(56,189,248,0.15)]"
              title="Refresh ML Shadow status and metrics"
            >
              <RefreshCw size={12} className={refreshing || loading ? "animate-spin text-cyan-400" : "text-sky-300"} />
              {refreshing ? "SYNCING..." : "REFRESH"}
            </button>
          </div>
        </div>

        {/* Status Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
            <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">Status</span>
            <div className="mt-1">
              <span className="text-sm sm:text-base font-bold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={14} />
                VALIDATING
              </span>
              <span className="text-[9.5px] text-zinc-500 block">Observer Active</span>
            </div>
          </div>

          <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
            <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">Aggregator Integration</span>
            <div className="mt-1">
              <span className="text-sm sm:text-base font-bold text-amber-300 flex items-center gap-1">
                <ShieldCheck size={14} />
                ACTIVE OBSERVER
              </span>
              <span className="text-[9.5px] text-zinc-400 block">{isBtc ? "26%" : "24%"} Nominal Weight</span>
            </div>
          </div>

          <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
            <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">Live Broker Execution</span>
            <div className="mt-1">
              <span className="text-sm sm:text-base font-bold text-rose-400 flex items-center gap-1">
                <ShieldAlert size={14} />
                DISABLED
              </span>
              <span className="text-[9.5px] text-zinc-500 block">0% Automated Execution</span>
            </div>
          </div>

          <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
            <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">Asset Scoping</span>
            <div className="mt-1">
              <span className="text-sm sm:text-base font-bold text-sky-300 flex items-center gap-1">
                <Layers size={14} />
                {targetSymbol} ISOLATED
              </span>
              <span className="text-[9.5px] text-zinc-500 block">Strictly {targetAssetName}</span>
            </div>
          </div>
        </div>

        {/* Research / Shadow Mode Banner */}
        <div className="p-3 bg-[#0d1c38]/70 border border-sky-500/30 rounded-xl flex items-center gap-2.5 text-[11px] text-sky-200">
          <Info size={15} className="text-sky-400 shrink-0" />
          <div className="leading-relaxed">
            <strong className="text-sky-100 font-bold uppercase tracking-wider">RESEARCH / SHADOW MODE:</strong>{" "}
            ML provides an advisory {isBtc ? "26%" : "24%"} nominal input to the multi-source SignalAggregator alongside Technical ({isBtc ? "25%" : "27%"}), Historical ({isBtc ? "27%" : "26%"}), and Strategy ({isBtc ? "22%" : "23%"}). Automated broker/exchange execution remains strictly DISABLED (0% Execution Authority) under S2 Evidence Collection governance.
          </div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 3. ASSET SCOPE INDICATOR                                              */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center bg-[#071330]/75 backdrop-blur-xl px-3 py-1.5 rounded-xl border border-sky-500/35 shadow-[0_4px_20px_rgba(2,132,199,0.22)] gap-2">
          <span className={`w-2 h-2 rounded-full ${isBtc ? "bg-orange-400" : "bg-yellow-400"}`} />
          <span className={`text-xs font-bold ${isBtc ? "text-orange-200" : "text-yellow-200"}`}>
            {targetSymbol} ({targetAssetName}) ML Shadow Model
          </span>
          <span className="text-[10px] text-zinc-400 px-1.5 py-0.5 rounded bg-sky-950/60 border border-sky-500/20 font-mono">
            {formatModelVersion(modelInfo?.version)}
          </span>
        </div>

        <div className="text-[11px] text-zinc-400 flex items-center gap-2">
          <span>Model Architecture: <strong className="text-zinc-200">{modelInfo?.model_name || (isBtc ? "Logistic Regression" : "Random Forest")}</strong></span>
          <span>&middot;</span>
          <span>
            Observations:{" "}
            <strong className="text-sky-300">
              {observations.length} ({targetAsset})
            </strong>
          </span>
        </div>
      </div>

      {/* Error State Banner */}
      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-xl flex items-center justify-between gap-2.5 text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadMLData(true)}
            className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800/80 text-rose-100 font-bold text-[11px] border border-rose-500/40"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !statusData ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3 text-sky-400 font-mono bg-[#071330]/40 border border-sky-500/20 rounded-2xl">
          <RefreshCw size={28} className="animate-spin text-cyan-400 drop-shadow-[0_0_14px_rgba(56,189,248,0.8)]" />
          <span className="text-xs font-bold tracking-wider text-sky-200 uppercase">
            Loading ML Shadow Model Outputs &amp; Observations for {targetSymbol}...
          </span>
        </div>
      ) : (
        <div className="space-y-8">
          <AssetMLSection
            symbol={targetSymbol}
            assetName={targetAssetName}
            theme={
              isBtc
                ? {
                    border: "border-orange-500/35 hover:border-orange-500/60",
                    headerBadge: "bg-orange-500/15 text-orange-300 border-orange-500/40",
                    accentText: "text-orange-400",
                    glow: "shadow-[0_4px_24px_rgba(249,115,22,0.12)]",
                    cardBg: "bg-[#0c0d12]",
                  }
                : {
                    border: "border-yellow-500/35 hover:border-yellow-500/60",
                    headerBadge: "bg-yellow-500/15 text-yellow-300 border-yellow-500/40",
                    accentText: "text-yellow-400",
                    glow: "shadow-[0_4px_24px_rgba(234,179,8,0.12)]",
                    cardBg: "bg-[#0c0d12]",
                  }
            }
            modelInfo={modelInfo}
            metrics={metrics}
            observations={observations}
            latestProb={ml.prob}
            latestPred={ml.pred}
            formatIsoDate={formatIsoDate}
          />
        </div>
      )}
    </div>
  );
}


/* ───────────────────────────────────────────────────────────────────────────── */
/* Asset ML Section (Strictly Isolated for BTC or XAU)                           */
/* ───────────────────────────────────────────────────────────────────────────── */

interface AssetMLSectionProps {
  symbol: string;
  assetName: string;
  theme: {
    border: string;
    headerBadge: string;
    accentText: string;
    glow: string;
    cardBg: string;
  };
  modelInfo?: MLShadowModelInfo;
  metrics?: MLShadowMetricsResponse | null;
  observations: MLShadowObservation[];
  latestProb?: number | null;
  latestPred?: string | null;
  formatIsoDate: (iso?: string | null) => string;
}

function AssetMLSection({
  symbol,
  assetName,
  theme,
  modelInfo,
  metrics,
  observations,
  latestProb,
  latestPred,
  formatIsoDate,
}: AssetMLSectionProps) {
  const [tableOpen, setTableOpen] = useState(false);
  const totalObs = metrics?.total_observations ?? observations.length;
  const pendingObs = metrics?.pending_observations ?? observations.filter((o) => o.outcome === "PENDING").length;
  const resolvedTrades = metrics?.resolved_trades ?? observations.filter((o) => o.outcome === "WIN" || o.outcome === "LOSS").length;
  const waitObs = metrics?.wait_observations ?? observations.filter((o) => o.outcome === "OBSERVED_WAIT").length;

  const m25Passed = resolvedTrades >= 25;
  const m50Passed = resolvedTrades >= 50;
  const m100Passed = resolvedTrades >= 100;

  const winRate = metrics?.win_rate;
  const evR = metrics?.ev_r;
  const pf = metrics?.profit_factor;
  const brier = metrics?.brier_score;
  const calibEce = metrics?.calibration?.expected_calibration_error;

  const currentHero = computeMLHeroSignal(latestProb, latestPred);

  return (
    <section className={`bg-[#080c14]/90 border ${theme.border} rounded-2xl p-4 sm:p-6 ${theme.glow} backdrop-blur-md space-y-5 transition-all duration-300`}>
      {/* Asset Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1b2234] pb-3.5">
        <div className="flex items-center gap-2.5">
          <span className={`text-xs sm:text-sm font-bold px-3 py-1 rounded-md border ${theme.headerBadge}`}>
            {symbol} &mdash; {assetName.toUpperCase()}
          </span>
          <span className="text-xs text-zinc-400 font-semibold">
            ML SHADOW MODEL
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {modelInfo?.available ? "SHADOW ACTIVE" : "INITIALIZING"}
          </span>
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
            {modelInfo?.version ? modelInfo.version.replace(/v1\.0\.0-research/i, "V1.0.0-Research") : "V1.0.0-Research"}
          </span>
        </div>
      </div>

      {/* Grid: 1. Model Output Card | 2. Observation Progress | 3. Validation Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* CARD 1: ML MODEL OUTPUT */}
        <div className="bg-[#0e121d] border border-[#1e2538] rounded-xl p-4 space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-[#1a2233] pb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Brain size={12} className={theme.accentText} />
              ML MODEL OUTPUT
            </span>
            <span className={`text-[10px] font-bold ${theme.accentText}`}>
              {modelInfo?.model_name || "ML Classifier"}
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500">Model Architecture:</span>
              <strong className="text-zinc-200">{modelInfo?.model_name || "N/A"}</strong>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500">Shadow Status:</span>
              <span className="text-emerald-400 font-bold">
                {modelInfo?.available ? "ACTIVE" : "N/A"}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500">Latest ML Probability:</span>
              <strong className={`text-sm font-bold ${latestProb != null ? currentHero.theme.text : "text-zinc-400"}`}>
                {latestProb != null ? `${(latestProb * 100).toFixed(1)}%` : "N/A"}
              </strong>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500">Model Prediction:</span>
              <span className={`font-bold px-2 py-0.5 rounded text-[10px] border ${currentHero.theme.badge}`}>
                {latestPred || "N/A"}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500">Observation Status:</span>
              <strong className="text-sky-300">
                {totalObs > 0 ? "RECORDED" : "AWAITING DATA"}
              </strong>
            </div>

            <div className="flex items-center justify-between text-xs border-t border-[#1a2233] pt-1.5">
              <span className="text-zinc-500">Production Impact:</span>
              <strong className="text-emerald-400">NONE</strong>
            </div>
          </div>
        </div>

        {/* CARD 2: OBSERVATION PROGRESS */}
        <div className="bg-[#0e121d] border border-[#1e2538] rounded-xl p-4 space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-[#1a2233] pb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Activity size={12} className="text-sky-400" />
              OBSERVATION SUMMARY
            </span>
            <span className="text-[10px] text-zinc-400 font-bold">
              {totalObs} Total
            </span>
          </div>

          <div className="space-y-2">
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="bg-[#121624] p-2 rounded-lg border border-[#1d2438]">
                <div className="text-[9.5px] text-zinc-500">Total</div>
                <div className="text-base font-bold text-zinc-200 mt-0.5">{totalObs}</div>
              </div>
              <div className="bg-[#121624] p-2 rounded-lg border border-[#1d2438]">
                <div className="text-[9.5px] text-zinc-500">Resolved</div>
                <div className="text-base font-bold text-emerald-400 mt-0.5">{resolvedTrades}</div>
              </div>
              <div className="bg-[#121624] p-2 rounded-lg border border-[#1d2438]">
                <div className="text-[9.5px] text-zinc-500">Pending</div>
                <div className="text-base font-bold text-sky-400 mt-0.5">{pendingObs}</div>
              </div>
            </div>

            {totalObs > 0 && resolvedTrades === 0 && (
              <div className="text-[10px] text-zinc-400 bg-[#121624]/60 px-2.5 py-1 rounded border border-[#1d2438] flex items-center justify-between">
                <span className="text-zinc-500">Non-Trade (WAIT):</span>
                <span className="text-zinc-300 font-semibold">{waitObs} (100%)</span>
              </div>
            )}

            {/* Milestone Trackers */}
            <div className="pt-1.5 space-y-1.5">
              <div className="text-[9.5px] text-zinc-400 uppercase font-bold tracking-wider">
                Forward Milestone Progress
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-[10px]">
                <div className={`p-1.5 rounded border text-center font-bold ${
                  m25Passed
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                    : resolvedTrades > 0
                    ? "bg-sky-500/15 text-sky-300 border-sky-500/40"
                    : "bg-zinc-800/60 text-zinc-400 border-zinc-700/60"
                }`}>
                  25 {m25Passed ? "✓ Preliminary" : resolvedTrades > 0 ? `○ (${resolvedTrades}/25)` : "○ Waiting"}
                </div>
                <div className={`p-1.5 rounded border text-center font-bold ${
                  m50Passed
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                    : resolvedTrades >= 25
                    ? "bg-sky-500/15 text-sky-300 border-sky-500/40"
                    : "bg-zinc-800/60 text-zinc-400 border-zinc-700/60"
                }`}>
                  50 {m50Passed ? "✓ Milestone" : resolvedTrades >= 25 ? `○ (${resolvedTrades}/50)` : "○ Pending"}
                </div>
                <div className={`p-1.5 rounded border text-center font-bold ${
                  m100Passed
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                    : resolvedTrades >= 50
                    ? "bg-sky-500/15 text-sky-300 border-sky-500/40"
                    : "bg-zinc-800/60 text-zinc-400 border-zinc-700/60"
                }`}>
                  100 {m100Passed ? "✓ Full" : resolvedTrades >= 50 ? `○ (${resolvedTrades}/100)` : "○ Pending"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CARD 3: ML VALIDATION METRICS */}
        <div className="bg-[#0e121d] border border-[#1e2538] rounded-xl p-4 space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-[#1a2233] pb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Award size={12} className="text-amber-400" />
              ML VALIDATION METRICS
            </span>
            <span className="text-[10px] text-amber-300 font-bold">
              {resolvedTrades > 0 ? `${resolvedTrades} Resolved` : "In Progress"}
            </span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Resolved N:</span>
              <strong className="text-zinc-200">{resolvedTrades}</strong>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Win Rate:</span>
              <strong className={winRate != null ? "text-emerald-400" : "text-zinc-400"}>
                {winRate != null ? `${winRate.toFixed(1)}%` : "N/A (Pending N ≥ 1)"}
              </strong>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-zinc-500">EV ($):</span>
              <strong className={evR != null ? (evR >= 0 ? "text-emerald-400" : "text-rose-400") : "text-zinc-400"}>
                {formatRAsUSD(evR, { showSign: true, digits: 4, fallback: "N/A" })}
              </strong>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Profit Factor:</span>
              <strong className="text-zinc-200">
                {pf != null ? pf.toFixed(2) : "N/A"}
              </strong>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Brier Score:</span>
              <strong className="text-zinc-300">
                {brier != null ? brier.toFixed(4) : "N/A"}
              </strong>
            </div>

            <div className="flex items-center justify-between border-t border-[#1a2233] pt-1">
              <span className="text-zinc-500">Calibration ECE:</span>
              <strong className="text-sky-300">
                {calibEce != null ? `${(calibEce * 100).toFixed(2)}%` : "N/A"}
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* 4. USER-FRIENDLY ML METRICS EXPLANATION GLOSSARY */}
      <div className="bg-[#0b101c] border border-[#1b2234] rounded-xl p-4 sm:p-5 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1b2234] pb-2.5">
          <Info size={14} className="text-cyan-400" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
            ML Reliability Metric Definitions
          </h4>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">Accuracy</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              How often the model was correct across all evaluated predictions.
            </p>
          </div>
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">Precision</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              How often positive directional predictions were correct.
            </p>
          </div>
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">Recall</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              How many positive setup cases the model detected.
            </p>
          </div>
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">F1 Score</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Harmonic balance between precision and recall.
            </p>
          </div>
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">Brier Score</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Probability prediction quality (mean squared error of probability; 0.0 is perfect).
            </p>
          </div>
          <div className="bg-[#121624] p-3 rounded-lg border border-[#1d2438] space-y-1">
            <span className="font-bold text-sky-300">Expected Calibration Error (ECE)</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Probability calibration quality measuring alignment between predicted probability and actual win rate.
            </p>
          </div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 6. LATEST ML OBSERVATIONS TABLE                                       */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="bg-[#0e121d] border border-[#1e2538] rounded-xl p-4 sm:p-5 space-y-3">
        <div className="flex items-center justify-between border-b border-[#1a2233] pb-2.5">
          <div className="flex items-center gap-2">
            <FileText size={14} className={theme.accentText} />
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              {symbol} &mdash; POINT-IN-TIME ML OBSERVATIONS ({observations.length})
            </h3>
          </div>
          <button
            onClick={() => setTableOpen(!tableOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-[10px] font-mono font-semibold transition-colors cursor-pointer"
          >
            <span>Evidence Details {tableOpen ? "▾" : "▸"}</span>
          </button>
        </div>

        {observations.length === 0 ? (
          <div className="py-8 text-center text-xs text-zinc-500 font-mono space-y-1">
            <p className="font-bold text-zinc-400">No ML observations recorded yet for {symbol}.</p>
            <p className="text-[11px] text-zinc-600">
              Shadow validation will appear here as real forward observations are collected.
            </p>
          </div>
        ) : !tableOpen ? (
          <div className="py-3 px-3.5 bg-[#0a0d16] border border-zinc-800 rounded-lg flex items-center justify-between text-xs font-mono text-zinc-400">
            <span>Summary: {observations.length} immutable T0 forward snapshots recorded for {symbol}.</span>
            <button
              onClick={() => setTableOpen(true)}
              className="text-sky-400 hover:text-sky-300 font-bold underline text-[11px] ml-2 cursor-pointer"
            >
              Evidence Details ▸
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1e2538] text-[10px] text-zinc-500 uppercase">
                  <th className="py-2 px-2 font-semibold">Timestamp (UTC)</th>
                  <th className="py-2 px-2 font-semibold">T0 Price</th>
                  <th className="py-2 px-2 font-semibold">Production Decision</th>
                  <th className="py-2 px-2 font-semibold">ML Prob</th>
                  <th className="py-2 px-2 font-semibold">Prediction</th>
                  <th className="py-2 px-2 font-semibold">Confluence</th>
                  <th className="py-2 px-2 font-semibold">Actual Outcome</th>
                  <th className="py-2 px-2 font-semibold">Realized P&L</th>
                  <th className="py-2 px-2 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#151b2a]">
                {[...observations].reverse().slice(0, 15).map((obs) => {
                  const isResolved = obs.outcome === "WIN" || obs.outcome === "LOSS";
                  const isPending = obs.outcome === "PENDING";
                  const obsHero = computeMLHeroSignal(
                    obs.ml_probability,
                    obs.ml_predicted_class === 1 ? "BULLISH" : "BEARISH"
                  );

                  return (
                    <tr key={obs.observation_id} className="hover:bg-[#121624] transition-colors">
                      <td className="py-2.5 px-2 text-zinc-300 text-[11px] whitespace-nowrap">
                        {formatIsoDate(obs.timestamp_t0)}
                      </td>
                      <td className="py-2.5 px-2 font-bold text-zinc-200 tabular-nums">
                        {fmtPrice(obs.entry_price)}
                      </td>
                      <td className="py-2.5 px-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                          obs.production_decision === "BUY"
                            ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                            : obs.production_decision === "SELL"
                            ? "bg-rose-500/15 text-rose-300 border-rose-500/40"
                            : "bg-blue-500/15 text-blue-300 border-blue-500/40"
                        }`}>
                          {obs.production_decision}
                        </span>
                      </td>
                      <td className={`py-2.5 px-2 font-bold tabular-nums ${obsHero.theme.text}`}>
                        {(obs.ml_probability * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${obsHero.theme.badge}`}>
                          {obs.ml_predicted_class === 1 ? "BUY" : "SELL"}
                        </span>
                      </td>
                      <td className="py-2.5 px-2 text-zinc-400 tabular-nums">
                        {obs.confluence_score} pts
                      </td>
                      <td className="py-2.5 px-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          obs.outcome === "WIN"
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                            : obs.outcome === "LOSS"
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/50"
                            : obs.outcome === "OBSERVED_WAIT"
                            ? "bg-zinc-800 text-zinc-400 border-zinc-700"
                            : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                        }`}>
                          {obs.outcome}
                        </span>
                      </td>
                      <td className="py-2.5 px-2 font-bold tabular-nums">
                        {obs.realized_r != null && obs.realized_r !== 0 ? (
                          <span className={obs.realized_r > 0 ? "text-emerald-400" : "text-rose-400"}>
                            {formatRAsUSD(obs.realized_r, { showSign: true })}
                          </span>
                        ) : (
                          <span className="text-zinc-500">$0.00</span>
                        )}
                      </td>
                      <td className="py-2.5 px-2">
                        {isPending ? (
                          <span className="text-[10px] font-bold text-amber-400 flex items-center gap-1">
                            <Clock size={10} />
                            PENDING
                          </span>
                        ) : isResolved ? (
                          <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 size={10} />
                            RESOLVED
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-zinc-400">
                            RECORDED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
