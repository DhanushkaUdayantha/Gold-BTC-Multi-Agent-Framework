"use client";

import React, { useMemo } from "react";
import { Activity } from "lucide-react";
import {
  fmtPrice,
  formatHeroPercentage,
  getSignalSemanticTheme,
  getNeutralSemanticTheme,
  getAssetBadgeClass,
  resolveHeroPresentation,
  type SignalSemanticTheme,
  type ResolvedHeroState,
} from "@/lib/format";
export {
  formatHeroPercentage,
  getSignalSemanticTheme,
  getNeutralSemanticTheme,
  getAssetBadgeClass,
  resolveHeroPresentation,
};
export type { SignalSemanticTheme, ResolvedHeroState };
import { useRelativeTime } from "@/lib/relativeTime";

/**
 * Clean circular dot loader for Hero loading states:
 * - 8 smooth dots moving along a circular path
 * - No arrows, no directional spinners, no lines
 * - Smooth, subtle, compact, dark-UI compatible
 * - Respects prefers-reduced-motion
 */
export function HeroCircularDotLoader({
  size = 28,
  className = "",
  color = "currentColor",
}: {
  size?: number;
  className?: string;
  color?: string;
}) {
  const dots = [
    { cx: 16, cy: 5.5, opacity: 1 },
    { cx: 23.42, cy: 8.58, opacity: 0.88 },
    { cx: 26.5, cy: 16, opacity: 0.75 },
    { cx: 23.42, cy: 23.42, opacity: 0.62 },
    { cx: 16, cy: 26.5, opacity: 0.5 },
    { cx: 8.58, cy: 23.42, opacity: 0.38 },
    { cx: 5.5, cy: 16, opacity: 0.25 },
    { cx: 8.58, cy: 8.58, opacity: 0.15 },
  ];

  return (
    <span
      className={`inline-flex items-center justify-center shrink-0 ${className}`}
      role="status"
      aria-label="Loading"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="animate-spin motion-reduce:animate-none"
        style={{ animationDuration: "1.2s", animationTimingFunction: "linear" }}
        aria-hidden="true"
      >
        {dots.map((dot, idx) => (
          <circle
            key={idx}
            cx={dot.cx}
            cy={dot.cy}
            r={2}
            fill={color}
            opacity={dot.opacity}
          />
        ))}
      </svg>
      <span className="sr-only">Loading...</span>
    </span>
  );
}

/**
 * Animated pulsing dots for WAIT state:
 * - Pure CSS/Tailwind animation, aria-hidden="true"
 * - Staggered opacity transitions, no layout shifting
 */
export function AnimatedWaitDots({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-baseline font-mono tracking-widest text-zinc-400 select-none ${className}`}
      aria-hidden="true"
    >
      <span className="inline-block animate-[pulse_1.4s_ease-in-out_infinite] opacity-40">.</span>
      <span className="inline-block animate-[pulse_1.4s_ease-in-out_0.25s_infinite] opacity-65">.</span>
      <span className="inline-block animate-[pulse_1.4s_ease-in-out_0.5s_infinite] opacity-90">.</span>
    </span>
  );
}

export function HeroCircularProgress({
  signal,
  percentage,
  subLabel,
  isEvaluating,
  isMarketClosed,
  theme,
  uniqueId = "heroProgressRing",
  fallbackPercentageText,
  heroState,
}: {
  signal?: string;
  percentage?: number | string | null;
  subLabel?: string;
  isEvaluating?: boolean;
  isMarketClosed?: boolean;
  theme?: SignalSemanticTheme;
  uniqueId?: string;
  fallbackPercentageText?: string;
  heroState?: ResolvedHeroState;
}) {
  const hero = heroState ?? resolveHeroPresentation({
    signal,
    percentage,
    isEvaluating,
    isMarketClosed,
    fallbackPercentageText,
  });

  // When in WAIT, LOADING, or UNAVAILABLE, strictly enforce the neutral semantic theme (unless market is closed)
  const isNeutralState = hero.state === "WAIT" || hero.isLoading || hero.isUnavailable;
  const activeTheme = isMarketClosed
    ? (theme ?? hero.theme)
    : isNeutralState
    ? getNeutralSemanticTheme()
    : (theme ?? hero.theme);
  const safePct =
    percentage != null && percentage !== "" && !isNaN(Number(percentage))
      ? Math.max(0, Math.min(100, Math.round(Number(percentage))))
      : null;

  // SVG dimensions: viewBox="0 0 112 112", center (56, 56), radius 44
  const radius = 44;
  const circumference = 2 * Math.PI * radius; // ~276.46
  const fillPct = isMarketClosed || hero.isLoading || hero.state === "WAIT" || hero.isUnavailable ? 0 : (safePct != null ? safePct : 0);
  const strokeDashoffset = circumference - (circumference * fillPct) / 100;
  const isAction = (hero.state === "BUY" || hero.state === "SELL") && !isMarketClosed && !hero.isLoading;

  return (
    <div
      className="relative w-28 h-28 rounded-full border flex items-center justify-center shrink-0 select-none transition-all duration-500 backdrop-blur-md"
      style={{
        borderColor: isMarketClosed ? "rgba(245, 158, 11, 0.4)" : activeTheme.borderColor,
        backgroundColor: isMarketClosed ? "#1c1204" : activeTheme.circleBgColor,
        boxShadow: isMarketClosed ? "0 0 20px rgba(245, 158, 11, 0.2)" : activeTheme.circleShadow,
      }}
    >
      {/* SVG Circular Progress Ring */}
      <svg className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none" viewBox="0 0 112 112" aria-hidden="true">
        <defs>
          <linearGradient id={`ringGrad_${uniqueId}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={activeTheme.frontWaveStart} />
            <stop offset="50%" stopColor={activeTheme.frontWaveMid} />
            <stop offset="100%" stopColor={activeTheme.frontWaveEnd} />
          </linearGradient>
        </defs>

        {/* Background Track */}
        <circle
          cx="56"
          cy="56"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="6.5"
          className="text-slate-800/60"
        />

        {/* Foreground Progress Arc - smooth static arc, no spinning arrow/spinner */}
        <circle
          cx="56"
          cy="56"
          r={radius}
          fill="none"
          stroke={`url(#ringGrad_${uniqueId})`}
          strokeWidth="6.5"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>

      {/* Subtle outer pulse on actionable trades */}
      {isAction && (
        <div
          className="absolute inset-0 rounded-full animate-ping pointer-events-none opacity-15"
          style={{
            border: `1.5px solid ${activeTheme.rippleColor}`,
            animationDuration: "3s",
          }}
        />
      )}

      {/* Central Content */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-1">
        <span
          className="text-2xl font-black font-mono tracking-tight transition-all duration-300 drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] flex items-center justify-center"
          style={{
            color: isMarketClosed ? "#fbbf24" : activeTheme.pctColor,
            textShadow: !isMarketClosed && activeTheme.textGlow !== "none" ? activeTheme.textGlow : "none",
          }}
        >
          {hero.isLoading ? (
            <HeroCircularDotLoader size={26} className="text-zinc-400" />
          ) : isMarketClosed ? (
            <span className="inline-block tracking-widest text-xl text-amber-400">...</span>
          ) : hero.isUnavailable ? (
            <span className="text-xl text-zinc-500 font-bold">--</span>
          ) : hero.state === "WAIT" ? (
            <span className="text-lg">WAIT...</span>
          ) : (
            hero.percentageText
          )}
        </span>
        {hero.state !== "WAIT" && !hero.isUnavailable && (
          <span
            className="text-[9px] font-bold uppercase tracking-wider transition-colors duration-300 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)] mt-0.5"
            style={{ color: isMarketClosed ? "#fbbf24" : activeTheme.pctColor }}
          >
            {isMarketClosed
              ? "CLOSED"
              : hero.isLoading
              ? "WAIT..."
              : subLabel && subLabel !== "EVALUATE" && subLabel !== "EVALUATING"
              ? subLabel
              : hero.signalText}
          </span>
        )}
      </div>
    </div>
  );
}

// Backwards-compatibility export for existing HeroWaterCircle callers
export const HeroWaterCircle = HeroCircularProgress;

export interface SignalHeroCardProps {
  pageTitle: string;
  icon?: React.ComponentType<{ size?: number | string; className?: string }>;
  iconClassName?: string;
  assetName: string;
  assetTicker: string;
  signal: string;
  percentage?: number | string | null;
  fallbackPercentageText?: string;
  statusBadge?: string;
  isEvaluating?: boolean;
  isMarketClosed?: boolean;
  timeChangeText?: string;
  lastUpdatedText?: string;
  supportingPills?: React.ReactNode;
  reasoning?: string;
  uniqueId?: string;
  className?: string;
  showActionLevels?: boolean;
  actionLabel?: string;
  entryPrice?: number | string | null;
  stopLoss?: number | string | null;
  takeProfit1?: number | string | null;
  takeProfit2?: number | string | null;
}

export function SignalHeroCard({
  pageTitle,
  icon: Icon = Activity,
  iconClassName,
  assetName,
  assetTicker,
  signal,
  percentage,
  fallbackPercentageText,
  statusBadge,
  isEvaluating = false,
  isMarketClosed = false,
  timeChangeText,
  lastUpdatedText,
  supportingPills,
  reasoning,
  uniqueId = "heroCard",
  className = "",
  showActionLevels,
  actionLabel,
  entryPrice,
  stopLoss,
  takeProfit1,
  takeProfit2,
}: SignalHeroCardProps) {
  const relativeUpdated = useRelativeTime(lastUpdatedText, { fallback: "--" });
  const displayUpdated = useMemo(() => {
    if (!lastUpdatedText) return null;
    const clean = relativeUpdated.replace(/^Updated\s*/i, "");
    return `Updated ${clean}`;
  }, [lastUpdatedText, relativeUpdated]);

  const hero = useMemo(
    () =>
      resolveHeroPresentation({
        signal,
        percentage,
        isEvaluating,
        isMarketClosed,
        fallbackPercentageText,
      }),
    [signal, percentage, isEvaluating, isMarketClosed, fallbackPercentageText]
  );

  const theme = hero.theme;

  // Clean formatted action levels: only show real prices when available and directional setup active
  const shouldRenderActionLevels = showActionLevels ?? (entryPrice != null || stopLoss != null || takeProfit1 != null);
  const hasValidActionLevels = !isMarketClosed && !hero.isLoading && hero.state !== "WAIT" && !hero.isUnavailable && (entryPrice != null || stopLoss != null || takeProfit1 != null);

  return (
    <div
      className={`p-5 sm:p-6 rounded-2xl border transition-all duration-700 space-y-4 relative overflow-hidden min-h-[195px] flex flex-col justify-between font-mono backdrop-blur-md ${className}`}
      style={{
        borderColor: theme.borderColor,
        boxShadow: theme.cardShadow,
        background: theme.cardBg,
      }}
    >
      {/* Top Header Row */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-2 text-center md:text-left flex-1 w-full">
          {/* Header Title & Badges */}
          <div className="flex items-center justify-center md:justify-start gap-2 flex-wrap">
            <span className="text-[11px] uppercase tracking-widest text-zinc-400 font-bold flex items-center gap-1.5">
              <Icon size={13} className={iconClassName || theme.text} />
              {pageTitle}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getAssetBadgeClass(`${assetTicker} ${assetName}`)}`}>
              {assetName} ({assetTicker})
            </span>
            {statusBadge && (
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border flex items-center gap-1 ${theme.badge}`}>
                <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                {statusBadge}
              </span>
            )}
          </div>

          {/* Standardized Card Shape: [ BUY / SELL / WAIT / -- ] [ percentage ] [ loader ] */}
          <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 sm:gap-4 pt-0.5">
            <div
              className={`text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight shrink-0 flex items-center gap-2.5 ${
                hero.isLoading ? "animate-pulse" : ""
              }`}
              style={{
                color: isMarketClosed ? "#fbbf24" : theme.pctColor,
                textShadow: !isMarketClosed && theme.textGlow !== "none" ? theme.textGlow : "none",
              }}
            >
              <span>{actionLabel || hero.signalText}</span>
              {hero.percentageText && (
                <span className="text-3xl sm:text-4xl lg:text-5xl opacity-90">{hero.percentageText}</span>
              )}
              {hero.isLoading && (
                <HeroCircularDotLoader size={30} className="text-zinc-400 ml-1 self-center" />
              )}
            </div>

            {/* Supporting metric details pill */}
            {supportingPills && (
              <div className="inline-flex flex-wrap items-center gap-x-2.5 gap-y-1 px-3.5 py-2 rounded-lg bg-[#14141c]/90 border border-[#242432] font-mono text-xs max-w-full">
                {supportingPills}
              </div>
            )}
          </div>

          {/* Action Levels: ENTRY | SL | TP1 | TP2 */}
          {shouldRenderActionLevels && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs max-w-2xl">
              <div className="bg-[#121624]/80 border border-[#1d2438] rounded-lg px-2.5 py-1.5 flex flex-col">
                <span className="text-[9.5px] text-zinc-400 font-semibold uppercase tracking-wider">Entry</span>
                <span className={`font-bold tabular-nums text-xs mt-0.5 ${hasValidActionLevels && entryPrice != null ? "text-zinc-200" : "text-zinc-500"}`}>
                  {hasValidActionLevels && entryPrice != null
                    ? fmtPrice(typeof entryPrice === "number" ? entryPrice : parseFloat(String(entryPrice)))
                    : "Not Available"}
                </span>
              </div>
              <div className="bg-[#121624]/80 border border-[#1d2438] rounded-lg px-2.5 py-1.5 flex flex-col">
                <span className="text-[9.5px] text-zinc-400 font-semibold uppercase tracking-wider">Stop Loss</span>
                <span className={`font-bold tabular-nums text-xs mt-0.5 ${hasValidActionLevels && stopLoss != null ? "text-rose-400" : "text-zinc-500"}`}>
                  {hasValidActionLevels && stopLoss != null
                    ? fmtPrice(typeof stopLoss === "number" ? stopLoss : parseFloat(String(stopLoss)))
                    : "Not Available"}
                </span>
              </div>
              <div className="bg-[#121624]/80 border border-[#1d2438] rounded-lg px-2.5 py-1.5 flex flex-col">
                <span className="text-[9.5px] text-zinc-400 font-semibold uppercase tracking-wider">TP 1</span>
                <span className={`font-bold tabular-nums text-xs mt-0.5 ${hasValidActionLevels && takeProfit1 != null ? "text-emerald-400" : "text-zinc-500"}`}>
                  {hasValidActionLevels && takeProfit1 != null
                    ? fmtPrice(typeof takeProfit1 === "number" ? takeProfit1 : parseFloat(String(takeProfit1)))
                    : "Not Available"}
                </span>
              </div>
              <div className="bg-[#121624]/80 border border-[#1d2438] rounded-lg px-2.5 py-1.5 flex flex-col">
                <span className="text-[9.5px] text-zinc-400 font-semibold uppercase tracking-wider">TP 2</span>
                <span className={`font-bold tabular-nums text-xs mt-0.5 ${hasValidActionLevels && takeProfit2 != null ? "text-emerald-300" : "text-zinc-500"}`}>
                  {hasValidActionLevels && takeProfit2 != null
                    ? fmtPrice(typeof takeProfit2 === "number" ? takeProfit2 : parseFloat(String(takeProfit2)))
                    : "Not Available"}
                </span>
              </div>
            </div>
          )}

          {/* Live Spot / Time-change indicator & Last updated */}
          {(timeChangeText || displayUpdated) && (
            <div className="flex items-center justify-center md:justify-start gap-2 text-[11px] text-zinc-400 font-mono pt-1">
              {timeChangeText && <span>{timeChangeText}</span>}
              {timeChangeText && displayUpdated && <span>&middot;</span>}
              {displayUpdated && <span>{displayUpdated}</span>}
            </div>
          )}

          {reasoning && (
            <p className="text-xs text-zinc-400 pt-0.5 line-clamp-2 max-w-4xl">
              {reasoning}
            </p>
          )}
        </div>

        {/* Right Side: Water Signal Circle */}
        <div className="shrink-0 self-center md:self-auto">
          <HeroWaterCircle
            signal={signal}
            percentage={percentage}
            subLabel={hero.signalText}
            isEvaluating={isEvaluating}
            isMarketClosed={isMarketClosed}
            theme={theme}
            uniqueId={uniqueId}
            fallbackPercentageText={fallbackPercentageText}
            heroState={hero}
          />
        </div>
      </div>
    </div>
  );
}

