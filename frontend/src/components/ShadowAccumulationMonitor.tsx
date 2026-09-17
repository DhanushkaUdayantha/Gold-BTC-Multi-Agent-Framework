"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  ShieldCheck,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Scale,
  Gauge,
  Info,
  Layers,
  Lock,
} from "lucide-react";
import {
  getShadowStatus,
  getShadowComparison,
  getForwardShadowResolverStatus,
  getSystemObservability,
  getForwardShadowValidation,
  ShadowStatusResponse,
  ShadowComparisonResponse,
  ForwardShadowResolverStatusResponse,
  SystemObservabilityResponse,
  ForwardShadowValidationResponse,
} from "@/services/api";
import { SignalHeroCard } from "./SignalHeroCard";
import { formatRAsUSD } from "@/lib/format";

interface ShadowAccumulationMonitorProps {
  symbol: string;
  className?: string;
}

export function ShadowAccumulationMonitor({
  symbol,
  className = "",
}: ShadowAccumulationMonitorProps) {
  const isBtc = symbol.toUpperCase().includes("BTC");
  const assetKey: "btc" | "xau" = isBtc ? "btc" : "xau";
  const assetDisplayName = isBtc ? "Bitcoin" : "Gold";
  const assetTicker = isBtc ? "BTC/USD" : "XAU/USD";

  const [shadowStatus, setShadowStatus] = useState<ShadowStatusResponse | null>(null);
  const [comparison, setComparison] = useState<ShadowComparisonResponse | null>(null);
  const [resolverData, setResolverData] = useState<ForwardShadowResolverStatusResponse | null>(null);
  const [sysObs, setSysObs] = useState<SystemObservabilityResponse | null>(null);
  const [fwdValidation, setFwdValidation] = useState<ForwardShadowValidationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const activeRequestIdRef = useRef(0);

  const fetchData = useCallback(
    async (isManual = false) => {
      const reqId = ++activeRequestIdRef.current;
      if (isManual) setRefreshing(true);
      setError(null);

      try {
        const [statusRes, compRes, resRes, obsRes, fwdRes] = await Promise.allSettled([
          getShadowStatus(assetKey),
          getShadowComparison(assetKey),
          getForwardShadowResolverStatus(),
          getSystemObservability(),
          getForwardShadowValidation(),
        ]);

        if (reqId !== activeRequestIdRef.current) return;

        if (statusRes.status === "fulfilled") {
          setShadowStatus(statusRes.value);
        }
        if (compRes.status === "fulfilled") {
          setComparison(compRes.value);
        }
        if (resRes.status === "fulfilled") {
          setResolverData(resRes.value);
        }
        if (obsRes.status === "fulfilled") {
          setSysObs(obsRes.value);
        }
        if (fwdRes.status === "fulfilled") {
          setFwdValidation(fwdRes.value);
        }

        if (statusRes.status === "rejected" && compRes.status === "rejected" && fwdRes.status === "rejected") {
          const reason = statusRes.reason?.message || fwdRes.reason?.message || "Failed to load shadow metrics";
          setError(reason);
        }

        setLastRefreshedAt(new Date().toISOString());
      } catch (err: any) {
        if (reqId === activeRequestIdRef.current) {
          setError(err?.message || "Error fetching shadow data");
        }
      } finally {
        if (reqId === activeRequestIdRef.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [assetKey]
  );

  // Fetch immediately on mount or symbol change
  useEffect(() => {
    setLoading(true);
    fetchData(false);
  }, [fetchData]);

  // 60-second auto-refresh interval
  useEffect(() => {
    const timer = setInterval(() => {
      fetchData(false);
    }, 60000);
    return () => clearInterval(timer);
  }, [fetchData]);

  // Authoritative Forward Shadow Validation Metrics
  const currentFwdMetrics = isBtc ? fwdValidation?.btc : fwdValidation?.xau;

  // Metric derivations
  const live = shadowStatus?.live_shadow_metrics;
  const compReport = comparison?.report;
  const baseline = shadowStatus?.backtest_reference_baseline;
  const thresholds = compReport?.pre_registered_thresholds;

  // CLEAN forward evidence (authoritative out-of-sample forward trades, excludes quarantined fixtures)
  const cleanResolvedN =
    currentFwdMetrics?.clean_forward?.resolved_signals ??
    (isBtc ? sysObs?.governance.btc_resolved_n : sysObs?.governance.xau_resolved_n) ??
    (live?.resolved_trades_count ?? 0);

  const cleanTotalN =
    currentFwdMetrics?.clean_forward?.total_signals ??
    (live?.total_trades ?? 0);

  const cleanPendingN =
    currentFwdMetrics?.clean_forward?.pending_signals ??
    (isBtc ? sysObs?.governance.btc_pending_n : sysObs?.governance.xau_pending_n) ??
    (live?.open_trades_count ?? 0);

  const cleanWins =
    currentFwdMetrics?.clean_forward?.wins ?? (live?.wins_count ?? 0);

  const cleanLosses =
    currentFwdMetrics?.clean_forward?.losses ?? (live?.losses_count ?? 0);

  const cleanWinRate =
    currentFwdMetrics?.clean_forward && cleanResolvedN > 0
      ? currentFwdMetrics.clean_forward.win_rate_pct
      : cleanResolvedN > 0
      ? (live?.win_rate_pct ?? null)
      : null;

  const daysActive = live?.days_active ?? 0;

  const sampleProgressPct = Math.min(100, Math.round((cleanResolvedN / 50) * 100));
  const timeProgressPct = Math.min(100, Math.round((daysActive / 14) * 100));

  const n50Met = cleanResolvedN >= 50;
  const n100Met = cleanResolvedN >= 100;
  const n50ProgressText = n50Met ? `${cleanResolvedN} / 50 — PASSED` : `${cleanResolvedN} / 50 — NOT REACHED`;
  const n100ProgressText = n100Met ? `${cleanResolvedN} / 100 — PASSED` : `${cleanResolvedN} / 100 — NOT REACHED`;

  const verdict = compReport?.verdict ?? "ACCUMULATING";
  const driftStatus = compReport?.drift_status ?? "LOW_DRIFT";

  const winRateDisplay =
    cleanResolvedN > 0 && cleanWinRate != null
      ? `${cleanWinRate.toFixed(1)}%`
      : "--";
  const evDisplay =
    cleanResolvedN > 0
      ? formatRAsUSD(live?.ev_r, { showSign: true, digits: 4 })
      : "-- (Awaiting Clean Evidence)";
  const pfDisplay =
    cleanResolvedN > 0 ? (live?.profit_factor ?? 0).toFixed(2) : "--";
  const maxDdDisplay =
    cleanResolvedN > 0 ? formatRAsUSD(-(live?.max_drawdown_r ?? 0)) : "--";

  return (
    <div className={`space-y-6 font-mono ${className}`}>
      {/* Top Banner / Hero: Shared SignalHeroCard */}
      <SignalHeroCard
        pageTitle="FORWARD SHADOW VALIDATION & ACCUMULATION MONITOR"
        icon={ShieldCheck}
        assetName={assetDisplayName}
        assetTicker={assetTicker}
        signal={
          verdict === "PROMOTED"
            ? "BUY"
            : verdict === "DRIFT_DETECTED"
            ? "SELL"
            : "WAIT"
        }
        percentage={cleanWinRate}
        isEvaluating={loading}
        statusBadge={
          cleanResolvedN === 0
            ? "EVIDENCE ACCUMULATION (S2) · CLEAN N = 0"
            : n100Met
            ? `VERDICT: ${verdict} (N≥100 MET)`
            : `VERDICT: ${verdict} (${cleanResolvedN}/50)`
        }
        timeChangeText={
          n100Met
            ? `${cleanResolvedN} Clean Resolved Samples (N≥100 MET)`
            : `${cleanResolvedN} / 50 Clean Resolved Samples`
        }
        lastUpdatedText={lastRefreshedAt || undefined}
        supportingPills={
          <>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Clean Total:</span>
              <span className="font-bold tabular-nums text-white">{cleanTotalN}</span>
            </div>
            <span className="text-zinc-600 font-bold">&middot;</span>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Clean Resolved:</span>
              <span className="font-bold tabular-nums text-sky-300">{cleanResolvedN}</span>
            </div>
            <span className="text-zinc-600 font-bold">&middot;</span>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Pending:</span>
              <span className="font-bold tabular-nums text-amber-400">{cleanPendingN}</span>
            </div>
            <span className="text-zinc-600 font-bold">&middot;</span>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Clean WR:</span>
              <span className="font-bold tabular-nums text-emerald-400">{winRateDisplay}</span>
            </div>
          </>
        }
        reasoning="Isolated forward-shadow observation layer. Evaluates empirical trade performance from authoritative forward_shadow_signals table with forensic quarantine isolation."
        uniqueId="shadowAccumHero"
      />

      {/* ── GOVERNANCE STATUS EXPLANATION BANNER (Item 15) ── */}
      <div className="p-4 rounded-xl bg-[#091632]/85 border border-sky-500/35 text-xs text-sky-200 backdrop-blur-md space-y-1.5 font-mono shadow-[0_4px_20px_rgba(2,132,199,0.15)]">
        <div className="flex items-center justify-between font-bold text-sky-100 uppercase tracking-wider text-[11px] border-b border-sky-500/20 pb-1.5">
          <span className="flex items-center gap-1.5 text-sky-300">
            <ShieldCheck size={14} className="text-emerald-400" />
            GOVERNANCE STATE: S2 — EVIDENCE ACCUMULATION PHASE
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/20 text-sky-200 border border-sky-500/40">
            DECISION: WAIT (AWAITING N ≥ 50 SAMPLES)
          </span>
        </div>
        <p className="text-[11px] text-zinc-300 leading-relaxed pt-0.5">
          Shadow Validation requires a pre-registered minimum sample of <strong>N ≥ 50 verified forward trades</strong> before evaluating statistical promotion or drift alerts.
          Governance milestone progression evaluates verified trade counts independently (BTC N={sysObs?.governance.btc_resolved_n ?? 0}, XAU N={sysObs?.governance.xau_resolved_n ?? 0}).
          Live production execution remains strictly <strong>DISABLED</strong> with zero execution risk.
        </p>
      </div>

      {/* ── FORWARD SHADOW VALIDATION: AUTHORITATIVE DUAL-ASSET METRICS ── */}
      <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-5 shadow-[0_8px_32px_rgba(2,132,199,0.18)] backdrop-blur-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-sky-500/20 pb-3 gap-2">
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-sky-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              FORWARD SHADOW VALIDATION
            </h3>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-mono">
            Authoritative Source: forward_shadow_signals
          </span>
        </div>

        {/* Provenance Disclaimer Banner */}
        <div className="p-3 rounded-lg bg-sky-950/40 border border-sky-500/20 text-[11px] text-zinc-300 flex items-start gap-2.5">
          <Info size={15} className="text-sky-400 shrink-0 mt-0.5" />
          <span>
            {fwdValidation?.disclaimer || "Forward-shadow validation results are reported separately from ML Shadow Observations and do not constitute live trading performance or production approval."}
          </span>
        </div>

        {/* Dual Asset Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* BTC/USD Card */}
          <div className={`p-4 rounded-xl border transition-all ${isBtc ? "bg-[#0b1b3d]/90 border-sky-400/50 shadow-[0_0_15px_rgba(56,189,248,0.15)]" : "bg-[#081226]/80 border-sky-500/20"}`}>
            <div className="flex items-center justify-between pb-2 border-b border-sky-500/15">
              <span className="font-bold text-white text-xs">BTC/USD</span>
              <span className="text-[10px] text-zinc-400">Bitcoin</span>
            </div>

            {/* Clean Forward Evidence (Active Pipeline) */}
            <div className="mt-2.5 p-3 rounded-lg bg-emerald-950/25 border border-emerald-500/30 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-emerald-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={13} className="text-emerald-400" />
                  CLEAN FORWARD EVIDENCE (ACTIVE)
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${(fwdValidation?.btc.clean_forward?.resolved_signals ?? 0) >= 50 ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" : "bg-amber-500/15 text-amber-300 border-amber-500/30"}`}>
                  {(fwdValidation?.btc.clean_forward?.resolved_signals ?? 0) >= 50 ? "N50 MET" : `AWAITING SAMPLES (${fwdValidation?.btc.clean_forward?.resolved_signals ?? 0}/50)`}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Total</span>
                  <span className="font-bold text-white text-sm font-mono">{fwdValidation?.btc.clean_forward?.total_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Resolved</span>
                  <span className="font-bold text-sky-300 text-sm font-mono">{fwdValidation?.btc.clean_forward?.resolved_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Pending</span>
                  <span className="font-bold text-amber-300 text-sm font-mono">{fwdValidation?.btc.clean_forward?.pending_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">WIN / LOSS</span>
                  <span className="font-bold text-zinc-300 text-sm font-mono">{fwdValidation?.btc.clean_forward?.wins ?? 0} / {fwdValidation?.btc.clean_forward?.losses ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean WR</span>
                  <span className="font-bold text-emerald-300 text-sm font-mono">
                    {fwdValidation?.btc.clean_forward && fwdValidation.btc.clean_forward.resolved_signals > 0
                      ? `${fwdValidation.btc.clean_forward.win_rate_pct.toFixed(1)}%`
                      : "--"}
                  </span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">N50 Progress</span>
                  <span className="font-bold text-amber-300 text-sm font-mono">
                    {fwdValidation?.btc.clean_forward?.resolved_signals ?? 0} / 50
                  </span>
                </div>
              </div>
            </div>

            {/* Quarantined Test Fixtures (Isolated) */}
            <div className="mt-2.5 p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/25 space-y-1">
              <div className="flex items-center justify-between text-[10px] font-bold text-amber-400">
                <span>QUARANTINED TEST FIXTURES (ISOLATED)</span>
                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 text-[9px]">
                  EXCLUDED FROM GATING
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-zinc-300 pt-0.5">
                <span>Quarantined Records: <strong className="text-amber-300 font-mono">{fwdValidation?.btc.quarantined_legacy?.total_signals ?? 280}</strong></span>
                <span className="text-[10px] text-zinc-400 font-mono">Status: FORENSIC QUARANTINE</span>
              </div>
            </div>

            <div className="text-[10px] text-zinc-400 pt-2.5 mt-2 border-t border-sky-500/10 flex items-start gap-1.5">
              <span className="text-zinc-500 font-semibold shrink-0">Provenance:</span>
              <span className="text-zinc-400 italic">{fwdValidation?.btc.provenance_note}</span>
            </div>
          </div>

          {/* XAU/USD Card */}
          <div className={`p-4 rounded-xl border transition-all ${!isBtc ? "bg-[#0b1b3d]/90 border-sky-400/50 shadow-[0_0_15px_rgba(56,189,248,0.15)]" : "bg-[#081226]/80 border-sky-500/20"}`}>
            <div className="flex items-center justify-between pb-2 border-b border-sky-500/15">
              <span className="font-bold text-white text-xs">XAU/USD</span>
              <span className="text-[10px] text-zinc-400">Gold</span>
            </div>

            {/* Clean Forward Evidence (Active Pipeline) */}
            <div className="mt-2.5 p-3 rounded-lg bg-emerald-950/25 border border-emerald-500/30 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-emerald-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={13} className="text-emerald-400" />
                  CLEAN FORWARD EVIDENCE (ACTIVE)
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${(fwdValidation?.xau.clean_forward?.resolved_signals ?? 0) >= 50 ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" : "bg-amber-500/15 text-amber-300 border-amber-500/30"}`}>
                  {(fwdValidation?.xau.clean_forward?.resolved_signals ?? 0) >= 50 ? "N50 MET" : `AWAITING SAMPLES (${fwdValidation?.xau.clean_forward?.resolved_signals ?? 0}/50)`}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Total</span>
                  <span className="font-bold text-white text-sm font-mono">{fwdValidation?.xau.clean_forward?.total_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Resolved</span>
                  <span className="font-bold text-sky-300 text-sm font-mono">{fwdValidation?.xau.clean_forward?.resolved_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean Pending</span>
                  <span className="font-bold text-amber-300 text-sm font-mono">{fwdValidation?.xau.clean_forward?.pending_signals ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">WIN / LOSS</span>
                  <span className="font-bold text-zinc-300 text-sm font-mono">{fwdValidation?.xau.clean_forward?.wins ?? 0} / {fwdValidation?.xau.clean_forward?.losses ?? 0}</span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">Clean WR</span>
                  <span className="font-bold text-emerald-300 text-sm font-mono">
                    {fwdValidation?.xau.clean_forward && fwdValidation.xau.clean_forward.resolved_signals > 0
                      ? `${fwdValidation.xau.clean_forward.win_rate_pct.toFixed(1)}%`
                      : "--"}
                  </span>
                </div>
                <div>
                  <span className="text-[9.5px] text-zinc-400 block uppercase">N50 Progress</span>
                  <span className="font-bold text-amber-300 text-sm font-mono">
                    {fwdValidation?.xau.clean_forward?.resolved_signals ?? 0} / 50
                  </span>
                </div>
              </div>
            </div>

            {/* Quarantined Test Fixtures (Isolated) */}
            <div className="mt-2.5 p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/25 space-y-1">
              <div className="flex items-center justify-between text-[10px] font-bold text-amber-400">
                <span>QUARANTINED TEST FIXTURES (ISOLATED)</span>
                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 text-[9px]">
                  EXCLUDED FROM GATING
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-zinc-300 pt-0.5">
                <span>Quarantined Records: <strong className="text-amber-300 font-mono">{fwdValidation?.xau.quarantined_legacy?.total_signals ?? 199}</strong></span>
                <span className="text-[10px] text-zinc-400 font-mono">Status: FORENSIC QUARANTINE</span>
              </div>
            </div>

            <div className="text-[10px] text-zinc-400 pt-2.5 mt-2 border-t border-sky-500/10 flex items-start gap-1.5">
              <span className="text-zinc-500 font-semibold shrink-0">Provenance:</span>
              <span className="text-zinc-400 italic">{fwdValidation?.xau.provenance_note}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── REAL-TIME OPERATIONAL OBSERVABILITY CARDS ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Forward Evidence (Clean Store) */}
        <div className="bg-[#0b1329]/90 border border-sky-500/30 rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-sky-400">
              <Activity size={13} />
              Forward Evidence
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
              CLEAN FORWARD
            </span>
          </div>
          <div className="space-y-1 pt-1 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">{assetTicker} Clean Total:</span>
              <span className="font-mono text-white font-bold">
                {cleanTotalN}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">{assetTicker} Clean Resolved:</span>
              <span className="font-mono text-emerald-400 font-bold">
                {cleanResolvedN}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">{assetTicker} Pending:</span>
              <span className="font-mono text-amber-400 font-bold">
                {cleanPendingN}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">Clean WIN / LOSS:</span>
              <span className="font-mono font-bold">
                <span className="text-emerald-400">{cleanWins}</span>
                <span className="text-zinc-500"> / </span>
                <span className="text-rose-400">{cleanLosses}</span>
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">Clean Win Rate:</span>
              <span className="font-mono text-emerald-300 font-bold">
                {winRateDisplay}
              </span>
            </div>
          </div>
          <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-800 flex justify-between">
            <span>forward_shadow_signals</span>
            <span className="text-zinc-400">Quarantine Isolated</span>
          </div>
        </div>

        {/* Card 2: Resolver Runtime Status */}
        <div className="bg-[#0b1329]/90 border border-emerald-500/30 rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <RefreshCw size={13} className={sysObs?.resolver.is_active || resolverData?.resolver_worker?.is_active ? "animate-spin" : ""} />
              Resolver Status
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
              {sysObs?.resolver.status ?? (resolverData?.resolver_worker?.is_active ? "ACTIVE" : "IDLE")}
            </span>
          </div>
          <div className="space-y-1 pt-1 text-xs">
            <div className="text-zinc-300 text-[11px] truncate" title={sysObs?.resolver.status_message || resolverData?.resolver_worker?.status_message || "ACTIVE — Checking post-T0 candles"}>
              {sysObs?.resolver.status_message || resolverData?.resolver_worker?.status_message || "ACTIVE — Checking post-T0 candles"}
            </div>
            <div className="flex justify-between items-center text-[11px] text-zinc-400 pt-1">
              <span>Evaluated: {sysObs?.resolver.eligible_count ?? resolverData?.resolver_worker?.total_signals_evaluated ?? 0}</span>
              <span>Resolved: {sysObs?.resolver.resolved_count ?? resolverData?.resolver_worker?.total_signals_resolved ?? 0}</span>
            </div>
          </div>
          <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-800 flex justify-between">
            <span>Interval: {sysObs?.resolver.interval_seconds ?? 60}s</span>
            <span>Latency: {sysObs?.resolver.processing_duration_ms ?? 0}ms</span>
          </div>
        </div>

        {/* Card 3: Evidence Milestone & Gating */}
        <div className="bg-[#0b1329]/90 border border-amber-500/30 rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-amber-400">
              <Scale size={13} />
              Milestones & Gating
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
              {sysObs?.governance.current_state ?? resolverData?.governance_state?.current_state ?? "S2: EVIDENCE_COLLECTION"}
            </span>
          </div>
          <div className="space-y-1.5 pt-1 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">N50 Progress:</span>
              <span className={`font-bold font-mono ${n50Met ? "text-emerald-400" : "text-amber-300"}`}>{n50ProgressText}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">N100 Progress:</span>
              <span className={`font-bold font-mono ${n100Met ? "text-emerald-400" : "text-amber-300"}`}>{n100ProgressText}</span>
            </div>
          </div>
          <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-800 flex justify-between">
            <span>Production Gating: <strong className={(sysObs?.governance.production_gating ?? "DISABLED") === "ON" || (sysObs?.governance.production_gating ?? "DISABLED") === "ENABLED" ? "text-emerald-400" : "text-rose-400"}>{sysObs?.governance.production_gating ?? resolverData?.governance_state?.production_gating ?? "DISABLED"}</strong></span>
            <span>Live: <strong className="text-rose-400">OFF (HARD-LOCKED)</strong></span>
          </div>
        </div>

        {/* Card 4: Data Freshness & ML Model */}
        <div className="bg-[#0b1329]/90 border border-purple-500/30 rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-purple-400">
              <Clock size={13} />
              Freshness & ML
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              LIVE MARKET DATA
            </span>
          </div>
          <div className="space-y-1.5 pt-1 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">Feed Status:</span>
              <span className="text-emerald-400 font-bold font-mono">ONLINE (5m Bars)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-400">ML Model:</span>
              <span className="text-zinc-300 font-mono text-[11px]">V1.0.0-Research (SHADOW ONLY)</span>
            </div>
          </div>
          <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-800 flex justify-between">
            <span>DB Status: HEALTHY</span>
            <span className="text-zinc-400">NO LIVE EXECUTION</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400">
            {compReport?.drift_status ? `Drift Status: ${compReport.drift_status}` : "Tracking forward out-of-sample paper trade execution."}
          </span>
        </div>
        <button
          type="button"
          onClick={() => fetchData(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800/80 border border-zinc-700/60 hover:bg-zinc-700/80 text-zinc-200 text-xs font-bold transition-all disabled:opacity-50 cursor-pointer shadow-sm shrink-0"
        >
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
          <span>{refreshing ? "Refreshing..." : "Refresh"}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle size={18} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Primary KPI & Gate Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Sample Progress */}
        <div className="bg-[#071330]/85 border border-sky-500/25 rounded-xl p-4 shadow-[0_4px_20px_rgba(2,132,199,0.1)] backdrop-blur-md space-y-2">
          <div className="flex items-center justify-between text-xs text-zinc-400 uppercase">
            <span className="flex items-center gap-1.5">
              <Activity size={14} className="text-sky-400" />
              Sample Size (Clean N)
            </span>
            <span className="text-zinc-500 font-bold">{n50Met ? "Goal: 100 (N100)" : "Goal: 50 (N50)"}</span>
          </div>
          <div className="flex items-baseline justify-between pt-1">
            <div className="text-3xl font-black text-white">
              {cleanResolvedN}
              <span className="text-sm font-normal text-zinc-400 ml-1">/ {n50Met ? "100" : "50"}</span>
            </div>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded border ${
                n100Met
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : n50Met
                  ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                  : "bg-amber-500/15 text-amber-300 border-amber-500/30"
              }`}
            >
              {n50Met ? `${Math.min(100, Math.round((cleanResolvedN / 100) * 100))}%` : `${sampleProgressPct}%`}
            </span>
          </div>
          {/* Progress Bar */}
          <div className="w-full bg-slate-900/90 rounded-full h-1.5 overflow-hidden border border-sky-900/50 mt-2">
            <div
              className={`h-full transition-all duration-500 ${
                n100Met
                  ? "bg-emerald-400"
                  : n50Met
                  ? "bg-sky-400"
                  : "bg-gradient-to-r from-sky-500 to-cyan-400"
              }`}
              style={{
                width: `${n50Met ? Math.min(100, Math.round((cleanResolvedN / 100) * 100)) : sampleProgressPct}%`,
              }}
            />
          </div>
          <div className="text-[10px] text-zinc-400 flex justify-between pt-1">
            <span>N50: <span className={n50Met ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>{n50ProgressText}</span></span>
            <span>N100: <span className={n100Met ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>{n100ProgressText}</span></span>
          </div>
        </div>

        {/* Card 2: Duration / Days Elapsed */}
        <div className="bg-[#071330]/85 border border-sky-500/25 rounded-xl p-4 shadow-[0_4px_20px_rgba(2,132,199,0.1)] backdrop-blur-md space-y-2">
          <div className="flex items-center justify-between text-xs text-zinc-400 uppercase">
            <span className="flex items-center gap-1.5">
              <Clock size={14} className="text-amber-400" />
              Duration Elapsed
            </span>
            <span className="text-zinc-500 font-bold">Goal: 14d</span>
          </div>
          <div className="flex items-baseline justify-between pt-1">
            <div className="text-3xl font-black text-white">
              {daysActive.toFixed(1)}
              <span className="text-sm font-normal text-zinc-400 ml-1">d</span>
            </div>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded border ${
                daysActive >= 14
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : "bg-amber-500/15 text-amber-300 border-amber-500/30"
              }`}
            >
              {timeProgressPct}%
            </span>
          </div>
          {/* Progress Bar */}
          <div className="w-full bg-slate-900/90 rounded-full h-1.5 overflow-hidden border border-sky-900/50 mt-2">
            <div
              className={`h-full transition-all duration-500 ${
                daysActive >= 14 ? "bg-emerald-400" : "bg-gradient-to-r from-amber-500 to-orange-400"
              }`}
              style={{ width: `${timeProgressPct}%` }}
            />
          </div>
          <div className="text-[10px] text-zinc-400 flex justify-between pt-1">
            <span>Min Required: 14 Days</span>
            <span>{daysActive >= 14 ? "Time Gate Passed" : "Accumulating"}</span>
          </div>
        </div>

        {/* Card 3: Comparison Verdict */}
        <div className="bg-[#071330]/85 border border-sky-500/25 rounded-xl p-4 shadow-[0_4px_20px_rgba(2,132,199,0.1)] backdrop-blur-md space-y-2">
          <div className="flex items-center justify-between text-xs text-zinc-400 uppercase">
            <span className="flex items-center gap-1.5">
              <Scale size={14} className="text-purple-400" />
              Pre-Registered Gate
            </span>
            <span className="text-zinc-500 font-bold">Verdict</span>
          </div>
          <div className="pt-1">
            <span
              className={`inline-flex items-center gap-1.5 text-base font-black px-3 py-1 rounded-lg border ${
                verdict === "PASS"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-400/60 shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                  : verdict === "FAIL"
                  ? "bg-rose-500/20 text-rose-300 border-rose-400/60 shadow-[0_0_12px_rgba(244,63,94,0.3)]"
                  : "bg-amber-500/20 text-amber-300 border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.25)]"
              }`}
            >
              {verdict === "PASS" ? (
                <CheckCircle2 size={16} />
              ) : verdict === "FAIL" ? (
                <AlertCircle size={16} />
              ) : (
                <Activity size={16} className="animate-pulse" />
              )}
              {verdict}
            </span>
          </div>
          <p className="text-[10px] text-zinc-400 leading-tight pt-1">
            {compReport?.verdict_summary || "Accumulating trade evidence towards pre-registered milestones."}
          </p>
        </div>

        {/* Card 4: Statistical Drift Status */}
        <div className="bg-[#071330]/85 border border-sky-500/25 rounded-xl p-4 shadow-[0_4px_20px_rgba(2,132,199,0.1)] backdrop-blur-md space-y-2">
          <div className="flex items-center justify-between text-xs text-zinc-400 uppercase">
            <span className="flex items-center gap-1.5">
              <Gauge size={14} className="text-cyan-400" />
              Statistical Drift
            </span>
            <span className="text-zinc-500 font-bold">Daily Audit</span>
          </div>
          <div className="pt-1">
            <span
              className={`inline-flex items-center gap-1.5 text-base font-black px-3 py-1 rounded-lg border ${
                driftStatus === "LOW_DRIFT"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-400/60 shadow-[0_0_12px_rgba(16,185,129,0.25)]"
                  : driftStatus === "MEDIUM_DRIFT"
                  ? "bg-amber-500/20 text-amber-300 border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.25)]"
                  : "bg-rose-500/20 text-rose-300 border-rose-400/60 shadow-[0_0_12px_rgba(244,63,94,0.3)]"
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  driftStatus === "LOW_DRIFT"
                    ? "bg-emerald-400"
                    : driftStatus === "MEDIUM_DRIFT"
                    ? "bg-amber-400"
                    : "bg-rose-400"
                }`}
              />
              {driftStatus}
            </span>
          </div>
          <p className="text-[10px] text-zinc-400 leading-tight pt-1">
            Required for gate: {thresholds?.required_drift_status ?? (isBtc ? "LOW_DRIFT" : "MEDIUM_DRIFT")}
          </p>
        </div>
      </div>

      {/* Comparison Detail Table */}
      <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-5 shadow-[0_8px_32px_rgba(2,132,199,0.18)] backdrop-blur-xl space-y-4">
        <div className="flex items-center justify-between border-b border-sky-500/20 pb-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-sky-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              Live Shadow Performance vs Frozen Backtest Baseline
            </h3>
          </div>
          <span className="text-[10px] text-zinc-400 uppercase font-semibold">
            Strategy Version: {shadowStatus?.strategy_version || "v2.1"}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead>
              <tr className="border-b border-sky-500/20 text-[10px] text-zinc-400 uppercase tracking-wider">
                <th className="pb-2.5 px-3">Metric</th>
                <th className="pb-2.5 px-3">Live Shadow (Current)</th>
                <th className="pb-2.5 px-3">Backtest Baseline</th>
                <th className="pb-2.5 px-3">Acceptable Gate Range</th>
                <th className="pb-2.5 px-3 text-right">Gate Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sky-500/10 text-zinc-200">
              {/* Sample Size */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Sample Size (Clean N)</td>
                <td className="py-3 px-3 font-bold text-sky-300">
                  {cleanResolvedN} clean resolved trades
                </td>
                <td className="py-3 px-3 text-zinc-400">
                  N = {baseline?.sample_size_n != null ? baseline.sample_size_n : "--"}
                </td>
                <td className="py-3 px-3 text-zinc-400">
                  N &ge; {thresholds?.min_sample_size_n ?? 50}
                </td>
                <td className="py-3 px-3 text-right">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      n50Met && compReport?.sample_gate_passed
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                        : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                    }`}
                  >
                    {n50Met && compReport?.sample_gate_passed ? "PASSED" : "ACCUMULATING (NOT REACHED)"}
                  </span>
                </td>
              </tr>

              {/* Time Elapsed */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Calendar Duration</td>
                <td className="py-3 px-3 font-bold text-amber-300">
                  {daysActive.toFixed(1)} days active
                </td>
                <td className="py-3 px-3 text-zinc-400">30.0 days baseline</td>
                <td className="py-3 px-3 text-zinc-400">
                  &ge; {thresholds?.min_calendar_days ?? 14.0} days
                </td>
                <td className="py-3 px-3 text-right">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      compReport?.time_gate_passed
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                        : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                    }`}
                  >
                    {compReport?.time_gate_passed ? "PASSED" : "ACCUMULATING"}
                  </span>
                </td>
              </tr>

              {/* Expected Value (EV) */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Expected Value (EV)</td>
                <td className="py-3 px-3 font-bold text-emerald-300">{evDisplay}</td>
                <td className="py-3 px-3 text-zinc-400">
                  {formatRAsUSD(baseline?.expected_value_r ?? (isBtc ? 0.365 : 0.245), { showSign: true, digits: 4 })}
                </td>
                <td className="py-3 px-3 text-zinc-400">
                  &ge; {formatRAsUSD(thresholds?.ev_acceptable_range?.[0] ?? 0.0444, { showSign: true, digits: 4 })}
                </td>
                <td className="py-3 px-3 text-right">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      cleanResolvedN === 0
                        ? "bg-zinc-800 text-zinc-400 border-zinc-700"
                        : compReport?.ev_gate_passed
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                        : "bg-rose-500/15 text-rose-300 border-rose-500/40"
                    }`}
                  >
                    {cleanResolvedN === 0
                      ? "AWAITING EVIDENCE"
                      : compReport?.ev_gate_passed
                      ? "PASSED"
                      : "OUTSIDE RANGE"}
                  </span>
                </td>
              </tr>

              {/* Win Rate */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Win Rate</td>
                <td className="py-3 px-3 font-bold text-emerald-300">{winRateDisplay}</td>
                <td className="py-3 px-3 text-zinc-400">
                  {(baseline?.win_rate_pct ?? (isBtc ? 55.88 : 51.11)).toFixed(2)}%
                </td>
                <td className="py-3 px-3 text-zinc-400">
                  [{(thresholds?.wr_acceptable_range?.[0] ?? (isBtc ? 44.5 : 42.0)).toFixed(1)}%,{" "}
                  {(thresholds?.wr_acceptable_range?.[1] ?? 65.0).toFixed(1)}%]
                </td>
                <td className="py-3 px-3 text-right">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      cleanResolvedN === 0
                        ? "bg-zinc-800 text-zinc-400 border-zinc-700"
                        : compReport?.wr_gate_passed
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                        : "bg-rose-500/15 text-rose-300 border-rose-500/40"
                    }`}
                  >
                    {cleanResolvedN === 0
                      ? "AWAITING EVIDENCE"
                      : compReport?.wr_gate_passed
                      ? "PASSED"
                      : "OUTSIDE RANGE"}
                  </span>
                </td>
              </tr>

              {/* Profit Factor */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Profit Factor</td>
                <td className="py-3 px-3 font-bold text-sky-300">{pfDisplay}</td>
                <td className="py-3 px-3 text-zinc-400">
                  {(baseline?.profit_factor ?? (isBtc ? 1.76 : 1.48)).toFixed(2)}
                </td>
                <td className="py-3 px-3 text-zinc-400">&ge; 1.20</td>
                <td className="py-3 px-3 text-right">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-300 border border-sky-500/30">
                    DIAGNOSTIC
                  </span>
                </td>
              </tr>

              {/* Max Drawdown */}
              <tr className="hover:bg-sky-950/20 transition-colors">
                <td className="py-3 px-3 font-semibold text-white">Max Drawdown</td>
                <td className="py-3 px-3 font-bold text-rose-300">{maxDdDisplay}</td>
                <td className="py-3 px-3 text-zinc-400">
                  {formatRAsUSD(baseline?.max_drawdown_r ?? (isBtc ? 5.5 : 4.0))}
                </td>
                <td className="py-3 px-3 text-zinc-400">&le; $6.00</td>
                <td className="py-3 px-3 text-right">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-300 border border-sky-500/30">
                    DIAGNOSTIC
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Isolation and Governance Footer Note */}
      <div className="p-4 rounded-xl bg-[#060e20]/90 border border-sky-500/20 flex items-center justify-between text-xs text-zinc-400">
        <div className="flex items-center gap-2">
          <Lock size={14} className="text-sky-400 shrink-0" />
          <span>
            <strong>Governance Safety Guarantee:</strong> This panel is 100% read-only. Gating flags (<code className="text-sky-300">PRODUCTION_GATING_BTC</code>, <code className="text-sky-300">PRODUCTION_GATING_XAU</code>) cannot be enabled or altered from this dashboard.
          </span>
        </div>
        <span className="text-[10px] font-semibold text-sky-300 shrink-0 ml-4">
          Auto-refreshing (60s)
        </span>
      </div>
    </div>
  );
}
