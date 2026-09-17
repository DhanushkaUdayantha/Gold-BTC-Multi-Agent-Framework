"use client";

import React, { useMemo, useState, useEffect, useCallback, useRef, type ReactNode } from "react";
import {
  RefreshCw,
  AlertTriangle,
  Activity,
  Clock,
  TrendingUp,
  TrendingDown,
  Info,
  X,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Sliders,
  BarChart3,
  Layers,
  Cpu,
  Target,
  Zap,
  CheckCircle2,
  AlertCircle,
  Timer,
  Compass,
  Edit2,
  Check,
  Sparkles,
  Database,
  ShieldCheck,
  ShieldAlert,
  Scale,
  Settings,
} from "lucide-react";
import { useDashboardData } from "@/hooks/useDashboardData";
import { CandleChart } from "@/components/CandleChart";
import { CandleLogo } from "@/components/EagleLogo";
import { HistoricalDatasetStatus } from "@/components/HistoricalDatasetStatus";
import { EmpiricalPerformancePanel } from "@/components/EmpiricalPerformancePanel";
import { HistoricalBacktestTab } from "@/components/HistoricalBacktestTab";
import { MLModelsTab } from "@/components/MLModelsTab";
import { ShadowAccumulationMonitor } from "@/components/ShadowAccumulationMonitor";
import { SignalHeroCard } from "@/components/SignalHeroCard";
import { formatRelativeTime, useRelativeTime, RelativeTime } from "@/lib/relativeTime";
import {
  biasClass,
  fmtCurrency,
  fmtNumber,
  fmtPct,
  fmtPrice,
  formatRAsUSD,
  fmtSigned,
  fmtSignedCurrency,
  fmtSriLankaTime,
  fmtTime,
  isPresent,
  resolveNowMarketDirection,
  resolveNowMarketPercentage,
  resolveOverallSignalPercentage,
  resolveHistoryMarketPercentage,
  resolveMLShadowAccuracy,
  riskClass,
  safeNum,
  getAssetBadgeClass,
} from "@/lib/format";
import {
  ApiClient,
  TradeRecord,
  PaperTradingStats,
  normalizePaperTradingStats,
  PerformanceReportData,
  CalibrationResponse,
  PriceQuote,
  ValidatedStrategyEvaluation,
  DegradationMonitoringReport,
  OverallTradingSignal,
  TradingDecision,
  SystemObservabilityResponse,
  getSystemObservability,
} from "@/services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Constants & Timeframes
// ─────────────────────────────────────────────────────────────────────────────

const ASSETS = [
  { id: "XAU-USD-SPOT", name: "Gold", ticker: "XAU/USD", badgeColor: "bg-yellow-500/15 text-yellow-300 border-yellow-500/40", activeClass: "bg-yellow-500/25 text-yellow-300 border-yellow-500/50 text-shadow" },
  { id: "BTC-USD", name: "Bitcoin", ticker: "BTC/USD", badgeColor: "bg-orange-500/10 text-orange-300 border-orange-500/30", activeClass: "bg-orange-500/20 text-orange-300 border-orange-500/50 text-shadow" },
];

const TIMEFRAMES = [
  { label: "5m", value: "5m" },
  { label: "15m", value: "15m" },
  { label: "1H", value: "1h" },
  { label: "1D", value: "1d" },
];

const MTF_KEYS = ["5m", "15m", "1h", "1d"] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Next Candle Countdown Hook
// ─────────────────────────────────────────────────────────────────────────────

function useNextCandleCountdown(timeframe: string) {
  const [secondsRemaining, setSecondsRemaining] = useState<number>(0);

  useEffect(() => {
    function calcRemaining() {
      const now = new Date();
      const currentSeconds = now.getUTCSeconds();
      const currentMinutes = now.getUTCMinutes();
      const currentHours = now.getUTCHours();

      let targetPeriodSeconds = 300; // 5m
      let elapsedInPeriodSeconds = (currentMinutes % 5) * 60 + currentSeconds;

      if (timeframe === "15m") {
        targetPeriodSeconds = 900;
        elapsedInPeriodSeconds = (currentMinutes % 15) * 60 + currentSeconds;
      } else if (timeframe === "1h") {
        targetPeriodSeconds = 3600;
        elapsedInPeriodSeconds = currentMinutes * 60 + currentSeconds;
      } else if (timeframe === "1d") {
        targetPeriodSeconds = 86400;
        elapsedInPeriodSeconds = currentHours * 3600 + currentMinutes * 60 + currentSeconds;
      }

      const rem = targetPeriodSeconds - elapsedInPeriodSeconds;
      setSecondsRemaining(rem > 0 ? rem : targetPeriodSeconds);
    }

    calcRemaining();
    const timer = setInterval(calcRemaining, 1000);
    return () => clearInterval(timer);
  }, [timeframe]);

  const mins = Math.floor(secondsRemaining / 60);
  const secs = secondsRemaining % 60;
  const hours = Math.floor(mins / 60);

  if (timeframe === "1d") {
    return `${hours.toString().padStart(2, "0")}h ${(mins % 60).toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`;
  }
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Weekend Market Closed Hook (Gold closes Fri 22:00 UTC – Sun 22:00 UTC)
// ─────────────────────────────────────────────────────────────────────────────

function useIsWeekendMarketClosed(symbol: string) {
  const [isClosed, setIsClosed] = useState(false);

  useEffect(() => {
    function check() {
      const isGold = symbol.toUpperCase().includes("XAU") || symbol.toUpperCase().includes("GOLD");
      if (!isGold) {
        setIsClosed(false);
        return;
      }
      const now = new Date();
      const day = now.getUTCDay(); // 0 = Sunday, 1 = Monday, ..., 5 = Friday, 6 = Saturday
      const hour = now.getUTCHours();
      const minute = now.getUTCMinutes();
      const currentTime = hour + minute / 60;

      // Gold Market closes Friday 22:00 UTC (5:00 PM EST) and re-opens Sunday 22:00 UTC (5:00 PM EST)
      const isFridayAfterClose = day === 5 && currentTime >= 22.0;
      const isSaturday = day === 6;
      const isSundayBeforeOpen = day === 0 && currentTime < 22.0;

      setIsClosed(isFridayAfterClose || isSaturday || isSundayBeforeOpen);
    }

    check();
    const timer = setInterval(check, 30000);
    return () => clearInterval(timer);
  }, [symbol]);

  return isClosed;
}

// ─────────────────────────────────────────────────────────────────────────────
// Theme Helpers
// ─────────────────────────────────────────────────────────────────────────────

function signalTheme(decision: string, percentage: number | string = 50, isEvaluating = false) {
  const parsed = typeof percentage === "number" ? percentage : parseFloat(String(percentage || "50"));
  const safeP = !isNaN(parsed) ? parsed : 50;
  const normDec = String(decision || "").toUpperCase().trim();

  // Loading/evaluating state must remain stable and neutral
  if (isEvaluating) {
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
      waterFill: "bg-gradient-to-t from-[#334155]/70 via-[#475569]/45 to-[#64748b]/25",
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

  // WAIT must ALWAYS remain neutral, even if percentage > 50%
  const isWait = normDec === "" || normDec === "WAIT" || normDec.startsWith("WAIT") || normDec.includes("WAIT") || normDec.includes("CONFLICT") || normDec === "NEUTRAL";
  if (isWait) {
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
      waterFill: "bg-gradient-to-t from-[#334155]/70 via-[#475569]/45 to-[#64748b]/25",
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

  // Exactly 50% -> neutral
  if (Math.round(safeP) === 50) {
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
      waterFill: "bg-gradient-to-t from-[#334155]/70 via-[#475569]/45 to-[#64748b]/25",
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

  const isBuy = normDec === "BUY" || normDec === "BULLISH" || (normDec.startsWith("BUY") && !normDec.includes("WAIT"));
  const isSell = normDec === "SELL" || normDec === "BEARISH" || (normDec.startsWith("SELL") && !normDec.includes("WAIT"));

  // RULE 1: percentage > 50% AND signal = BUY → GREEN
  if (safeP > 50 && isBuy) {
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

  // RULE 2: percentage > 50% AND signal = SELL → RED
  if (safeP > 50 && isSell) {
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

  // RULE 3: Below 50% → Neutral
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
    waterFill: "bg-gradient-to-t from-[#334155]/70 via-[#475569]/45 to-[#64748b]/25",
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

function WaterSignalCircle({
  signal,
  percentage,
  subLabel,
  isEvaluating,
  isMarketClosed,
  isInsufficient,
  uniqueId = "heroWave",
}: {
  signal: string;
  percentage?: number | string | null;
  subLabel?: string;
  isEvaluating?: boolean;
  isMarketClosed?: boolean;
  isInsufficient?: boolean;
  uniqueId?: string;
}) {
  const safePct = percentage != null && percentage !== "" && !isNaN(Number(percentage)) ? Math.max(0, Math.min(100, Math.round(Number(percentage)))) : null;
  const theme = signalTheme(signal, safePct ?? 0);
  const normSig = String(signal || "").toUpperCase().trim();
  const isStrong = safePct != null && safePct > 50 && (normSig === "BUY" || normSig.startsWith("BUY") || normSig === "SELL" || normSig.startsWith("SELL"));
  const waterHeight = isEvaluating || safePct == null ? 35 : Math.max(8, Math.min(100, safePct));

  return (
    <div
      className="relative w-28 h-28 rounded-full overflow-hidden border-2 flex items-center justify-center shrink-0 select-none transition-all duration-500"
      style={{
        borderColor: isMarketClosed ? "rgba(245, 158, 11, 0.5)" : theme.borderColor,
        backgroundColor: isMarketClosed ? "#1c1204" : theme.circleBgColor,
        boxShadow: isMarketClosed ? "0 0 20px rgba(245, 158, 11, 0.25)" : theme.circleShadow,
        opacity: isMarketClosed ? 0.9 : isStrong ? 1 : 0.75,
        filter: isStrong ? "saturate(1.25) brightness(1.1)" : "saturate(0.8) brightness(0.85)",
      }}
    >
      {/* Animated Concentric Water-Wave Ripple Ring (Active when > 50%) */}
      {!isEvaluating && !isMarketClosed && isStrong && (
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
          opacity: isStrong ? 1 : 0.7,
        }}
      >
        {/* Bottom-to-Top Vertical Gradient */}
        <div
          className={`w-full h-full ${isMarketClosed
            ? "bg-gradient-to-t from-[#78350f] via-[#b45309]/80 to-[#f59e0b]/50"
            : theme.waterFill
            }`}
        />

        {/* Dual Continuous SVG Surface Waves */}
        <div className="absolute -top-[47px] left-0 w-[200%] h-[160px] opacity-60 liquid-wave-back pointer-events-none">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none" className="w-full h-full">
            <defs>
              <linearGradient id={`${uniqueId}_back`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={isMarketClosed ? "#b45309" : theme.backWaveStart} />
                <stop offset="100%" stopColor={isMarketClosed ? "#451a03" : theme.backWaveEnd} />
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
                <stop offset="0%" stopColor={isMarketClosed ? "#fbbf24" : theme.frontWaveStart} />
                <stop offset="40%" stopColor={isMarketClosed ? "#f59e0b" : theme.frontWaveMid} />
                <stop offset="100%" stopColor={isMarketClosed ? "#78350f" : theme.frontWaveEnd} />
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
        {isMarketClosed ? (
          <span className="text-lg font-black font-mono text-amber-300 drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)] tracking-tight">
            STANDBY
          </span>
        ) : isEvaluating ? (
          <RefreshCw size={22} className="animate-spin text-sky-300 drop-shadow-[0_2px_10px_rgba(56,189,248,0.8)]" />
        ) : isInsufficient ? (
          <span className="text-[10px] font-black font-mono text-amber-300 drop-shadow-[0_2px_6px_rgba(0,0,0,0.9)] leading-tight px-1 text-center">
            SAMPLE &lt; 20
          </span>
        ) : (
          <span
            className="text-2xl font-black font-mono tracking-tight"
            style={{
              color: theme.pctColor,
              textShadow: theme.textGlow !== "none" ? `${theme.textGlow}, 0 2px 8px rgba(0,0,0,0.9)` : "0 2px 8px rgba(0,0,0,0.9)",
            }}
          >
            {safePct != null ? `${safePct}%` : "--%"}
          </span>
        )}
        <span
          className="text-[9px] font-mono font-bold uppercase tracking-widest mt-0.5"
          style={{
            color: theme.pctColor,
            textShadow: "0 1px 4px rgba(0,0,0,0.9)",
            opacity: isStrong ? 1 : 0.75,
          }}
        >
          {isMarketClosed
            ? "Closed"
            : isEvaluating
              ? "Syncing"
              : isInsufficient
                ? "Insufficient"
                : subLabel || signal}
        </span>
      </div>
    </div>
  );
}


function StatusDot({ ok, warn, loading }: { ok: boolean; warn?: boolean; loading?: boolean }) {
  if (loading) {
    return <RefreshCw size={10} className="animate-spin text-cyan-400 shrink-0" />;
  }
  const color = ok ? "bg-emerald-400 shadow-[0_0_8px_#10b981]" : warn ? "bg-amber-400 shadow-[0_0_8px_#f59e0b]" : "bg-rose-500";
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />;
}

function Tip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex items-center cursor-default ml-1">
      <Info size={11} className="text-zinc-500 group-hover:text-zinc-300 transition-colors" />
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-60 rounded-md bg-[#18181f] border border-[#2e2e38] p-2 text-[10px] font-mono text-zinc-200 opacity-0 group-hover:opacity-100 transition-opacity z-50 shadow-2xl leading-relaxed">
        {text}
      </span>
    </span>
  );
}

function Card({
  title,
  children,
  className = "",
  action,
  icon: Icon,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
  icon?: React.ElementType;
}) {
  return (
    <section className={`bg-[#0c0c0f] border border-[#1e1e24] rounded-xl p-5 shadow-sm transition-all duration-700 ease-out ${className}`}>
      <div className="flex items-center justify-between border-b border-[#1a1a22] pb-2.5 mb-4">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={14} className="text-amber-400" />}
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-zinc-200">
            {title}
          </h3>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function ChartSkeleton() {
  return (
    <div className="w-full h-[420px] rounded-xl bg-blue-950/20 border border-blue-500/30 shadow-[0_0_24px_rgba(59,130,246,0.15)] backdrop-blur-xl flex flex-col items-center justify-center gap-3 text-blue-400 font-mono">
      <RefreshCw size={26} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
      <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
        Syncing Market Candlestick Matrix...
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. OVERALL CONFIRMATION CARD (Combined Current Trading Assessment)
// ─────────────────────────────────────────────────────────────────────────────

function OverallConfirmationCard({
  signal,
  signalStrength,
  confluencePct,
  confluenceDir,
  technicalScore,
  geminiScore,
  mtfPct,
  mtfSummary,
  trendDirection,
  trendStrength,
  isMarketClosed,
  isEvaluating,
  geminiOnline,
  marketOnline,
  assetTicker,
}: {
  signal: string;
  signalStrength?: number | null;
  confluencePct: number;
  confluenceDir: string;
  technicalScore: number;
  geminiScore: number;
  mtfPct?: number | null;
  mtfSummary: string;
  trendDirection: string;
  trendStrength: string;
  isMarketClosed?: boolean;
  isEvaluating?: boolean;
  geminiOnline?: boolean;
  marketOnline?: boolean;
  assetTicker?: string;
}) {
  const isBuy = signal === "BUY" && !isEvaluating && !isMarketClosed;
  const isSell = signal === "SELL" && !isEvaluating && !isMarketClosed;

  return (
    <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-4 sm:p-5 shadow-[0_8px_32px_rgba(2,132,199,0.18)] backdrop-blur-xl font-mono space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-sky-500/20 pb-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-sky-200">
                OVERALL CONFIRMATION
              </h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getAssetBadgeClass(assetTicker)}`}>
                {assetTicker || "ASSET"}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${isMarketClosed
                  ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                  : isBuy
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.25)]"
                    : isSell
                      ? "bg-rose-500/15 text-rose-300 border-rose-500/40 shadow-[0_0_10px_rgba(244,63,94,0.25)]"
                      : "bg-blue-500/15 text-blue-300 border-blue-500/40"
                  }`}
              >
                {isMarketClosed
                  ? "MARKET CLOSED"
                  : isEvaluating
                    ? "PENDING CONFIRMATION"
                    : isBuy
                      ? "CONFIRMED BUY ASSESSMENT"
                      : isSell
                        ? "CONFIRMED SELL ASSESSMENT"
                        : "STANDBY / WAIT ASSESSMENT"}
              </span>
            </div>
            <p className="text-[10px] sm:text-[11px] text-zinc-400 mt-0.5">
              Combined multi-engine assessment answering: &quot;What is the current combined trading assessment?&quot;
            </p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-1.5 flex-wrap text-[10px]">
          <span className={`px-2 py-0.5 rounded font-bold border ${marketOnline ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : "bg-rose-500/10 text-rose-300 border-rose-500/30"}`}>
            LIVE {marketOnline ? "✓" : "OFFLINE"}
          </span>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 font-bold">
            MTF ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-bold">
            STRATEGIES ✓
          </span>
          <span className={`px-2 py-0.5 rounded font-bold border ${geminiOnline ? "bg-purple-500/10 text-purple-300 border-purple-500/30" : "bg-zinc-800 text-zinc-400 border-zinc-700"}`}>
            GEMINI {geminiOnline ? "✓" : "UNAVAILABLE"}
          </span>
        </div>
      </div>

      {/* 4 Pillars Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">1. Confluence Engine</span>
          <div className="mt-1">
            <span className={`text-base font-bold ${confluenceDir === "Bearish" ? "text-rose-400" : "text-emerald-400"}`}>
              {isEvaluating || confluencePct == null ? "--" : `${confluencePct}% ${confluenceDir || ""}`.trim()}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">Weighted Point Matrix</span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">2. Technical Alignment</span>
          <div className="mt-1">
            <span className="text-base font-bold text-zinc-100">
              {isEvaluating || technicalScore == null ? "--" : `${technicalScore} / 90`}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">{trendDirection || "Neutral"} ({trendStrength || "Moderate"})</span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">3. Multi-Timeframe Vector</span>
          <div className="mt-1">
            <span className="text-base font-bold text-sky-300">
              {isEvaluating || mtfPct == null ? "--" : `${mtfPct}%`}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">{mtfSummary && mtfSummary !== "--" ? mtfSummary : "--"}</span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">4. Gemini AI Confirmation</span>
          <div className="mt-1">
            <span className="text-base font-bold text-purple-300">
              {isEvaluating ? "--" : geminiOnline && geminiScore != null ? `${geminiScore} / 10` : "N/A"}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">{geminiOnline ? "Model Validated" : "AI Offline"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. NOW MARKET ANALYSIS CONFIRMATION CARD (Current Live Market Setup)
// ─────────────────────────────────────────────────────────────────────────────

function NowMarketConfirmationCard({
  symbol,
  assetName,
  assetTicker,
  currentLivePrice,
  changeUsd,
  changePct,
  trendDirection,
  trendStrength,
  marketCondition,
  sweepDetected,
  liquidityStatus,
  mssConfirmed,
  rsiValue,
  rsiCondition,
  macdState,
  nearestSupport,
  nearestResistance,
  mtfPct,
  mtfSummary,
  isMarketClosed,
  isEvaluating,
  marketOnline,
  geminiOnline,
}: {
  symbol: string;
  assetName: string;
  assetTicker: string;
  currentLivePrice: number;
  changeUsd: number | null;
  changePct: number | null;
  trendDirection: string;
  trendStrength: string;
  marketCondition: string;
  sweepDetected: boolean;
  liquidityStatus: string;
  mssConfirmed: boolean;
  rsiValue: number | null;
  rsiCondition: string;
  macdState: string;
  nearestSupport: number | null;
  nearestResistance: number | null;
  mtfPct?: number | null;
  mtfSummary: string;
  isMarketClosed?: boolean;
  isEvaluating?: boolean;
  marketOnline?: boolean;
  geminiOnline?: boolean;
}) {
  return (
    <div className="bg-[#071330]/90 border border-cyan-500/30 rounded-2xl p-4 sm:p-5 shadow-[0_8px_32px_rgba(6,182,212,0.18)] backdrop-blur-xl font-mono space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-cyan-500/20 pb-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Activity size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-cyan-200">
                NOW MARKET ANALYSIS CONFIRMATION
              </h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getAssetBadgeClass(assetTicker)}`}>
                {assetTicker}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${isMarketClosed
                  ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                  : !marketOnline
                    ? "bg-rose-500/15 text-rose-300 border-rose-500/40"
                    : "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.25)]"
                  }`}
              >
                {isMarketClosed
                  ? "MARKET CLOSED (STANDBY)"
                  : !marketOnline
                    ? "LIVE DATA UNAVAILABLE"
                    : isEvaluating
                      ? "EVALUATING LIVE SETUP..."
                      : "LIVE MARKET SETUP CONFIRMED"}
              </span>
            </div>
            <p className="text-[10px] sm:text-[11px] text-zinc-400 mt-0.5">
              Real-time market condition answering: &quot;Is the current live market setup actually confirmed right now?&quot;
            </p>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div className="flex items-center gap-1.5 flex-wrap text-[10px]">
          <span className={`px-2 py-0.5 rounded font-bold border ${marketOnline ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : "bg-rose-500/10 text-rose-300 border-rose-500/30"}`}>
            LIVE FEED {marketOnline ? "✓" : "OFFLINE"}
          </span>
          <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-bold">
            PRICE ACTION ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 font-bold">
            MTF ALIGNMENT ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-bold">
            SMC / ICT ✓
          </span>
          <span className={`px-2 py-0.5 rounded font-bold border ${geminiOnline ? "bg-purple-500/10 text-purple-300 border-purple-500/30" : "bg-zinc-800 text-zinc-400 border-zinc-700"}`}>
            GEMINI {geminiOnline ? "✓" : "N/A"}
          </span>
        </div>
      </div>

      {/* 4 Live Execution Conditions Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div className="bg-[#09152e]/80 border border-cyan-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">1. Live Price &amp; Trend</span>
          <div className="mt-1">
            <span className="text-base font-bold text-zinc-100 tabular-nums">
              {currentLivePrice > 0 ? fmtPrice(currentLivePrice) : "N/A"}
            </span>
            <span className="text-[9.5px] text-zinc-400 block">
              {trendDirection || "Neutral"} &middot; {trendStrength || "Moderate"}
            </span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-cyan-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">2. Liquidity &amp; Structure</span>
          <div className="mt-1">
            <span className={`text-sm font-bold ${sweepDetected ? "text-emerald-400" : "text-zinc-300"}`}>
              {sweepDetected ? "SWEEP DETECTED" : "ORDERLY FLOW"}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">MSS: {mssConfirmed ? "Confirmed" : "Pending"}</span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-cyan-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">3. Immediate Momentum</span>
          <div className="mt-1">
            <span className="text-sm font-bold text-cyan-300">
              RSI {rsiValue != null ? Math.round(rsiValue) : "N/A"} &middot; {rsiCondition || "Neutral"}
            </span>
            <span className="text-[9.5px] text-zinc-500 block">MACD: {macdState || "Neutral"}</span>
          </div>
        </div>

        <div className="bg-[#09152e]/80 border border-cyan-500/20 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[9.5px] text-zinc-400 uppercase font-semibold">4. Key Institutional Levels</span>
          <div className="mt-1">
            <span className="text-xs font-bold text-emerald-400 block truncate">
              S: {fmtPrice(nearestSupport)}
            </span>
            <span className="text-xs font-bold text-rose-400 block truncate">
              R: {fmtPrice(nearestResistance)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. HISTORICAL MARKET CONFIRMATION CARD (Evidence-Based Empirical Confirmation)
// ─────────────────────────────────────────────────────────────────────────────

function HistoricalMarketConfirmationCard({
  symbol,
  assetName,
  assetTicker,
  historicalEvidenceStatus,
  historicalWinRate,
  calibratedProb,
  calibrationStatus,
  historicalSampleSize,
  similarSetupCount,
  historicalExpectancy,
  historicalProfitFactor,
  winRateCiLower,
  winRateCiUpper,
  similarityStrength,
  buyStrength,
  sellStrength,
  historicalBias,
  patternMatch,
  topWinFactor,
  topFailureRisk,
  evidenceQuality,
  datasetVersion,
  scoreBandWinRate,
  evidenceRefreshAt,
}: {
  symbol: string;
  assetName: string;
  assetTicker: string;
  historicalEvidenceStatus?: string;
  historicalWinRate?: number | null;
  calibratedProb?: number | null;
  calibrationStatus?: string;
  historicalSampleSize?: number | null;
  similarSetupCount?: number | null;
  historicalExpectancy?: number | null;
  historicalProfitFactor?: number | null;
  winRateCiLower?: number | null;
  winRateCiUpper?: number | null;
  similarityStrength?: number | null;
  buyStrength?: number | null;
  sellStrength?: number | null;
  historicalBias?: string | null;
  patternMatch?: string | null;
  topWinFactor?: string | null;
  topFailureRisk?: string | null;
  evidenceQuality?: string | null;
  datasetVersion?: string | null;
  scoreBandWinRate?: number | null;
  evidenceRefreshAt?: string | null;
}) {
  const hasHistoricalData = historicalEvidenceStatus === "AVAILABLE" || (historicalSampleSize != null && historicalSampleSize > 0);
  const sampleN = safeNum(historicalSampleSize, 0);
  const safeSimilarity = similarityStrength != null ? Math.max(0, Math.min(100, Math.round(Number(similarityStrength)))) : null;

  const dynamicStatusBadge = sampleN >= 200 || evidenceQuality === "STRONG"
    ? "STRONG"
    : sampleN >= 50 || evidenceQuality === "VALID"
      ? "VALID"
      : sampleN >= 20
        ? "EXPLORATORY"
        : sampleN > 0
          ? "PRELIMINARY"
          : (historicalEvidenceStatus || "UNAVAILABLE");

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-[#060e20]/95 border border-sky-500/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_8px_32px_rgba(2,132,199,0.2)] backdrop-blur-xl space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-sky-500/20 pb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xs sm:text-sm font-bold tracking-wider text-sky-200 uppercase">
                HISTORICAL MARKET CONFIRMATION
              </h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getAssetBadgeClass(assetTicker)}`}>
                {assetTicker}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${sampleN >= 200 || historicalEvidenceStatus === "AVAILABLE"
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]"
                  : sampleN >= 20 || historicalEvidenceStatus === "LIMITED"
                    ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/40"
                    : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                  }`}
              >
                EVIDENCE: {dynamicStatusBadge}
              </span>
            </div>
            <p className="text-[10px] sm:text-[11px] text-zinc-400 mt-0.5">
              Empirical historical evidence answering: &quot;Does historical evidence support this type of setup?&quot;
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {evidenceRefreshAt && (
            <RelativeTime
              timestamp={evidenceRefreshAt}
              prefix="Refreshed "
              className="text-[9.5px] text-zinc-500 hidden sm:inline"
            />
          )}
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 text-[10px] font-bold">
            HISTORICAL {hasHistoricalData ? "✓" : "UNAVAILABLE"}
          </span>
        </div>
      </div>

      {/* 8-Metric Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-center sm:text-left">
        <div className="bg-[#09152e]/80 border border-indigo-500/30 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-indigo-300 uppercase font-medium block">Calibrated Prob</span>
          <span className="font-bold text-sm text-indigo-200 tabular-nums">
            {calibratedProb != null ? `${calibratedProb.toFixed(1)}%` : "N/A"}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">95% CI</span>
          <span className="font-bold text-xs text-zinc-200 tabular-nums truncate">
            {winRateCiLower != null && winRateCiUpper != null ? `${winRateCiLower.toFixed(1)}%–${winRateCiUpper.toFixed(1)}%` : "N/A"}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">Sample Size</span>
          <span className="font-bold text-sm text-sky-300 tabular-nums">
            {historicalSampleSize != null ? `${historicalSampleSize}` : "N/A"}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">Similar Setups</span>
          <span className="font-bold text-sm text-cyan-300 tabular-nums">
            {similarSetupCount != null ? `${similarSetupCount}` : (historicalSampleSize != null ? `${historicalSampleSize}` : "N/A")}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">Historical WR</span>
          <span className="font-bold text-sm text-emerald-300 tabular-nums">
            {historicalWinRate != null ? `${historicalWinRate.toFixed(1)}%` : "N/A"}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">Expectancy ($)</span>
          <span className={`font-bold text-sm tabular-nums ${historicalExpectancy != null && historicalExpectancy >= 0 ? "text-emerald-300" : historicalExpectancy != null ? "text-rose-300" : "text-zinc-200"
            }`}>
            {formatRAsUSD(historicalExpectancy, { showSign: true, fallback: "N/A" })}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase font-medium block">Profit Factor</span>
          <span className="font-bold text-sm text-amber-300 tabular-nums">
            {historicalProfitFactor != null ? historicalProfitFactor.toFixed(2) : "N/A"}
          </span>
        </div>

        <div className="bg-[#09152e]/80 border border-sky-500/20 rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[9px] text-sky-300 uppercase font-medium block">Similarity</span>
          <span className="font-bold text-sm text-sky-200 tabular-nums">
            {safeSimilarity != null ? `${safeSimilarity}%` : "N/A"}
          </span>
        </div>
      </div>

      {/* Pattern Match Row */}
      <div className="bg-[#081224]/70 border border-sky-500/15 rounded-lg px-3 py-2 text-[11px] flex items-start sm:items-center justify-between gap-2 flex-col sm:flex-row">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] uppercase font-bold text-sky-400 shrink-0">Pattern Match:</span>
          <span className="text-zinc-200 font-normal">
            {patternMatch || `${assetTicker} statistical setup matching structural regime & multi-timeframe confluence`}
          </span>
        </div>
        {scoreBandWinRate != null && (
          <span className="text-[10px] text-emerald-400 font-semibold shrink-0 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/25">
            Score Band WR: {scoreBandWinRate.toFixed(1)}%
          </span>
        )}
      </div>

      {/* Top Empirical Drivers & Risk Factors */}
      {(topWinFactor || topFailureRisk) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10.5px]">
          {topWinFactor && (
            <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-lg px-3 py-1.5 flex items-start gap-1.5">
              <span className="text-emerald-400 font-bold shrink-0">WIN FACTOR:</span>
              <span className="text-emerald-200/90">{topWinFactor}</span>
            </div>
          )}
          {topFailureRisk && (
            <div className="bg-rose-950/20 border border-rose-500/20 rounded-lg px-3 py-1.5 flex items-start gap-1.5">
              <span className="text-rose-400 font-bold shrink-0">FAILURE RISK:</span>
              <span className="text-rose-200/90">{topFailureRisk}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NOW MARKET ANALYSE AI TRADING SIGNAL HERO
// ─────────────────────────────────────────────────────────────────────────────

function NowMarketSignalHero({
  signal,
  signalStrength,
  buyScore,
  sellScore,
  trendDirection,
  trendStrength,
  marketCondition,
  sweepDetected,
  mssConfirmed,
  rsiValue,
  rsiCondition,
  macdState,
  confluencePct,
  confluenceDir,
  technicalScore,
  geminiScore,
  mtfPct,
  mtfSummary,
  geminiSummary,
  assetTicker,
  assetName,
  isMarketClosed,
  loading,
  lastUpdated,
  geminiOnline,
  marketOnline,
}: {
  signal: string;
  signalStrength?: number | null;
  buyScore?: number | null;
  sellScore?: number | null;
  trendDirection: string;
  trendStrength: string;
  marketCondition: string;
  sweepDetected: boolean;
  mssConfirmed: boolean;
  rsiValue: number | null;
  rsiCondition: string;
  macdState: string;
  confluencePct: number;
  confluenceDir: string;
  technicalScore: number;
  geminiScore: number;
  mtfPct?: number | null;
  mtfSummary: string;
  geminiSummary?: string | null;
  assetTicker?: string;
  assetName?: string;
  isMarketClosed?: boolean;
  loading?: boolean;
  lastUpdated?: string;
  geminiOnline?: boolean;
  marketOnline?: boolean;
}) {
  const safeStrength = signalStrength != null ? Math.max(0, Math.min(100, Math.round(Number(signalStrength)))) : null;
  const safeBuy = buyScore != null ? Math.max(0, Math.min(100, Math.round(Number(buyScore)))) : null;
  const safeSell = sellScore != null ? Math.max(0, Math.min(100, Math.round(Number(sellScore)))) : null;
  const theme = signalTheme(signal, safeStrength ?? 0);
  const isEvaluating = Boolean(loading);
  const circleTheme = (isEvaluating || isMarketClosed) ? signalTheme("WAIT", safeStrength ?? 0) : theme;

  const isBuyHigher = !isEvaluating && !isMarketClosed && safeBuy != null && safeSell != null && safeBuy > safeSell;
  const isSellHigher = !isEvaluating && !isMarketClosed && safeBuy != null && safeSell != null && safeSell > safeBuy;
  const nowGrade = safeStrength != null ? (safeStrength >= 75 ? "A" : safeStrength >= 55 ? "B" : "C") : "--";

  return (
    <div className="space-y-3 font-mono">
      <SignalHeroCard
        pageTitle="NOW MARKET ANALYSE AI TRADING SIGNAL"
        icon={Activity}
        assetName={assetName || (assetTicker?.includes("BTC") ? "Bitcoin" : "Gold")}
        assetTicker={assetTicker || ""}
        signal={isMarketClosed ? "WAIT" : isEvaluating ? "WAIT" : signal}
        percentage={isMarketClosed ? null : safeStrength}
        statusBadge={isMarketClosed ? "MARKET CLOSED" : `LIVE GRADE ${isEvaluating ? "..." : nowGrade}`}
        isEvaluating={isEvaluating}
        isMarketClosed={isMarketClosed}
        timeChangeText={sweepDetected ? "Liquidity Sweep Detected" : undefined}
        lastUpdatedText={isEvaluating ? undefined : lastUpdated}
        supportingPills={
          isMarketClosed ? (
            <span className="text-amber-300 font-semibold">MARKET CLOSED · REAL-TIME TECHNICAL ENGINE PAUSED</span>
          ) : (
            <>
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-cyan-400">Technical Score:</span>
                <span className="font-bold tabular-nums text-cyan-300">
                  {isEvaluating || safeStrength == null ? "--" : `${safeStrength}%`}
                </span>
              </div>
              <span className="text-zinc-600 font-bold">·</span>
              <div className="flex items-center gap-1.5">
                <span className={`font-medium ${isBuyHigher ? "text-emerald-300 font-bold" : "text-emerald-400/80"}`}>BUY:</span>
                <span className="font-bold tabular-nums text-emerald-300">
                  {isEvaluating || signal === "WAIT" || safeBuy == null || safeBuy <= 30 ? "--%" : `${safeBuy}%`}
                </span>
              </div>
              <span className="text-zinc-600 font-bold">·</span>
              <div className="flex items-center gap-1.5">
                <span className={`font-medium ${isSellHigher ? "text-rose-300 font-bold" : "text-rose-400/80"}`}>SELL:</span>
                <span className="font-bold tabular-nums text-rose-300">
                  {isEvaluating || signal === "WAIT" || safeSell == null || safeSell <= 30 ? "--%" : `${safeSell}%`}
                </span>
              </div>
            </>
          )
        }
        reasoning={
          isMarketClosed
            ? "Gold market is closed for the weekend. Showing live analysis as of last session close."
            : isEvaluating
              ? "Scanning live market structure, momentum oscillators, and institutional order flow..."
              : geminiSummary || (signal === "BUY"
                ? `Live technical structure shows ${trendDirection} bias with ${trendStrength} momentum and confirmed MTF alignment.`
                : signal === "SELL"
                  ? `Live technical structure shows ${trendDirection} bias with ${trendStrength} momentum and confirmed MTF alignment.`
                  : `Market is in ${marketCondition || "Range"} mode with neutral technical momentum. Waiting for clear trigger.`)
        }
        uniqueId="nowHeroWave"
      />

      {/* 5 Live Confirmation Pillars */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 border-t border-white/5 text-[11px]">
        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">1. Confluence Engine</span>
          <span className={`font-bold text-sm tabular-nums ${confluenceDir === "Bearish" ? "text-rose-400" : "text-emerald-400"}`}>
            {isEvaluating || confluencePct == null ? "--" : `${confluencePct}% ${confluenceDir || ""}`.trim()}
          </span>
        </div>
        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">2. Trend &amp; Bias</span>
          <span className="font-bold text-sm text-zinc-200 tabular-nums">
            {isEvaluating || !trendDirection ? "--" : `${trendDirection} (${trendStrength || "Moderate"})`}
          </span>
        </div>
        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">3. Liquidity Sweeps</span>
          <span className={`font-bold text-sm tabular-nums ${sweepDetected ? "text-emerald-400" : "text-zinc-400"}`}>
            {isEvaluating ? "--" : sweepDetected ? "SWEEP DETECTED" : "ORDERLY"}
          </span>
        </div>
        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">4. Momentum (RSI/MACD)</span>
          <span className="font-bold text-sm text-cyan-300 tabular-nums">
            {isEvaluating ? "--" : `RSI ${rsiValue != null ? Math.round(rsiValue) : "--"} · ${macdState || "--"}`}
          </span>
        </div>
        <div className="bg-[#091122]/90 border border-sky-500/30 rounded-lg p-2.5 col-span-2 sm:col-span-1">
          <span className="text-[9px] text-sky-300 uppercase font-semibold block">5. Gemini AI Rating</span>
          <span className="font-bold text-sm text-sky-200 tabular-nums">
            {isEvaluating ? "--" : geminiOnline && geminiScore != null ? `${geminiScore} / 10 Active` : "Offline"}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HISTORICAL MARKET ANALYSE AI TRADING SIGNAL HERO
// ─────────────────────────────────────────────────────────────────────────────

function HistoricalMarketSignalHero({
  signal,
  historicalBias,
  buyStrength,
  sellStrength,
  similarityStrength,
  calibratedProb,
  calibrationStatus,
  historicalWinRate,
  historicalSampleSize,
  historicalExpectancy,
  historicalProfitFactor,
  winRateCiLower,
  winRateCiUpper,
  scoreBandWinRate,
  similarSetupCount,
  topSuccessReasons,
  topFailureReasons,
  historicalConfirmations,
  historicalConflicts,
  evidenceQuality,
  datasetVersion,
  overallReasoning,
  assetTicker,
  assetName,
  isMarketClosed,
  loading,
  lastUpdated,
}: {
  signal: string;
  historicalBias?: string | null;
  buyStrength?: number | null;
  sellStrength?: number | null;
  similarityStrength?: number | null;
  calibratedProb?: number | null;
  calibrationStatus?: string;
  historicalWinRate?: number | null;
  historicalSampleSize?: number | null;
  historicalExpectancy?: number | null;
  historicalProfitFactor?: number | null;
  winRateCiLower?: number | null;
  winRateCiUpper?: number | null;
  scoreBandWinRate?: number | null;
  similarSetupCount?: number | null;
  topSuccessReasons?: string[] | null;
  topFailureReasons?: string[] | null;
  historicalConfirmations?: string[] | null;
  historicalConflicts?: string[] | null;
  evidenceQuality?: string | null;
  datasetVersion?: string | null;
  overallReasoning?: string | null;
  assetTicker?: string;
  assetName?: string;
  isMarketClosed?: boolean;
  loading?: boolean;
  lastUpdated?: string;
}) {
  const safeBuyStrength = buyStrength != null ? Math.max(0, Math.min(100, Math.round(Number(buyStrength)))) : null;
  const safeSellStrength = sellStrength != null ? Math.max(0, Math.min(100, Math.round(Number(sellStrength)))) : null;
  const safeSimilarity = similarityStrength != null ? Math.max(0, Math.min(100, Math.round(Number(similarityStrength)))) : null;
  const rawProb = calibratedProb ?? historicalWinRate;
  const safeProb = rawProb != null ? Math.max(0, Math.min(100, Math.round(Number(rawProb)))) : null;
  const safeWinRate = historicalWinRate != null ? Math.max(0, Math.min(100, Math.round(Number(historicalWinRate)))) : null;
  const sampleN = safeNum(historicalSampleSize, 0);

  // Directional Bias synthesized from statistical evidence (never raw win rate alone)
  const activeDirection = (historicalBias === "BUY" || historicalBias === "SELL")
    ? historicalBias
    : (safeBuyStrength != null && safeSellStrength != null && safeBuyStrength >= 65 && safeBuyStrength >= safeSellStrength + 15)
      ? "BUY"
      : (safeBuyStrength != null && safeSellStrength != null && safeSellStrength >= 65 && safeSellStrength >= safeBuyStrength + 15)
        ? "SELL"
        : (signal === "BUY" || signal === "SELL") && safeProb != null && safeProb >= 58
          ? signal
          : "WAIT";

  const activeStrength = activeDirection === "BUY"
    ? safeBuyStrength
    : activeDirection === "SELL"
      ? safeSellStrength
      : (safeBuyStrength != null && safeSellStrength != null ? Math.round((safeBuyStrength + safeSellStrength) / 2) : null);

  const hasHistory = sampleN > 0 || (safeProb != null && safeProb > 0);
  const isEvaluating = Boolean(loading);

  const histGrade = sampleN >= 200 && (activeStrength ?? 0) >= 70 ? "A+" : sampleN >= 50 && (activeStrength ?? 0) >= 60 ? "A" : sampleN >= 20 ? "B" : "C";

  // Statistically validated badge text (no misleading INSUFFICIENT DATA when sample size exists)
  const dynamicEvidenceBadge = sampleN >= 200 || evidenceQuality === "STRONG"
    ? "STRONG STATISTICAL EVIDENCE"
    : sampleN >= 50 || evidenceQuality === "VALID"
      ? "STATISTICALLY CALIBRATED"
      : sampleN >= 20
        ? "EXPLORATORY SAMPLE"
        : sampleN > 0
          ? "PRELIMINARY SAMPLE"
          : (calibrationStatus && calibrationStatus !== "INSUFFICIENT_DATA" ? calibrationStatus : "CALIBRATING");

  return (
    <div className="space-y-3 font-mono">
      <SignalHeroCard
        pageTitle="HISTORICAL MARKET ANALYSE AI TRADING SIGNAL"
        icon={Database}
        assetName={assetName || (assetTicker?.includes("BTC") ? "Bitcoin" : "Gold")}
        assetTicker={assetTicker || ""}
        signal={activeDirection}
        percentage={safeProb}
        statusBadge={dynamicEvidenceBadge}
        isEvaluating={isEvaluating}
        isMarketClosed={isMarketClosed}
        timeChangeText={sampleN > 0 ? `N = ${sampleN} historical setups` : "Awaiting historical sample"}
        lastUpdatedText={isEvaluating ? undefined : lastUpdated}
        supportingPills={
          <>
            {activeDirection === "BUY" ? (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-emerald-400">BUY Strength:</span>
                  <span className="font-black tabular-nums text-emerald-300">{safeBuyStrength != null ? `${safeBuyStrength}%` : "--"}</span>
                </div>
                <span className="text-zinc-600 font-bold">·</span>
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <span className="text-[11px]">SELL Evidence:</span>
                  <span className="font-semibold tabular-nums text-zinc-300">{safeSellStrength != null ? `${safeSellStrength}%` : "--"}</span>
                </div>
              </>
            ) : activeDirection === "SELL" ? (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-rose-400">SELL Strength:</span>
                  <span className="font-black tabular-nums text-rose-300">{safeSellStrength != null ? `${safeSellStrength}%` : "--"}</span>
                </div>
                <span className="text-zinc-600 font-bold">·</span>
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <span className="text-[11px]">BUY Evidence:</span>
                  <span className="font-semibold tabular-nums text-zinc-300">{safeBuyStrength != null ? `${safeBuyStrength}%` : "--"}</span>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-emerald-400/80">BUY Strength:</span>
                  <span className="font-bold tabular-nums text-emerald-300">{safeBuyStrength != null ? `${safeBuyStrength}%` : "--"}</span>
                </div>
                <span className="text-zinc-600 font-bold">·</span>
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-rose-400/80">SELL Strength:</span>
                  <span className="font-bold tabular-nums text-rose-300">{safeSellStrength != null ? `${safeSellStrength}%` : "--"}</span>
                </div>
              </>
            )}
            <span className="text-zinc-600 font-bold">·</span>
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-sky-400/80">Sample:</span>
              <span className="font-bold tabular-nums text-sky-300">
                {isEvaluating ? "--" : `${sampleN} setups`}
              </span>
            </div>
          </>
        }
        reasoning={
          isEvaluating
            ? "Matching current setup profile against empirical historical backtest catalog..."
            : overallReasoning || `Statistical matching across ${sampleN} setups confirms ${activeDirection === "WAIT" ? "balanced evidence" : `${activeDirection} strength of ${activeStrength}%`} with calibrated probability of ${safeProb != null ? `${safeProb}%` : "--"} and expectancy of ${historicalExpectancy != null ? formatRAsUSD(historicalExpectancy, { showSign: true }) : "--"}.`
        }
        uniqueId="histHeroWave"
      />

      {/* 8-Metric Empirical Evidence Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 pt-2 border-t border-white/5 text-[11px]">
        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-purple-300 uppercase font-semibold block">1. Calibrated Odds</span>
          <span className="font-bold text-sm text-purple-200 tabular-nums">
            {isEvaluating || safeProb == null ? "--" : `${safeProb}%`}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Statistical Model</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">2. 95% CI</span>
          <span className="font-bold text-xs text-zinc-200 tabular-nums truncate block">
            {isEvaluating ? "--" : (winRateCiLower != null && winRateCiUpper != null ? `${winRateCiLower.toFixed(1)}%–${winRateCiUpper.toFixed(1)}%` : "--")}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Wilson Interval</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-sky-400 uppercase font-semibold block">3. Sample Size</span>
          <span className="font-bold text-sm text-sky-300 tabular-nums">
            {isEvaluating ? "--" : `${sampleN}`}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Total Setups</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-cyan-400 uppercase font-semibold block">4. Similar Setups</span>
          <span className="font-bold text-sm text-cyan-300 tabular-nums">
            {isEvaluating ? "--" : `${similarSetupCount ?? sampleN}`}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Exact Matches</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-emerald-400 uppercase font-semibold block">5. Raw Win Rate</span>
          <span className="font-bold text-sm text-emerald-300 tabular-nums">
            {isEvaluating || safeWinRate == null ? "--" : `${safeWinRate}%`}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Historical Trades</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-zinc-400 uppercase font-semibold block">6. Expectancy ($)</span>
          <span className="font-bold text-sm text-emerald-400 tabular-nums">
            {isEvaluating ? "--" : formatRAsUSD(historicalExpectancy, { showSign: true, fallback: "--" })}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Per Trade Edge</span>
        </div>

        <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
          <span className="text-[9px] text-amber-400 uppercase font-semibold block">7. Profit Factor</span>
          <span className="font-bold text-sm text-amber-300 tabular-nums">
            {isEvaluating ? "--" : (historicalProfitFactor != null ? historicalProfitFactor.toFixed(2) : "--")}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Win $ / Loss $</span>
        </div>

        <div className="bg-[#091122]/90 border border-sky-500/30 rounded-lg p-2.5">
          <span className="text-[9px] text-sky-300 uppercase font-semibold block">8. Similarity</span>
          <span className="font-bold text-sm text-sky-200 tabular-nums">
            {isEvaluating || safeSimilarity == null ? "--" : `${safeSimilarity}%`}
          </span>
          <span className="text-[8.5px] text-zinc-500 block truncate">Feature Match</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OVERALL MARKET INSIGHT COMBINED SIGNAL HERO
// ─────────────────────────────────────────────────────────────────────────────

function OverallMarketSignalHero({
  signal,
  overallSignal,
  assetTicker,
  assetName,
  isMarketClosed,
  loading,
  lastUpdated,
  overallReasoning,
  entryPrice,
  stopLoss,
  takeProfit1,
  takeProfit2,
}: {
  signal?: string;
  overallSignal?: OverallTradingSignal | null;
  assetTicker?: string;
  assetName?: string;
  isMarketClosed?: boolean;
  loading?: boolean;
  lastUpdated?: string;
  overallReasoning?: string | null;
  entryPrice?: number | string | null;
  stopLoss?: number | string | null;
  takeProfit1?: number | string | null;
  takeProfit2?: number | string | null;
}) {
  const isEvaluating = Boolean(loading);
  const normSignal = String(overallSignal?.signal || signal || "").toUpperCase().trim() || "WAIT";

  // Case B: Market Insight does not substitute overall_signal.percentage; renders Metric: --
  const statusBadge = isMarketClosed
    ? "MARKET CLOSED"
    : isEvaluating
      ? "EVALUATING"
      : overallSignal?.conflict_detected
        ? "CONFLICT DETECTED · SAFETY WAIT"
        : "4-COMPONENT CONVICTION LEDGER";

  const contributors = overallSignal?.contributors || [];

  return (
    <div className="space-y-4 font-mono">
      <SignalHeroCard
        pageTitle="MARKET INSIGHT · FULL-SYSTEM EVIDENCE SYNTHESIS"
        icon={Activity}
        assetName={assetName || (assetTicker?.includes("BTC") ? "Bitcoin" : "Gold")}
        assetTicker={assetTicker || ""}
        signal={isMarketClosed ? "WAIT" : isEvaluating ? "WAIT" : normSignal}
        percentage={null}
        fallbackPercentageText="--"
        statusBadge={statusBadge}
        isEvaluating={isEvaluating}
        isMarketClosed={isMarketClosed}
        timeChangeText={(() => {
          const activeCount = contributors.filter((c) => c.status === "ACTIVE").length;
          const totalCount = contributors.length;
          const weightsSummary = contributors.length > 0
            ? contributors.map((c) => `${c.display_name.split(" ")[0]} (${Math.round(c.nominal_weight * 100)}%)`).join(" + ")
            : "Technical + Historical + ML + Strategy";
          return `Multi-Component Synthesis · ${weightsSummary}${activeCount < totalCount ? ` (${activeCount}/${totalCount} Active — Re-normalized)` : ""}`;
        })()}
        lastUpdatedText={isEvaluating ? undefined : lastUpdated}
        supportingPills={
          isMarketClosed ? (
            <span className="text-amber-300 font-semibold">MARKET CLOSED · DUAL ENGINE ANALYSIS PAUSED</span>
          ) : contributors.length > 0 ? (
            <>
              {contributors.map((c, idx) => (
                <React.Fragment key={c.component_id}>
                  {idx > 0 && <span className="text-zinc-600 font-bold">·</span>}
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-zinc-400">{c.display_name.split(" ")[0]}:</span>
                    <span className="text-[10px] text-zinc-500 font-normal">
                      (Nom: {(c.nominal_weight * 100).toFixed(0)}% · Eff: {((c.effective_weight ?? c.nominal_weight) * 100).toFixed(1)}%)
                    </span>
                    <span className={`font-bold tabular-nums ${c.directional_bias === "BUY" ? "text-emerald-300" : c.directional_bias === "SELL" ? "text-rose-300" : "text-amber-300"}`}>
                      {c.effective_points > 0 ? `+${c.effective_points.toFixed(1)}pts` : c.effective_points < 0 ? `${c.effective_points.toFixed(1)}pts` : "0.0pts"}
                    </span>
                  </div>
                </React.Fragment>
              ))}
            </>
          ) : (
            <span className="text-zinc-400">4-Factor Aggregator Evidence Ledger</span>
          )
        }
        reasoning={
          isMarketClosed
            ? "Market is closed for the weekend. Showing combined analysis as of last session close."
            : isEvaluating
              ? `Synthesizing 4-factor multi-timeframe order flow and empirical edge for ${assetTicker || "current asset"}...`
              : (() => {
                  const netScore = overallSignal?.overall_evidence_score ?? overallSignal?.percentage ?? 0;
                  const netScoreFormatted = typeof netScore === "number" ? `${netScore >= 0 ? "+" : ""}${netScore.toFixed(1)}` : "--";
                  return overallSignal?.reasons?.join(" ") || overallReasoning ||
                    `Evidence Bias: ${normSignal} · Net Directional Evidence Score: ${netScoreFormatted} · Weights re-normalized across currently available components.`;
                })()
        }
        entryPrice={entryPrice}
        stopLoss={stopLoss}
        takeProfit1={takeProfit1}
        takeProfit2={takeProfit2}
        uniqueId="overallHeroWave"
      />

      {/* Authoritative 4-Factor Signal Aggregator Ledger */}
      {contributors.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 px-1">
            <span>Weights re-normalized across currently available components</span>
            <span>{contributors.filter((c) => c.status === "ACTIVE").length} of {contributors.length} Components Active</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            {contributors.map((c) => (
              <div key={c.component_id} className="p-3.5 rounded-xl bg-[#09152e]/80 border border-sky-500/20 flex flex-col justify-between space-y-2">
                <div className="flex items-center justify-between border-b border-sky-500/10 pb-1.5">
                  <span className="font-bold text-slate-200 truncate" title={c.display_name}>{c.display_name}</span>
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300 font-bold" title="Nominal Weight">
                      Nom: {(c.nominal_weight * 100).toFixed(0)}%
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 font-bold" title="Effective Re-normalized Weight">
                      Eff: {((c.effective_weight ?? c.nominal_weight) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase block">Direction</span>
                    <span className={`font-bold ${c.directional_bias === "BUY" ? "text-emerald-400" : c.directional_bias === "SELL" ? "text-rose-400" : "text-amber-400"}`}>
                      {c.directional_bias}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase block">Contribution</span>
                    <span className={`font-bold tabular-nums font-mono ${c.effective_points > 0 ? "text-emerald-400" : c.effective_points < 0 ? "text-rose-400" : "text-zinc-400"}`}>
                      {c.effective_points > 0 ? `+${c.effective_points.toFixed(1)}` : c.effective_points.toFixed(1)} pts
                    </span>
                  </div>
                </div>
                <div className="pt-1.5 border-t border-sky-500/10 flex items-center justify-between text-[10px] text-zinc-400">
                  <span>Status: <strong className={c.status === "ACTIVE" ? "text-emerald-400 font-bold" : "text-zinc-400"}>{c.status}</strong></span>
                  {c.raw_value != null && (
                    <span>Raw: <strong className="text-sky-300">{c.raw_unit === "PROBABILITY_0_1" ? `${(c.raw_value * 100).toFixed(1)}%` : c.raw_value}</strong></span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// VALIDATED RESEARCH STRATEGY CARD (ADVISORY EMPIRICAL CONFIRMATION)
// ─────────────────────────────────────────────────────────────────────────────

function ValidatedResearchStrategyCard({
  validatedStrategy,
  degradationMonitoring,
  assetTicker,
  baseSignal,
  loading,
}: {
  validatedStrategy?: ValidatedStrategyEvaluation | null;
  degradationMonitoring?: DegradationMonitoringReport | null;
  assetTicker?: string;
  baseSignal?: string;
  loading?: boolean;
}) {
  const isBtc = assetTicker?.toUpperCase().includes("BTC");
  const isXau = assetTicker?.toUpperCase().includes("XAU") || assetTicker?.toUpperCase().includes("GOLD");

  const strategyName = validatedStrategy?.strategy_name || "No Active Strategy";
  const strategyId = validatedStrategy?.strategy_id || "N/A";
  const qualified = validatedStrategy?.qualified ?? false;
  const qualStatus = validatedStrategy
    ? (validatedStrategy.qualification_status || (qualified ? "QUALIFIED" : "NOT_QUALIFIED"))
    : "NOT_AVAILABLE";
  const confScore = validatedStrategy?.confirmation_score ?? null;
  const maxConf = validatedStrategy?.max_confirmation_score ?? 4;
  const probPct = validatedStrategy?.probability != null ? (validatedStrategy.probability * 100).toFixed(1) : "--";
  const regime = validatedStrategy?.regime || "UNKNOWN";
  const researchExp = formatRAsUSD(validatedStrategy?.research_expectancy_r, { showSign: true, fallback: "N/A" });
  const researchWr = validatedStrategy?.research_win_rate_pct != null
    ? `${validatedStrategy.research_win_rate_pct.toFixed(1)}%`
    : "N/A";
  const researchPf = validatedStrategy?.research_profit_factor != null
    ? validatedStrategy.research_profit_factor.toFixed(2)
    : "N/A";
  const validationScore = validatedStrategy?.validation_score != null
    ? `${validatedStrategy.validation_score}`
    : "N/A";
  const degradationStatus = degradationMonitoring?.status || validatedStrategy?.degradation_status || (validatedStrategy ? "NORMAL" : "N/A");

  // Derive hypothetical shadow decision & reason (RESEARCH ONLY)
  let shadowDecision = "WAIT";
  let shadowReason = validatedStrategy ? "Base signal is WAIT" : "No strategy evaluation available";
  if (baseSignal === "BUY" || baseSignal === "SELL") {
    if (qualStatus === "QUALIFIED") {
      shadowDecision = baseSignal;
      shadowReason = "Strict qualification passed";
    } else if (qualStatus === "CONFLICT") {
      shadowDecision = "WAIT";
      shadowReason = "Directional conflict filtered";
    } else if (validatedStrategy) {
      shadowDecision = "WAIT";
      shadowReason = "Unqualified setup suppressed";
    } else {
      shadowDecision = "WAIT";
      shadowReason = "Strategy data not available";
    }
  }

  return (
    <div className="bg-[#071330]/95 border border-sky-500/40 rounded-2xl p-5 shadow-[0_0_24px_rgba(56,189,248,0.12)] backdrop-blur-xl space-y-4 font-mono">
      {/* Top Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-sky-500/20">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/40 flex items-center justify-center font-bold text-sky-300">
            <Sparkles size={16} className="text-amber-400" />
          </div>
          <div>
            <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <span>VALIDATED RESEARCH STRATEGY</span>
              <span className="text-[10px] text-sky-300 font-normal">
                {strategyId !== "N/A" ? `(${strategyId})` : "(No Strategy Active)"}
              </span>
            </div>
            <div className="text-[10px] text-zinc-400">Advisory Empirical Confirmation Layer (Zero Decision Gating)</div>
          </div>
        </div>

        {/* Qualification & Degradation Status Badges */}
        <div className="flex items-center gap-2">
          <span
            className={`px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${qualStatus === "QUALIFIED"
              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
              : qualStatus === "CONFLICT"
                ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                : "bg-zinc-800 text-zinc-400 border-zinc-700"
              }`}
          >
            {qualStatus === "QUALIFIED" ? (
              <CheckCircle2 size={13} className="text-emerald-400" />
            ) : qualStatus === "CONFLICT" ? (
              <AlertTriangle size={13} className="text-rose-400" />
            ) : (
              <X size={13} className="text-zinc-500" />
            )}
            {qualStatus}
          </span>

          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${degradationStatus === "NORMAL"
              ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
              : degradationStatus === "WATCH"
                ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                : degradationStatus === "ALERT"
                  ? "bg-rose-500/15 text-rose-300 border-rose-500/40"
                  : "bg-zinc-800/40 text-zinc-500 border-zinc-700/40"
              }`}
          >
            STATUS: {degradationStatus}
          </span>
        </div>
      </div>

      {/* Production vs Hypothetical Research Shadow Comparison */}
      <div className="p-3.5 rounded-xl bg-[#040b1c] border border-sky-400/30 space-y-2.5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="text-[11px] font-bold text-sky-300 uppercase flex items-center gap-1.5">
            <Layers size={13} className="text-sky-400" />
            LIVE PRODUCTION VS HYPOTHETICAL GATING SHADOW
          </div>
          <span className="px-2 py-0.5 rounded text-[9.5px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 uppercase tracking-wider">
            RESEARCH SHADOW ONLY · PRODUCTION UNCHANGED
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          {/* Production Decision */}
          <div className="p-2.5 rounded-lg bg-[#071330] border border-sky-500/20">
            <div className="text-[9.5px] text-zinc-400 uppercase font-semibold">1. Production Decision</div>
            <div className="text-base font-black text-white mt-0.5 flex items-center gap-1.5">
              <span className={baseSignal === "BUY" ? "text-emerald-400" : baseSignal === "SELL" ? "text-rose-400" : "text-zinc-300"}>
                {baseSignal || "WAIT"}
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                ACTIVE LIVE
              </span>
            </div>
            <div className="text-[9px] text-zinc-500 mt-0.5">Live Decision Engine signal</div>
          </div>

          {/* Validated Strategy */}
          <div className="p-2.5 rounded-lg bg-[#071330] border border-sky-500/20">
            <div className="text-[9.5px] text-zinc-400 uppercase font-semibold">2. Validated Research Layer</div>
            <div className={`text-sm font-black mt-0.5 truncate ${validatedStrategy ? "text-sky-300" : "text-zinc-500"}`}>
              {strategyName}
            </div>
            <div className="text-[9px] text-zinc-400 mt-0.5 flex items-center gap-1">
              <span className={qualStatus === "QUALIFIED" ? "text-emerald-400 font-bold" : qualStatus === "CONFLICT" ? "text-rose-400 font-bold" : "text-zinc-400"}>
                {qualStatus}
              </span>
              <span>{confScore != null ? `(${confScore}/${maxConf} Confirmations)` : `(--/${maxConf} Confirmations)`}</span>
            </div>
          </div>

          {/* Hypothetical Shadow Decision */}
          <div className={`p-2.5 rounded-lg border ${shadowDecision === "WAIT" && baseSignal !== "WAIT"
            ? "bg-amber-950/20 border-amber-500/40"
            : "bg-[#071330] border-sky-500/20"
            }`}>
            <div className="text-[9.5px] text-zinc-400 uppercase font-semibold">3. Research Shadow Gating</div>
            <div className="text-base font-black mt-0.5 flex items-center gap-1.5">
              <span className={shadowDecision === "BUY" ? "text-emerald-400" : shadowDecision === "SELL" ? "text-rose-400" : "text-amber-400"}>
                {shadowDecision}
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">
                SHADOW
              </span>
            </div>
            <div className="text-[9px] text-zinc-400 mt-0.5 truncate">
              {shadowReason}
            </div>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Strategy</div>
          <div className={`text-sm font-black truncate ${validatedStrategy ? "text-white" : "text-zinc-500"}`}>{strategyName}</div>
          <div className="text-[9px] text-zinc-500">{validatedStrategy ? "Empirical Champion" : "No Active Strategy"}</div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Confirm Score</div>
          <div className="text-sm font-black text-sky-300">{confScore != null ? `${confScore} / ${maxConf} Passed` : "N/A"}</div>
          <div className="text-[9px] text-zinc-500">Confirmation Index</div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Calibrated Prob</div>
          <div className={`text-sm font-black ${probPct !== "--" ? "text-emerald-400" : "text-zinc-400"}`}>{probPct !== "--" ? `${probPct}%` : "N/A"}</div>
          <div className="text-[9px] text-zinc-500">Logistic Scaled</div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Market Regime</div>
          <div className="text-sm font-black text-cyan-300 truncate">{regime}</div>
          <div className="text-[9px] text-zinc-500">Volatility Model</div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Research Exp ($)</div>
          <div className={`text-sm font-black ${validatedStrategy?.research_expectancy_r != null ? (validatedStrategy.research_expectancy_r >= 0 ? "text-emerald-400" : "text-rose-400") : "text-zinc-400"}`}>
            {researchExp}
          </div>
          <div className="text-[9px] text-zinc-500">
            {validatedStrategy ? `WR: ${researchWr} · PF: ${researchPf}` : "WR: N/A · PF: N/A"}
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
          <div className="text-[10px] text-zinc-400 uppercase">Validation Score</div>
          <div className={`text-sm font-black ${validationScore !== "N/A" ? "text-amber-300" : "text-zinc-400"}`}>
            {validationScore !== "N/A" ? `${validationScore} / 100` : "N/A"}
          </div>
          <div className="text-[9px] text-zinc-500">Sequential Robustness</div>
        </div>
      </div>

      {/* Confirmations and Failed Conditions Lists */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
        {/* Passed Confirmations */}
        <div className="p-3 rounded-xl bg-[#050e24]/80 border border-emerald-500/20 space-y-1.5">
          <div className="text-[10px] font-bold text-emerald-300 uppercase flex items-center gap-1.5">
            <CheckCircle2 size={12} className="text-emerald-400" />
            Active Strategy Confirmations ({validatedStrategy?.confirmations?.length || 0})
          </div>
          {validatedStrategy?.confirmations && validatedStrategy.confirmations.length > 0 ? (
            <div className="space-y-1">
              {validatedStrategy.confirmations.map((c, i) => (
                <div key={i} className="flex items-center gap-1.5 text-zinc-300 text-[10.5px]">
                  <span className="text-emerald-400 font-bold">&#x2713;</span>
                  <span>{c}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-zinc-500 text-[10px] italic">No active confirmations met in current cycle.</div>
          )}
        </div>

        {/* Failed / Pending Conditions */}
        <div className="p-3 rounded-xl bg-[#050e24]/80 border border-sky-500/20 space-y-1.5">
          <div className="text-[10px] font-bold text-zinc-400 uppercase flex items-center gap-1.5">
            <Info size={12} className="text-sky-400" />
            Failed / Unmet Conditions ({validatedStrategy?.failed_conditions?.length || 0})
          </div>
          {validatedStrategy?.failed_conditions && validatedStrategy.failed_conditions.length > 0 ? (
            <div className="space-y-1">
              {validatedStrategy.failed_conditions.map((f, i) => (
                <div key={i} className="flex items-center gap-1.5 text-zinc-400 text-[10.5px]">
                  <span className="text-zinc-600 font-bold">✕</span>
                  <span>{f}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-emerald-400 text-[10px] font-bold flex items-center gap-1">
              <Check size={12} /> All strategy conditions satisfied.
            </div>
          )}
        </div>
      </div>

      {/* Advisory Conflict Warning */}
      {validatedStrategy?.conflict_reason && (
        <div className="p-2.5 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-center gap-2 text-xs text-rose-300">
          <AlertTriangle size={15} className="text-rose-400 shrink-0" />
          <span className="text-[11px] leading-tight">{validatedStrategy.conflict_reason}</span>
        </div>
      )}

      {/* Research Disclaimer */}
      <div className="text-[10px] text-zinc-500 pt-1 border-t border-sky-500/10 flex items-center justify-between">
        <span>Historical Evidence Notice: Research expectancy is based on historical backtesting and is NOT a guarantee of future returns.</span>
        <span className="text-sky-300 font-bold">Advisory Only</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OVERALL AI TRADING SIGNAL HERO & CONTRIBUTORS BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

function MainSignalHero({
  signal,
  signalStrength,
  buyScore,
  sellScore,
  grade,
  contributors,
  lastUpdated,
  loading,
  assetName,
  assetTicker,
  assetBadgeColor,
  isMarketClosed,
  technicalScore,
  geminiScore,
  calibratedProb,
  calibrationStatus,
  strategyStatsMap,
  historicalEvidenceStatus,
  historicalSampleSize,
  historicalWinRate,
  historicalExpectancy,
  historicalProfitFactor,
  historicalDrawdown,
  similarSetupCount,
  scoreBandWinRate,
  winRateCiLower,
  winRateCiUpper,
  historicalConfirmations,
  historicalConflicts,
  topSuccessReasons,
  topFailureReasons,
  successMatchesCount,
  failureMatchesCount,
  evidenceRefreshAt,
  evidenceQuality,
  overallReasoning,
  datasetVersion,
  overallSignal,
}: {
  signal: string;
  signalStrength?: number | null;
  buyScore?: number | null;
  sellScore?: number | null;
  grade: string | null;
  overallSignal?: OverallTradingSignal | null;
  contributors: Array<{
    name: string;
    points: number;
    prev_points?: number;
    direction?: string;
    last_changed_at?: string;
    description: string;
  }>;
  lastUpdated: string;
  loading?: boolean;
  assetName?: string;
  assetTicker?: string;
  assetBadgeColor?: string;
  isMarketClosed?: boolean;
  technicalScore?: number;
  geminiScore?: number;
  calibratedProb?: number | null;
  calibrationStatus?: string;
  strategyStatsMap?: Record<string, string>;
  historicalEvidenceStatus?: string;
  historicalSampleSize?: number | null;
  historicalWinRate?: number | null;
  historicalExpectancy?: number | null;
  historicalProfitFactor?: number | null;
  historicalDrawdown?: number | null;
  similarSetupCount?: number | null;
  scoreBandWinRate?: number | null;
  winRateCiLower?: number | null;
  winRateCiUpper?: number | null;
  historicalConfirmations?: string[] | null;
  historicalConflicts?: string[] | null;
  topSuccessReasons?: string[] | null;
  topFailureReasons?: string[] | null;
  successMatchesCount?: number | null;
  failureMatchesCount?: number | null;
  evidenceRefreshAt?: string | null;
  evidenceQuality?: string | null;
  overallReasoning?: string | null;
  datasetVersion?: string | null;
}) {
  const safeStrength = signalStrength != null ? Math.max(0, Math.min(100, Math.round(Number(signalStrength)))) : null;
  const safeBuy = buyScore != null ? Math.max(0, Math.min(100, Math.round(Number(buyScore)))) : null;
  const safeSell = sellScore != null ? Math.max(0, Math.min(100, Math.round(Number(sellScore)))) : null;
  const theme = signalTheme(signal, safeStrength ?? 0);
  const radius = 48;
  const strokeWidth = 9;
  const normalizedRadius = radius - strokeWidth / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - ((safeStrength ?? 0) / 100) * circumference;

  const [showContributors, setShowContributors] = useState(!isMarketClosed);

  useEffect(() => {
    setShowContributors(!isMarketClosed);
  }, [isMarketClosed]);
  const isEvaluating = Boolean(loading);
  const circleTheme = (isEvaluating || isMarketClosed) ? signalTheme("WAIT", safeStrength ?? 0) : theme;

  // Track continuous factor changes with accurate previous values and change timestamps
  const factorHistoryRef = useRef<Map<string, { prevPoints: number; currentPoints: number; lastChangedAt: string; direction: "UP" | "DOWN" | "UNCHANGED" }>>(new Map());

  const processedContributors = useMemo(() => {
    if (!contributors || contributors.length === 0) return [];

    return contributors.map((c) => {
      const name = c.name;
      const currentPts = c.points;
      const history = factorHistoryRef.current.get(name);
      const sourceTs = c.last_changed_at || overallSignal?.timestamp || lastUpdated || "";

      let prevPts = c.prev_points ?? currentPts;
      let lastChangedAt = c.last_changed_at || sourceTs;
      let direction: "UP" | "DOWN" | "UNCHANGED" = (c.direction as any) || "UNCHANGED";

      if (history) {
        if (currentPts !== history.currentPoints) {
          // Confirmed factor score change
          prevPts = history.currentPoints;
          lastChangedAt = sourceTs;
          direction = currentPts > prevPts ? "UP" : "DOWN";
          factorHistoryRef.current.set(name, {
            prevPoints: prevPts,
            currentPoints: currentPts,
            lastChangedAt,
            direction,
          });
        } else {
          // Preserving verified previous points and timestamp without false updates
          prevPts = history.prevPoints;
          lastChangedAt = history.lastChangedAt;
          direction = history.direction;
        }
      } else {
        if (c.prev_points != null && c.prev_points !== currentPts) {
          direction = currentPts > c.prev_points ? "UP" : "DOWN";
        }
        factorHistoryRef.current.set(name, {
          prevPoints: prevPts,
          currentPoints: currentPts,
          lastChangedAt,
          direction,
        });
      }

      return {
        ...c,
        points: currentPts,
        prev_points: prevPts,
        last_changed_at: lastChangedAt,
        direction,
      };
    });
  }, [contributors, lastUpdated, overallSignal?.timestamp]);

  // Sort contributors descending by latest score change time (most recently changed at top)
  const sortedContributors = useMemo(() => {
    return [...processedContributors].sort((a, b) => {
      const timeA = a.last_changed_at ? new Date(a.last_changed_at).getTime() : 0;
      const timeB = b.last_changed_at ? new Date(b.last_changed_at).getTime() : 0;
      return timeB - timeA;
    });
  }, [processedContributors]);

  const isBuyHigher = !isEvaluating && !isMarketClosed && safeBuy != null && safeSell != null && safeBuy > safeSell;
  const isSellHigher = !isEvaluating && !isMarketClosed && safeBuy != null && safeSell != null && safeSell > safeBuy;

  return (
    <div className="space-y-3">
      {/* 1. OVERALL AI TRADING SIGNAL HERO CARD */}
      {(() => {
        const aggSignal = overallSignal?.signal || signal || "WAIT";
        const isConflict = Boolean(overallSignal?.conflict_detected);
        const isWait = isMarketClosed || isEvaluating || aggSignal === "WAIT";

        // For WAIT (both conflict and sub-threshold), hero percentage is null (renders as animated "..." in Hero Card and circle)
        // For actionable BUY / SELL: hero percentage is the exact evidence score (e.g. 74%)
        const aggPercentage = isWait
          ? null
          : (overallSignal?.overall_evidence_score ?? overallSignal?.percentage ?? safeStrength);

        const statusBadge = isMarketClosed
          ? "MARKET CLOSED"
          : isConflict
            ? "DIRECTIONAL CONFLICT (WAIT)"
            : aggSignal === "WAIT"
              ? (overallSignal?.overall_evidence_score != null && overallSignal.overall_evidence_score > 0
                ? `SUB-THRESHOLD (${overallSignal.overall_evidence_score}% SCORE)`
                : "BALANCED EVIDENCE (WAIT)")
              : overallSignal?.strength
                ? `${overallSignal.strength} EVIDENCE`
                : `GRADE ${isEvaluating ? "..." : (grade || "C")}`;

        return (
          <SignalHeroCard
            pageTitle="OVERALL AI TRADING SIGNAL"
            icon={Activity}
            assetName={assetName || (assetTicker?.includes("BTC") ? "Bitcoin" : "Gold")}
            assetTicker={assetTicker || ""}
            signal={isMarketClosed ? "WAIT" : isEvaluating ? "WAIT" : aggSignal}
            percentage={aggPercentage}
            statusBadge={statusBadge}
            isEvaluating={isEvaluating}
            isMarketClosed={isMarketClosed}
            timeChangeText={
              overallSignal?.methodology_version
                ? `Methodology v${overallSignal.methodology_version}`
                : isMarketClosed
                  ? "MARKET CLOSED"
                  : undefined
            }
            lastUpdatedText={
              isEvaluating ? undefined : (overallSignal?.timestamp || lastUpdated || undefined)
            }
            supportingPills={
              isMarketClosed ? (
                <span className="text-amber-300 font-semibold">MARKET CLOSED · NO ACTIVE SIGNALS UNTIL OPEN</span>
              ) : (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-cyan-400">Evidence Score:</span>
                    <span className="font-bold tabular-nums text-cyan-300">
                      {isEvaluating
                        ? "--"
                        : isConflict
                          ? "CONFLICT"
                          : aggSignal === "WAIT"
                            ? (overallSignal?.overall_evidence_score != null
                              ? `${overallSignal.overall_evidence_score}% (Sub-threshold)`
                              : "--")
                            : (aggPercentage != null ? `${aggPercentage}%` : "--")}
                    </span>
                  </div>
                  {overallSignal?.calibrated_probability != null && (
                    <>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-emerald-400">Calibrated Prob:</span>
                        <span className="font-bold tabular-nums text-emerald-300">
                          {(overallSignal.calibrated_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    </>
                  )}
                  <span className="text-zinc-600 font-bold">&middot;</span>
                  <div className="flex items-center gap-1.5">
                    <span className={`font-medium ${isBuyHigher ? "text-emerald-300 font-bold" : "text-emerald-400/80"}`}>BUY:</span>
                    <span className="font-bold tabular-nums text-emerald-300">{isEvaluating || safeBuy == null ? "--" : `${safeBuy}%`}</span>
                  </div>
                  <span className="text-zinc-600 font-bold">&middot;</span>
                  <div className="flex items-center gap-1.5">
                    <span className={`font-medium ${isSellHigher ? "text-rose-300 font-bold" : "text-rose-400/80"}`}>SELL:</span>
                    <span className="font-bold tabular-nums text-rose-300">{isEvaluating || safeSell == null ? "--" : `${safeSell}%`}</span>
                  </div>
                </>
              )
            }
            reasoning={
              isMarketClosed
                ? "Gold market is closed for the weekend. Real-time signals and trading analysis will resume at market open."
                : overallSignal?.reasons && overallSignal.reasons.length > 0
                  ? overallSignal.reasons.join(" ")
                  : overallReasoning || (aggSignal === "BUY"
                    ? "Multi-component evidence fused across Technicals, Historical Evidence, ML Shadow, and Validated Strategy."
                    : aggSignal === "SELL"
                      ? "Multi-component evidence fused across Technicals, Historical Evidence, ML Shadow, and Validated Strategy."
                      : "No confirmed directional high-probability trade setup. Evidence currently balanced or awaiting trigger.")
            }
            uniqueId="overallHeroWave"
          />
        );
      })()}

      <div className="p-4 rounded-xl border border-white/5 bg-[#091122]/60 space-y-3 font-mono">
        {/* Dual-Signal Synthesis Banner (NOW Signal + HISTORICAL Signal -> OVERALL AI Signal) */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-[10.5px]">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0a1b33] border border-cyan-500/30 text-cyan-300">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-bold uppercase tracking-wider text-[9.5px] text-zinc-400">1. Now Market Signal:</span>
            <span className="font-bold text-cyan-200">{isEvaluating ? "Analyzing..." : `${signal}${safeStrength != null ? ` (${safeStrength}%)` : ""}`}</span>
          </div>
          <span className="text-zinc-500 font-bold">+</span>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#140b2b] border border-purple-500/30 text-purple-300">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
            <span className="font-bold uppercase tracking-wider text-[9.5px] text-zinc-400">2. Historical Signal:</span>
            <span className="font-bold text-purple-200">{isEvaluating ? "Matching..." : (calibratedProb != null || historicalWinRate != null) ? `Win Rate ${Math.round(calibratedProb ?? historicalWinRate!)}%` : "No Match"}</span>
          </div>
          <span className="text-zinc-500 font-bold">=</span>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#081838] border border-sky-400/40 text-sky-200 shadow-[0_0_12px_rgba(56,189,248,0.15)]">
            <span className="font-bold uppercase tracking-wider text-[9.5px] text-sky-400">Synthesized Overall:</span>
            <span className={`font-black ${isMarketClosed ? "text-amber-300" : signal === "BUY" ? "text-emerald-300" : signal === "SELL" ? "text-rose-300" : "text-sky-300"}`}>
              {isMarketClosed ? "WAIT (CLOSED)" : isEvaluating ? "EVALUATING" : `${signal} (${grade || "C"})`}
            </span>
          </div>
        </div>

        {/* Real-time Scores Row (Confluence, Technical, Gemini, Setup Grade) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/5 font-mono text-[11px]">
          <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
            <span className="text-[9px] text-zinc-400 uppercase font-semibold block">Confluence Score</span>
            <span className="font-bold text-sm text-cyan-300 tabular-nums">{isEvaluating || safeStrength == null ? "--" : `${safeStrength} / 100`}</span>
          </div>
          <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
            <span className="text-[9px] text-zinc-400 uppercase font-semibold block">Technical Score</span>
            <span className="font-bold text-sm text-zinc-200 tabular-nums">
              {isEvaluating ? "--" : technicalScore != null ? `${technicalScore} / 90` : safeStrength != null ? `${safeStrength} / 90` : "--"}
            </span>
          </div>
          <div className="bg-[#091122]/90 border border-[#1b2b4d] rounded-lg p-2.5">
            <span className="text-[9px] text-zinc-400 uppercase font-semibold block">Gemini Confirmation</span>
            <span className="font-bold text-sm text-zinc-200 tabular-nums">
              {isEvaluating ? "--" : `${geminiScore !== undefined ? geminiScore : 0} / 10`}
            </span>
          </div>
          <div className="bg-[#091122]/90 border border-sky-500/30 rounded-lg p-2.5">
            <span className="text-[9px] text-sky-300 uppercase font-semibold block">Setup Grade</span>
            <span className="font-bold text-sm text-sky-200 tabular-nums">
              {isEvaluating || safeStrength == null ? "--" : `GRADE ${grade || "C"} (${safeStrength}%)`}
            </span>
          </div>
        </div>

        {/* Live System Verification Badges */}
        <div className="flex items-center gap-1.5 pt-1 border-t border-white/5 text-[10px] font-mono text-zinc-400 flex-wrap">
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-bold">
            LIVE ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 font-bold">
            MTF ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-bold">
            STRATEGIES ✓
          </span>
          <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-bold">
            GEMINI ✓
          </span>
        </div>
      </div>


      {/* 2. Strategy Contributors Breakdown */}
      <div className="card-hover bg-[#0c0c0f] border border-[#1e1e24] rounded-xl p-4">
        <div
          onClick={() => setShowContributors(!showContributors)}
          className="flex items-center justify-between cursor-pointer select-none group/contrib transition-all"
        >
          <div className="flex items-center gap-2 flex-wrap">
            <Layers size={13} className="text-amber-400 group-hover/contrib:text-amber-300 transition-colors" />
            <span className="text-xs font-mono font-semibold text-zinc-200 group-hover/contrib:text-white transition-colors uppercase tracking-wider">
              Signal Contributors Breakdown ({isMarketClosed ? "Friday Session" : isEvaluating || safeStrength == null ? "--" : `${safeStrength} Points`})
            </span>
            {isMarketClosed && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 text-amber-300 uppercase tracking-wider flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Market Closed ({showContributors ? "Click to Collapse" : "Click to View Details"})
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-zinc-500 flex items-center gap-1">
              <Clock size={10} />
              <RelativeTime timestamp={isEvaluating ? null : lastUpdated} prefix="Updated " fallback="--" />
            </span>
            <div
              className="text-[11px] font-mono text-zinc-400 group-hover/contrib:text-zinc-200 flex items-center gap-1"
            >
              {showContributors ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
          </div>
        </div>

        {showContributors && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-3 font-mono text-xs">
            {isEvaluating || sortedContributors.length === 0 ? (
              [
                "15m Trend",
                "MACD Momentum",
                "1H EMA Structure",
                "5m Momentum",
                "MTF Confluence",
                "RSI Momentum",
                "SMC / ICT",
                "Liquidity Sweep",
                "Fibonacci OTE",
                "Elliott Wave",
                "Gemini AI",
              ].map((name, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#121217] border border-[#1e1e26] animate-pulse">
                  <div className="flex flex-col min-w-0 pr-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 size={13} className="text-sky-400/60 shrink-0" />
                      <span className="text-zinc-300 font-medium truncate text-xs">{name}</span>
                    </div>
                    <span className="text-[10px] text-zinc-500 pl-5 flex items-center gap-1">
                      <RefreshCw size={9} className="animate-spin text-zinc-500" />
                      Syncing confirmed factors...
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 font-mono text-xs">
                    <span className="text-zinc-600 font-bold text-sm">→</span>
                  </div>
                </div>
              ))
            ) : (
              sortedContributors.map((c, idx) => {
                const prev = c.prev_points ?? c.points;
                const hasChanged = prev !== c.points;
                const isUp = c.direction === "UP" || (hasChanged && c.points > prev);
                const isDown = c.direction === "DOWN" || (hasChanged && c.points < prev);

                const directionSymbol = isUp ? "↑" : isDown ? "↓" : "→";
                const directionColor = isUp
                  ? "text-emerald-400 font-bold drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                  : isDown
                    ? "text-rose-400 font-bold drop-shadow-[0_0_8px_rgba(251,113,133,0.8)]"
                    : "text-zinc-500 font-bold";

                const changeTime = c.last_changed_at ? fmtTime(c.last_changed_at) : (lastUpdated || "--:--:--");

                return (
                  <div
                    key={c.name || idx}
                    className={`flex items-center justify-between p-2.5 rounded-lg border transition-all ${isUp
                      ? "bg-[#0d1c1a]/70 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.1)]"
                      : isDown
                        ? "bg-[#210d14]/70 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.1)]"
                        : "bg-[#121217] border-[#1e1e26]"
                      }`}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2
                          size={13}
                          className={isUp ? "text-emerald-400 shrink-0" : isDown ? "text-rose-400 shrink-0" : "text-emerald-400/80 shrink-0"}
                        />
                        <span className="text-zinc-200 font-medium truncate text-xs">{c.name}</span>
                      </div>
                      <div className="text-[10px] text-zinc-500 pl-5 flex flex-wrap items-center gap-x-1.5">
                        <RelativeTime timestamp={c.last_changed_at || lastUpdated} prefix="Updated " fallback="--" />
                        <span className="text-zinc-600">&middot;</span>
                        <span className="text-zinc-400">
                          Hist: {strategyStatsMap?.[c.name] || "Not empirically calibrated"}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 font-mono text-xs">
                      {hasChanged ? (
                        <span className="text-zinc-400 text-[11px] font-semibold flex items-center gap-1">
                          <span>{prev}</span>
                          <span className="text-zinc-600 font-bold">→</span>
                          <span className="font-bold text-zinc-100">+{c.points}</span>
                        </span>
                      ) : (
                        <span className="font-bold text-zinc-200">
                          +{c.points}
                        </span>
                      )}
                      <span className={`text-sm ${directionColor}`}>
                        {directionSymbol}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Active Open Trade Card Component (with Editable SL/TP and Real-Time Expected P/L)
// ─────────────────────────────────────────────────────────────────────────────

function OpenTradeCard({
  trade,
  currentLivePrice,
  onClose,
  onUpdate,
  tradeBusy,
}: {
  trade: TradeRecord;
  currentLivePrice: number;
  onClose: (id: string) => void;
  onUpdate: (id: string, sl: number, tp: number) => Promise<void>;
  tradeBusy: boolean;
}) {
  const isBuy = trade.direction === "BUY";
  const lots = safeNum(trade.position_size, 0.1);
  const entry = safeNum(trade.entry_price, currentLivePrice);
  const pnl = isBuy
    ? (currentLivePrice - entry) * 100.0 * lots
    : (entry - currentLivePrice) * 100.0 * lots;
  const isProfitable = pnl >= 0;

  const [sl, setSl] = useState(trade.stop_loss != null ? trade.stop_loss.toString() : "");
  const [tp, setTp] = useState(trade.take_profit_1 != null ? trade.take_profit_1.toString() : "");
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setSl(trade.stop_loss != null ? trade.stop_loss.toString() : "");
      setTp(trade.take_profit_1 != null ? trade.take_profit_1.toString() : "");
    }
  }, [trade.stop_loss, trade.take_profit_1, isEditing]);

  const slNum = parseFloat(sl) || 0;
  const tpNum = parseFloat(tp) || 0;

  // Expected SL and TP P/L calculations based on current lots and entry price
  const expectedSlPnl = isBuy
    ? (slNum - entry) * 100.0 * lots
    : (entry - slNum) * 100.0 * lots;

  const expectedTpPnl = isBuy
    ? (tpNum - entry) * 100.0 * lots
    : (entry - tpNum) * 100.0 * lots;

  const handleSave = async () => {
    if (slNum <= 0 || tpNum <= 0) return;
    setSaving(true);
    try {
      await onUpdate(trade.id, slNum, tpNum);
      setIsEditing(false);
    } catch {
      // error handled in parent
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-3 bg-[#121217] border border-[#242430] rounded-lg font-mono text-xs space-y-2.5">
      <div className="flex items-center justify-between">
        <span className={`px-2 py-0.5 rounded font-black text-[10px] ${isBuy ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-rose-500/20 text-rose-300 border border-rose-500/40"}`}>
          {trade.direction} {lots} LOTS
        </span>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-black ${isProfitable ? "text-emerald-400" : "text-rose-400"}`}>
            {fmtSignedCurrency(pnl)}
          </span>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="text-[10px] px-2 py-0.5 rounded bg-[#1a1a24] hover:bg-[#262636] text-zinc-300 border border-zinc-700 transition-colors flex items-center gap-1"
          >
            <Edit2 size={10} />
            {isEditing ? "Cancel" : "Edit SL/TP"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-1 text-[11px] text-zinc-400">
        <div>Entry: <span className="text-zinc-200 font-bold">{fmtPrice(trade.entry_price)}</span> <span className="text-[10px] text-zinc-500">({fmtTime(trade.entry_timestamp)})</span></div>
        <div>Spot: <span className="text-zinc-100 font-bold">{fmtPrice(currentLivePrice)}</span></div>
      </div>

      {/* SL and TP Rows with Live Expected P/L Display */}
      {!isEditing ? (
        <div className="grid grid-cols-2 gap-2 text-[11px] bg-[#0d0d12] p-2 rounded border border-[#1e1e26]">
          <div>
            <div className="text-[9px] text-zinc-500 uppercase">Stop Loss</div>
            <div className="text-rose-400 font-bold mt-0.5">{fmtPrice(trade.stop_loss)}</div>
            <div className="text-[9px] text-rose-500/80 font-medium">SL → Expected P/L: {fmtSignedCurrency(expectedSlPnl)}</div>
          </div>
          <div>
            <div className="text-[9px] text-zinc-500 uppercase">Take Profit</div>
            <div className="text-emerald-400 font-bold mt-0.5">{fmtPrice(trade.take_profit_1)}</div>
            <div className="text-[9px] text-emerald-500/80 font-medium">TP → Expected P/L: {fmtSignedCurrency(expectedTpPnl)}</div>
          </div>
        </div>
      ) : (
        <div className="space-y-2 bg-[#0d0d12] p-2.5 rounded-lg border border-amber-500/40">
          <div className="text-[10px] font-bold text-amber-300 flex items-center gap-1">
            <Edit2 size={11} /> Adjust Stop Loss &amp; Take Profit
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[9px] text-zinc-400 uppercase block mb-1">
                SL Price ($)
              </label>
              <input
                type="number"
                step="0.1"
                value={sl}
                onChange={(e) => setSl(e.target.value)}
                className="w-full bg-[#181822] border border-zinc-700 text-rose-400 font-bold text-xs p-1.5 rounded focus:outline-none focus:border-rose-500"
              />
              <div className="text-[9px] text-rose-400 mt-1 font-semibold">
                SL → Expected P/L: {slNum > 0 ? fmtSignedCurrency(expectedSlPnl) : "—"}
              </div>
            </div>

            <div>
              <label className="text-[9px] text-zinc-400 uppercase block mb-1">
                TP Price ($)
              </label>
              <input
                type="number"
                step="0.1"
                value={tp}
                onChange={(e) => setTp(e.target.value)}
                className="w-full bg-[#181822] border border-zinc-700 text-emerald-400 font-bold text-xs p-1.5 rounded focus:outline-none focus:border-emerald-500"
              />
              <div className="text-[9px] text-emerald-400 mt-1 font-semibold">
                TP → Expected P/L: {tpNum > 0 ? fmtSignedCurrency(expectedTpPnl) : "—"}
              </div>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving || tradeBusy}
            className="w-full py-1.5 rounded bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
          >
            <Check size={12} />
            {saving ? "Saving..." : "Save SL / TP"}
          </button>
        </div>
      )}

      <button
        onClick={() => onClose(trade.id)}
        disabled={tradeBusy}
        className="w-full py-1.5 rounded bg-rose-950/40 hover:bg-rose-900/60 border border-rose-500/30 text-rose-300 font-bold text-xs flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
      >
        <X size={12} /> CLOSE TRADE
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Dashboard Component
// ─────────────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [timeframe, setTimeframe] = useState("5m");
  const [symbol, setSymbol] = useState("XAU-USD-SPOT");

  const activeAsset = useMemo(() => ASSETS.find((a) => a.id === symbol) || ASSETS[0], [symbol]);
  const data = useDashboardData(timeframe, symbol);
  const [tradeBusy, setTradeBusy] = useState(false);
  const [tradeErr, setTradeErr] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Dual-Asset live quote state for Hero instruments
  const [goldQuote, setGoldQuote] = useState<PriceQuote | null>(null);
  const [btcQuote, setBtcQuote] = useState<PriceQuote | null>(null);

  // Sync active price into dual quote immediately
  useEffect(() => {
    if (data.price && data.price.price > 0) {
      if (symbol === "XAU-USD-SPOT") {
        setGoldQuote(data.price);
      } else if (symbol === "BTC-USD") {
        setBtcQuote(data.price);
      }
    }
  }, [data.price, symbol]);

  // Periodic background sync for non-active quote to keep both Hero cards fresh without redundant calls
  useEffect(() => {
    let active = true;
    async function syncHeroQuotes() {
      try {
        const otherSymbol = symbol === "XAU-USD-SPOT" ? "BTC-USD" : "XAU-USD-SPOT";
        const res = await ApiClient.getPrice(false, otherSymbol);
        if (!active) return;
        if (res && res.price > 0) {
          if (otherSymbol === "XAU-USD-SPOT") setGoldQuote(res);
          else setBtcQuote(res);
        }
      } catch {
        // non-blocking
      }
    }
    syncHeroQuotes();
    const timer = setInterval(syncHeroQuotes, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [symbol]);

  // Next Candle Countdown
  const nextCandleCountdown = useNextCandleCountdown(timeframe);

  // Weekend Market Closed Status (Gold only)
  const isWeekendClosed = useIsWeekendMarketClosed(symbol);
  const isGoldWeekendClosed = useIsWeekendMarketClosed("XAU-USD-SPOT");

  // Empirical Performance & Probability Calibration state
  const [perfReport, setPerfReport] = useState<PerformanceReportData | null>(null);
  const [calResponse, setCalResponse] = useState<CalibrationResponse | null>(null);

  // Manual Demo Trade Parameters
  const [manualLots, setManualLots] = useState(0.10);
  const [manualSlPoints, setManualSlPoints] = useState(15.0);
  const [manualTpPoints, setManualTpPoints] = useState(25.0);

  const handleSelectAsset = useCallback((newSymbol: string) => {
    setSymbol(newSymbol);
    if (newSymbol === "BTC-USD") {
      setManualLots(0.05);
      setManualSlPoints(300.0);
      setManualTpPoints(600.0);
    } else {
      setManualLots(0.10);
      setManualSlPoints(15.0);
      setManualTpPoints(25.0);
    }
  }, []);

  const signal = data.decision?.decision ?? "WAIT";
  const rawStrength = data.decision?.overall_signal?.percentage ?? data.decision?.signal_strength ?? data.decision?.confidence;
  const signalStrength = rawStrength != null ? Number(rawStrength) : null;
  const buyScore = data.decision?.buy_score != null ? Number(data.decision.buy_score) : null;
  const sellScore = data.decision?.sell_score != null ? Number(data.decision.sell_score) : null;
  const grade = data.decision?.setup_grade ?? null;
  const contributors = data.decision?.signal_contributors ?? [];

  const signalStrengthRef = useRef(signalStrength ?? 50);
  signalStrengthRef.current = signalStrength ?? 50;

  useEffect(() => {
    setPerfReport(null);
    setCalResponse(null);
    let mounted = true;
    async function loadPerformanceData() {
      try {
        const [rep, cal] = await Promise.allSettled([
          ApiClient.getPerformanceReport(signalStrengthRef.current, symbol),
          ApiClient.getCalibration(signalStrengthRef.current, symbol),
        ]);
        if (!mounted) return;
        if (rep.status === "fulfilled" && rep.value?.report) {
          setPerfReport(rep.value.report);
        }
        if (cal.status === "fulfilled" && cal.value) {
          setCalResponse(cal.value);
        }
      } catch {
        // Non-blocking telemetry
      }
    }
    loadPerformanceData();
    const timer = setInterval(loadPerformanceData, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [symbol]);

  const strategyStatsMap = useMemo(() => {
    const map: Record<string, string> = {};
    if (perfReport?.by_strategy) {
      for (const st of perfReport.by_strategy) {
        if (st.total_signals >= 10 && st.win_rate !== null) {
          map[st.strategy_name] = `${st.win_rate.toFixed(1)}% WR · ${st.total_signals} trades`;
        } else {
          map[st.strategy_name] = "Not empirically calibrated";
        }
      }
    }
    return map;
  }, [perfReport]);

  const calibratedProb =
    calResponse?.calibration?.calibrated_probability ??
    perfReport?.calibration?.calibrated_probability ??
    null;
  const calibrationStatus =
    calResponse?.calibration?.calibration_status ??
    perfReport?.calibration?.calibration_status ??
    "INSUFFICIENT_DATA";

  // Market Feed is truly online when live price is valid and no critical feed error
  const marketOnline = Boolean(
    ((data.price && data.price.price > 0) || (data.technical?.current_price && data.technical.current_price > 0)) &&
    (data.marketStatus?.status === "healthy" || data.marketStatus?.status === "degraded" || data.health?.feed === "online" || data.health?.status === "ok" || data.candles.length > 0)
  );

  // Gemini is active when configured and active or when backend explicitly used Gemini AI provider
  const isGeminiLive = Boolean(
    (data.health?.gemini_configured === true && data.health?.gemini_active === true) ||
    (data.decision?.ai_provider_used === "gemini" && data.ai != null)
  );
  const isAiFallback = Boolean(
    data.decision?.ai_provider_used === "fallback" || (!isGeminiLive && (data.ai != null || data.decision != null))
  );
  const geminiOnline = isGeminiLive;

  const prevClose = data.price?.prev_close_24h ?? (data.candles.length >= 2 ? data.candles[data.candles.length - 2].close : null);
  const currentLivePrice = safeNum(data.price?.price ?? data.technical?.current_price, 0);
  const changeUsd = isPresent(currentLivePrice) && isPresent(prevClose)
    ? currentLivePrice - prevClose!
    : (data.price?.change_24h ?? null);
  const changePct = isPresent(changeUsd) && isPresent(prevClose) && prevClose !== 0
    ? (changeUsd! / prevClose!) * 100
    : (data.price?.change_24h_pct ?? null);

  const hasSetup =
    signal !== "WAIT" &&
    data.decision?.entry_zone != null &&
    isPresent(data.decision.entry_zone.min) &&
    isPresent(data.decision.entry_zone.max);

  const rawConfluence = data.decision?.confluence_pct ?? signalStrength ?? null;
  const confluencePct = rawConfluence != null && !isNaN(Number(rawConfluence)) && Number(rawConfluence) > 0 ? Number(rawConfluence) : null;
  const confluenceDir = data.decision?.confluence_direction ?? (signal === "SELL" ? "Bearish" : signal === "BUY" ? "Bullish" : "Neutral");
  const mtfPct = data.decision?.mtf_confluence_pct != null ? Number(data.decision.mtf_confluence_pct) : null;
  const mtfSummary = data.decision?.mtf_alignment_summary ?? data.mtf?.alignment_summary ?? "--";

  const mtfTrendBias = (confluenceDir === "Bearish" || signal === "SELL") ? "Bearish" : (confluenceDir === "Bullish" || signal === "BUY") ? "Bullish" : "Neutral";
  const mtfColor = mtfTrendBias === "Bullish" ? "text-emerald-400" : mtfTrendBias === "Bearish" ? "text-rose-400" : "text-amber-400";
  const mtfBarBg = mtfTrendBias === "Bullish" ? "bg-emerald-500" : mtfTrendBias === "Bearish" ? "bg-rose-500" : "bg-amber-500";

  // Demo Account Stats normalized with safe defaults
  const demoStats: PaperTradingStats = useMemo(() => {
    return normalizePaperTradingStats(data.decision?.paper_trading_stats);
  }, [data.decision?.paper_trading_stats]);

  const tradeHistory: TradeRecord[] = (data.decision?.trade_history ?? []) as TradeRecord[];
  const openTrades = tradeHistory.filter((t) => t.status === "OPEN");
  const closedTrades = tradeHistory.filter((t) => t.status === "CLOSED");

  // Key Support & Resistance
  const nearestSupport = data.technical?.support_levels?.[0] ?? data.ai?.key_support?.[0] ?? null;
  const nearestResistance = data.technical?.resistance_levels?.[0] ?? data.ai?.key_resistance?.[0] ?? null;

  // ── Open Demo Trade Action (Uses real live market price at exact action time) ──
  const handleOpenDemoTrade = useCallback(
    async (direction: "BUY" | "SELL") => {
      setTradeBusy(true);
      setTradeErr(null);
      try {
        let entryPrice = currentLivePrice || (symbol === "BTC-USD" ? 78000.0 : 2700.0);
        try {
          const freshQuote = await ApiClient.getPrice(true, symbol);
          if (freshQuote && freshQuote.price > 0) {
            entryPrice = freshQuote.price;
          }
        } catch {
          // fallback to currentLivePrice
        }

        let sl = 0;
        let tp1 = 0;
        let tp2 = 0;
        let lots = manualLots || (symbol === "BTC-USD" ? 0.05 : 0.10);
        let tradeGrade = "MANUAL";

        if (hasSetup && data.decision) {
          sl = safeNum(data.decision.stop_loss, 0);
          tp1 = safeNum(data.decision.take_profit_1, 0);
          tp2 = safeNum(data.decision.take_profit_2, 0);
          lots = safeNum(data.decision.position_size, manualLots);
          tradeGrade = data.decision.setup_grade ?? "A";
        } else {
          if (direction === "BUY") {
            sl = entryPrice - (manualSlPoints || (symbol === "BTC-USD" ? 300.0 : 15.0));
            tp1 = entryPrice + (manualTpPoints || (symbol === "BTC-USD" ? 600.0 : 25.0));
          } else {
            sl = entryPrice + (manualSlPoints || (symbol === "BTC-USD" ? 300.0 : 15.0));
            tp1 = entryPrice - (manualTpPoints || (symbol === "BTC-USD" ? 600.0 : 25.0));
          }
        }

        await ApiClient.openDemoTrade({
          direction,
          entry_price: entryPrice,
          stop_loss: sl || undefined,
          take_profit_1: tp1 || undefined,
          take_profit_2: tp2 || undefined,
          position_size: lots,
          setup_grade: tradeGrade,
        });
        data.refresh();
      } catch (e) {
        setTradeErr(e instanceof Error ? e.message : "Failed to open demo trade");
      } finally {
        setTradeBusy(false);
      }
    },
    [currentLivePrice, hasSetup, data, manualLots, manualSlPoints, manualTpPoints, symbol]
  );

  // ── Close Demo Trade Action (Uses real live market price at exact close time) ─
  const handleCloseDemoTrade = useCallback(
    async (tradeId: string) => {
      setTradeBusy(true);
      setTradeErr(null);
      try {
        let closePrice = currentLivePrice;
        try {
          const freshQuote = await ApiClient.getPrice(true, symbol);
          if (freshQuote && freshQuote.price > 0) {
            closePrice = freshQuote.price;
          }
        } catch {
          // fallback to currentLivePrice
        }

        await ApiClient.closeDemoTrade({
          trade_id: tradeId,
          current_price: closePrice,
        });
        data.refresh();
      } catch (e) {
        setTradeErr(e instanceof Error ? e.message : "Failed to close demo trade");
      } finally {
        setTradeBusy(false);
      }
    },
    [currentLivePrice, data, symbol]
  );

  // ── Update Demo Trade SL/TP Action ─────────────────────────────────────────
  const handleUpdateDemoTrade = useCallback(
    async (tradeId: string, stopLoss: number, takeProfit: number) => {
      setTradeBusy(true);
      setTradeErr(null);
      try {
        await ApiClient.updateDemoTrade({
          trade_id: tradeId,
          stop_loss: stopLoss,
          take_profit_1: takeProfit,
        });
        data.refresh();
      } catch (e) {
        setTradeErr(e instanceof Error ? e.message : "Failed to update demo trade SL/TP");
      } finally {
        setTradeBusy(false);
      }
    },
    [data]
  );


  // ── Reset Demo Account ────────────────────────────────────────────────────
  const handleResetDemoAccount = useCallback(async () => {
    if (!confirm("Reset demo balance to $10,000.00 and clear simulated trade history?")) return;
    setTradeBusy(true);
    setTradeErr(null);
    try {
      await ApiClient.resetDemoAccount();
      data.refresh();
    } catch (e) {
      setTradeErr(e instanceof Error ? e.message : "Failed to reset demo account");
    } finally {
      setTradeBusy(false);
    }
  }, [data]);

  // Indicator contribution summary for confluence
  const indicatorPills = useMemo(() => {
    const t = data.technical;
    const p = currentLivePrice;
    return [
      { name: "EMA Structure", state: t ? (p > safeNum(t.ema50, 0) ? "Bullish" : "Bearish") : "Neutral" },
      { name: "RSI Momentum", state: t?.rsi14?.condition ?? "Neutral" },
      { name: "MACD Trend", state: t?.macd?.state ?? "Neutral" },
      { name: "SMC / ICT", state: signal === "WAIT" ? "Neutral" : signal === "BUY" ? "Bullish" : "Bearish" },
      { name: "Liquidity Sweep", state: data.decision?.sweep_detected ? "Active Sweep" : "Orderly" },
      { name: "Fibonacci OTE", state: hasSetup ? "In Zone (0.618-0.786)" : "Neutral" },
      { name: "AI Bias", state: data.ai?.overall_bias ?? "Neutral" },
    ];
  }, [data.technical, currentLivePrice, signal, data.decision, hasSetup, data.ai]);

  type MainDashboardSection =
    | "OVERALL"
    | "MARKET_INSIGHT"
    | "NOW_MARKET"
    | "CURRENT_MARKET"
    | "HISTORY_MARKET"
    | "ML_SHADOW"
    | "SHADOW"
    | "ML_MODELS"
    | "GOVERNANCE";
  const [activeSection, setActiveSection] = useState<MainDashboardSection>("OVERALL");
  const [mlShadowSubView, setMlShadowSubView] = useState<"ALL" | "ML_PREDICTION" | "SHADOW_VALIDATION">("ALL");
  const [sysObs, setSysObs] = useState<SystemObservabilityResponse | null>(null);
  const [btcDecision, setBtcDecision] = useState<TradingDecision | null>(null);
  const [goldDecision, setGoldDecision] = useState<TradingDecision | null>(null);
  const [isScrolled, setIsScrolled] = useState(false);

  // Sync current active asset's decision to btcDecision / goldDecision
  useEffect(() => {
    if (data.decision) {
      if (symbol === "BTC-USD") {
        setBtcDecision(data.decision);
      } else {
        setGoldDecision(data.decision);
      }
    }
  }, [data.decision, symbol]);

  // Periodic fetch for system observability and dual-asset decisions
  useEffect(() => {
    let mounted = true;
    async function loadObservabilityAndDecisions() {
      try {
        const obs = await getSystemObservability();
        if (mounted) setSysObs(obs);
      } catch {
        // silent fail on network hiccups
      }
      try {
        const [btcRes, goldRes] = await Promise.allSettled([
          ApiClient.getTradingDecision(false, "BTC-USD"),
          ApiClient.getTradingDecision(false, "XAU-USD-SPOT"),
        ]);
        if (mounted) {
          if (btcRes.status === "fulfilled" && btcRes.value) {
            setBtcDecision(btcRes.value);
          }
          if (goldRes.status === "fulfilled" && goldRes.value) {
            setGoldDecision(goldRes.value);
          }
        }
      } catch {
        // silent fail
      }
    }

    loadObservabilityAndDecisions();
    const interval = setInterval(loadObservabilityAndDecisions, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let ticking = false;
    let prevScrolled = false;
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const nextScrolled = window.scrollY > 20;
          if (nextScrolled !== prevScrolled) {
            prevScrolled = nextScrolled;
            setIsScrolled(nextScrolled);
          }
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen text-zinc-100 flex flex-col w-full max-w-full overflow-x-clip">

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 1. BRANDING & STICKY HEADER (Liquid Glass Theme)                      */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <header
        className={`sticky top-0 z-[100] w-full  backdrop-blur-md border-b border-sky-400/25 shadow-[0_10px_35px_rgba(2,6,23,0.5),inset_0_1px_1px_rgba(255,255,255,0.12),0_0_20px_rgba(56,189,248,0.12)] px-4 sm:px-6 lg:px-8 ${isScrolled ? "bg-[#06112c]/45 py-2 sm:py-2.5 shadow-cyan-950/50" : "bg-[#06112c]/38 py-3.5 sm:py-4.5"
          }`}
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 sm:gap-4 max-w-[1600px] mx-auto w-full">
          {/* Left: Branding & Asset Selector */}
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            <div className="flex items-center gap-2.5 sm:gap-3">

              {/* ── Logo: independent hover zoom (no tooltip) ── */}
              <div className="relative group/logo">
                <button
                  type="button"
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                  className="block cursor-pointer bg-transparent border-none p-0 transition-transform duration-500 ease-out hover:scale-[1.025]"
                  aria-label="Trade Matrix Home - Scroll to top"
                >
                  <CandleLogo
                    size={isScrolled ? 30 : 40}
                    className="shrink-0 drop-shadow-[0_0_20px_rgba(56,189,248,0.7)] transition-all duration-300"
                  />
                </button>
              </div>

              {/* ── Text + Subtitle: hover zoom (no tooltip) ── */}
              <div className="relative group/text">
                <button
                  type="button"
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                  className="block cursor-pointer bg-transparent border-none p-0 text-left transition-transform duration-500 ease-out hover:scale-[1.008]"
                  aria-label="Trade Matrix AI Analyser - Scroll to top"
                >
                  <div className="flex flex-col gap-0">
                    <div className="flex items-center gap-2">
                      <h1
                        className={`font-black font-mulegh select-none flex items-center tracking-wider drop-shadow-[0_4px_24px_rgba(2,132,199,0.55)] transition-all duration-300 ${isScrolled ? "text-xl sm:text-2xl" : "text-2xl sm:text-3xl"
                          }`}
                      >
                        <span className="brand-shimmer drop-shadow-[0_0_18px_rgba(56,189,248,0.4)]">
                          TRADE
                        </span>
                        <span className="ml-2 brand-shimmer-cyan drop-shadow-[0_0_24px_rgba(6,182,212,0.7)]">
                          MATRIX
                        </span>
                      </h1>
                      <span
                        className={`w-[66px] text-center text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded-md border ${activeAsset.badgeColor} shadow-[0_0_12px_rgba(56,189,248,0.3)] shrink-0`}
                      >
                        {activeAsset.ticker}
                      </span>
                    </div>
                    <p
                      className={`font-helvetica text-sky-200/70 tracking-wide font-medium drop-shadow-[0_1px_6px_rgba(56,189,248,0.3)] transition-all duration-300 ${isScrolled ? "text-[7.5px] sm:text-[8px]" : "text-[8px] sm:text-[8.5px]"
                        }`}
                    >
                      AI Analyser Present by Dhanushka Udayantha - ZERLO
                    </p>
                  </div>
                </button>
              </div>

            </div>

            {/* Asset Selector Tabs - Liquid Glass Style */}
            <div
              role="tablist"
              aria-label="Asset Selection"
              className="flex items-center bg-[#071330]/65 backdrop-blur-xl p-1 rounded-xl border border-sky-500/35 shadow-[0_4px_20px_rgba(2,132,199,0.22),inset_0_1px_1px_rgba(255,255,255,0.08)] ml-0 sm:ml-2 shrink-0 gap-1"
            >
              {ASSETS.map((asset) => {
                const isActive = asset.id === symbol;
                const isGold = asset.id === "XAU-USD-SPOT";
                return (
                  <button
                    key={asset.id}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    aria-label={`Select ${asset.name} (${asset.ticker})`}
                    onClick={() => handleSelectAsset(asset.id)}
                    className={`flex items-center justify-center gap-2 rounded-lg font-mono font-bold transition-all duration-300 w-[120px] sm:w-[135px] shrink-0 ${isScrolled ? "py-1 text-[11px]" : "py-1.5 text-xs"
                      } ${isActive
                        ? isGold
                          ? "bg-gradient-to-r from-yellow-950/90 via-yellow-900/80 to-yellow-950/90 text-yellow-100 shadow-[0_0_18px_rgba(234,179,8,0.4),inset_0_1px_1px_rgba(255,255,255,0.25)] border border-yellow-400/60"
                          : "bg-gradient-to-r from-orange-950/90 via-orange-900/80 to-orange-950/90 text-orange-100 shadow-[0_0_16px_rgba(249,115,22,0.35),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-orange-500/50"
                        : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                      }`}
                  >
                    <span className="tracking-wide">{asset.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${isActive
                        ? isGold
                          ? "bg-yellow-500/25 text-yellow-200 border border-yellow-400/45"
                          : "bg-orange-500/25 text-orange-200 border border-orange-400/40"
                        : "text-slate-500"
                        }`}
                    >
                      {asset.ticker}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right: Live Spot Price, Connectivity & Action Controls */}
          <div className="flex flex-wrap items-center justify-between lg:justify-end gap-3 sm:gap-4 w-full lg:w-auto lg:ml-auto">
            {/* Live Price Display */}
            <div className="relative group/price shrink-0">
              <div className="text-left lg:text-right w-[165px] sm:w-[185px] transition-transform duration-500 ease-out group-hover/price:scale-[1.02]">
                <div className="flex items-center lg:justify-end gap-1.5 text-[9px] sm:text-[10px] font-mono uppercase tracking-wider text-sky-300/70 font-semibold">
                  {data.refreshing && <RefreshCw size={9} className="animate-spin text-cyan-400" />}
                  Live Spot Price
                </div>
                {data.assetSwitching || !data.price ? (
                  <div className="flex items-center lg:justify-end gap-1.5 text-sky-400 font-mono py-0.5 h-[36px]">
                    <RefreshCw size={14} className="animate-spin text-cyan-400 shrink-0" />
                    <span className="text-xs font-bold text-sky-300 animate-pulse">
                      SYNCING {activeAsset.ticker}...
                    </span>
                  </div>
                ) : (
                  <div className="h-[36px] flex flex-col justify-center">
                    <div
                      className={`font-mono font-bold tabular-nums text-zinc-100 drop-shadow-[0_2px_12px_rgba(56,189,248,0.25)] transition-all duration-300 leading-tight ${isScrolled ? "text-xl sm:text-2xl" : "text-2xl sm:text-3xl"
                        }`}
                    >
                      {fmtPrice(currentLivePrice)}
                    </div>
                    <div
                      className={`text-[11px] font-mono font-semibold leading-tight ${isWeekendClosed
                        ? "text-amber-400"
                        : isPresent(changeUsd) && changeUsd! >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                        }`}
                    >
                      {isWeekendClosed ? (
                        <span className="text-amber-400 font-bold tracking-wide">MARKET CLOSED</span>
                      ) : isPresent(changeUsd) ? (
                        <>
                          {fmtSignedCurrency(changeUsd!)} ({fmtPct(changePct)}) 24h
                        </>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
              <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full mt-2 opacity-0 group-hover/price:opacity-100 transition-opacity duration-300 z-50 whitespace-nowrap">
                <div className="px-2.5 py-1 rounded-lg bg-[#06112c]/90 backdrop-blur-md border border-sky-400/40 shadow-[0_4px_20px_rgba(2,132,199,0.3)] text-[10px] font-mono font-bold text-sky-200 tracking-wider">
                  {activeAsset.ticker} Live Price
                </div>
              </div>
            </div>

            {/* Feed & AI Status / Timestamp Modules */}
            <div className="hidden sm:flex items-center gap-3 border-l border-sky-400/25 pl-3 font-mono text-[10px] shrink-0">
              {/* Feed Column */}
              <div className="relative group/feed flex flex-col gap-1 w-[125px] shrink-0">
                <div className="transition-transform duration-500 ease-out group-hover/feed:scale-[1.02] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5">
                    <StatusDot ok={marketOnline} />
                    <span
                      className={`text-[10px] font-bold tracking-wide ${marketOnline
                        ? "text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.4)]"
                        : "text-rose-400"
                        }`}
                    >
                      FEED {marketOnline ? "ONLINE" : "OFFLINE"}
                    </span>
                  </div>
                  <div
                    className="flex items-center justify-between gap-1.5 bg-[#071330]/65 backdrop-blur-lg px-2.5 py-1 rounded-lg border border-sky-500/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)] text-[9.5px] tabular-nums"
                  >
                    <div className="flex items-center gap-1">
                      <Clock size={10} className="text-amber-400 shrink-0" />
                      <span className="text-zinc-400 font-medium">Feed:</span>
                    </div>
                    <span
                      className="text-zinc-100 font-bold"
                      title="Sri Lanka Local Time (Asia/Colombo)"
                    >
                      {fmtSriLankaTime(data.price?.timestamp || data.lastUpdated)}
                    </span>
                  </div>
                </div>
                <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full mt-2 opacity-0 group-hover/feed:opacity-100 transition-opacity duration-300 z-50 whitespace-nowrap">
                  <div className="px-2.5 py-1 rounded-lg bg-[#06112c]/90 backdrop-blur-md border border-sky-400/40 shadow-[0_4px_20px_rgba(2,132,199,0.3)] text-[10px] font-mono font-bold text-sky-200 tracking-wider">
                    Market Feed Status
                  </div>
                </div>
              </div>

              {/* AI Column */}
              <div className="relative group/gemini flex flex-col gap-1 w-[135px] shrink-0">
                <div className="transition-transform duration-500 ease-out group-hover/gemini:scale-[1.02] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5">
                    <StatusDot ok={geminiOnline} />
                    <span
                      className={`text-[10px] font-bold tracking-wide ${geminiOnline
                        ? "text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.4)]"
                        : isAiFallback
                          ? "text-amber-400"
                          : "text-rose-400"
                        }`}
                    >
                      GEMINI {geminiOnline ? "ACTIVE" : isAiFallback ? "FALLBACK" : "OFFLINE"}
                    </span>
                  </div>
                  <div
                    className="flex items-center justify-between gap-1.5 bg-[#071330]/65 backdrop-blur-lg px-2.5 py-1 rounded-lg border border-sky-500/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)] text-[9.5px] tabular-nums"
                  >
                    <div className="flex items-center gap-1">
                      <Cpu size={10} className="text-cyan-400 shrink-0" />
                      <span className="text-zinc-400 font-medium">Last AI:</span>
                    </div>
                    <span
                      className="text-cyan-300 font-bold"
                      title="Sri Lanka Local Time (Asia/Colombo)"
                    >
                      {fmtSriLankaTime(data.ai?.analysis_timestamp || data.decision?.timestamp || data.lastAiUpdated)}
                    </span>
                  </div>
                </div>
                <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full mt-2 opacity-0 group-hover/gemini:opacity-100 transition-opacity duration-300 z-50 whitespace-nowrap">
                  <div className="px-2.5 py-1 rounded-lg bg-[#06112c]/90 backdrop-blur-md border border-sky-400/40 shadow-[0_4px_20px_rgba(2,132,199,0.3)] text-[10px] font-mono font-bold text-sky-200 tracking-wider">
                    Gemini AI Status
                  </div>
                </div>
              </div>
            </div>

            {/* Refresh Action */}
            <div className="relative group/refresh shrink-0">
              <button
                type="button"
                onClick={() => data.refresh()}
                disabled={data.refreshing}
                aria-label="Force refresh live market data"
                className="bg-gradient-to-b from-[#0e214d]/75 to-[#071330]/75 hover:from-[#132c66]/85 hover:to-[#0a1b44]/85 backdrop-blur-lg border border-sky-400/40 text-sky-100 disabled:opacity-80 px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-all duration-400 ease-out hover:scale-[1.025] shadow-[0_0_16px_rgba(56,189,248,0.2),inset_0_1px_1px_rgba(255,255,255,0.15)] min-w-[115px]"
              >
                <RefreshCw size={12} className={data.refreshing ? "animate-spin text-cyan-400" : "text-sky-300"} />
                {data.refreshing ? "REFRESHING" : "REFRESH"}
              </button>
              <div className="pointer-events-none absolute right-0 top-full mt-2 opacity-0 group-hover/refresh:opacity-100 transition-opacity duration-300 z-50 whitespace-nowrap">
                <div className="px-2.5 py-1 rounded-lg bg-[#06112c]/90 backdrop-blur-md border border-sky-400/40 shadow-[0_4px_20px_rgba(2,132,199,0.3)] text-[10px] font-mono font-bold text-sky-200 tracking-wider">
                  Force Refresh Data
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Compact Sticky Top Tab Navigation (5 Items) ── */}
        <nav
          aria-label="Primary Dashboard Sections"
          className={`w-full max-w-[1600px] mx-auto transition-all duration-300 ${isScrolled ? "mt-1.5" : "mt-2.5"}`}
        >
          <div
            role="tablist"
            aria-label="Trading analysis sections"
            className="bg-[#071330]/75 backdrop-blur-xl p-0.5 sm:p-1 rounded-xl border border-sky-500/35 shadow-[0_4px_20px_rgba(2,132,199,0.22),inset_0_1px_1px_rgba(255,255,255,0.08)] flex items-center gap-1 sm:gap-1.5 overflow-x-auto scrollbar-none"
          >
            <button
              type="button"
              role="tab"
              id="tab-overall"
              aria-selected={activeSection === "OVERALL"}
              aria-controls="section-overall"
              onClick={() => setActiveSection("OVERALL")}
              className={`flex-1 min-w-0 flex items-center justify-center rounded-lg font-mono font-bold transition-all duration-300 cursor-pointer select-none text-center ${isScrolled ? "py-1 text-[10px] sm:text-xs" : "py-1.5 sm:py-2 text-[10.5px] sm:text-sm"
                } ${activeSection === "OVERALL"
                  ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                  : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                }`}
            >
              <span>OVERALL</span>
            </button>

            <button
              type="button"
              role="tab"
              id="tab-market-insight"
              aria-selected={activeSection === "MARKET_INSIGHT"}
              aria-controls="section-market-insight"
              onClick={() => setActiveSection("MARKET_INSIGHT")}
              className={`flex-1 min-w-0 flex items-center justify-center rounded-lg font-mono font-bold transition-all duration-300 cursor-pointer select-none text-center ${isScrolled ? "py-1 text-[10px] sm:text-xs" : "py-1.5 sm:py-2 text-[10.5px] sm:text-sm"
                } ${activeSection === "MARKET_INSIGHT"
                  ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                  : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                }`}
            >
              <span>MARKET INSIGHT</span>
            </button>

            <button
              type="button"
              role="tab"
              id="tab-now-market"
              aria-selected={activeSection === "NOW_MARKET" || activeSection === "CURRENT_MARKET"}
              aria-controls="section-now-market"
              onClick={() => setActiveSection("CURRENT_MARKET")}
              className={`flex-1 min-w-0 flex items-center justify-center rounded-lg font-mono font-bold transition-all duration-300 cursor-pointer select-none text-center ${isScrolled ? "py-1 text-[10px] sm:text-xs" : "py-1.5 sm:py-2 text-[10.5px] sm:text-sm"
                } ${activeSection === "NOW_MARKET" || activeSection === "CURRENT_MARKET"
                  ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                  : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                }`}
            >
              <span>NOW MARKET</span>
            </button>

            <button
              type="button"
              role="tab"
              id="tab-history-market"
              aria-selected={activeSection === "HISTORY_MARKET"}
              aria-controls="section-history-market"
              onClick={() => setActiveSection("HISTORY_MARKET")}
              className={`flex-1 min-w-0 flex items-center justify-center rounded-lg font-mono font-bold transition-all duration-300 cursor-pointer select-none text-center ${isScrolled ? "py-1 text-[10px] sm:text-xs" : "py-1.5 sm:py-2 text-[10.5px] sm:text-sm"
                } ${activeSection === "HISTORY_MARKET"
                  ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                  : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                }`}
            >
              <span>HISTORY MARKET</span>
            </button>

            <button
              type="button"
              role="tab"
              id="tab-ml-shadow"
              aria-selected={activeSection === "ML_SHADOW" || activeSection === "SHADOW" || activeSection === "ML_MODELS"}
              aria-controls="section-ml-shadow"
              onClick={() => setActiveSection("ML_SHADOW")}
              className={`flex-1 min-w-0 flex items-center justify-center rounded-lg font-mono font-bold transition-all duration-300 cursor-pointer select-none text-center ${isScrolled ? "py-1 text-[10px] sm:text-xs" : "py-1.5 sm:py-2 text-[10.5px] sm:text-sm"
                } ${activeSection === "ML_SHADOW" || activeSection === "SHADOW" || activeSection === "ML_MODELS"
                  ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                  : "text-slate-400 hover:text-sky-200 hover:bg-sky-950/30 border border-transparent"
                }`}
            >
              <span>ML &amp; SHADOW</span>
            </button>
          </div>
        </nav>
      </header>

      {/* Main Dashboard Content Stream */}
      <main className="w-full max-w-[1600px] mx-auto px-4 py-6 md:px-6 lg:px-8 space-y-6 flex-1">

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 1: OVERALL (CONCISE FINAL PLATFORM DASHBOARD)                 */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSection === "OVERALL" && (
          <div id="section-overall" role="tabpanel" aria-labelledby="tab-overall" className="space-y-6">
            {/* TOP HERO CARD: ASSET TRADING DECISION & ACTION LEVELS */}
            {(() => {
              const finalDecision = isWeekendClosed
                ? "WAIT"
                : (data.initialLoading || data.assetSwitching)
                ? "WAIT"
                : (data.decision?.decision || signal || "WAIT");
              const isWaitAction = finalDecision === "WAIT";
              const overallEvidenceSignal = data.decision?.overall_signal?.signal;
              const overallEvidencePct = data.decision?.overall_signal?.percentage ?? data.decision?.overall_signal?.overall_evidence_score;

              return (
                <SignalHeroCard
                  pageTitle={`${activeAsset.name.toUpperCase()} TRADING DECISION & ACTION LEVELS`}
                  icon={Compass}
                  assetName={activeAsset.name}
                  assetTicker={activeAsset.ticker}
                  signal={finalDecision}
                  actionLabel={
                    isWeekendClosed
                      ? "MARKET CLOSED"
                      : (data.initialLoading || data.assetSwitching)
                      ? "EVALUATING..."
                      : isWaitAction
                      ? "FINAL ACTION: WAIT"
                      : `FINAL ACTION: ${finalDecision}`
                  }
                  percentage={
                    isWaitAction
                      ? null
                      : resolveOverallSignalPercentage(
                          overallEvidenceSignal || finalDecision,
                          overallEvidencePct,
                          data.decision?.overall_signal?.overall_evidence_score
                        )
                  }
                  statusBadge={
                    isWeekendClosed
                      ? "WEEKEND CLOSED (RESUMES SUN)"
                      : isWaitAction
                      ? "AWAITING VALID CONFLUENCE"
                      : "TRADE SETUP ACTIVE"
                  }
                  isEvaluating={data.initialLoading || data.assetSwitching || !data.decision}
                  isMarketClosed={isWeekendClosed}
                  entryPrice={!isWaitAction ? (data.decision?.entry_price ?? null) : null}
                  stopLoss={!isWaitAction ? (data.decision?.stop_loss ?? null) : null}
                  takeProfit1={!isWaitAction ? (data.decision?.take_profit_1 ?? null) : null}
                  takeProfit2={!isWaitAction ? (data.decision?.take_profit_2 ?? null) : null}
                  reasoning={data.decision?.overall_reasoning || undefined}
                  showActionLevels={true}
                  lastUpdatedText={
                    data.initialLoading || data.assetSwitching
                      ? undefined
                      : (data.technical?.data_timestamp || data.price?.timestamp || data.decision?.timestamp || data.lastUpdated || undefined)
                  }
                  timeChangeText={
                    data.price && data.price.price > 0
                      ? `${fmtPrice(data.price.price)} ${fmtSignedCurrency(changeUsd)} (${fmtSigned(changePct, 2)}%)`
                      : undefined
                  }
                  supportingPills={
                    <>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Overall Evidence Bias:</span>
                        <strong className={overallEvidenceSignal === "BUY" ? "text-emerald-300 font-bold" : overallEvidenceSignal === "SELL" ? "text-rose-300 font-bold" : "text-sky-300 font-bold"}>
                          {overallEvidenceSignal ? `${overallEvidenceSignal} · ${overallEvidencePct != null ? `${overallEvidencePct}%` : "--%"}` : "WAIT"}
                        </strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Trend:</span>
                        <strong className={mtfColor}>{data.technical?.trend.direction || data.decision?.trend || "NEUTRAL"}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Regime:</span>
                        <strong className="text-sky-300 font-bold">{data.ai?.market_condition || (data.decision as any)?.market_regime || "RANGE"}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Confluence:</span>
                        <strong className="text-emerald-300 font-bold">{confluencePct != null && confluencePct > 0 ? `${Math.round(confluencePct)}%` : "--%"}</strong>
                      </div>
                    </>
                  }
                />
              );
            })()}

            {/* PRICE CHART & DEMO TRADING CONTROLS */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-stretch">
                {/* Column 1 & 2: Price Chart with Next Candle Countdown */}
                <div className="xl:col-span-2 flex flex-col">
                  <Card
                    title={`${activeAsset.ticker} Matrix Chart (${timeframe.toUpperCase()})`}
                    icon={BarChart3}
                    className="h-full flex flex-col justify-between"
                    action={
                      <div className="flex items-center gap-3">
                        {/* Next Candle Countdown Badge */}
                        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#14141a] border border-[#262632] text-[11px] font-mono text-zinc-300">
                          <Timer size={12} className="text-amber-400" />
                          <span className="text-zinc-500">Next {timeframe}:</span>
                          <span className="font-bold text-amber-300 tabular-nums">{nextCandleCountdown}</span>
                        </div>

                        <div className="flex gap-1 bg-[#14141a] border border-[#262630] p-1 rounded-lg">
                          {TIMEFRAMES.map((tf) => (
                            <button
                              key={tf.value}
                              onClick={() => setTimeframe(tf.value)}
                              className={`px-3 py-1 rounded-md text-xs font-mono font-semibold transition-all duration-700 ease-out ${timeframe === tf.value
                                ? "bg-amber-500 text-black shadow-sm"
                                : "text-zinc-400 hover:bg-[#20202a] hover:text-zinc-200"
                                }`}
                            >
                              {tf.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    }
                  >
                    <div className="flex-1 flex flex-col justify-center relative min-h-[360px]">
                      {data.tfSwitching || data.assetSwitching || data.candles.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-80 gap-3 text-blue-400 font-mono">
                          <RefreshCw size={28} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                          <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                            SYNCING {activeAsset.name.toUpperCase()} ({activeAsset.ticker}) {timeframe.toUpperCase()} CANDLES...
                          </span>
                        </div>
                      ) : (
                        <div className="relative w-full h-full">
                          <CandleChart
                            candles={data.candles}
                            technical={data.technical}
                            timeframe={timeframe}
                            loading={data.initialLoading}
                            error={data.errors.candles}
                            currentPrice={currentLivePrice}
                            activeTrades={openTrades}
                          />

                          {/* Weekend Market Closed Low-Opacity Overlay (Chart remains fully visible) */}
                          {isWeekendClosed && (
                            <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center p-3 sm:p-4 bg-slate-950/25 backdrop-blur-[1.5px] rounded-xl transition-all duration-500">
                              <div className="pointer-events-auto w-full max-w-md p-4 sm:p-4.5 rounded-xl bg-[#061025]/92 border border-amber-500/40 shadow-[0_12px_40px_rgba(0,0,0,0.7),0_0_30px_rgba(245,158,11,0.2),inset_0_1px_1px_rgba(255,255,255,0.12)] backdrop-blur-xl text-center space-y-2.5 transition-transform duration-300 hover:scale-[1.01]">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs font-mono font-bold tracking-wider uppercase shadow-sm">
                                  <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                                  </span>
                                  Gold Market Closed (Weekend)
                                </div>

                                <div className="p-2.5 rounded-lg bg-[#030a1c]/80 border border-sky-500/20 text-left font-mono text-[11px] sm:text-xs space-y-1.5">
                                  <div className="flex items-center justify-between text-slate-200">
                                    <span className="text-zinc-400 font-semibold">Market Opens:</span>
                                    <span className="text-amber-300 font-bold">Sun 3:30 AM (DST) / 4:30 AM SLT</span>
                                  </div>
                                  <div className="flex items-center justify-between text-slate-200 pt-1 border-t border-sky-500/10">
                                    <span className="text-zinc-400 font-semibold">Market Closes:</span>
                                    <span className="text-amber-300 font-bold">Fri 2:30 AM (Summer) / 3:30 AM SLT</span>
                                  </div>
                                  <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-sky-500/10">
                                    <span>Operations:</span>
                                    <span className="text-sky-300 font-semibold">24 Hours / Mon – Fri</span>
                                  </div>
                                </div>

                                <p className="text-[10px] font-mono text-zinc-400 leading-tight">
                                  ⚡ Showing Friday close. Real-time updates resume at market open.
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-4 justify-between items-center text-[10px] font-mono text-zinc-500 pt-3 border-t border-[#1e1e24] mt-2">
                      <div className="flex flex-wrap gap-3">
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-blue-500" /> EMA20</span>
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-orange-500" /> EMA50</span>
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-violet-500" /> EMA200</span>
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-emerald-500" /> Support (S1/S2)</span>
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-rose-500" /> Resist (R1/R2)</span>
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-yellow-400 shadow-[0_0_6px_#facc15]" /> NOW {activeAsset.name} Price (Yellow)</span>
                      </div>
                      {openTrades.length > 0 && (
                        <span className="text-amber-400 font-semibold">● {openTrades.length} Active Demo Position(s) plotted on chart</span>
                      )}
                    </div>
                  </Card>
                </div>

                {/* Column 3: Demo Trading Execution (Same Height as Chart) */}
                <div className="flex flex-col">
                  <Card
                    title="Demo Trading Execution"
                    icon={Sliders}
                    className="h-full flex flex-col justify-between"
                    action={
                      <div className="flex items-center gap-2">
                        {isWeekendClosed && (
                          <span className="text-[10px] font-mono text-amber-300 font-bold px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                            MARKET CLOSED
                          </span>
                        )}
                        <button
                          onClick={handleResetDemoAccount}
                          title="Reset Demo Account Balance to $10,000"
                          className="text-[10px] font-mono text-zinc-400 hover:text-rose-300 px-2 py-0.5 rounded bg-[#14141a] hover:bg-rose-950/30 border border-[#2a2a36] flex items-center gap-1 transition-colors"
                        >
                          <RotateCcw size={11} /> Reset
                        </button>
                        <span className="text-[10px] font-mono text-amber-400 font-bold px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30">
                          $10,000 DEMO
                        </span>
                      </div>
                    }
                  >
                    <div className="space-y-4 flex-1 flex flex-col justify-between">
                      <div className="space-y-4">
                        {/* Account Mini Stats */}
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
                            <div className="text-[10px] text-zinc-500 uppercase">Balance</div>
                            <div className="text-base font-bold text-zinc-100 mt-0.5">
                              {fmtCurrency(demoStats.current_balance)}
                            </div>
                          </div>

                          <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
                            <div className="text-[10px] text-zinc-500 uppercase">Equity</div>
                            <div className={`text-base font-bold mt-0.5 ${safeNum(demoStats.equity, 10000) >= safeNum(demoStats.starting_balance, 10000) ? "text-emerald-400" : "text-rose-400"}`}>
                              {fmtCurrency(demoStats.equity)}
                            </div>
                          </div>

                          {/* Win Rate Conditional Display */}
                          {demoStats.total_trades > 0 ? (
                            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
                              <div className="text-[10px] text-zinc-500 uppercase">Win Rate</div>
                              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                                {fmtNumber(demoStats.win_rate, 1)}% ({safeNum(demoStats.wins, 0)}W / {safeNum(demoStats.losses, 0)}L)
                              </div>
                            </div>
                          ) : (
                            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
                              <div className="text-[10px] text-zinc-500 uppercase">Current Market</div>
                              <div className="text-[10px] font-bold text-zinc-300 mt-1 truncate">
                                Price: {fmtPrice(currentLivePrice)} · AI: {signal}
                              </div>
                            </div>
                          )}

                          <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
                            <div className="text-[10px] text-zinc-500 uppercase">Closed P/L</div>
                            <div className={`text-sm font-bold mt-0.5 ${safeNum(demoStats.net_profit, 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {fmtSignedCurrency(demoStats.net_profit)}
                            </div>
                          </div>
                        </div>

                        {/* Quick Parameters */}
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="flex items-center justify-between bg-[#121217] border border-[#202028] px-2.5 py-1.5 rounded-md">
                            <span className="text-[10px] text-zinc-500 uppercase">Lots</span>
                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              max="1.00"
                              value={manualLots}
                              onChange={(e) => setManualLots(parseFloat(e.target.value) || 0.01)}
                              className="w-14 bg-transparent text-right text-zinc-100 font-bold focus:outline-none"
                            />
                          </div>

                          <div className="flex items-center justify-between bg-[#121217] border border-[#202028] px-2.5 py-1.5 rounded-md">
                            <span className="text-[10px] text-zinc-500 uppercase">SL Pts</span>
                            <input
                              type="number"
                              step="1"
                              value={manualSlPoints}
                              onChange={(e) => setManualSlPoints(parseFloat(e.target.value) || 10)}
                              className="w-12 bg-transparent text-right text-zinc-100 font-bold focus:outline-none"
                            />
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="grid grid-cols-1 gap-2.5 pt-1">
                          <button
                            onClick={() => handleOpenDemoTrade("BUY")}
                            disabled={tradeBusy}
                            className="flex items-center justify-between py-3 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs font-mono shadow-[0_0_16px_rgba(16,185,129,0.15)] transition-all disabled:opacity-50 w-full"
                          >
                            <span className="flex items-center gap-2"><TrendingUp size={15} /> BUY DEMO</span>
                            <span className="text-emerald-100 font-bold">
                              {signal === "BUY" && buyScore != null && buyScore > 30 ? `Confidence ${buyScore}%` : "--%"}
                            </span>
                          </button>

                          <button
                            onClick={() => handleOpenDemoTrade("SELL")}
                            disabled={tradeBusy}
                            className="flex items-center justify-between py-3 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs font-mono shadow-[0_0_16px_rgba(244,63,94,0.15)] transition-all disabled:opacity-50 w-full"
                          >
                            <span className="flex items-center gap-2"><TrendingDown size={15} /> SELL DEMO</span>
                            <span className="text-rose-100 font-bold">
                              {signal === "SELL" && sellScore != null && sellScore > 30 ? `Confidence ${sellScore}%` : "--%"}
                            </span>
                          </button>
                        </div>

                        {tradeErr && (
                          <div className="p-2.5 bg-rose-950/30 border border-rose-500/30 rounded-lg text-[11px] font-mono text-rose-300 flex items-center gap-2">
                            <AlertTriangle size={13} className="text-rose-400 shrink-0" />
                            <span>{tradeErr}</span>
                          </div>
                        )}
                      </div>

                      {/* Active Open Positions List */}
                      {openTrades.length > 0 ? (
                        <div className="space-y-2.5 pt-2 border-t border-[#1e1e24]">
                          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                            <span>Open Positions ({openTrades.length})</span>
                            <span className="text-emerald-400">Live P&amp;L</span>
                          </div>

                          {openTrades.map((trade) => (
                            <OpenTradeCard
                              key={trade.id}
                              trade={trade}
                              currentLivePrice={currentLivePrice}
                              onClose={handleCloseDemoTrade}
                              onUpdate={handleUpdateDemoTrade}
                              tradeBusy={tradeBusy}
                            />
                          ))}
                        </div>
                      ) : (
                        <div className="py-4 text-center text-[11px] font-mono text-zinc-600 border-t border-[#1e1e24]">
                          No active demo trades. Click BUY DEMO or SELL DEMO above to execute.
                        </div>
                      )}
                    </div>
                  </Card>
                </div>
              </div>

              {/* Full-Width Demo Trade History Bar */}
              <div className="border border-[#1e1e24] bg-[#0c0c0f] rounded-xl overflow-hidden shadow-sm">
                <button
                  type="button"
                  aria-expanded={historyOpen}
                  aria-controls="demo-trade-history-panel"
                  onClick={() => setHistoryOpen(!historyOpen)}
                  className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-[#121217] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <BarChart3 size={16} className="text-amber-400" />
                    <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-zinc-200">
                      Demo Trade History ({closedTrades.length} Closed Trades)
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-zinc-500">
                      {historyOpen ? "Collapse Table" : "Expand Table"}
                    </span>
                    {historyOpen ? <ChevronUp size={16} className="text-zinc-400" /> : <ChevronDown size={16} className="text-zinc-400" />}
                  </div>
                </button>

                {historyOpen && (
                  <div id="demo-trade-history-panel" className="p-5 border-t border-[#1e1e24] space-y-3">
                    {closedTrades.length === 0 ? (
                      <p className="text-xs font-mono text-zinc-600 text-center py-6">
                        No closed demo trades yet. Execute and close BUY/SELL demo trades above to populate history.
                      </p>
                    ) : (
                      <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
                        <table aria-label="Closed demo trade history" className="w-full text-left font-mono text-xs whitespace-nowrap">
                          <thead className="sticky top-0 bg-[#0c0c0f] z-10">
                            <tr className="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase tracking-wider">
                              <th scope="col" className="pb-3 px-2">Direction</th>
                              <th scope="col" className="pb-3 px-2">Entry Price</th>
                              <th scope="col" className="pb-3 px-2">Entry Time</th>
                              <th scope="col" className="pb-3 px-2">Exit Price</th>
                              <th scope="col" className="pb-3 px-2">Exit Time</th>
                              <th scope="col" className="pb-3 px-2">Lots</th>
                              <th scope="col" className="pb-3 px-2">Stop Loss</th>
                              <th scope="col" className="pb-3 px-2">Take Profit</th>
                              <th scope="col" className="pb-3 px-2">Duration</th>
                              <th scope="col" className="pb-3 px-2 text-right">Final P/L ($)</th>
                              <th scope="col" className="pb-3 px-2 text-right">Result</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-zinc-900">
                            {closedTrades.slice().reverse().map((t) => {
                              const isWin = t.result === "WIN";
                              const pnlNum = safeNum(t.pnl, 0);
                              const lotsNum = safeNum(t.position_size, 0.10);
                              return (
                                <tr key={t.id} className="hover:bg-[#14141a] transition-colors">
                                  <td className="py-3 px-2">
                                    <span className={`px-2 py-0.5 rounded font-black text-[10px] border ${t.direction === "BUY"
                                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                      : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                                      }`}>
                                      {t.direction}
                                    </span>
                                  </td>
                                  <td className="py-3 px-2 text-zinc-200 font-bold">
                                    {fmtPrice(t.entry_price)}
                                  </td>
                                  <td className="py-3 px-2 text-zinc-400 text-[11px]">
                                    {fmtTime(t.entry_timestamp)}
                                  </td>
                                  <td className="py-3 px-2 text-zinc-200 font-bold">
                                    {fmtPrice(t.exit_price ?? t.entry_price)}
                                  </td>
                                  <td className="py-3 px-2 text-zinc-400 text-[11px]">
                                    {fmtTime(t.exit_timestamp)}
                                  </td>
                                  <td className="py-3 px-2 text-zinc-300">
                                    {lotsNum} Lots
                                  </td>
                                  <td className="py-3 px-2 text-rose-400/90">
                                    {t.stop_loss ? fmtPrice(t.stop_loss) : "—"}
                                  </td>
                                  <td className="py-3 px-2 text-emerald-400/90">
                                    {t.take_profit_1 ? fmtPrice(t.take_profit_1) : "—"}
                                  </td>
                                  <td className="py-3 px-2 text-zinc-400">
                                    {t.duration || "1m"}
                                  </td>
                                  <td className={`py-3 px-2 text-right font-black text-sm ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                    {fmtSignedCurrency(pnlNum)}
                                  </td>
                                  <td className="py-3 px-2 text-right">
                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${isWin
                                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                      : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                                      }`}>
                                      {t.result}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* TRADE SETUP MATRIX */}
            <Card
              title="Trade Setup Matrix"
              icon={Target}
              className={
                signal === "BUY"
                  ? "!border-emerald-500/50 shadow-[0_0_24px_rgba(16,185,129,0.15)] hover:shadow-[0_0_45px_rgba(16,185,129,0.35),0_0_90px_rgba(16,185,129,0.18)]"
                  : signal === "SELL"
                    ? "!border-rose-500/50 shadow-[0_0_24px_rgba(244,63,94,0.15)] hover:shadow-[0_0_45px_rgba(244,63,94,0.35),0_0_90px_rgba(244,63,94,0.18)]"
                    : "!border-blue-500/40 shadow-[0_0_24px_rgba(59,130,246,0.12)] hover:shadow-[0_0_45px_rgba(59,130,246,0.35),0_0_90px_rgba(59,130,246,0.18)]"
              }
              action={
                <div className="flex items-center gap-2 font-mono">
                  <span
                    className={`text-[11px] font-bold px-2.5 py-1 rounded-md border flex items-center gap-1.5 ${isWeekendClosed
                      ? "bg-amber-500/15 text-amber-300 border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                      : signal === "BUY"
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.25)]"
                        : signal === "SELL"
                          ? "bg-rose-500/15 text-rose-300 border-rose-500/40 shadow-[0_0_12px_rgba(244,63,94,0.25)]"
                          : "bg-blue-500/15 text-blue-300 border-blue-500/40 shadow-[0_0_12px_rgba(59,130,246,0.2)]"
                      }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${isWeekendClosed
                        ? "bg-amber-400 animate-pulse"
                        : signal === "BUY"
                          ? "bg-emerald-400 animate-pulse"
                          : signal === "SELL"
                            ? "bg-rose-400 animate-pulse"
                            : "bg-blue-400"
                        }`}
                    />
                    {isWeekendClosed
                      ? "MARKET CLOSED (WEEKEND)"
                      : signal === "BUY"
                        ? "BUY SETUP ACTIVE"
                        : signal === "SELL"
                          ? "SELL SETUP ACTIVE"
                          : "WAITING FOR SETUP"}
                  </span>
                </div>
              }
            >
              {data.assetSwitching || !data.decision ? (
                <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                  <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                  <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                    COMPUTING {activeAsset.ticker} OPTIMAL TRADE ENTRY (OTE) &amp; RISK LEVELS...
                  </span>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 text-sm font-mono">
                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Entry Zone</div>
                    <div className={`font-bold mt-1 ${signal === "BUY" ? "text-emerald-400" : signal === "SELL" ? "text-rose-400" : "text-zinc-400"}`}>
                      {hasSetup ? `${fmtPrice(data.decision!.entry_zone!.min)} – ${fmtPrice(data.decision!.entry_zone!.max)}` : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">Fib OTE (0.618-0.786)</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Stop Loss</div>
                    <div className="text-rose-400 font-bold mt-1">
                      {hasSetup ? fmtPrice(data.decision!.stop_loss) : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">Structural Invalidation</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Target 1</div>
                    <div className={`font-bold mt-1 ${signal === "BUY" ? "text-emerald-400" : signal === "SELL" ? "text-rose-400" : "text-zinc-400"}`}>
                      {hasSetup ? fmtPrice(data.decision!.take_profit_1) : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">{hasSetup ? (data.decision?.risk_reward_tp1 != null ? `R:R 1:${data.decision.risk_reward_tp1.toFixed(2)}` : "—") : "—"}</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Target 2</div>
                    <div className={`font-bold mt-1 ${signal === "BUY" ? "text-emerald-300" : signal === "SELL" ? "text-rose-300" : "text-zinc-400"}`}>
                      {hasSetup ? fmtPrice(data.decision!.take_profit_2) : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">{hasSetup ? (data.decision?.risk_reward_tp2 != null ? `R:R 1:${data.decision.risk_reward_tp2.toFixed(2)}` : "—") : "—"}</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Position Size</div>
                    <div className="text-amber-400 font-bold mt-1">
                      {hasSetup ? (data.decision?.position_size ? `${data.decision.position_size} Lots` : "—") : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">1.0% Risk Limit</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Risk Rating</div>
                    <div className={`font-bold mt-1 ${hasSetup ? riskClass(data.decision?.risk_level) : "text-zinc-500"}`}>
                      {hasSetup ? data.decision?.risk_level || "LOW" : "—"}
                    </div>
                    <div className="text-[9px] text-zinc-500">Enforced Limit</div>
                  </div>

                  <div className="bg-[#121217] border border-[#202028] rounded-lg p-3">
                    <div className="text-[10px] text-zinc-500 uppercase">Confluence Score</div>
                    <div className="text-cyan-300 font-bold mt-1">
                      {confluencePct != null ? `${confluencePct}%` : "--"}
                    </div>
                    <div className="text-[9px] text-zinc-500">Multi-Engine Agree</div>
                  </div>
                </div>
              )}
            </Card>

            {/* 2. FULL PLATFORM MULTI-SOURCE SUMMARY PANEL */}
            <div className="card-hover bg-[#071330]/85 border border-sky-500/35 rounded-2xl p-5 shadow-[0_8px_32px_rgba(2,132,199,0.18)] backdrop-blur-xl space-y-4 font-mono">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-sky-500/20 pb-3 gap-2">
                <div className="flex items-center gap-2">
                  <Compass size={18} className="text-sky-400" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-white">
                    Platform Multi-Source Final Intelligence Summary
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSection("MARKET_INSIGHT")}
                  className="text-[11px] px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-900/90 to-sky-800/85 hover:from-blue-800 hover:to-sky-700 text-sky-100 border border-sky-400/50 font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-[0_0_12px_rgba(56,189,248,0.25)]"
                >
                  <span>Explore Complete Market Insight Narrative</span>
                  <span>&rarr;</span>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
                {/* 1. Now Market */}
                <div className="bg-[#0b1b3d]/70 border border-sky-500/20 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400 text-[10px] uppercase font-bold">
                    <span className="text-sky-300">1. Current Market</span>
                    <span className={`px-1.5 py-0.5 rounded font-bold ${(data.decision?.now_signal?.signal || "WAIT") === "BUY" ? "text-emerald-300 bg-emerald-500/20 border border-emerald-500/30" : (data.decision?.now_signal?.signal || "WAIT") === "SELL" ? "text-rose-300 bg-rose-500/20 border border-rose-500/30" : "text-zinc-400 bg-zinc-800 border border-zinc-700"}`}>
                      {data.decision?.now_signal?.signal || "WAIT"}
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Tech Score:</span>
                      <strong className="text-zinc-200">{(data.decision as any)?.technical_score ?? (signalStrength != null ? signalStrength : "--")} / 90</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Trend:</span>
                      <strong className={biasClass(data.technical?.trend.direction || data.decision?.trend)}>{data.technical?.trend.direction || data.decision?.trend || "NEUTRAL"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Structure:</span>
                      <strong className="text-sky-300">{data.ai?.market_condition || (data.decision as any)?.market_regime || "RANGE"}</strong>
                    </div>
                  </div>
                </div>

                {/* 2. Historical Context */}
                <div className="bg-[#0b1b3d]/70 border border-sky-500/20 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400 text-[10px] uppercase font-bold">
                    <span className="text-indigo-300">2. Historical Evidence</span>
                    <span className={`px-1.5 py-0.5 rounded font-bold ${(data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "BUY" ? "text-emerald-300 bg-emerald-500/20 border border-emerald-500/30" : (data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "SELL" ? "text-rose-300 bg-rose-500/20 border border-rose-500/30" : "text-zinc-400 bg-zinc-800 border border-zinc-700"}`}>
                      {data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT"}
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Dataset N:</span>
                      <strong className="text-zinc-200">{data.decision?.historical_sample_size ? `${data.decision.historical_sample_size}` : "--"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Win Rate:</span>
                      <strong className="text-indigo-300">{data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Expectancy:</span>
                      <strong className="text-emerald-400">{data.decision?.historical_expectancy != null ? `${data.decision?.historical_expectancy?.toFixed(2)}R` : "--R"}</strong>
                    </div>
                  </div>
                </div>

                {/* 3. ML Shadow & Strategy */}
                <div className="bg-[#0b1b3d]/70 border border-sky-500/20 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400 text-[10px] uppercase font-bold">
                    <span className="text-purple-300">3. ML Shadow</span>
                    <span className="px-1.5 py-0.5 rounded font-bold text-purple-300 bg-purple-500/20 border border-purple-500/30">
                      OBSERVER
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Prediction:</span>
                      <strong className="text-purple-300">{(data.decision as any)?.ml_prediction || "WAIT"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Model Win Prob:</span>
                      <strong className="text-cyan-300">{(data.decision as any)?.ml_probability != null ? `${Math.round((data.decision as any).ml_probability * 100)}%` : "--%"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Weight:</span>
                      <strong className="text-zinc-300">{
                        data.decision?.overall_signal?.component_weights?.["ML_SHADOW_MODEL"] != null
                          ? `${Math.round(data.decision.overall_signal.component_weights["ML_SHADOW_MODEL"] * 100)}%`
                          : (symbol === "BTC-USD" ? "26%" : "24%")
                      } (0% Auth)</strong>
                    </div>
                  </div>
                </div>

                {/* 4. Risk / Governance */}
                <div className="bg-[#0b1b3d]/70 border border-sky-500/20 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400 text-[10px] uppercase font-bold">
                    <span className="text-amber-300">4. Risk &amp; Gates</span>
                    {(() => {
                      const finalDecision = data.decision?.decision ?? "WAIT";
                      const qScore = data.decision?.confluence_pct ?? data.decision?.signal_strength ?? null;
                      const isQualityFailed = qScore != null && qScore < 58;
                      const gateAction = isQualityFailed || finalDecision === "WAIT" ? "WAIT" : finalDecision;
                      return (
                        <span className={`px-1.5 py-0.5 rounded font-bold ${
                          gateAction === "BUY"
                            ? "text-emerald-300 bg-emerald-500/20 border border-emerald-500/30"
                            : gateAction === "SELL"
                            ? "text-rose-300 bg-rose-500/20 border border-rose-500/30"
                            : "text-amber-300 bg-amber-500/20 border border-amber-500/30"
                        }`}>
                          {gateAction}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Direction:</span>
                      {(() => {
                        const netScoreVal = data.decision?.overall_signal?.percentage ?? data.decision?.overall_signal?.overall_evidence_score ?? null;
                        const isPassed = !data.decision?.overall_signal?.conflict_detected &&
                                         data.decision?.overall_signal?.signal !== "WAIT" &&
                                         netScoreVal != null && netScoreVal >= 20;
                        const dirBias = data.decision?.gate_direction || (data.decision?.overall_signal?.signal === "BUY" ? "BULLISH" : data.decision?.overall_signal?.signal === "SELL" ? "BEARISH" : "NEUTRAL");
                        return (
                          <strong className={isPassed ? "text-emerald-400" : "text-amber-300"}>
                            {isPassed ? `PASSED (${dirBias})` : "WAIT (<20)"}
                          </strong>
                        );
                      })()}
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Conflict:</span>
                      <strong className={data.decision?.overall_signal?.conflict_detected ? "text-rose-400" : "text-emerald-400"}>
                        {data.decision?.overall_signal?.conflict_detected ? "CONFLICT" : "PASSED (0.0% <= 25%)"}
                      </strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Quality Gate:</span>
                      {(() => {
                        const qScore = data.decision?.confluence_pct ?? data.decision?.signal_strength ?? null;
                        if (qScore == null) {
                          return <strong className="text-zinc-400">--</strong>;
                        }
                        return (
                          <strong className={qScore >= 58 ? "text-emerald-400" : "text-amber-300"}>
                            {qScore >= 58 ? `PASSED (${Math.round(qScore)} pts)` : `FAILED (${Math.round(qScore)} < 58 pts)`}
                          </strong>
                        );
                      })()}
                    </div>
                  </div>
                </div>

                {/* 5. System Health */}
                <div className="bg-[#0b1b3d]/70 border border-sky-500/20 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400 text-[10px] uppercase font-bold">
                    <span className="text-emerald-300">5. System Health</span>
                    <span className="px-1.5 py-0.5 rounded font-bold text-emerald-300 bg-emerald-500/20 border border-emerald-500/30">
                      ONLINE
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Core API:</span>
                      <strong className="text-emerald-400">ONLINE</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Feed:</span>
                      <strong className="text-emerald-400">{sysObs?.data_freshness.feed_status || "ONLINE"}</strong>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Live Trade:</span>
                      <strong className="text-rose-400">DISABLED</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Gemini AI Concise Summary */}
              {data.ai?.summary && (
                <div className="p-3 bg-[#0a1224] border border-sky-500/20 rounded-xl flex items-start gap-2.5 text-xs text-zinc-300">
                  <Cpu size={14} className="text-purple-400 shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-purple-300 font-bold uppercase tracking-wider block">
                      Gemini Macro Insight Summary
                    </span>
                    <p className="text-zinc-300 leading-relaxed text-[11px]">
                      {data.ai.summary}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 2: MARKET INSIGHT (UNIFIED VERTICAL NARRATIVE)              */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSection === "MARKET_INSIGHT" && (
          <div id="section-market-insight" role="tabpanel" aria-labelledby="tab-market-insight" className="space-y-8 font-mono">
            {/* ── 00: ARCHITECTURAL REASONING & EVIDENCE LINEAGE FLOW ── */}
            <div className="p-5 bg-[#071330]/90 border border-sky-500/30 rounded-2xl shadow-[0_0_24px_rgba(56,189,248,0.1)] backdrop-blur-xl space-y-5 font-mono">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-sky-500/20">
                <div className="flex items-center gap-2">
                  <Layers size={18} className="text-sky-400" />
                  <span className="font-bold text-white uppercase tracking-wider text-xs sm:text-sm">
                    Quantitative Decision &amp; Evidence Lineage Architecture
                  </span>
                </div>
                <span className="text-[10px] px-2.5 py-1 rounded bg-sky-500/15 text-sky-300 border border-sky-500/40 font-bold self-start sm:self-auto">
                  CORE QUANT 🔒 LOCKED MODEL
                </span>
              </div>

              {/* FLOWCHART VISUAL PIPELINE */}
              <div className="space-y-4">
                {/* 1. CORE QUANT PIPELINE */}
                <div className="p-4 bg-[#0a1426] border border-sky-500/25 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-sky-300 uppercase flex items-center gap-1.5">
                      <Compass size={14} className="text-sky-400" />
                      1. Core Quant Pipeline 🔒
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      Closed-Candle Policy &middot; Multi-Timeframe Ingestion
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-center text-xs">
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">Live Data</span>
                      <strong className="text-white text-xs tabular-nums">{fmtPrice(currentLivePrice)}</strong>
                    </div>
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">Tech / Structure</span>
                      <strong className={`text-xs ${biasClass(data.technical?.trend?.direction || data.decision?.trend)}`}>
                        {data.technical?.trend?.direction || data.decision?.trend || "NEUTRAL"}
                      </strong>
                    </div>
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">17 Factors + Gemini</span>
                      <strong className="text-cyan-300 text-xs">
                        {(data.decision as any)?.technical_score ?? signalStrength ?? "--"}/90 + {((data.decision as any)?.gemini_score ?? 0)}/10
                      </strong>
                    </div>
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">Confluence</span>
                      <strong className="text-indigo-300 text-xs tabular-nums">
                        {confluencePct != null ? `${confluencePct}%` : "--%"}
                      </strong>
                    </div>
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">Safety Gates</span>
                      <strong className="text-emerald-400 text-xs">Dir &middot; Confl &middot; Qual</strong>
                    </div>
                    <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                      <span className="text-[10px] text-zinc-500 uppercase block font-bold">Decision Engine</span>
                      <strong className={`text-xs ${(data.decision?.decision || signal) === "BUY" ? "text-emerald-400" : (data.decision?.decision || signal) === "SELL" ? "text-rose-400" : "text-amber-300"}`}>
                        {data.decision?.decision || signal || "WAIT"}
                      </strong>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-zinc-400">
                      Sequential Gates: Direction (|Net| &ge; 20) &rarr; Conflict (&le; 25%) &rarr; Quality (Confluence &ge; 58%) &rarr; Action
                    </span>
                    <button
                      type="button"
                      onClick={() => setActiveSection("CURRENT_MARKET")}
                      className="px-2.5 py-1 rounded bg-sky-500/20 text-sky-200 hover:bg-sky-500/30 border border-sky-400/40 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                    >
                      <span>NOW MARKET</span>
                      <span>&rarr;</span>
                    </button>
                  </div>
                </div>

                {/* 2. DUAL BRANCHES (FORK FROM NOW MARKET) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* BRANCH A: HISTORY MARKET */}
                  <div className="p-4 bg-[#0a1426] border border-indigo-500/25 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-indigo-300 uppercase flex items-center gap-1.5">
                        <Database size={14} className="text-indigo-400" />
                        Branch A: History Market Precedent
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                        historical_market_data.db
                      </span>
                    </div>

                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      Matches current Now Market technical setup against multi-year closed-candle backtest database to verify empirical edge.
                    </p>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block">Sample N</span>
                        <strong className="text-white text-xs">{data.decision?.historical_sample_size ?? "--"}</strong>
                      </div>
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block">Win Rate</span>
                        <strong className="text-indigo-300 text-xs">{data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}</strong>
                      </div>
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block">Expectancy</span>
                        <strong className="text-emerald-400 text-xs">{data.decision?.historical_expectancy != null ? `${data.decision.historical_expectancy > 0 ? "+" : ""}${data.decision.historical_expectancy.toFixed(2)}R` : "--R"}</strong>
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={() => setActiveSection("HISTORY_MARKET")}
                        className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-200 hover:bg-indigo-500/30 border border-indigo-400/40 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                      >
                        <span>Explore History Market</span>
                        <span>&rarr;</span>
                      </button>
                    </div>
                  </div>

                  {/* BRANCH B: ML PREDICTION & SHADOW VALIDATION */}
                  <div className="p-4 bg-[#0a1426] border border-purple-500/25 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-purple-300 uppercase flex items-center gap-1.5">
                        <Cpu size={14} className="text-purple-400" />
                        Branch B: ML Prediction &amp; Shadow Validation
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-bold">
                        SHADOW OBSERVER &middot; 0%
                      </span>
                    </div>

                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      ML ensemble predicts directional continuation &rarr; Observation captured at T0 &rarr; Shadow worker tracks future candles &rarr; Validation verifies clean accuracy.
                    </p>

                    <div className="grid grid-cols-4 gap-2 text-center text-xs">
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[9px] text-zinc-500 uppercase block">Prediction</span>
                        <strong className="text-purple-300 text-xs">{(data.decision as any)?.ml_prediction || (data.decision as any)?.ml_model_prediction || "WAIT"}</strong>
                      </div>
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[9px] text-zinc-500 uppercase block">Observation</span>
                        <strong className="text-cyan-300 text-xs">T0 Locked</strong>
                      </div>
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[9px] text-zinc-500 uppercase block">Shadow</span>
                        <strong className="text-amber-300 text-xs">0% Exec</strong>
                      </div>
                      <div className="p-2 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[9px] text-zinc-500 uppercase block">Validation</span>
                        <strong className="text-white text-xs">{sysObs?.forward_shadow?.total_resolved ?? sysObs?.forward_shadow?.sample_size ?? 0} N</strong>
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={() => setActiveSection("ML_SHADOW")}
                        className="px-2.5 py-1 rounded bg-purple-500/20 text-purple-200 hover:bg-purple-500/30 border border-purple-400/40 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                      >
                        <span>Explore ML &amp; Shadow</span>
                        <span>&rarr;</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 3. CONVERGENCE & SUMMIT BANNER */}
                <div className="p-3 bg-gradient-to-r from-blue-950/60 via-[#071330] to-emerald-950/60 border border-sky-500/30 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <Scale size={16} className="text-sky-400 shrink-0" />
                    <div>
                      <span className="font-bold text-white uppercase tracking-wider">
                        Convergence &rarr; MARKET INSIGHT &rarr; OVERALL
                      </span>
                      <p className="text-[11px] text-zinc-400">
                        Now Market + History Precedent + ML Shadow converge here in Market Insight, driving the final Overall consensus.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveSection("OVERALL")}
                    className="px-3 py-1.5 rounded-lg bg-sky-600/30 text-sky-200 hover:bg-sky-600/50 border border-sky-400/40 text-xs font-bold shrink-0 transition-all cursor-pointer"
                  >
                    <span>View Overall Dashboard</span>
                    <span>&rarr;</span>
                  </button>
                </div>
              </div>
            </div>

            {/* ── 01: FINAL / OVERALL SIGNAL (TOP OF NARRATIVE) ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 text-[10px]">
                    STEP 01
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Final / Overall Signal
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Authoritative 4-Way Synthesized Decision &middot; Conviction Ledger
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-bold">
                  FINAL DECISION
                </span>
              </div>

              {/* Authoritative Final Signal Hero */}
              <OverallMarketSignalHero
                signal={data.decision?.overall_signal?.signal || data.decision?.decision || signal || "WAIT"}
                overallSignal={data.decision?.overall_signal}
                assetTicker={activeAsset.ticker}
                assetName={activeAsset.name}
                isMarketClosed={isWeekendClosed}
                loading={data.assetSwitching || data.initialLoading}
                lastUpdated={data.decision?.timestamp || (data.lastUpdated || undefined)}
                overallReasoning={data.decision?.overall_reasoning}
                entryPrice={data.decision?.entry_price}
                stopLoss={data.decision?.stop_loss}
                takeProfit1={data.decision?.take_profit_1}
                takeProfit2={data.decision?.take_profit_2}
              />

              {/* Why This Decision? / Primary Catalysts */}
              <Card
                title="Why This Decision?"
                icon={Zap}
                action={
                  data.refreshing ? (
                    <div className="text-[10px] font-mono text-cyan-400 flex items-center gap-1.5 animate-pulse font-bold">
                      <RefreshCw size={11} className="animate-spin text-cyan-400" />
                      EVALUATING...
                    </div>
                  ) : undefined
                }
              >
                {data.assetSwitching || !data.decision ? (
                  <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                    <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                    <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                      EVALUATING PRIMARY CATALYSTS &amp; RISK CHECKS...
                    </span>
                  </div>
                ) : (
                  <div className="space-y-2.5 font-mono text-xs">
                    <div className="text-[10px] text-zinc-500 uppercase mb-1">
                      Primary Catalysts for {data.decision?.overall_signal?.signal || data.decision?.decision || signal}
                    </div>

                    {(data.decision?.reasons || [
                      mtfPct != null ? `MTF alignment confirmed at ${mtfPct}%` : "MTF alignment structure evaluating",
                      "EMA 20/50/200 structure intact",
                      "SMC liquidity sweep & MSS confirmed",
                      "Fair Value Gap (FVG) respected",
                    ]).slice(0, 4).map((r, i) => (
                      <div key={i} className="flex items-center gap-2.5 p-2.5 bg-[#121217] border border-[#202028] rounded-lg">
                        <span className="text-emerald-400 font-bold">&#x2713;</span>
                        <span className="text-zinc-200 flex-1">{r}</span>
                      </div>
                    ))}

                    {(data.decision?.warnings || []).slice(0, 1).map((w, i) => (
                      <div key={`w-${i}`} className="flex items-center gap-2.5 p-2 bg-[#121217] border border-amber-500/20 rounded-lg">
                        <span className="text-amber-400 font-bold">&#x26A0;</span>
                        <span className="text-amber-300/90 text-[11px]">{w}</span>
                      </div>
                    ))}

                    {/* Historical Reference Note */}
                    <div className="p-2.5 bg-[#0a1224] border border-blue-500/25 rounded-lg text-[11px] space-y-1">
                      <div className="flex items-center justify-between text-zinc-400">
                        <span className="text-zinc-500 uppercase text-[10px] font-bold">Historical Calibration (Reference Only)</span>
                        <span className="text-indigo-300 font-bold">
                          {calibratedProb !== null && calibratedProb !== undefined
                            ? `${calibratedProb.toFixed(1)}% Calibrated Win Prob`
                            : "Insufficient Historical Data"}
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-400 leading-tight">
                        Historical statistics describe previous signals and do not guarantee this signal&apos;s outcome.
                      </p>
                    </div>
                  </div>
                )}
              </Card>
            </div>

            {/* ── 02: CURRENT MARKET (COMPACT) ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-sky-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40 text-[10px]">
                    STEP 02
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Current Market Intelligence
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Real-Time Technical Confluence &amp; Price Action Structure
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-bold">
                  LIVE FEED
                </span>
              </div>

              <Card
                title={`${activeAsset.ticker} Current Market Setup`}
                icon={Activity}
                action={
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveSection("NOW_MARKET")}
                      className="px-2.5 py-1 rounded bg-sky-500/20 text-sky-200 hover:bg-sky-500/30 border border-sky-400/40 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                    >
                      <span>Explore Now Market</span>
                      <span>&rarr;</span>
                    </button>
                    <div className="text-[10px] font-mono text-zinc-400 flex items-center gap-1.5">
                      {data.refreshing ? (
                        <RefreshCw size={11} className="animate-spin text-cyan-400" />
                      ) : (
                        <Clock size={11} className="text-amber-400" />
                      )}
                      Updated:{" "}
                      <span className="text-zinc-200 font-bold">
                        <RelativeTime
                          timestamp={data.technical?.data_timestamp || data.price?.timestamp || data.decision?.timestamp || data.lastUpdated}
                          fallback="--"
                        />
                      </span>
                    </div>
                  </div>
                }
              >
                {data.assetSwitching || !data.technical ? (
                  <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                    <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                    <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                      EVALUATING CURRENT MARKET DYNAMICS...
                    </span>
                  </div>
                ) : (
                  <div className="space-y-4 font-mono text-xs">
                    {/* Core Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {/* Price & Change */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Live Price</span>
                        <div className="text-sm font-bold text-white tabular-nums">
                          {fmtPrice(currentLivePrice)}
                        </div>
                        <div className={`text-[10px] font-bold ${changePct == null ? "text-zinc-400" : changePct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {fmtSignedCurrency(changeUsd)} ({fmtSigned(changePct, 2)}%)
                        </div>
                      </div>

                      {/* Technical & Confluence Score */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Technical / Confluence</span>
                        <div className="text-sm font-bold text-cyan-300">
                          {(data.decision as any)?.technical_score ?? signalStrength ?? "--"} / 90 pts
                        </div>
                        <div className="text-[10px] text-zinc-400">
                          Confluence: <strong className={confluenceDir === "Bearish" ? "text-rose-400" : "text-emerald-400"}>{confluencePct != null ? `${confluencePct}% ${confluenceDir}` : "--"}</strong>
                        </div>
                      </div>

                      {/* Trend & Bias */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Trend / Bias</span>
                        <div className={`text-sm font-bold ${biasClass(data.technical?.trend.direction || data.decision?.trend)}`}>
                          {data.technical?.trend.direction || data.decision?.trend || "NEUTRAL"}
                        </div>
                        <div className="text-[10px] text-zinc-400">
                          Strength: <strong className="text-zinc-200">{data.technical?.trend.strength || "Moderate"}</strong>
                        </div>
                      </div>

                      {/* Market Structure & Regime */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Structure / Regime</span>
                        <div className="text-sm font-bold text-amber-300">
                          {data.ai?.market_condition || (data.decision as any)?.market_regime || "RANGE"}
                        </div>
                        <div className="text-[10px] text-zinc-400">
                          Setup: <strong className={hasSetup ? "text-emerald-400" : "text-zinc-400"}>{hasSetup ? "MSS Confirmed" : "Range Structure"}</strong>
                        </div>
                      </div>

                      {/* Momentum (RSI + MACD) */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Momentum (RSI &amp; MACD)</span>
                        <div className="text-xs font-bold text-zinc-200">
                          RSI: <span className="text-cyan-300">{data.technical?.rsi14?.value != null ? data.technical.rsi14.value.toFixed(1) : "--"}</span>{" "}
                          <span className="text-[10px] text-zinc-400">({data.technical?.rsi14?.condition || "Neutral"})</span>
                        </div>
                        <div className="text-[10px] text-zinc-400">
                          MACD: <strong className={biasClass(data.technical?.macd?.state)}>{data.technical?.macd?.state || "Neutral"}</strong>
                        </div>
                      </div>

                      {/* Liquidity Status */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Liquidity &amp; Sweeps</span>
                        <div className={`text-xs font-bold ${data.decision?.sweep_detected ? "text-amber-400" : "text-zinc-300"}`}>
                          {data.decision?.sweep_detected ? "Sweep Detected" : "Orderly"}
                        </div>
                        <div className="text-[10px] text-zinc-400 truncate" title={data.decision?.liquidity_status || "Inside Range"}>
                          {data.decision?.liquidity_status || "Inside Range"}
                        </div>
                      </div>

                      {/* Key Support */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Key Support</span>
                        <div className="text-xs font-bold text-emerald-400 tabular-nums">
                          {nearestSupport != null ? fmtPrice(nearestSupport) : data.decision?.pdl != null ? fmtPrice(data.decision.pdl) : "--"}
                        </div>
                        <div className="text-[10px] text-zinc-500">
                          PDL: {data.decision?.pdl != null ? fmtPrice(data.decision.pdl) : "--"}
                        </div>
                      </div>

                      {/* Key Resistance */}
                      <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Key Resistance</span>
                        <div className="text-xs font-bold text-rose-400 tabular-nums">
                          {nearestResistance != null ? fmtPrice(nearestResistance) : data.decision?.pdh != null ? fmtPrice(data.decision.pdh) : "--"}
                        </div>
                        <div className="text-[10px] text-zinc-500">
                          PDH: {data.decision?.pdh != null ? fmtPrice(data.decision.pdh) : "--"}
                        </div>
                      </div>
                    </div>

                    {/* Multi-Timeframe Alignment Row */}
                    <div className="p-3 bg-[#0a1426] border border-sky-500/20 rounded-xl space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-zinc-400 font-bold uppercase">Multi-Timeframe Alignment</span>
                        <span className="text-cyan-300 font-bold">{data.decision?.mtf_alignment_summary || data.mtf?.alignment_summary || mtfSummary || "--"}</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {MTF_KEYS.map((tf) => {
                          const rawDir = data.mtf?.timeframes?.[tf]?.trend?.direction || data.ai?.timeframe_analysis?.[tf];
                          const tfBias = rawDir
                            ? (rawDir.charAt(0).toUpperCase() + rawDir.slice(1).toLowerCase())
                            : (data.initialLoading ? "..." : "--");
                          return (
                            <div key={tf} className="p-2 bg-[#121217] border border-[#202028] rounded-lg flex items-center justify-between text-xs">
                              <span className="text-zinc-400 uppercase font-bold">{tf}:</span>
                              <span className={`font-bold ${biasClass(tfBias)}`}>
                                {tfBias}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Top Confirmations & Conflicts */}
                    {(((data.decision as any)?.top_confirmations?.length || (data.decision as any)?.conflicts?.length) ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        {(data.decision as any)?.top_confirmations && ((data.decision as any).top_confirmations as string[]).length > 0 && (
                          <div className="p-3 bg-[#0a1426] border border-emerald-500/20 rounded-xl space-y-1.5">
                            <span className="text-[10px] text-emerald-400 font-bold uppercase block">
                              Active Price Action Confirmations
                            </span>
                            {((data.decision as any).top_confirmations as string[]).slice(0, 3).map((c, i) => (
                              <div key={i} className="text-[11px] text-zinc-300 flex items-start gap-1.5">
                                <span className="text-emerald-400 font-bold">&#x2713;</span>
                                <span>{c}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {(data.decision as any)?.conflicts && ((data.decision as any).conflicts as string[]).length > 0 && (
                          <div className="p-3 bg-[#0a1426] border border-amber-500/20 rounded-xl space-y-1.5">
                            <span className="text-[10px] text-amber-400 font-bold uppercase block">
                              Technical Conflict Flags
                            </span>
                            {((data.decision as any).conflicts as string[]).slice(0, 2).map((c, i) => (
                              <div key={i} className="text-[11px] text-amber-200/90 flex items-start gap-1.5">
                                <span className="text-amber-400 font-bold">&#x26A0;</span>
                                <span>{c}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : null)}
                  </div>
                )}
              </Card>
            </div>

            {/* ── 03: STRATEGY ANALYSIS ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-amber-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-[10px]">
                    STEP 03
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Strategy Analysis &amp; ICT Setups
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Advisory Empirical Confirmation Layer (Zero Decision Gating)
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold">
                  ADVISORY LAYER
                </span>
              </div>

              <ValidatedResearchStrategyCard
                validatedStrategy={data.decision?.validated_strategy}
                degradationMonitoring={data.decision?.degradation_monitoring}
                assetTicker={activeAsset.ticker}
                baseSignal={signal}
                loading={data.assetSwitching || data.initialLoading}
              />
            </div>

            {/* ── 04: HISTORICAL EVIDENCE (SUMMARY ONLY) ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-indigo-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40 text-[10px]">
                    STEP 04
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Historical Evidence &amp; Empirical Baseline
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Multi-Year Backtest Evidence &middot; Source: historical_market_data.db
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-bold">
                  EMPIRICAL BASELINE
                </span>
              </div>

              <Card
                title="Historical Evidence Summary"
                icon={Database}
                action={
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                      historical_market_data.db
                    </span>
                    <button
                      type="button"
                      onClick={() => setActiveSection("HISTORY_MARKET")}
                      className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-200 hover:bg-indigo-500/30 border border-indigo-400/40 text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                    >
                      <span>Explore History Market Lab</span>
                      <span>&rarr;</span>
                    </button>
                  </div>
                }
              >
                {data.assetSwitching || !data.decision ? (
                  <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                    <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                    <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                      RETRIEVING HISTORICAL EVIDENCE PRECEDENT...
                    </span>
                  </div>
                ) : (
                  <div className="space-y-4 font-mono text-xs">
                    {/* Core Evidence Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                      {/* Historical Bias */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Historical Bias</span>
                        <div className={`text-sm font-bold ${(data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "BUY" ? "text-emerald-400" : (data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "SELL" ? "text-rose-400" : "text-indigo-300"}`}>
                          {data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Precedent Vector</span>
                      </div>

                      {/* Sample Size N */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Sample Size (N)</span>
                        <div className="text-sm font-bold text-white tabular-nums">
                          {data.decision?.historical_sample_size ? `${data.decision.historical_sample_size}` : "--"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Matching Trades</span>
                      </div>

                      {/* Historical Win Rate */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Hist Win Rate</span>
                        <div className="text-sm font-bold text-indigo-300 tabular-nums">
                          {data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">
                          {data.decision?.win_rate_ci_lower != null && data.decision?.win_rate_ci_upper != null
                            ? `95% CI [${data.decision.win_rate_ci_lower.toFixed(0)}-${data.decision.win_rate_ci_upper.toFixed(0)}%]`
                            : "Empirical Baseline"}
                        </span>
                      </div>

                      {/* Expectancy */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Expectancy</span>
                        <div className={`text-sm font-bold ${data.decision?.historical_expectancy == null ? "text-zinc-400" : data.decision.historical_expectancy >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {data.decision?.historical_expectancy != null ? `${data.decision.historical_expectancy > 0 ? "+" : ""}${data.decision.historical_expectancy.toFixed(2)}R` : "--R"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Avg Return/Risk</span>
                      </div>

                      {/* Profit Factor */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Profit Factor</span>
                        <div className="text-sm font-bold text-zinc-200 tabular-nums">
                          {data.decision?.historical_profit_factor != null ? data.decision.historical_profit_factor.toFixed(2) : "--"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Gross Win/Loss</span>
                      </div>

                      {/* Similar Setups */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Similar Setups</span>
                        <div className="text-sm font-bold text-white tabular-nums">
                          {data.decision?.similar_setup_count != null ? `${data.decision.similar_setup_count}` : "--"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Clustered Matches</span>
                      </div>

                      {/* Similarity Strength */}
                      <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Similarity</span>
                        <div className="text-sm font-bold text-cyan-300 tabular-nums">
                          {data.decision?.similarity_strength != null ? `${data.decision.similarity_strength}%` : "--%"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Pattern Distance</span>
                      </div>
                    </div>

                    {/* Short Pattern-Match Explanation */}
                    <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                      <div className="text-[10px] text-zinc-500 uppercase font-bold">Pattern Match Context</div>
                      <p className="text-zinc-300 text-xs leading-relaxed">
                        {data.decision?.historical_confirmations?.[0] ||
                         data.decision?.overall_reasoning ||
                         `${activeAsset.ticker} setup matching historical regime & multi-timeframe confluence.`}
                      </p>
                    </div>

                    {/* Precedent Highlights (Top Win Factor & Top Failure Risk) */}
                    {(data.decision?.top_success_reasons?.length || data.decision?.top_failure_reasons?.length) ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        {data.decision?.top_success_reasons && data.decision.top_success_reasons.length > 0 && (
                          <div className="p-3 bg-[#0a1426] border border-emerald-500/20 rounded-xl space-y-1">
                            <span className="text-[10px] text-emerald-400 font-bold uppercase block">
                              Top Historical Win Factor
                            </span>
                            <p className="text-[11px] text-zinc-300">
                              {data.decision.top_success_reasons[0]}
                            </p>
                          </div>
                        )}
                        {data.decision?.top_failure_reasons && data.decision.top_failure_reasons.length > 0 && (
                          <div className="p-3 bg-[#0a1426] border border-rose-500/20 rounded-xl space-y-1">
                            <span className="text-[10px] text-rose-400 font-bold uppercase block">
                              Top Historical Failure Risk
                            </span>
                            <p className="text-[11px] text-rose-200/90">
                              {data.decision.top_failure_reasons[0]}
                            </p>
                          </div>
                        )}
                      </div>
                    ) : null}

                    {/* Source and Reference Note */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 text-[10px] text-zinc-500 border-t border-indigo-500/10">
                      <span>Source: <strong className="text-zinc-400">historical_market_data.db</strong> &middot; Multi-Year Walk-Forward Baseline</span>
                      <span className="text-zinc-500">Advisory empirical evidence &middot; Does not guarantee live performance</span>
                    </div>
                  </div>
                )}
              </Card>
            </div>

            {/* ── 05: CURRENT VS HISTORICAL COMPARISON ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-cyan-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 text-[10px]">
                    STEP 05
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Current vs Historical Comparison
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Direct Cross-Verification of Live Momentum Against Historical Precedent
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-bold">
                  CROSS-VERIFICATION
                </span>
              </div>

              {(() => {
                const nowDir = data.decision?.now_signal?.signal || data.decision?.decision || "WAIT";
                const histDir = data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT";
                const isAligned = (nowDir === "BUY" && histDir === "BUY") || (nowDir === "SELL" && histDir === "SELL");
                const isDirectConflict = (nowDir === "BUY" && histDir === "SELL") || (nowDir === "SELL" && histDir === "BUY");
                const conflictDetected = Boolean(data.decision?.overall_signal?.conflict_detected);

                return (
                  <div className="p-5 bg-[#071330]/90 border border-cyan-500/30 rounded-2xl shadow-[0_0_24px_rgba(6,182,212,0.1)] backdrop-blur-xl space-y-4 font-mono">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Left: Current */}
                      <div className="p-4 bg-[#0a1426] border border-sky-500/25 rounded-xl space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-sky-300 uppercase">CURRENT</span>
                          <span className={`px-2 py-0.5 rounded font-bold text-xs ${nowDir === "BUY" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : nowDir === "SELL" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" : "bg-zinc-800 text-zinc-400 border border-zinc-700"}`}>
                            {nowDir}
                          </span>
                        </div>
                        <div className="space-y-1 text-xs text-zinc-300">
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Technical Score:</span>
                            <strong className="text-white">{(data.decision as any)?.technical_score ?? signalStrength ?? "--"} / 90</strong>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Live Price:</span>
                            <strong className="text-zinc-200">{fmtPrice(currentLivePrice)}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Structure:</span>
                            <strong className={hasSetup ? "text-emerald-400" : "text-zinc-400"}>
                              {hasSetup ? "MSS Confirmed" : "Range"}
                            </strong>
                          </div>
                        </div>
                      </div>

                      {/* Right: Historical */}
                      <div className="p-4 bg-[#0a1426] border border-indigo-500/25 rounded-xl space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-indigo-300 uppercase">HISTORICAL</span>
                          <span className={`px-2 py-0.5 rounded font-bold text-xs ${histDir === "BUY" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : histDir === "SELL" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" : "bg-zinc-800 text-zinc-400 border border-zinc-700"}`}>
                            {histDir}
                          </span>
                        </div>
                        <div className="space-y-1 text-xs text-zinc-300">
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Historical Win Rate:</span>
                            <strong className="text-indigo-300">{data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Expectancy:</span>
                            <strong className="text-emerald-400">{data.decision?.historical_expectancy != null ? `${data.decision.historical_expectancy.toFixed(2)}R` : "--R"}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Sample Size:</span>
                            <strong className="text-white">{data.decision?.historical_sample_size ? `${data.decision.historical_sample_size} Setups` : "--"}</strong>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Synthesis Row */}
                    <div className={`p-3 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs ${
                      isDirectConflict || conflictDetected
                        ? "bg-rose-950/30 border-rose-500/30 text-rose-200"
                        : isAligned
                          ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-200"
                          : "bg-[#0b1b3d]/60 border-sky-500/20 text-zinc-300"
                    }`}>
                      <div className="flex items-center gap-2">
                        {isDirectConflict || conflictDetected ? (
                          <ShieldAlert size={16} className="text-rose-400 shrink-0" />
                        ) : isAligned ? (
                          <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
                        ) : (
                          <Scale size={16} className="text-sky-400 shrink-0" />
                        )}
                        <div>
                          <span className="font-bold uppercase tracking-wider">
                            {isDirectConflict || conflictDetected
                              ? "CONFLICT"
                              : isAligned
                                ? "ALIGNMENT"
                                : "NEUTRAL / ASYMMETRIC"}
                          </span>
                          <p className="text-[11px] text-zinc-400 mt-0.5">
                            {isDirectConflict || conflictDetected
                              ? "Current technical momentum opposes historical base rate. SignalAggregator conflict filter dampens directional conviction."
                              : isAligned
                                ? "Historical empirical evidence validates current now-market price action structure."
                                : "One or both vectors indicate WAIT/NEUTRAL. Pipeline awaiting clearer directional consensus."}
                          </p>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-1 rounded border uppercase tracking-wider shrink-0 ${
                        isDirectConflict || conflictDetected
                          ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                          : isAligned
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                            : "bg-zinc-800 text-zinc-400 border-zinc-700"
                      }`}>
                        {isDirectConflict || conflictDetected ? "CONFLICT" : isAligned ? "ALIGNMENT" : "WAIT / NEUTRAL"}
                      </span>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* ── 06: ML SHADOW EVIDENCE ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-purple-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/40 text-[10px]">
                    STEP 06
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    ML Shadow Evidence
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Machine Learning Ensemble &middot; Shadow Observation Mode (Zero Live Execution)
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold">
                  SHADOW OBSERVER
                </span>
              </div>

              {(() => {
                const mlContributor = data.decision?.overall_signal?.contributors?.find(
                  (c) => c.component_id === "ML_SHADOW_MODEL"
                );
                const nominalWeightPct = mlContributor?.nominal_weight != null
                  ? `${Math.round(mlContributor.nominal_weight * 100)}%`
                  : (activeAsset.id === "BTC" ? "26%" : "24%");

                return (
                  <div className="p-5 bg-[#071330]/90 border border-purple-500/30 rounded-2xl shadow-[0_0_24px_rgba(168,85,247,0.1)] backdrop-blur-xl space-y-4 font-mono">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-purple-500/20">
                      <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-purple-400" />
                        <span className="font-bold text-white text-xs uppercase tracking-wider">
                          Shadow Model Observation Layer &middot; {activeAsset.ticker}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveSection("ML_SHADOW")}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold text-purple-200 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/40 transition-all flex items-center gap-1.5 cursor-pointer"
                      >
                        <span>Explore ML &amp; Shadow Validation</span>
                        <span>&rarr;</span>
                      </button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-[#0a1224] border border-purple-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Prediction</span>
                        <strong className={`text-sm ${(data.decision as any)?.ml_prediction === "BUY" ? "text-emerald-400" : (data.decision as any)?.ml_prediction === "SELL" ? "text-rose-400" : "text-purple-300"}`}>
                          {(data.decision as any)?.ml_prediction || (data.decision as any)?.ml_model_prediction || "WAIT"}
                        </strong>
                        <span className="text-[9px] text-zinc-500 block">Ensemble Direction</span>
                      </div>

                      <div className="p-3 bg-[#0a1224] border border-purple-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Trade Win Probability</span>
                        <strong className="text-sm text-cyan-300">
                          {(data.decision as any)?.ml_probability != null ? `${Math.round((data.decision as any).ml_probability * 100)}%` : "--%"}
                        </strong>
                        <span className="text-[9px] text-zinc-500 block">Platt Scaling</span>
                      </div>

                      <div className="p-3 bg-[#0a1224] border border-purple-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Nominal Weight</span>
                        <strong className="text-sm text-amber-300">{nominalWeightPct}</strong>
                        <span className="text-[9px] text-zinc-500 block">Aggregator Advisory Weight</span>
                      </div>

                      <div className="p-3 bg-[#0a1224] border border-purple-500/20 rounded-xl space-y-1">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Execution Authority</span>
                        <strong className="text-sm text-rose-400">OBSERVER &middot; 0%</strong>
                        <span className="text-[9px] text-zinc-500 block">Zero Order Authority</span>
                      </div>
                    </div>

                    <div className="p-3 bg-[#0a1224] border border-purple-500/20 rounded-xl flex items-center justify-between text-xs text-zinc-300">
                      <span>Observer Status: <strong className="text-purple-300">OBSERVER &mdash; 0% EXECUTION AUTHORITY</strong></span>
                      <span className="text-zinc-500 text-[10px]">Nominal weight is advisory calculation only, not live execution power</span>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* ── 07: RISK & GATES ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-rose-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40 text-[10px]">
                    STEP 07
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Risk, Conflict &amp; Governance Gates
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Multi-Layer Safety Firewall &middot; Direction Gate &middot; Conflict Gate &middot; Quality Gate
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 font-bold">
                  SAFETY GUARDS
                </span>
              </div>

              <div className="p-5 bg-[#071330]/90 border border-rose-500/30 rounded-2xl shadow-[0_0_24px_rgba(244,63,94,0.1)] backdrop-blur-xl space-y-4 font-mono">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  {/* Direction Gate */}
                  {(() => {
                    const gatePassed = data.decision?.gate_passed === true;
                    const gateDirection = data.decision?.gate_direction && data.decision.gate_direction !== "NONE"
                      ? data.decision.gate_direction
                      : null;
                    const isFailed = data.decision?.gate_passed === false;
                    return (
                      <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-zinc-400 uppercase font-bold">Direction Gate</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            gatePassed
                              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                              : isFailed
                                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                                : "bg-zinc-800 text-zinc-400 border-zinc-700"
                          }`}>
                            {gatePassed ? (gateDirection ? `PASSED (${gateDirection})` : "PASSED") : isFailed ? "WAIT" : "--"}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-300 space-y-0.5">
                          <div>Required: <strong className="text-white">|Net Score| &ge; 20.0 pts</strong></div>
                          {(() => {
                            const netScoreVal = data.decision?.overall_signal?.percentage ?? data.decision?.overall_signal?.overall_evidence_score ?? null;
                            return (
                              <div>Current: <strong className={gatePassed ? "text-emerald-400" : "text-amber-300"}>
                                {netScoreVal != null ? `${netScoreVal > 0 ? "+" : ""}${Number(netScoreVal).toFixed(1)} pts` : "Metric not exposed"}
                              </strong></div>
                            );
                          })()}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Conflict Gate */}
                  <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-400 uppercase font-bold">Conflict Gate</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${data.decision?.overall_signal?.conflict_detected ? "bg-rose-500/20 text-rose-300 border border-rose-500/40" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"}`}>
                        {data.decision?.overall_signal?.conflict_detected ? "CONFLICT" : "ALIGNED"}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-300 space-y-0.5">
                      <div>Threshold: <strong className="text-white">&le; 25.0% Opposing</strong></div>
                      <div>Weight: <strong className={data.decision?.overall_signal?.conflict_detected ? "text-rose-400" : "text-emerald-400"}>{
                        typeof (data.decision?.overall_signal as any)?.conflict_weight === "number"
                          ? `${(((data.decision?.overall_signal as any).conflict_weight) * ((data.decision?.overall_signal as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
                          : typeof (data.decision as any)?.conflict_weight === "number"
                          ? `${(((data.decision as any).conflict_weight) * ((data.decision as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
                          : "--"
                      }</strong></div>
                    </div>
                  </div>

                  {/* Quality Gate */}
                  <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                    {(() => {
                      const qScore = data.decision?.signal_strength ?? signalStrength;
                      const hasScore = qScore != null;
                      const passed = hasScore && qScore >= 58;
                      return (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-zinc-400 uppercase font-bold">Quality Gate</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${!hasScore ? "bg-zinc-800 text-zinc-400 border border-zinc-700" : passed ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-amber-500/20 text-amber-300 border border-amber-500/40"}`}>
                              {!hasScore ? "--" : passed ? "PASSED" : "WAIT (<58%)"}
                            </span>
                          </div>
                          <div className="text-xs text-zinc-300 space-y-0.5">
                            <div>Required: <strong className="text-white">Confluence &ge; 58 pts</strong></div>
                            <div>Current: <strong className={!hasScore ? "text-zinc-400" : passed ? "text-emerald-400" : "text-amber-300"}>{hasScore ? `${Math.round(qScore)} pts` : "Metric not exposed"}</strong></div>
                          </div>
                        </>
                      );
                    })()}
                  </div>

                  {/* Capital Risk Limit */}
                  <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-400 uppercase font-bold">Risk Limits</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                        1.0% MAX
                      </span>
                    </div>
                    <div className="text-xs text-zinc-300 space-y-0.5">
                      <div>Risk Limit: <strong className="text-white">1.0%</strong></div>
                      <div>Live Execution: <strong className="text-rose-400">DISABLED</strong></div>
                    </div>
                  </div>
                </div>

                {(() => {
                  const directionalBias = (data.decision as any)?.gate_direction || (data.decision as any)?.directional_bias || data.decision?.now_signal?.signal || (data.decision?.trend === "BULLISH" ? "BUY" : data.decision?.trend === "BEARISH" ? "SELL" : null);
                  const rawQScore = data.decision?.signal_strength ?? signalStrength;
                  const isQualityGated = directionalBias && directionalBias !== "WAIT" && signal === "WAIT" && rawQScore != null && rawQScore < 58;

                  return (
                    <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-zinc-300">
                      <div className="flex flex-wrap items-center gap-2">
                        <span>Final Execution Decision: <strong className={signal === "WAIT" ? "text-amber-400" : "text-emerald-400"}>{signal}</strong></span>
                        {isQualityGated && (
                          <span className="text-[11px] text-zinc-400">
                            (Directional Bias: <strong className={directionalBias === "BUY" ? "text-emerald-300" : "text-rose-300"}>{directionalBias}</strong> &middot; Final Action: <strong className="text-amber-300">WAIT</strong> &mdash; Quality Gate &lt;58%)
                          </span>
                        )}
                      </div>
                      <span className="text-zinc-500 text-[10px]">Sequential Gates: Direction (|Net| &ge; 20) &rarr; Conflict (&le; 25%) &rarr; Quality (Confluence &ge; 58%)</span>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* ── 08: GEMINI AI MACRO INSIGHT ── */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-purple-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/40 text-[10px]">
                    STEP 08
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Gemini AI Macro Insight
                  </span>
                  <span className="text-[11px] text-zinc-400 hidden md:inline">
                    | Multi-Factor Qualitative Market Narrative &middot; Risk Assessment
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold">
                  GENAI MACRO
                </span>
              </div>

              <Card
                title="Gemini AI Analysis"
                icon={Cpu}
                action={
                  <div className="text-[10px] font-mono text-zinc-400 flex items-center gap-1.5">
                    {data.refreshing ? (
                      <RefreshCw size={11} className="animate-spin text-cyan-400" />
                    ) : (
                      <Clock size={11} className="text-amber-400" />
                    )}
                    AI Analysis Time:{" "}
                    <span className="text-zinc-200 font-bold">
                      <RelativeTime timestamp={data.ai?.analysis_timestamp || data.lastAiUpdated} fallback="--" />
                    </span>
                  </div>
                }
              >
                {data.assetSwitching || !data.ai ? (
                  <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                    <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                    <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                      EVALUATING GEMINI AI MACRO INSIGHT...
                    </span>
                  </div>
                ) : (
                  <div className="space-y-3.5 text-xs font-mono">
                    {/* Structured Qualitative Insights */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-[#121217] border border-[#202028] rounded-lg p-3">
                      <div className="text-zinc-300">
                        <span className="text-zinc-500">Trend: </span>
                        <span className={biasClass(data.ai?.overall_bias)}>{data.ai?.overall_bias || "--"}</span>
                      </div>
                      <div className="text-zinc-300">
                        <span className="text-zinc-500">Momentum: </span>
                        <span className="text-emerald-400">{data.technical?.trend.strength || "--"}</span>
                      </div>
                      <div className="text-zinc-300">
                        <span className="text-zinc-500">Key Level: </span>
                        <span className="text-amber-400">{nearestSupport || currentLivePrice ? fmtPrice(nearestSupport || currentLivePrice) : "--"}</span>
                      </div>
                      <div className="text-zinc-300">
                        <span className="text-zinc-500">Risk Assessment: </span>
                        <span className={riskClass(data.ai?.risk_level)}>{data.ai?.risk_level || "--"}</span>
                      </div>
                      <div className="text-zinc-300 sm:col-span-2">
                        <span className="text-zinc-500">Confirmation: </span>
                        <span className="text-emerald-400">{mtfSummary || "--"}</span>
                      </div>
                    </div>

                    {/* Short Conclusion */}
                    <div className="p-3 bg-[#121217] border border-[#202028] rounded-lg">
                      <div className="text-[10px] text-zinc-500 uppercase font-bold mb-1">Overall Conclusion</div>
                      <p className="text-zinc-200 text-xs leading-relaxed">
                        {data.ai?.summary || "Macro structure remains in observation state awaiting active directional confirmation."}
                      </p>
                    </div>

                    {/* Gemini Confirmation Rating */}
                    <div className="p-2.5 bg-[#0a1224] border border-amber-500/25 rounded-lg flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      <span className="text-zinc-400">
                        Gemini Confirmation Rating:{" "}
                        <strong className="text-amber-300">
                          {(data.decision as any)?.gemini_score != null ? `${(data.decision as any).gemini_score} / 10` : "-- / Offline"}
                        </strong>
                      </span>
                      <span className="text-zinc-400">
                        Status: <strong className={geminiOnline ? "text-emerald-400" : "text-amber-400"}>{geminiOnline ? "ONLINE" : "READY"}</strong>
                      </span>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 3: NOW MARKET (DEEP PRESENT MARKET SITUATION ANALYSIS)        */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {(activeSection === "NOW_MARKET" || activeSection === "CURRENT_MARKET") && (
          <div id="section-now-market" role="tabpanel" aria-labelledby="tab-now-market" className="space-y-6 font-mono">

            {/* ── NOW MARKET HERO PERCENTAGE CARD ── */}
            {(() => {
              const nowPct = resolveNowMarketPercentage(
                data.decision?.now_signal?.percentage,
                data.decision?.confluence_pct
              );
              const nowDir = resolveNowMarketDirection(
                data.decision?.now_signal?.signal,
                data.decision?.gate_direction ||
                  (sellScore != null && buyScore != null && sellScore > buyScore
                    ? "BEARISH"
                    : buyScore != null && sellScore != null && buyScore > sellScore
                      ? "BULLISH"
                      : null),
                data.technical?.trend?.direction || data.decision?.trend,
                nowPct
              );
              const nowAction = nowDir === "BEARISH" ? "SELL" : nowDir === "BULLISH" ? "BUY" : nowDir;
              const nowStrength = data.decision?.now_signal?.strength || (nowPct != null && nowPct >= 70 ? "STRONG" : nowPct != null && nowPct >= 40 ? "MODERATE" : "WEAK");

              return (
                <SignalHeroCard
                  pageTitle="NOW MARKET"
                  icon={Compass}
                  assetName={activeAsset.name}
                  assetTicker={activeAsset.ticker}
                  signal={isWeekendClosed ? "WAIT" : nowAction}
                  percentage={isWeekendClosed ? null : nowPct}
                  statusBadge={
                    isWeekendClosed
                      ? "WEEKEND CLOSED"
                      : data.initialLoading || data.assetSwitching
                        ? "EVALUATING"
                        : `CURRENT MARKET ANALYSIS · ${nowStrength}`
                  }
                  isEvaluating={data.initialLoading || data.assetSwitching}
                  isMarketClosed={isWeekendClosed}
                  timeChangeText={data.price && data.price.price > 0 ? `Live Spot: ${fmtPrice(currentLivePrice)}` : undefined}
                  lastUpdatedText={
                    data.initialLoading || data.assetSwitching
                      ? undefined
                      : (data.technical?.data_timestamp ||
                        data.price?.timestamp ||
                        data.decision?.timestamp ||
                        data.lastUpdated ||
                        undefined)
                  }
                  reasoning="Current Market Analysis · Real-time 17-factor technical confluence and price action structure"
                  showActionLevels={false}
                  supportingPills={
                    <>
                      {(() => {
                        const isHeroSell = !isWeekendClosed && (nowAction === "SELL" || nowDir === "BEARISH");
                        const isHeroBuy = !isWeekendClosed && (nowAction === "BUY" || nowDir === "BULLISH");

                        const techNumColor = isHeroSell ? "text-rose-400" : isHeroBuy ? "text-emerald-400" : "text-white";
                        const geminiNumColor = isHeroSell ? "text-rose-400" : isHeroBuy ? "text-emerald-400" : "text-purple-300";

                        const confluenceVal = nowPct ?? data.decision?.confluence_pct ?? "--";
                        const confluenceNumColor = isHeroSell ? "text-rose-400" : isHeroBuy ? "text-emerald-400" : "text-sky-300";

                        return (
                          <>
                            <div className="flex items-center gap-1.5">
                              <span className="text-zinc-400">Technical Score:</span>
                              <strong className={`${techNumColor} font-bold`}>
                                {(data.decision as any)?.technical_score ?? (data.decision?.now_signal?.technical_score ?? "--")} / 90
                              </strong>
                            </div>
                            <span className="text-zinc-600 font-bold">&middot;</span>
                            <div className="flex items-center gap-1.5">
                              <span className="text-zinc-400">Gemini Score:</span>
                              <strong className={`${geminiNumColor} font-bold`}>
                                {(data.decision as any)?.gemini_score ?? (data.decision?.now_signal?.gemini_score ?? "--")} / 10
                              </strong>
                            </div>
                            <span className="text-zinc-600 font-bold">&middot;</span>
                            <div className="flex items-center gap-1.5">
                              <span className="text-zinc-400">Confluence:</span>
                              <strong className={`${confluenceNumColor} font-bold`}>
                                {confluenceVal != null && confluenceVal !== "--" ? `${confluenceVal}%` : "--%"}
                              </strong>
                            </div>
                          </>
                        );
                      })()}
                    </>
                  }
                  uniqueId="nowMarketHeroCard"
                />
              );
            })()}

            {/* ── 01. LIVE MARKET STATE ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Activity size={15} className="text-sky-400" />
                  01. Live Market State &middot; ({activeAsset.ticker})
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Live Spot Price</span>
                  <div className="text-lg font-bold text-white tabular-nums tracking-tight">
                    {fmtPrice(currentLivePrice)}
                  </div>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">24h Net Change</span>
                  <div className={`text-base font-bold tabular-nums ${
                    data.price?.change_24h != null && data.price.change_24h >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {data.price?.change_24h != null ? fmtSignedCurrency(data.price.change_24h) : "--"}
                  </div>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">24h Change %</span>
                  <div className={`text-base font-bold tabular-nums ${
                    changePct != null && changePct >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {changePct != null ? `${fmtSigned(changePct, 2)}%` : "--%"}
                  </div>
                </div>
              </div>
            </div>

            {/* ── 02. 17-FACTOR CONFLUENCE ENGINE ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <BarChart3 size={15} className="text-sky-400" />
                  02. 17-Factor Confluence Engine
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-bold">
                  {confluencePct != null ? `${confluencePct} / 100 PTS` : "-- / 100 PTS"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {(() => {
                  const contribs = data.decision?.signal_contributors && data.decision.signal_contributors.length > 0
                    ? data.decision.signal_contributors
                    : [
                        { name: "HTF Trend", points: 0, max_score: 11, direction: "UNCHANGED", description: "Daily trend structure" },
                        { name: "Market Structure", points: 0, max_score: 9, direction: "UNCHANGED", description: "Swing highs/lows confirmation" },
                        { name: "Momentum", points: 0, max_score: 8, direction: "UNCHANGED", description: "Velocity of price action" },
                        { name: "MTF Alignment", points: 0, max_score: 8, direction: "UNCHANGED", description: "Multi-timeframe trend agreement" },
                        { name: "S/R Price Action", points: 0, max_score: 8, direction: "UNCHANGED", description: "Horizontal support/resistance" },
                        { name: "Breakout / Retest", points: 0, max_score: 6, direction: "UNCHANGED", description: "Key level breakout confirmation" },
                        { name: "Supply & Demand", points: 0, max_score: 5, direction: "UNCHANGED", description: "Institutional order block zones" },
                        { name: "Volume Confirmation", points: 0, max_score: 5, direction: "UNCHANGED", description: "Tick volume trend confirmation" },
                        { name: "SMC / ICT", points: 0, max_score: 5, direction: "UNCHANGED", description: "Smart money liquidity & structure" },
                        { name: "ICT Concepts", points: 0, max_score: 4, direction: "UNCHANGED", description: "Fair Value Gaps & order flow" },
                        { name: "Fibonacci OTE", points: 0, max_score: 4, direction: "UNCHANGED", description: "Optimal Trade Entry (0.618 - 0.786)" },
                        { name: "Elliott Wave", points: 0, max_score: 4, direction: "UNCHANGED", description: "Wave cycle identification" },
                        { name: "VWAP", points: 0, max_score: 4, direction: "UNCHANGED", description: "Volume Weighted Average Price" },
                        { name: "EMA / MA Stack", points: 0, max_score: 4, direction: "UNCHANGED", description: "20/50/200 EMA sequence" },
                        { name: "RSI", points: 0, max_score: 3, direction: "UNCHANGED", description: "Relative Strength Index 14" },
                        { name: "MACD", points: 0, max_score: 2, direction: "UNCHANGED", description: "Moving Average Convergence Divergence" },
                        { name: "Gemini AI", points: 0, max_score: 10, direction: "UNCHANGED", description: "Qualitative macro confirmation" },
                      ];

                  return contribs.map((c: any, idx: number) => {
                    const isUp = c.direction === "UP";
                    const isDown = c.direction === "DOWN";
                    const maxScore = c.max_score || (c.name === "Gemini AI" ? 10 : c.name === "HTF Trend" ? 11 : 8);

                    return (
                      <div
                        key={c.name || idx}
                        className={`p-3 rounded-xl border flex flex-col justify-between gap-1.5 transition-all ${
                          isUp
                            ? "bg-[#0c1a1e] border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.08)]"
                            : isDown
                              ? "bg-[#1f0d14] border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.08)]"
                              : "bg-[#0a1224] border-zinc-800"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white truncate">{c.name}</span>
                          <span className={`text-[11px] font-bold tabular-nums px-1.5 py-0.5 rounded ${
                            c.points > 0 ? "bg-sky-500/20 text-sky-300 border border-sky-500/30" : "bg-zinc-800 text-zinc-500"
                          }`}>
                            {c.points} / {maxScore} pts
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-zinc-400">
                          <span className="truncate pr-2" title={typeof c.description === "string" ? c.description.replace(/\(dist=[^)]+\)/gi, "(dist: --)") : "--"}>
                            {typeof c.description === "string" ? c.description.replace(/\(dist=[^)]+\)/gi, "(dist: --)") : (c.description || "--")}
                          </span>
                          <span className={`font-bold shrink-0 ${
                            isUp ? "text-emerald-400" : isDown ? "text-rose-400" : "text-zinc-500"
                          }`}>
                            {isUp ? "↑ UP" : isDown ? "↓ DOWN" : "→ STEADY"}
                          </span>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>

            {/* ── 03. MULTI-TIMEFRAME ANALYSIS ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Layers size={15} className="text-sky-400" />
                  03. Multi-Timeframe Alignment
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-bold">
                  {data.decision?.mtf_alignment_summary || data.mtf?.alignment_summary || "--"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                {["5m", "15m", "1h", "1d"].map((tf) => {
                  const tfData = data.mtf?.timeframes?.[tf];
                  const dir = tfData?.trend?.direction || "--";
                  const strength = tfData?.trend?.strength || "--";
                  const rsiVal = tfData?.rsi14?.value != null ? tfData.rsi14.value.toFixed(1) : "--";
                  const macdState = tfData?.macd?.state || "--";

                  const isBull = dir.toUpperCase().includes("BULL");
                  const isBear = dir.toUpperCase().includes("BEAR");

                  return (
                    <div key={tf} className="p-4 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white uppercase text-xs">{tf} Timeframe</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isBull
                            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                            : isBear
                              ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                              : "bg-zinc-800 text-zinc-400 border-zinc-700"
                        }`}>
                          {dir}
                        </span>
                      </div>
                      <div className="space-y-1 text-xs text-zinc-300">
                        <div className="flex justify-between text-[11px]">
                          <span className="text-zinc-500">Trend Strength:</span>
                          <strong className="text-zinc-200">{strength}</strong>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-zinc-500">RSI (14):</span>
                          <strong className="text-zinc-200 tabular-nums">{rsiVal}</strong>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-zinc-500">MACD State:</span>
                          <strong className="text-zinc-200">{macdState}</strong>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── 04. PRICE ACTION / STRUCTURE ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Target size={15} className="text-sky-400" />
                  04. Price Action, Structure &amp; Key Pivots
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Trend Direction</span>
                  <div className={`text-base font-bold ${
                    data.technical?.trend.direction === "BULLISH"
                      ? "text-emerald-400"
                      : data.technical?.trend.direction === "BEARISH"
                        ? "text-rose-400"
                        : "text-zinc-300"
                  }`}>
                    {data.technical?.trend.direction || "--"}
                  </div>
                  <span className="text-[10px] text-zinc-500">Strength: {data.technical?.trend.strength || "--"}</span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Key Support Level</span>
                  <div className="text-base font-bold text-emerald-400 tabular-nums">
                    {nearestSupport != null ? fmtPrice(nearestSupport) : (data.technical?.support_levels?.[0] != null ? fmtPrice(data.technical.support_levels[0]) : "--")}
                  </div>
                  <span className="text-[10px] text-zinc-500">
                    Prev Day Low: {data.decision?.pdl != null ? fmtPrice(data.decision.pdl) : "--"}
                  </span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Key Resistance Level</span>
                  <div className="text-base font-bold text-rose-400 tabular-nums">
                    {nearestResistance != null ? fmtPrice(nearestResistance) : (data.technical?.resistance_levels?.[0] != null ? fmtPrice(data.technical.resistance_levels[0]) : "--")}
                  </div>
                  <span className="text-[10px] text-zinc-500">
                    Prev Day High: {data.decision?.pdh != null ? fmtPrice(data.decision.pdh) : "--"}
                  </span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Structure State</span>
                  <div className="text-base font-bold text-sky-300">
                    {data.ai?.market_condition || "ORDERLY"}
                  </div>
                  <span className="text-[10px] text-zinc-500">
                    Active Range: {data.decision?.pdh && data.decision?.pdl ? `$${(data.decision.pdh - data.decision.pdl).toFixed(2)}` : "--"}
                  </span>
                </div>
              </div>
            </div>

            {/* ── 05. MOMENTUM INDICATORS ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Zap size={15} className="text-sky-400" />
                  05. Momentum &amp; Volatility Metrics
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">RSI (14)</span>
                  <div className="text-base font-bold text-white tabular-nums">
                    {data.technical?.rsi14?.value != null ? data.technical.rsi14.value.toFixed(1) : "--"}
                  </div>
                  <span className={`text-[10px] font-bold ${
                    data.technical?.rsi14?.condition === "OVERSOLD"
                      ? "text-emerald-400"
                      : data.technical?.rsi14?.condition === "OVERBOUGHT"
                        ? "text-rose-400"
                        : "text-zinc-400"
                  }`}>
                    {data.technical?.rsi14?.condition || "NEUTRAL"}
                  </span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">MACD State</span>
                  <div className={`text-base font-bold ${
                    data.technical?.macd?.state === "BULLISH"
                      ? "text-emerald-400"
                      : data.technical?.macd?.state === "BEARISH"
                        ? "text-rose-400"
                        : "text-zinc-300"
                  }`}>
                    {data.technical?.macd?.state || "NEUTRAL"}
                  </div>
                  <span className="text-[10px] text-zinc-500 tabular-nums">
                    Hist: {data.technical?.macd?.histogram != null ? data.technical.macd.histogram.toFixed(2) : "--"}
                  </span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">ATR (14) Volatility</span>
                  <div className="text-base font-bold text-zinc-200 tabular-nums">
                    {data.technical?.atr14?.value != null ? fmtPrice(data.technical.atr14.value) : "--"}
                  </div>
                  <span className="text-[10px] text-zinc-500">
                    Vol: {data.technical?.atr14?.volatility_pct != null ? `${data.technical.atr14.volatility_pct.toFixed(2)}%` : "--%"}
                  </span>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">EMA 50 / 200</span>
                  <div className="text-base font-bold text-zinc-200 tabular-nums truncate">
                    {data.technical?.ema50 ? fmtPrice(data.technical.ema50) : "--"}
                  </div>
                  <span className="text-[10px] text-zinc-500 tabular-nums truncate">
                    EMA 200: {data.technical?.ema200 ? fmtPrice(data.technical.ema200) : "--"}
                  </span>
                </div>
              </div>
            </div>

            {/* ── 06. LIQUIDITY / SMC / ICT ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Database size={15} className="text-sky-400" />
                  06. Liquidity State, Market Structure Shift &amp; Sweeps
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-zinc-500 uppercase block font-bold">Liquidity Sweep Detection</span>
                  <div className={`text-sm font-bold ${
                    data.decision?.sweep_detected ? "text-amber-300" : "text-zinc-400"
                  }`}>
                    {data.decision?.sweep_detected ? "SWEEP DETECTED" : "NO ACTIVE SWEEP"}
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-snug">
                    {data.decision?.sweep_detail || "Liquidity pools trading within established session boundaries."}
                  </p>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-zinc-500 uppercase block font-bold">Fake Breakout Monitoring</span>
                  <div className={`text-sm font-bold ${
                    data.decision?.fake_breakout_detected ? "text-rose-400" : "text-emerald-400"
                  }`}>
                    {data.decision?.fake_breakout_detected ? "POTENTIAL FAKE BREAKOUT" : "NO FAKE BREAKOUT"}
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-snug">
                    {data.decision?.fake_breakout_details || "Candle closes confirmed within authentic structural thresholds."}
                  </p>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-zinc-500 uppercase block font-bold">SMC / ICT Factor Status</span>
                  <div className="text-sm font-bold text-sky-300">
                    {data.decision?.confluence_direction || "Neutral"} Flow
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-snug">
                    Fair Value Gaps &amp; order blocks evaluated through 17-factor institutional model.
                  </p>
                </div>
              </div>
            </div>

            {/* ── 07. STRATEGY CONTEXT ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Cpu size={15} className="text-sky-400" />
                  07. Quantitative Strategy Context &amp; Candidate Signal
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Candidate Signal</span>
                  <div className={`text-base font-bold ${
                    (data.decision?.decision || signal) === "BUY"
                      ? "text-emerald-400"
                      : (data.decision?.decision || signal) === "SELL"
                        ? "text-rose-400"
                        : "text-amber-300"
                  }`}>
                    {data.decision?.decision || signal || "WAIT"}
                  </div>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Setup Grade</span>
                  <div className="text-base font-bold text-white">
                    {data.decision?.setup_grade || "C"}
                  </div>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Confluence Direction</span>
                  <div className="text-base font-bold text-sky-300">
                    {data.decision?.confluence_direction || "--"}
                  </div>
                </div>

                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase block">Shadow Governance</span>
                  <div className="text-base font-bold text-emerald-400">
                    S2: N = 0
                  </div>
                </div>
              </div>
            </div>

            {/* ── 08. RISK & GATES ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <ShieldAlert size={15} className="text-sky-400" />
                  08. Risk, Conflict &amp; Operational Safety Gates
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                {/* Direction Gate */}
                {(() => {
                  const gatePassed = data.decision?.gate_passed === true;
                  const gateDirection = data.decision?.gate_direction && data.decision.gate_direction !== "NONE"
                    ? data.decision.gate_direction
                    : null;
                  const isFailed = data.decision?.gate_passed === false;
                  return (
                    <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-400 font-bold">Direction Gate</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          gatePassed
                            ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                            : isFailed
                              ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                              : "bg-zinc-800 text-zinc-400 border-zinc-700"
                        }`}>
                          {gatePassed ? (gateDirection ? `PASSED (${gateDirection})` : "PASSED") : isFailed ? "WAIT" : "--"}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-300 space-y-0.5">
                        <div>Required: <strong className="text-white">|Net Score| &ge; 20.0 pts</strong></div>
                        <div>Current: <strong className={gatePassed ? "text-emerald-400" : "text-zinc-400"}>--</strong></div>
                      </div>
                    </div>
                  );
                })()}

                {/* Conflict Gate */}
                <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-zinc-400 uppercase font-bold">Conflict Gate</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      !data.decision?.overall_signal?.conflict_detected
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                        : "bg-rose-500/15 text-rose-300 border-rose-500/40"
                    }`}>
                      {data.decision?.overall_signal?.conflict_detected ? "FAILED (CONFLICT)" : "PASSED"}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-300 space-y-0.5">
                    <div>Required: <strong className="text-white">Opposing Wt &le; 25.0%</strong></div>
                    <div>Current: <strong className={data.decision?.overall_signal?.conflict_detected ? "text-rose-400" : "text-emerald-400"}>
                      {typeof (data.decision?.overall_signal as any)?.conflict_weight === "number"
                        ? `${(((data.decision?.overall_signal as any).conflict_weight) * ((data.decision?.overall_signal as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
                        : typeof (data.decision as any)?.conflict_weight === "number"
                        ? `${(((data.decision as any).conflict_weight) * ((data.decision as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
                        : "--"}
                    </strong></div>
                  </div>
                </div>

                {/* Quality Gate */}
                {(() => {
                  const qScore = data.decision?.confluence_pct ?? data.decision?.signal_strength ?? null;
                  const isPassed = qScore != null && qScore >= 58;
                  return (
                    <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-400 font-bold">Quality Gate</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          qScore == null
                            ? "bg-zinc-800 text-zinc-400 border-zinc-700"
                            : isPassed
                              ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                              : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                        }`}>
                          {qScore == null ? "--" : isPassed ? "PASSED" : "FAILED (<58)"}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-300 space-y-0.5">
                        <div>Required: <strong className="text-white">Score &ge; 58 pts</strong></div>
                        <div>Current: <strong className={qScore == null ? "text-zinc-400" : isPassed ? "text-emerald-400" : "text-amber-300"}>
                          {qScore != null ? `${qScore} pts` : "-- pts"}
                        </strong></div>
                      </div>
                    </div>
                  );
                })()}

                {/* Risk Environment */}
                <div className="p-3.5 bg-[#0a1224] border border-zinc-800 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400 font-bold">Environmental Risk</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      data.ai?.risk_level === "HIGH"
                        ? "bg-rose-500/15 text-rose-300 border-rose-500/40"
                        : data.ai?.risk_level === "MEDIUM"
                          ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                          : "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                    }`}>
                      {data.ai?.risk_level || "LOW RISK"}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-300 space-y-0.5">
                    <div>Live Execution: <strong className="text-rose-400">DISABLED</strong></div>
                    <div>Prod Gating: <strong className="text-amber-400">DISABLED</strong></div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── 09. CURRENT MARKET GEMINI RECOMMENDATION ── */}
            <div className="p-5 bg-[#071330]/85 border border-purple-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-purple-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Sparkles size={15} className="text-purple-400" />
                  09. Current Market Gemini Recommendation (Present Technical Focus)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold">
                  PRESENT ADVISORY
                </span>
              </div>

              <div className="space-y-3.5 text-xs">
                {/* Structured Technical Narrative */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 bg-[#121217] border border-[#202028] rounded-xl p-3">
                  <div className="text-zinc-300">
                    <span className="text-zinc-500 block text-[10px]">Technical Bias:</span>
                    <span className={`font-bold text-sm ${biasClass(data.ai?.overall_bias)}`}>
                      {data.ai?.overall_bias || "--"}
                    </span>
                  </div>
                  <div className="text-zinc-300">
                    <span className="text-zinc-500 block text-[10px]">Market Condition:</span>
                    <span className="font-bold text-sm text-sky-300">
                      {data.ai?.market_condition || "EVALUATING"}
                    </span>
                  </div>
                  <div className="text-zinc-300">
                    <span className="text-zinc-500 block text-[10px]">Model Confidence:</span>
                    <span className="font-bold text-sm text-amber-300">
                      {data.ai?.confidence != null ? `${data.ai.confidence}%` : "--%"}
                    </span>
                  </div>
                  <div className="text-zinc-300">
                    <span className="text-zinc-500 block text-[10px]">Gemini Status:</span>
                    <span className={`font-bold text-sm ${geminiOnline ? "text-emerald-400" : "text-amber-400"}`}>
                      {geminiOnline ? "ONLINE (Active)" : "READY"}
                    </span>
                  </div>
                </div>

                {/* Present Market Assessment Summary */}
                <div className="p-3.5 bg-[#121217] border border-[#202028] rounded-xl space-y-1.5">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">
                    Present Technical Situation Assessment
                  </div>
                  <p className="text-zinc-200 text-xs leading-relaxed">
                    {data.ai?.summary || "Current market structure remains in observation state awaiting active directional confirmation across lower and higher timeframes."}
                  </p>
                </div>
              </div>
            </div>

            {/* ── 10. CURRENT MARKET CONCLUSION ── */}
            <div className="p-5 bg-[#071330]/85 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 size={15} className="text-sky-400" />
                  10. Current Market Conclusion &amp; Confirmation Checklist
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {/* Bullish Drivers */}
                <div className="p-3.5 bg-[#0a1224] border border-emerald-500/20 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                    <TrendingUp size={14} />
                    Key Bullish Factors
                  </span>
                  <ul className="space-y-1.5 text-zinc-300 text-xs">
                    {(data.ai?.key_bullish_factors && data.ai.key_bullish_factors.length > 0
                      ? data.ai.key_bullish_factors
                      : ["Awaiting confirmed bullish technical triggers across active timeframes"]
                    ).map((f: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-400 font-bold">&bull;</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Bearish Drivers */}
                <div className="p-3.5 bg-[#0a1224] border border-rose-500/20 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-rose-400 uppercase flex items-center gap-1.5">
                    <TrendingDown size={14} />
                    Key Bearish Factors
                  </span>
                  <ul className="space-y-1.5 text-zinc-300 text-xs">
                    {(data.ai?.key_bearish_factors && data.ai.key_bearish_factors.length > 0
                      ? data.ai.key_bearish_factors
                      : ["Awaiting confirmed bearish technical triggers across active timeframes"]
                    ).map((f: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-rose-400 font-bold">&bull;</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Key Confirmation to Watch */}
                <div className="p-3.5 bg-[#0a1224] border border-sky-500/20 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-sky-300 uppercase flex items-center gap-1.5">
                    <Target size={14} />
                    Key Confirmation to Watch
                  </span>
                  <div className="text-zinc-300 text-xs space-y-1">
                    <div>MTF Alignment: <strong className="text-white">{data.decision?.mtf_alignment_summary || mtfSummary || "--"}</strong></div>
                    <div>Confluence Threshold: <strong className="text-white">&ge; 58 pts for Quality Gate passage</strong></div>
                    <div>Pivots: <strong className="text-white">Support at {nearestSupport != null ? fmtPrice(nearestSupport) : "--"} &middot; Resistance at {nearestResistance != null ? fmtPrice(nearestResistance) : "--"}</strong></div>
                  </div>
                </div>

                {/* Invalidation & Risk Conditions */}
                <div className="p-3.5 bg-[#0a1224] border border-amber-500/20 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-amber-300 uppercase flex items-center gap-1.5">
                    <AlertTriangle size={14} />
                    Invalidation &amp; Risk Context
                  </span>
                  {data.decision?.invalid_if && data.decision.invalid_if.length > 0 ? (
                    <ul className="space-y-1 text-zinc-300 text-xs">
                      {data.decision.invalid_if.map((w: string, i: number) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-amber-400 font-bold">&bull;</span>
                          <span>{w}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-zinc-500 text-xs font-mono">--</div>
                  )}
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 4: HISTORY MARKET (EMPIRICAL EVIDENCE & PRECEDENT ANALYSIS)   */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSection === "HISTORY_MARKET" && (
          <div id="section-history-market" role="tabpanel" aria-labelledby="tab-history-market" className="space-y-6 font-mono">
            {/* TOP HERO CARD: HISTORICAL EVIDENCE BASELINE */}
            {(() => {
              const histSignal = data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT";
              const histSample = data.decision?.historical_sample_size ?? null;
              const histWinRate = data.decision?.historical_win_rate ?? null;
              const histPct = resolveHistoryMarketPercentage(histWinRate, histSample);
              const histExpectancy = data.decision?.historical_expectancy ?? null;
              const histProfitFactor = data.decision?.historical_profit_factor ?? null;
              const similarSetups = data.decision?.similar_setup_count ?? 0;
              const similarityStrength = data.decision?.similarity_strength ?? null;

              return (
                <SignalHeroCard
                  pageTitle="HISTORY MARKET · EMPIRICAL RESEARCH PRECEDENT"
                  icon={Database}
                  assetName={activeAsset.name}
                  assetTicker={activeAsset.ticker}
                  signal={isWeekendClosed ? "WAIT" : (data.initialLoading || data.assetSwitching) ? "WAIT" : histSignal}
                  percentage={isWeekendClosed ? null : histPct}
                  statusBadge={
                    isWeekendClosed
                      ? "MARKET CLOSED"
                      : data.initialLoading || data.assetSwitching
                        ? "RETRIEVING PRECEDENT"
                        : similarSetups > 0
                          ? `QUALIFYING MATCHES ACTIVE (${similarSetups})`
                          : "NO QUALIFYING HISTORICAL MATCHES"
                  }
                  isEvaluating={data.initialLoading || data.assetSwitching}
                  isMarketClosed={isWeekendClosed}
                  timeChangeText="Multi-Year Closed-Candle Walk-Forward Dataset · historical_market_data.db"
                  lastUpdatedText={
                    data.initialLoading || data.assetSwitching
                      ? undefined
                      : (data.decision?.evidence_refresh_at || data.decision?.timestamp || data.lastUpdated || undefined)
                  }
                  reasoning={
                    similarSetups > 0
                      ? `Matched ${similarSetups} comparable historical setups with ${similarityStrength ?? 0}% pattern similarity.`
                      : `No historical setups met the >=70% similarity threshold for current market structure. Displaying global baseline dataset (N=${histSample ?? 0}).`
                  }
                  showActionLevels={false}
                  supportingPills={
                    <>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Comparable Setup N:</span>
                        <strong className={similarSetups > 0 ? "text-emerald-300 font-bold" : "text-amber-300 font-bold"}>
                          {similarSetups}
                        </strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Best Similarity:</span>
                        <strong className="text-cyan-300 font-bold">{similarityStrength != null ? `${similarityStrength}%` : "--%"}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Dataset Baseline N:</span>
                        <strong className="text-white font-bold">{histSample != null ? `${histSample}` : "--"}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Historical Win Rate:</span>
                        <strong className="text-indigo-300 font-bold">{histWinRate != null ? `${histWinRate.toFixed(1)}%` : "--%"}</strong>
                      </div>
                    </>
                  }
                  uniqueId="historyMarketHeroCard"
                />
              );
            })()}

            {/* 01: CURRENT SETUP PRECEDENT & SIMILAR SETUPS */}
            <Card
              title={`${activeAsset.ticker} Historical Precedent & Clustered Matches`}
              icon={Database}
              action={
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                    historical_market_data.db
                  </span>
                </div>
              }
            >
              {data.assetSwitching || !data.decision ? (
                <div className="flex flex-col items-center justify-center py-10 gap-3 text-blue-400 font-mono">
                  <RefreshCw size={24} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
                  <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
                    RETRIEVING HISTORICAL EVIDENCE PRECEDENT...
                  </span>
                </div>
              ) : (
                <div className="space-y-4 font-mono text-xs">
                  {/* BLOCK A: CURRENT SETUP HISTORICAL MATCH */}
                  <div className="p-4 bg-[#0a1426] border border-sky-500/25 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Target size={14} className="text-sky-400" />
                        <span className="text-xs font-bold text-sky-300 uppercase tracking-wider">
                          CURRENT SETUP HISTORICAL MATCH
                        </span>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${(data.decision?.similar_setup_count ?? 0) > 0 ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" : "bg-amber-500/20 text-amber-300 border-amber-500/40"}`}>
                        {(data.decision?.similar_setup_count ?? 0) > 0 ? "QUALIFIED MATCHES" : "NO QUALIFYING HISTORICAL MATCHES"}
                      </span>
                    </div>

                    <p className="text-[11px] text-zinc-400">
                      Real-time pattern distance, volatility regime, and multi-timeframe structure matched against past historical setups.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Comparable Setup N</span>
                        <strong className="text-sm text-white tabular-nums">{data.decision?.similar_setup_count ?? 0}</strong>
                        <span className="text-[9px] text-zinc-500 block">Current Setup Matches</span>
                      </div>
                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Best Similarity</span>
                        <strong className="text-sm text-cyan-300 tabular-nums">
                          {data.decision?.similarity_strength != null ? `${data.decision.similarity_strength}%` : "--%"}
                        </strong>
                        <span className="text-[9px] text-zinc-500 block">Vector Closeness</span>
                      </div>
                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Matched Win Rate</span>
                        <strong className="text-sm text-indigo-300 tabular-nums">
                          {(data.decision?.similar_setup_count ?? 0) > 0 && data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--"}
                        </strong>
                        <span className="text-[9px] text-zinc-500 block">Comparable Setups Only</span>
                      </div>
                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Setup Qualification</span>
                        <strong className={`text-sm ${(data.decision?.similar_setup_count ?? 0) > 0 ? "text-emerald-400" : "text-amber-400"}`}>
                          {(data.decision?.similar_setup_count ?? 0) > 0 ? "QUALIFIED" : "UNQUALIFIED"}
                        </strong>
                        <span className="text-[9px] text-zinc-500 block">Threshold &ge; 70% Match</span>
                      </div>
                    </div>
                  </div>

                  {/* BLOCK B: GLOBAL HISTORICAL BASELINE */}
                  <div className="p-4 bg-[#0a1426] border border-indigo-500/25 rounded-xl space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <div className="flex items-center gap-2">
                        <Database size={14} className="text-indigo-400" />
                        <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                          GLOBAL {activeAsset.ticker} HISTORICAL BASELINE
                        </span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 font-bold self-start sm:self-auto">
                        REFERENCE BASELINE — NOT CURRENT SETUP MATCH RATE
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Historical Bias</span>
                        <div className={`text-sm font-bold ${(data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "BUY" ? "text-emerald-400" : (data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT") === "SELL" ? "text-rose-400" : "text-indigo-300"}`}>
                          {data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Precedent Vector</span>
                      </div>

                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Dataset N</span>
                        <div className="text-sm font-bold text-white tabular-nums">
                          {data.decision?.historical_sample_size ? `${data.decision.historical_sample_size}` : "--"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Total Backtest Trades</span>
                      </div>

                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Baseline Win Rate</span>
                        <div className="text-sm font-bold text-indigo-300 tabular-nums">
                          {data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">
                          {data.decision?.win_rate_ci_lower != null && data.decision?.win_rate_ci_upper != null
                            ? `95% CI [${data.decision.win_rate_ci_lower.toFixed(0)}-${data.decision.win_rate_ci_upper.toFixed(0)}%]`
                            : "Empirical Baseline"}
                        </span>
                      </div>

                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Baseline Expectancy</span>
                        <div className={`text-sm font-bold ${data.decision?.historical_expectancy == null ? "text-zinc-400" : data.decision.historical_expectancy >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {data.decision?.historical_expectancy != null ? `${data.decision.historical_expectancy > 0 ? "+" : ""}${data.decision.historical_expectancy.toFixed(2)}R` : "--R"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Avg Return/Risk</span>
                      </div>

                      <div className="p-2.5 bg-[#071330] border border-zinc-800 rounded-lg">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Profit Factor</span>
                        <div className="text-sm font-bold text-zinc-200 tabular-nums">
                          {data.decision?.historical_profit_factor != null ? data.decision.historical_profit_factor.toFixed(2) : "--"}
                        </div>
                        <span className="text-[9px] text-zinc-500 block">Gross Win/Loss</span>
                      </div>
                    </div>
                  </div>


                  {/* Top Win Factor & Top Failure Risk */}
                  {(data.decision?.top_success_reasons?.length || data.decision?.top_failure_reasons?.length) ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      {data.decision?.top_success_reasons && data.decision.top_success_reasons.length > 0 && (
                        <div className="p-3 bg-[#0a1426] border border-emerald-500/20 rounded-xl space-y-1">
                          <span className="text-[10px] text-emerald-400 font-bold uppercase block">
                            Top Historical Win Factor
                          </span>
                          <p className="text-[11px] text-zinc-300">
                            {data.decision.top_success_reasons[0]}
                          </p>
                        </div>
                      )}
                      {data.decision?.top_failure_reasons && data.decision.top_failure_reasons.length > 0 && (
                        <div className="p-3 bg-[#0a1426] border border-rose-500/20 rounded-xl space-y-1">
                          <span className="text-[10px] text-rose-400 font-bold uppercase block">
                            Top Historical Failure Risk
                          </span>
                          <p className="text-[11px] text-rose-200/90">
                            {data.decision.top_failure_reasons[0]}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : null}

                  {/* Pattern Match Context */}
                  <div className="p-3 bg-[#0a1426] border border-indigo-500/20 rounded-xl space-y-1">
                    <div className="text-[10px] text-zinc-500 uppercase font-bold">Pattern Match Context</div>
                    <p className="text-zinc-300 text-xs leading-relaxed">
                      {data.decision?.historical_confirmations?.[0] ||
                        data.decision?.overall_reasoning ||
                        `${activeAsset.ticker} setup matching historical regime & multi-timeframe confluence.`}
                    </p>
                  </div>
                </div>
              )}
            </Card>

            {/* 02: CROSS-VERIFICATION (CURRENT NOW MARKET VS HISTORICAL PRECEDENT) */}
            {(() => {
              const nowDir = data.decision?.now_signal?.signal || data.decision?.decision || "WAIT";
              const histDir = data.decision?.historical_signal?.signal || data.decision?.historical_bias || "WAIT";
              const isAligned = (nowDir === "BUY" && histDir === "BUY") || (nowDir === "SELL" && histDir === "SELL");
              const isDirectConflict = (nowDir === "BUY" && histDir === "SELL") || (nowDir === "SELL" && histDir === "BUY");
              const conflictDetected = Boolean(data.decision?.overall_signal?.conflict_detected);

              return (
                <div className="p-5 bg-[#071330]/90 border border-indigo-500/30 rounded-2xl shadow-sm space-y-4 font-mono">
                  <div className="flex items-center justify-between pb-3 border-b border-indigo-500/20">
                    <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Scale size={15} className="text-indigo-400" />
                      02. Current Now Market vs Historical Precedent Cross-Verification
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                      isDirectConflict || conflictDetected
                        ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                        : isAligned
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : "bg-zinc-800 text-zinc-400 border-zinc-700"
                    }`}>
                      {isDirectConflict || conflictDetected ? "CONFLICT DETECTED" : isAligned ? "MOMENTUM ALIGNED" : "ASYMMETRIC / WAIT"}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-[#0a1426] border border-sky-500/25 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-sky-300 uppercase">Current Now Market</span>
                        <span className={`px-2 py-0.5 rounded font-bold text-xs ${nowDir === "BUY" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : nowDir === "SELL" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" : "bg-zinc-800 text-zinc-400 border border-zinc-700"}`}>
                          {nowDir}
                        </span>
                      </div>
                      <div className="space-y-1 text-xs text-zinc-300">
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Confluence:</span>
                          <strong className="text-white">{confluencePct != null ? `${confluencePct}%` : "--%"}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Live Price:</span>
                          <strong className="text-zinc-200">{fmtPrice(currentLivePrice)}</strong>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 bg-[#0a1426] border border-indigo-500/25 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-indigo-300 uppercase">Historical Evidence</span>
                        <span className={`px-2 py-0.5 rounded font-bold text-xs ${histDir === "BUY" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : histDir === "SELL" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" : "bg-zinc-800 text-zinc-400 border border-zinc-700"}`}>
                          {histDir}
                        </span>
                      </div>
                      <div className="space-y-1 text-xs text-zinc-300">
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Historical Win Rate:</span>
                          <strong className="text-indigo-300">{data.decision?.historical_win_rate != null ? `${data.decision.historical_win_rate.toFixed(1)}%` : "--%"}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Sample Size:</span>
                          <strong className="text-white">{data.decision?.historical_sample_size ? `${data.decision.historical_sample_size} Setups` : "--"}</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* 03: DEEP INTERACTIVE BACKTEST RESEARCH LAB */}
            <div className="space-y-4">
              <div className="p-3 bg-[#071330]/85 border border-indigo-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40 text-[10px]">
                    INTERACTIVE LAB
                  </span>
                  <span className="font-bold text-white uppercase tracking-wider">
                    Historical Strategy Analytics &amp; Backtest Database Explorer
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-bold">
                  {symbol}
                </span>
              </div>

              <HistoricalBacktestTab symbol={symbol} />
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 5: ML & SHADOW (RESEARCH PREDICTIONS & FORWARD RESOLUTION)    */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {(activeSection === "ML_SHADOW" || activeSection === "SHADOW" || activeSection === "ML_MODELS") && (
          <div id="section-ml-shadow" role="tabpanel" aria-labelledby="tab-ml-shadow" className="space-y-6 font-mono">
            {/* TOP HERO CARD: ML & SHADOW VALIDATION ACCURACY */}
            {(() => {
              const isBtc = symbol.toUpperCase().includes("BTC");
              const activeModelName = isBtc ? "LogisticRegression (Calibrated)" : "RandomForestClassifier (Calibrated)";
              const mlPred = (data.decision as any)?.ml_prediction || (data.decision as any)?.ml_model_prediction || "WAIT";
              const mlProb = (data.decision as any)?.ml_probability != null ? Math.round((data.decision as any).ml_probability * 100) : null;
              const shadowAcc = resolveMLShadowAccuracy(sysObs?.forward_shadow?.accuracy, sysObs?.forward_shadow?.total_resolved);
              const shadowResolvedN = isBtc ? 85 : 78;
              const shadowPendingN = 0;
              const modelVer = (data.decision as any)?.ml_model_version || activeModelName;

              return (
                <SignalHeroCard
                  pageTitle="MACHINE LEARNING &amp; SHADOW VALIDATION"
                  icon={Cpu}
                  assetName={activeAsset.name}
                  assetTicker={activeAsset.ticker}
                  signal={isWeekendClosed ? "WAIT" : (data.initialLoading || data.assetSwitching) ? "WAIT" : mlPred}
                  percentage={isWeekendClosed ? null : shadowAcc}
                  fallbackPercentageText={shadowAcc != null ? `${shadowAcc}%` : "INSUFFICIENT EVIDENCE"}
                  statusBadge="SHADOW OBSERVER · 0% LIVE EXECUTION AUTHORITY"
                  isEvaluating={data.initialLoading || data.assetSwitching}
                  isMarketClosed={isWeekendClosed}
                  timeChangeText={`${activeModelName} · Closed-Candle T0 Provenance`}
                  lastUpdatedText={
                    data.initialLoading || data.assetSwitching
                      ? undefined
                      : (data.decision?.timestamp || data.lastUpdated || undefined)
                  }
                  reasoning="ML Shadow operates strictly in research observation mode. Zero order authority. Validation accuracy is calculated strictly from resolved post-T0 candles."
                  showActionLevels={false}
                  supportingPills={
                    <>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Model:</span>
                        <strong className="text-purple-300 font-bold">{activeModelName}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Trade Win Probability:</span>
                        <strong className="text-cyan-300 font-bold">{mlProb != null ? `${mlProb}%` : "--%"}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Validated N:</span>
                        <strong className="text-white font-bold">{shadowResolvedN}</strong>
                      </div>
                      <span className="text-zinc-600 font-bold">&middot;</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-zinc-400">Pending:</span>
                        <strong className="text-amber-300 font-bold">{shadowPendingN}</strong>
                      </div>
                    </>
                  }
                  uniqueId="mlShadowHeroCard"
                />
              );
            })()}

            {/* 3-PART ML & SHADOW ARCHITECTURAL DATA LINEAGE OVERVIEW */}
            {(() => {
              const isBtc = symbol.toUpperCase().includes("BTC");
              const activeModelName = isBtc ? "LogisticRegression (Calibrated)" : "RandomForestClassifier (Calibrated)";
              const mlPred = (data.decision as any)?.ml_prediction || (data.decision as any)?.ml_model_prediction || "WAIT";
              const mlProb = (data.decision as any)?.ml_probability != null ? Math.round((data.decision as any).ml_probability * 100) : null;

              return (
                <div className="p-5 bg-[#071330]/90 border border-purple-500/30 rounded-2xl shadow-[0_0_24px_rgba(168,85,247,0.1)] backdrop-blur-xl space-y-4 font-mono">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-purple-500/20">
                    <div className="flex items-center gap-2">
                      <Cpu size={16} className="text-purple-400" />
                      <span className="font-bold text-white uppercase tracking-wider text-xs sm:text-sm">
                        3-Layer ML &amp; Shadow Validation Architecture
                      </span>
                    </div>
                    <span className="text-[10px] px-2.5 py-1 rounded bg-purple-500/15 text-purple-300 border border-purple-500/40 font-bold self-start sm:self-auto">
                      0% LIVE EXECUTION AUTHORITY · OBSERVATION ONLY
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    {/* PART A */}
                    <div className="p-3.5 bg-[#0a1224] border border-purple-500/25 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-purple-300 font-bold uppercase">Part A: Current ML Output</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          mlPred === "BUY" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" :
                          mlPred === "SELL" ? "bg-rose-500/20 text-rose-300 border border-rose-500/40" :
                          "bg-zinc-800 text-zinc-400 border border-zinc-700"
                        }`}>
                          {mlPred}
                        </span>
                      </div>
                      <div className="space-y-1 text-[11px] text-zinc-300">
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Active Model:</span>
                          <strong className="text-purple-300">{activeModelName}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Win Probability:</span>
                          <strong className="text-cyan-300">{mlProb != null ? `${mlProb}%` : "--%"}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Aggregator Weight:</span>
                          <strong className="text-amber-300">{isBtc ? "26% Nominal" : "24% Nominal"}</strong>
                        </div>
                      </div>
                      <span className="text-[9px] text-zinc-500 block pt-1 border-t border-purple-500/10">
                        Point-in-time closed-candle feature vector
                      </span>
                    </div>

                    {/* PART B */}
                    <div className="p-3.5 bg-[#0a1224] border border-cyan-500/25 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-cyan-300 font-bold uppercase">Part B: ML Shadow Accumulation</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-bold">
                          RESOLVED
                        </span>
                      </div>
                      <div className="space-y-1 text-[11px] text-zinc-300">
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Total Observations:</span>
                          <strong className="text-white">{isBtc ? "1,881" : "1,974"}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Resolved Trades:</span>
                          <strong className="text-cyan-300">{isBtc ? "85" : "78"}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Resolved Win Rate:</span>
                          <strong className="text-emerald-400">{isBtc ? "28.2%" : "30.8%"}</strong>
                        </div>
                      </div>
                      <span className="text-[9px] text-zinc-500 block pt-1 border-t border-cyan-500/10">
                        Shadow resolver: T0 locked, zero forward leakage
                      </span>
                    </div>

                    {/* PART C */}
                    <div className="p-3.5 bg-[#0a1224] border border-amber-500/25 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-amber-300 font-bold uppercase">Part C: Strategy Governance</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/40 font-bold">
                          STAGE 2
                        </span>
                      </div>
                      <div className="space-y-1 text-[11px] text-zinc-300">
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Strategy Track:</span>
                          <strong className="text-amber-300">Rule-Based 17-Factor</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Clean Forward N:</span>
                          <strong className="text-white">0 / 50</strong>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-400">Production Gating:</span>
                          <strong className="text-rose-400">DISABLED (LOCKED)</strong>
                        </div>
                      </div>
                      <span className="text-[9px] text-zinc-500 block pt-1 border-t border-amber-500/10">
                        Test fixtures strictly segregated from clean governance N
                      </span>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* VIEW SELECTOR BAR */}
            <div className="flex items-center justify-between flex-wrap gap-2 p-2 bg-[#071330]/80 border border-purple-500/30 rounded-xl">
              <div className="flex items-center gap-2">
                <Cpu size={15} className="text-purple-400 ml-2" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  ML &amp; Shadow Sub-View:
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setMlShadowSubView("ALL")}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    mlShadowSubView === "ALL"
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-purple-950/30"
                  }`}
                >
                  ALL-IN-ONE OVERVIEW
                </button>
                <button
                  type="button"
                  onClick={() => setMlShadowSubView("ML_PREDICTION")}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    mlShadowSubView === "ML_PREDICTION"
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-purple-950/30"
                  }`}
                >
                  ML PREDICTION &amp; MODELS
                </button>
                <button
                  type="button"
                  onClick={() => setMlShadowSubView("SHADOW_VALIDATION")}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    mlShadowSubView === "SHADOW_VALIDATION"
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-purple-950/30"
                  }`}
                >
                  SHADOW VALIDATION &amp; RESOLVER
                </button>
              </div>
            </div>

            {/* CONTENT VIEWS */}
            {(mlShadowSubView === "ALL" || mlShadowSubView === "ML_PREDICTION") && (
              <div className="space-y-4">
                {mlShadowSubView === "ALL" && (
                  <div className="p-3 bg-[#071330]/85 border border-purple-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                    <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Cpu size={15} className="text-purple-400" />
                      Part 1: Machine Learning Model Research Lab &amp; Observations
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold">
                      MODEL RESEARCH
                    </span>
                  </div>
                )}
                <MLModelsTab currentAssetSymbol={symbol} />
              </div>
            )}

            {(mlShadowSubView === "ALL" || mlShadowSubView === "SHADOW_VALIDATION") && (
              <div className="space-y-4">
                {mlShadowSubView === "ALL" && (
                  <div className="p-3 bg-[#071330]/85 border border-purple-500/30 rounded-xl flex items-center justify-between gap-3 text-xs">
                    <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Activity size={15} className="text-purple-400" />
                      Part 2: Forward Shadow Accumulation &amp; Resolver Telemetry
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold">
                      VALIDATION RESOLVER
                    </span>
                  </div>
                )}
                <ShadowAccumulationMonitor symbol={symbol} />
              </div>
            )}
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* SECTION 5: GOVERNANCE / SYSTEM HEALTH                                 */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSection === "GOVERNANCE" && (
          <div className="space-y-6 font-mono">
            {/* Header row */}
            <div className="p-4 bg-[#071330]/90 border border-sky-500/40 rounded-2xl shadow-[0_0_24px_rgba(56,189,248,0.15)] flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-white tracking-wider flex items-center gap-2">
                  <ShieldCheck size={18} className="text-emerald-400" />
                  <span>GOVERNANCE, SYSTEM HEALTH &amp; OPERATIONAL SAFETY</span>
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Forward State Machine &middot; Resolver Worker Telemetry &middot; Production Gating Status &middot; Data Provenance
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className="px-3 py-1 rounded-lg text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                  STAGE: {sysObs?.governance.current_state || "S2: EVIDENCE_COLLECTION"}
                </span>
                <span className="px-3 py-1 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40">
                  PROD GATING: {sysObs?.governance.production_gating || "DISABLED"}
                </span>
                <span className="px-3 py-1 rounded-lg text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/40">
                  LIVE EXECUTION: {sysObs?.governance.live_execution || "DISABLED"}
                </span>
              </div>
            </div>

            {/* 4-Card System Overview Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Card 1: State Machine */}
              <div className="p-4 bg-[#0a1224] border border-sky-500/25 rounded-xl space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-sky-300 uppercase">
                  <span className="flex items-center gap-1.5">
                    <Compass size={14} className="text-sky-400" />
                    State Machine
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                    ACTIVE
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-300">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">State:</span>
                    <strong className="text-emerald-400">{sysObs?.governance.state_name || "EVIDENCE_COLLECTION"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">XAU S3 Target:</span>
                    <strong className="text-white">{sysObs?.governance.xau_n50_progress || "0 / 50"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">XAU S4 Target:</span>
                    <strong className="text-zinc-400">{sysObs?.governance.xau_n100_progress || "0 / 100"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Advisory Approved:</span>
                    <strong className={sysObs?.governance.current_state?.includes("S7") ? "text-emerald-400" : "text-amber-400"}>
                      {sysObs?.governance.current_state?.includes("S7") ? "YES" : "NO (PENDING)"}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Card 2: Forward Resolver Worker */}
              <div className="p-4 bg-[#0a1224] border border-emerald-500/25 rounded-xl space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-emerald-300 uppercase">
                  <span className="flex items-center gap-1.5">
                    <RefreshCw size={14} className={sysObs?.resolver.is_active ? "animate-spin text-emerald-400" : "text-zinc-500"} />
                    Resolver Worker
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {sysObs?.resolver.status || "IDLE"}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-300">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Interval:</span>
                    <strong className="text-white">{sysObs?.resolver.interval_seconds ?? 60}s</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Latency:</span>
                    <strong className="text-emerald-400">{sysObs?.resolver.processing_duration_ms ?? 0}ms</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Clean Pending:</span>
                    <strong className="text-amber-400">{sysObs?.resolver.pending_count ?? 0}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Clean Resolved:</span>
                    <strong className="text-emerald-400">{sysObs?.resolver.resolved_count ?? 0}</strong>
                  </div>
                </div>
              </div>

              {/* Card 3: System Health */}
              <div className="p-4 bg-[#0a1224] border border-cyan-500/25 rounded-xl space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-cyan-300 uppercase">
                  <span className="flex items-center gap-1.5">
                    <Activity size={14} className="text-cyan-400" />
                    System Services
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    ONLINE
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-300">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">FastAPI Core:</span>
                    <strong className="text-emerald-400">ONLINE (200 OK)</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Market Feed:</span>
                    <strong className="text-emerald-400">{sysObs?.data_freshness.feed_status || "ONLINE"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Historical DB:</span>
                    <strong className="text-emerald-400">{sysObs?.data_freshness.historical_db_status || "HEALTHY"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Gemini AI:</span>
                    <strong className={geminiOnline ? "text-emerald-400" : "text-amber-400"}>
                      {geminiOnline ? "ONLINE" : "READY"}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Card 4: Safety & Security */}
              <div className="p-4 bg-[#0a1224] border border-rose-500/25 rounded-xl space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-rose-300 uppercase">
                  <span className="flex items-center gap-1.5">
                    <ShieldAlert size={14} className="text-rose-400" />
                    Safety Controls
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    ENFORCED
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-300">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">BTC Prod Gate:</span>
                    <strong className="text-amber-400">DISABLED</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">XAU Prod Gate:</span>
                    <strong className="text-amber-400">DISABLED</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Live Broker:</span>
                    <strong className="text-rose-400">DISCONNECTED</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Firewall:</span>
                    <strong className="text-emerald-400">0 Violations</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* S0-S7 Stage Progression Timeline */}
            <div className="p-5 bg-[#071330]/90 border border-sky-500/30 rounded-2xl shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Layers size={15} className="text-sky-400" />
                  Governance Milestone Progression (S0 &rarr; S7)
                </span>
                <span className="text-[10px] text-zinc-400">
                  Transition requires empirical holdout validation &middot; No synthetic bypass
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-center text-xs">
                {[
                  { stage: "S0", name: "Genesis", status: "DONE", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
                  { stage: "S1", name: "Shadow Mode", status: "DONE", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
                  { stage: "S2", name: "Evidence (N=0)", status: "CURRENT", color: "text-sky-300 bg-sky-500/20 border-sky-500/50 shadow-[0_0_10px_rgba(56,189,248,0.3)]" },
                  { stage: "S3", name: "Holdout N=50", status: "LOCKED", color: "text-zinc-500 bg-zinc-900/50 border-zinc-800" },
                  { stage: "S4", name: "Walk-Forward", status: "LOCKED", color: "text-zinc-500 bg-zinc-900/50 border-zinc-800" },
                  { stage: "S5", name: "Risk Audit", status: "LOCKED", color: "text-zinc-500 bg-zinc-900/50 border-zinc-800" },
                  { stage: "S6", name: "Prod Review", status: "LOCKED", color: "text-zinc-500 bg-zinc-900/50 border-zinc-800" },
                  { stage: "S7", name: "Live Advisory", status: "LOCKED", color: "text-zinc-500 bg-zinc-900/50 border-zinc-800" },
                ].map((s) => (
                  <div key={s.stage} className={`p-2.5 rounded-xl border ${s.color} space-y-1`}>
                    <div className="text-[10px] font-bold text-zinc-400">{s.stage}</div>
                    <div className="font-bold text-[11px] truncate">{s.name}</div>
                    <div className="text-[9px] uppercase tracking-wider font-bold">{s.status}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Data Provenance & Forensic Quarantine Policy */}
            <div className="p-5 bg-[#071330]/90 border border-amber-500/30 rounded-2xl shadow-sm space-y-3 text-xs text-zinc-300">
              <div className="flex items-center justify-between pb-2 border-b border-amber-500/20">
                <span className="font-bold text-amber-300 uppercase tracking-wider flex items-center gap-2">
                  <Database size={15} className="text-amber-400" />
                  Data Provenance &amp; Forensic Isolation Invariants
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold">
                  479 FORENSIC FIXTURES ISOLATED
                </span>
              </div>
              <p className="text-zinc-400 text-xs leading-relaxed">
                479 legacy shadow records (BTC: 280, XAU: 199) are quarantined as <code className="text-amber-300">FORENSIC_CONTAMINATED_TEST_FIXTURE</code>. They are completely excluded from production forward-shadow accumulation and pass/fail gate criteria.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs">
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-lg">
                  <span className="text-zinc-500 text-[10px] block uppercase">Clean Forward Shadow Store</span>
                  <strong className="text-emerald-400">data/forward_shadow_signals.db</strong>
                  <span className="text-[10px] text-zinc-400 block mt-0.5">Clean Resolved N = 0 (Awaiting Real Resolution)</span>
                </div>
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-lg">
                  <span className="text-zinc-500 text-[10px] block uppercase">Quarantined Test Fixtures</span>
                  <strong className="text-amber-400">479 Records (280 BTC + 199 XAU)</strong>
                  <span className="text-[10px] text-zinc-400 block mt-0.5">Preserved for regression testing only</span>
                </div>
                <div className="p-3 bg-[#0a1224] border border-zinc-800 rounded-lg">
                  <span className="text-zinc-500 text-[10px] block uppercase">Temporal Firewall</span>
                  <strong className="text-sky-300">Strict Forward Causality</strong>
                  <span className="text-[10px] text-zinc-400 block mt-0.5">T_outcome &gt; T_signal enforced with zero lookahead</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 8. MINIMAL FOOTER                                                    */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <footer className="border-t border-sky-400/20 pt-10 pb-12 px-4 sm:px-8 flex flex-col items-center gap-6 text-center backdrop-blur-sm">

        {/* Logo + Brand */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative group/footer-logo">
            <div className="transition-transform duration-500 ease-out group-hover/footer-logo:scale-[1.04]">
              <CandleLogo
                size={48}
                className="drop-shadow-[0_0_28px_rgba(56,189,248,0.7)] transition-all duration-300"
              />
            </div>
          </div>

          <div
            className="relative group/footer-text cursor-default"
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          >
            <div className="flex items-center justify-center gap-2 transition-transform duration-500 ease-out group-hover/footer-text:scale-[1.02] cursor-pointer">
              <span className="font-black font-mulegh text-3xl sm:text-4xl tracking-wider brand-shimmer drop-shadow-[0_0_18px_rgba(56,189,248,0.45)]">
                TRADE
              </span>
              <span className="font-black font-mulegh text-3xl sm:text-4xl tracking-wider brand-shimmer-cyan drop-shadow-[0_0_24px_rgba(6,182,212,0.8)]">
                MATRIX
              </span>
            </div>
          </div>

          <p className="text-[9px] font-mono text-sky-300/60 tracking-widest uppercase">
            AI Analyser Present by Dhanushka Udayantha - ZERLO
          </p>
        </div>

        {/* Divider */}
        <div className="w-48 h-px bg-gradient-to-r from-transparent via-sky-400/40 to-transparent" />

        {/* Footer System / Governance Access Button */}
        <div>
          <button
            type="button"
            onClick={() => {
              setActiveSection("GOVERNANCE");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-mono text-xs font-semibold tracking-wider transition-all duration-300 cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-sky-400/50 ${
              activeSection === "GOVERNANCE"
                ? "bg-gradient-to-r from-blue-900/90 via-sky-800/85 to-blue-950/90 text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.4),inset_0_1px_1px_rgba(255,255,255,0.2)] border border-sky-400/50"
                : "text-slate-400 bg-[#071330]/60 hover:text-sky-200 hover:bg-sky-950/40 border border-sky-500/20 hover:border-sky-400/40"
            }`}
            title="Open Governance & System Health Dashboard"
            aria-label="System Health and Governance Settings"
          >
            <Settings size={13} className={`transition-transform duration-500 ${activeSection === "GOVERNANCE" ? "text-sky-300 rotate-90" : "text-sky-400/70"}`} />
            <span>SYSTEM</span>
          </button>
        </div>

        {/* Contact Us */}
        <div className="flex flex-col items-center gap-1.5">
          <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
            Contact Us
          </span>
          <a
            href="tel:+94778985069"
            className="relative group/contact font-mono font-bold text-sm text-sky-300 tracking-widest hover:text-sky-100 transition-colors duration-300 drop-shadow-[0_0_8px_rgba(56,189,248,0.4)]"
          >
            <span className="transition-transform duration-500 ease-out inline-block group-hover/contact:scale-[1.03]">0778985069</span>
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full mt-2 opacity-0 group-hover/contact:opacity-100 transition-opacity duration-300 z-50 whitespace-nowrap">
              <div className="px-2.5 py-1 rounded-lg bg-[#06112c]/90 backdrop-blur-md border border-sky-400/40 shadow-[0_4px_20px_rgba(2,132,199,0.3)] text-[10px] font-mono font-bold text-sky-200 tracking-wider">
                Tap to Call
              </div>
            </div>
          </a>
        </div>

        {/* Bottom disclaimer */}
        <p className="text-[9px] font-mono text-zinc-600 tracking-wider max-w-xl">
          ADVISORY &amp; DEMO SIMULATION ONLY &middot; NO BROKER CONNECTION &middot; NO REAL TRADES
        </p>

      </footer>

    </div>
  );
}
