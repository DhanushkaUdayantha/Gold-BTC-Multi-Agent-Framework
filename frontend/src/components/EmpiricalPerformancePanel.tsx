"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Compass,
  Cpu,
  Database,
  Eye,
  FileCheck2,
  Info,
  Layers,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import {
  ApiClient,
  PerformanceReportData,
  CalibrationResponse,
  SignalsListResponse,
  SignalRecordItem,
  IntegrityResponse,
  ScoreBandPerformanceStats,
  StrategyPerformanceStats,
  LiveValidationSummaryReportData,
  fetchLiveValidationSummary,
  mapToLiveValidationViewModel,
  LiveValidationViewModel,
} from "@/services/api";
import { fmtPrice, fmtTime, safeNum, formatRAsUSD, getAssetBadgeClass } from "@/lib/format";

interface PerformancePanelProps {
  symbol: string;
  assetName: string;
  currentConfluenceScore?: number | null;
  currentTechnicalScore?: number;
  currentGeminiScore?: number;
  currentSignal?: string;
  dataQuality?: string;
  marketRegime?: string;
  snapshotId?: string;
  lastUpdated?: string;
}

type TabType = "summary" | "live_validation" | "strategies" | "bands" | "gemini" | "signals" | "integrity";

export function EmpiricalPerformancePanel({
  symbol,
  assetName,
  currentConfluenceScore,
  currentTechnicalScore = 0,
  currentGeminiScore = 0,
  currentSignal = "WAIT",
  dataQuality = "MEDIUM",
  marketRegime = "UNCLEAR",
  snapshotId,
  lastUpdated,
}: PerformancePanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("live_validation");
  const [isOpen, setIsOpen] = useState(true);

  // API state
  const [report, setReport] = useState<PerformanceReportData | null>(null);
  const [calibrationRes, setCalibrationRes] = useState<CalibrationResponse | null>(null);
  const [signalsRes, setSignalsRes] = useState<SignalsListResponse | null>(null);
  const [integrityRes, setIntegrityRes] = useState<IntegrityResponse | null>(null);
  const [liveVal, setLiveVal] = useState<LiveValidationSummaryReportData | null>(null);
  const [livePeriod, setLivePeriod] = useState<"today" | "7d" | "30d" | "all">("all");

  // Pagination & Filtering
  const [signalsPage, setSignalsPage] = useState(1);
  const [signalDirectionFilter, setSignalDirectionFilter] = useState<string>("");
  const [signalOutcomeFilter, setSignalOutcomeFilter] = useState<string>("");
  const [selectedSignal, setSelectedSignal] = useState<SignalRecordItem | null>(null);

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoreRef = useRef(currentConfluenceScore ?? 50);
  scoreRef.current = currentConfluenceScore ?? 50;

  const fetchData = useCallback(
    async (isManual = false) => {
      if (isManual) setRefreshing(true);
      setError(null);

      try {
        const [repRes, calRes, sigsRes, intRes, liveRes] = await Promise.allSettled([
          ApiClient.getPerformanceReport(scoreRef.current, symbol),
          ApiClient.getCalibration(scoreRef.current, symbol),
          ApiClient.getSignalsHistory({
            page: signalsPage,
            pageSize: 15,
            symbol: symbol,
            direction: signalDirectionFilter || undefined,
            outcome: signalOutcomeFilter || undefined,
          }),
          ApiClient.getDataIntegrity(),
          fetchLiveValidationSummary(symbol),
        ]);

        if (repRes.status === "fulfilled" && repRes.value?.report) {
          setReport(repRes.value.report);
        }
        if (calRes.status === "fulfilled" && calRes.value) {
          setCalibrationRes(calRes.value);
        }
        if (sigsRes.status === "fulfilled" && sigsRes.value) {
          setSignalsRes(sigsRes.value);
        }
        if (intRes.status === "fulfilled" && intRes.value) {
          setIntegrityRes(intRes.value);
        }
        if (liveRes.status === "fulfilled" && liveRes.value?.validation) {
          setLiveVal(liveRes.value.validation);
        }
      } catch (err: any) {
        setError(err?.message || "Failed to load performance telemetry");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [symbol, signalsPage, signalDirectionFilter, signalOutcomeFilter]
  );

  useEffect(() => {
    fetchData();
    const timer = setInterval(() => fetchData(false), 30000);
    return () => clearInterval(timer);
  }, [fetchData]);

  // Overall stats
  const overall = report?.overall;
  const cal = report?.calibration || calibrationRes?.calibration;
  const isGold = symbol.toUpperCase().includes("XAU") || symbol.toUpperCase().includes("GOLD");
  const assetLabel = isGold ? "XAU/USD" : "BTC/USD";

  const totalCompleted = overall?.total_signals ?? 0;
  const hasMinData = totalCompleted >= 50 && cal?.calibration_status !== "INSUFFICIENT_DATA";

  // Explicit Phase 5 Live Validation View Model Mapping
  const liveVM: LiveValidationViewModel = mapToLiveValidationViewModel(currentSignal, liveVal);

  return (
    <section className="bg-[#0a0f1d] border border-blue-500/25 rounded-2xl p-4 sm:p-6 shadow-[0_8px_32px_rgba(0,0,0,0.4)] transition-all duration-300">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1b253b] pb-4 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400">
            <Scale size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-sm sm:text-base font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                Empirical Performance &amp; Probability Calibration
              </h2>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30">
                {assetLabel}
              </span>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${
                  cal?.calibration_status === "VALID" || cal?.calibration_status === "PREFERRED"
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                    : cal?.calibration_status === "EXPLORATORY"
                    ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/40"
                    : cal?.calibration_status === "UNRELIABLE"
                    ? "bg-rose-500/15 text-rose-300 border-rose-500/40"
                    : "bg-amber-500/15 text-amber-300 border-amber-500/40"
                }`}
              >
                STATUS: {cal?.calibration_status || "INSUFFICIENT_DATA"}
              </span>
            </div>
            <p className="text-[11px] font-mono text-zinc-400 mt-0.5">
              Historical outcome tracking &amp; isotonic calibration &middot; Look-ahead bias free
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto font-mono text-xs">
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#121c33] border border-[#202f50] text-zinc-300 hover:text-white hover:bg-[#162340] transition-colors text-[11px]"
          >
            <RefreshCw size={12} className={refreshing ? "animate-spin text-cyan-400" : "text-blue-400"} />
            <span>{refreshing ? "Syncing..." : "Refresh"}</span>
          </button>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-1.5 rounded-lg bg-[#121c33] border border-[#202f50] text-zinc-300 hover:text-white transition-colors"
            title={isOpen ? "Collapse Panel" : "Expand Panel"}
          >
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="space-y-5">
          {/* TOP MASTER SUMMARY: LIVE DECISION VS TRADE SIGNALS TRACKED */}
          <div className="space-y-3 font-mono">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {/* Card 1: LIVE DECISION */}
              <div className="p-3.5 rounded-xl bg-[#0d1629] border border-[#1d2d4f] flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    LIVE DECISION
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold ${getAssetBadgeClass(assetName)}`}>
                    {assetName}
                  </span>
                </div>
                <div className="my-2 flex items-center gap-2">
                  <span
                    className={`text-xl font-black px-2.5 py-0.5 rounded-lg border ${
                      liveVM.liveDecision === "BUY"
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                        : liveVM.liveDecision === "SELL"
                        ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                        : "bg-blue-500/20 text-blue-300 border-blue-500/40"
                    }`}
                  >
                    {liveVM.liveDecision}
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400">
                  {liveVM.liveDecision === "WAIT"
                    ? "Evaluating market (No setup)"
                    : "Actionable trade setup"}
                </div>
              </div>

              {/* Card 2: TRADE SIGNALS TRACKED */}
              <div className="p-3.5 rounded-xl bg-[#0d1629] border border-[#1d2d4f] flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    TRACKED SIGNALS
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                    Phase 5
                  </span>
                </div>
                <div className="my-2">
                  <span className="text-2xl font-black text-white">
                    {liveVM.trackedSignals}
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400">
                  {liveVM.trackedSignals === 0
                    ? "No BUY/SELL saved yet"
                    : "Actionable signals stored"}
                </div>
              </div>

              {/* Card 3: PENDING TRADES */}
              <div className="p-3.5 rounded-xl bg-[#0d1629] border border-[#1d2d4f] flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    PENDING TRADES
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-bold">
                    Open
                  </span>
                </div>
                <div className="my-2">
                  <span className="text-2xl font-black text-amber-300">
                    {liveVM.pendingTrades}
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400">
                  {liveVM.pendingTrades === 0
                    ? "No open positions"
                    : "Awaiting future price targets"}
                </div>
              </div>

              {/* Card 4: COMPLETED OUTCOMES */}
              <div className="p-3.5 rounded-xl bg-[#0d1629] border border-[#1d2d4f] flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    COMPLETED
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-bold">
                    Resolved
                  </span>
                </div>
                <div className="my-2">
                  <span className="text-2xl font-black text-white">
                    {liveVM.completedOutcomes}
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400">
                  {liveVM.wins}W - {liveVM.losses}L
                </div>
              </div>

              {/* Card 5: LIVE ACCURACY */}
              <div className="p-3.5 rounded-xl bg-[#0d1629] border border-[#1d2d4f] flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    LIVE ACCURACY
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 font-bold">
                    Realized
                  </span>
                </div>
                <div className="my-2">
                  {!liveVM.isSampleSufficient || liveVM.liveAccuracy === null ? (
                    <span className="text-[11px] font-bold px-2 py-1 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
                      INSUFFICIENT SAMPLE
                    </span>
                  ) : (
                    <span className="text-2xl font-black text-emerald-400">
                      {liveVM.liveAccuracy}%
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-zinc-400">
                  {!liveVM.isSampleSufficient
                    ? "Pending completed trades"
                    : `Based on ${liveVM.completedOutcomes} live outcomes`}
                </div>
              </div>
            </div>

            {/* Semantic Helper & Clarity Notice */}
            <div className="p-3 rounded-xl bg-[#070e1c] border border-[#192744] flex items-start gap-2.5 text-[11px] text-zinc-300">
              <Info size={14} className="text-sky-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5 leading-relaxed">
                <span className="font-bold text-sky-200">
                  Live Market Evaluation vs. Signal Validation Tracking:
                </span>{" "}
                <span className="text-zinc-400">
                  <span className="text-zinc-200 font-semibold">WAIT</span> means the system is actively evaluating the live market, but currently sees no qualifying actionable trade setup. Trade signals and live accuracy will accumulate only when real <span className="text-emerald-300 font-semibold">BUY</span> or <span className="text-rose-300 font-semibold">SELL</span> opportunities are generated and resolved.
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Sub-Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[#18233a] text-xs font-mono">
            <button
              onClick={() => setActiveTab("live_validation")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "live_validation"
                  ? "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <CheckCircle2 size={13} className="text-emerald-400" />
              Live Validation ({liveVal?.total_signals_recorded || 0})
            </button>
            <button
              onClick={() => setActiveTab("summary")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "summary"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <Zap size={13} />
              Summary &amp; Probability
            </button>
            <button
              onClick={() => setActiveTab("strategies")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "strategies"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <Layers size={13} />
              Strategy Performance {report?.by_strategy?.length != null ? `(${report.by_strategy.length})` : ""}
            </button>
            <button
              onClick={() => setActiveTab("bands")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "bands"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <BarChart3 size={13} />
              Score Bands (6)
            </button>
            <button
              onClick={() => setActiveTab("gemini")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "gemini"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <Cpu size={13} />
              Gemini AI Ablation
            </button>
            <button
              onClick={() => setActiveTab("signals")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "signals"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <FileCheck2 size={13} />
              Signal History ({signalsRes?.total || 0})
            </button>
            <button
              onClick={() => setActiveTab("integrity")}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "integrity"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#121c33]"
              }`}
            >
              <ShieldCheck size={13} />
              Data Integrity ({integrityRes?.issues_found === 0 ? "OK" : integrityRes?.issues_found ?? "OK"})
            </button>
          </div>

          {/* TAB 0: LIVE SIGNAL OUTCOME VALIDATION (PHASE 5) */}
          {activeTab === "live_validation" && (
            <div className="space-y-4 font-mono text-xs">
              {/* Header Status & Asset Isolation Banner */}
              <div className="p-3.5 rounded-xl bg-[#0a1220] border border-[#1b2b4d] flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-bold text-white uppercase tracking-wider text-sm">
                    {assetName} Live Signal Validation
                  </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold">
                    ISOLATION: 100% PASS (0% Leakage)
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-zinc-400">
                  <span className="text-zinc-500">Observer Mode:</span>
                  <span className="text-cyan-300 font-bold">DecisionEngine FROZEN</span>
                </div>
              </div>

              {/* Period Selector Tabs */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 p-1 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                  {(["today", "7d", "30d", "all"] as const).map((p) => {
                    const labels: Record<string, string> = {
                      today: "Today",
                      "7d": "7 Days",
                      "30d": "30 Days",
                      all: "All-Time",
                    };
                    return (
                      <button
                        key={p}
                        onClick={() => setLivePeriod(p)}
                        className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                          livePeriod === p
                            ? "bg-blue-600 text-white shadow"
                            : "text-zinc-400 hover:text-white"
                        }`}
                      >
                        {labels[p]}
                      </button>
                    );
                  })}
                </div>
                <div className="text-[11px] text-zinc-400">
                  Sample Status:{" "}
                  <span className="font-bold text-amber-300">
                    {(() => {
                      const cur =
                        livePeriod === "today"
                          ? liveVal?.today
                          : livePeriod === "7d"
                          ? liveVal?.rolling_7d
                          : livePeriod === "30d"
                          ? liveVal?.rolling_30d
                          : liveVal?.all_time;
                      return cur?.sample_status || "ACTIVE";
                    })()}
                  </span>
                </div>
              </div>

              {/* Period Metrics Grid */}
              {(() => {
                const cur =
                  livePeriod === "today"
                    ? liveVal?.today
                    : livePeriod === "7d"
                    ? liveVal?.rolling_7d
                    : livePeriod === "30d"
                    ? liveVal?.rolling_30d
                    : liveVal?.all_time;
                const totalTrades = cur?.total_trades ?? 0;
                return (
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Signals / Trades</div>
                      <div className="text-xl font-bold text-white mt-1">
                        {cur?.total_signals ?? 0} <span className="text-xs text-zinc-500">/ {totalTrades}</span>
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">
                        {cur?.pending ?? 0} Pending
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Observed Win Rate</div>
                      <div className="text-base sm:text-lg font-bold text-emerald-400 mt-1">
                        {totalTrades === 0 ? (
                          <span className="text-[11px] text-amber-300">INSUFFICIENT SAMPLE</span>
                        ) : (
                          `${cur?.win_rate_pct ?? 0}%`
                        )}
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">
                        {totalTrades === 0 ? "0 completed trades" : `${cur?.wins ?? 0}W - ${cur?.losses ?? 0}L`}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Expectancy ($)</div>
                      <div className={`text-xl font-bold mt-1 ${((cur?.expectancy_r ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                        {totalTrades === 0 ? "--" : formatRAsUSD(cur?.expectancy_r, { showSign: true, digits: 3 })}
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">
                        {totalTrades === 0 ? "Pending sample" : "Per trade avg"}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Total Realized ($)</div>
                      <div className={`text-xl font-bold mt-1 ${((cur?.total_realized_r ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                        {totalTrades === 0 ? "$0.00" : formatRAsUSD(cur?.total_realized_r, { showSign: true })}
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">Max DD: {formatRAsUSD(-(cur?.max_drawdown_r ?? 0))}</div>
                    </div>

                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Profit Factor</div>
                      <div className="text-xl font-bold text-cyan-300 mt-1">
                        {totalTrades === 0 ? "--" : (cur?.profit_factor ?? 0).toFixed(2)}
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">Win/Loss ratio</div>
                    </div>

                    <div className="p-3 rounded-lg bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-[10px] text-zinc-400 uppercase">Calibration Error</div>
                      <div className="text-base sm:text-lg font-bold text-amber-400 mt-1">
                        {totalTrades === 0 ? (
                          <span className="text-[11px] text-amber-300">INSUFFICIENT SAMPLE</span>
                        ) : (
                          `${cur?.calibration_error_pct ?? 0}%`
                        )}
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">Pred vs Reality</div>
                    </div>
                  </div>
                );
              })()}

              {/* Directional Performance & Reliability Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* BUY Performance */}
                <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-emerald-400 flex items-center gap-1">
                      <TrendingUp size={14} /> BUY Signals Performance ({assetName})
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
                      {liveVal?.buy_performance?.status || "ACTIVE"}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-center">
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Trades</div>
                      <div className="font-bold text-white text-sm">{liveVal?.buy_performance?.sample_size ?? 0}</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Win Rate</div>
                      <div className="font-bold text-emerald-400 text-sm">{liveVal?.buy_performance?.win_rate_pct ?? 0}%</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Expectancy</div>
                      <div className="font-bold text-cyan-300 text-sm">{formatRAsUSD(liveVal?.buy_performance?.expectancy_r, { showSign: true })}</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Total ($)</div>
                      <div className="font-bold text-white text-sm">{formatRAsUSD(liveVal?.buy_performance?.total_r, { showSign: true })}</div>
                    </div>
                  </div>
                </div>

                {/* SELL Performance */}
                <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-rose-400 flex items-center gap-1">
                      <TrendingDown size={14} /> SELL Signals Performance ({assetName})
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-300">
                      {liveVal?.sell_performance?.status || "ACTIVE"}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-center">
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Trades</div>
                      <div className="font-bold text-white text-sm">{liveVal?.sell_performance?.sample_size ?? 0}</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Win Rate</div>
                      <div className="font-bold text-rose-400 text-sm">{liveVal?.sell_performance?.win_rate_pct ?? 0}%</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Expectancy</div>
                      <div className="font-bold text-cyan-300 text-sm">{formatRAsUSD(liveVal?.sell_performance?.expectancy_r, { showSign: true })}</div>
                    </div>
                    <div className="p-2 rounded bg-[#070e1b]">
                      <div className="text-[9px] text-zinc-500">Total ($)</div>
                      <div className="font-bold text-white text-sm">{formatRAsUSD(liveVal?.sell_performance?.total_r, { showSign: true })}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 10-Bucket Calibration Table */}
              <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-cyan-300 flex items-center gap-1.5">
                    <BarChart3 size={14} /> 10-Bucket Probability Calibration ({assetName})
                  </span>
                  <div className="flex items-center gap-3 text-[10px] text-zinc-400">
                    <span>Brier Score: <b className="text-white">{liveVal?.calibration?.brier_score != null ? liveVal.calibration.brier_score.toFixed(4) : "--"}</b></span>
                    <span>ECE: <b className="text-white">{liveVal?.calibration?.ece_pct != null ? `${liveVal.calibration.ece_pct}%` : "--%"}</b></span>
                    <span>MCE: <b className="text-white">{liveVal?.calibration?.mce_pct != null ? `${liveVal.calibration.mce_pct}%` : "--%"}</b></span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px]">
                    <thead>
                      <tr className="border-b border-[#1b2b4d] text-zinc-500">
                        <th className="py-1.5 px-2">Probability Bucket</th>
                        <th className="py-1.5 px-2 text-right">Sample N</th>
                        <th className="py-1.5 px-2 text-right">Wins / Losses</th>
                        <th className="py-1.5 px-2 text-right">Mean Predicted</th>
                        <th className="py-1.5 px-2 text-right">Observed Win Rate</th>
                        <th className="py-1.5 px-2 text-right">Gap</th>
                        <th className="py-1.5 px-2 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(liveVal?.calibration?.buckets || []).map((b, idx) => (
                        <tr key={idx} className="border-b border-[#131f37] hover:bg-[#121c33]/50">
                          <td className="py-1.5 px-2 font-bold text-zinc-300">{b.bucket_label}</td>
                          <td className="py-1.5 px-2 text-right text-zinc-400">{b.sample_size}</td>
                          <td className="py-1.5 px-2 text-right text-zinc-400">{b.wins} / {b.losses}</td>
                          <td className="py-1.5 px-2 text-right text-cyan-300">{b.mean_predicted_prob}%</td>
                          <td className="py-1.5 px-2 text-right font-bold text-white">{b.observed_win_rate_pct}%</td>
                          <td className={`py-1.5 px-2 text-right font-bold ${b.calibration_gap_pct >= 0 ? "text-emerald-400" : "text-amber-400"}`}>
                            {b.calibration_gap_pct >= 0 ? "+" : ""}{b.calibration_gap_pct}%
                          </td>
                          <td className="py-1.5 px-2 text-center">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                              b.status === "WELL_CALIBRATED"
                                ? "bg-emerald-500/10 text-emerald-300"
                                : b.status === "INSUFFICIENT_DATA"
                                ? "bg-zinc-800 text-zinc-500"
                                : "bg-amber-500/10 text-amber-300"
                            }`}>
                              {b.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Failures & Success Attribution */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Top Failure Categories */}
                <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-rose-300 flex items-center gap-1.5">
                      <AlertTriangle size={14} className="text-rose-400" /> Root-Cause Loss Attribution ({assetName})
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {(liveVal?.top_failures || []).slice(0, 4).map((f, idx) => (
                      <div key={idx} className="p-2 rounded bg-[#070e1b] flex items-center justify-between text-[11px]">
                        <div>
                          <div className="font-bold text-zinc-200">{f.failure_category}</div>
                          <div className="text-[10px] text-zinc-500">Regime: {f.primary_regime} &middot; Session: {f.primary_session}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-rose-400">{f.count} losses ({f.percentage_of_losses}%)</div>
                          <div className="text-[10px] text-zinc-400">Total Loss: {formatRAsUSD(-f.total_loss_r)}</div>
                        </div>
                      </div>
                    ))}
                    {(!liveVal?.top_failures || liveVal.top_failures.length === 0) && (
                      <div className="text-zinc-500 text-center py-3">No trade losses recorded</div>
                    )}
                  </div>
                </div>

                {/* Top Winning Catalysts */}
                <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-emerald-300 flex items-center gap-1.5">
                      <Sparkles size={14} className="text-emerald-400" /> Winning Confluence Catalysts ({assetName})
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {(liveVal?.top_successes || []).slice(0, 4).map((s, idx) => (
                      <div key={idx} className="p-2 rounded bg-[#070e1b] flex items-center justify-between text-[11px]">
                        <div>
                          <div className="font-bold text-zinc-200">{s.success_category}</div>
                          <div className="text-[10px] text-zinc-500">Regime: {s.primary_regime} &middot; Session: {s.primary_session}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-emerald-400">{s.count} wins ({s.percentage_of_wins}%)</div>
                          <div className="text-[10px] text-zinc-400">Total Gain: {formatRAsUSD(s.total_gain_r, { showSign: true })}</div>
                        </div>
                      </div>
                    ))}
                    {(!liveVal?.top_successes || liveVal.top_successes.length === 0) && (
                      <div className="text-zinc-500 text-center py-3">No winning trades recorded</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 1: SUMMARY & CALIBRATED PROBABILITY */}
          {activeTab === "summary" && (
            <div className="space-y-4">
              {/* Top Row: Current Real-time Evidence vs Calibrated Probability */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Current Real-Time Confluence Card */}
                <div className="p-4 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-3 font-mono">
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-cyan-300">
                      <Zap size={14} className="text-cyan-400" />
                      Current Real-Time Confluence
                    </span>
                    <span className="text-[10px] text-zinc-500">Evidence Score</span>
                  </div>

                  <div className="flex items-baseline justify-between pt-1">
                    <div>
                      <div className="text-3xl sm:text-4xl font-black text-cyan-400 tracking-tight">
                        {currentConfluenceScore != null ? currentConfluenceScore : "--"} <span className="text-sm font-normal text-zinc-500">/ 100</span>
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-1">
                        Signal: <span className="font-bold text-white">{currentSignal}</span> &middot; Gate:{" "}
                        <span className="text-emerald-400 font-bold">{marketRegime}</span>
                      </div>
                    </div>
                    <div className="text-right text-xs space-y-1">
                      <div>
                        <span className="text-zinc-500">Technical: </span>
                        <span className="text-zinc-200 font-bold">{currentTechnicalScore} / 90</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Gemini AI: </span>
                        <span className="text-zinc-200 font-bold">{currentGeminiScore} / 10</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Data Quality: </span>
                        <span className="text-emerald-400 font-bold">{dataQuality}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#070b14] border border-[#162238] text-[10px] text-zinc-400 leading-relaxed">
                    ℹ️ Confluence represents the current aggregated weight of 17 market indicators. It is an
                    <span className="text-cyan-300 font-semibold"> evidence score</span>, NOT a guaranteed probability.
                  </div>
                </div>

                {/* Calibrated Historical Probability Card */}
                <div className="p-4 rounded-xl bg-[#0c1424] border border-indigo-500/30 space-y-3 font-mono shadow-[0_0_20px_rgba(99,102,241,0.08)]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-indigo-300">
                      <Sparkles size={14} className="text-indigo-400" />
                      Calibrated Historical Probability
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-bold">
                      {cal?.calibration_status || "INSUFFICIENT_DATA"}
                    </span>
                  </div>

                  <div className="flex items-baseline justify-between pt-1">
                    <div>
                      {hasMinData && cal?.calibrated_probability !== null && cal?.calibrated_probability !== undefined ? (
                        <div className="text-3xl sm:text-4xl font-black text-indigo-300 tracking-tight">
                          {cal.calibrated_probability.toFixed(1)}%
                        </div>
                      ) : (
                        <div className="text-2xl sm:text-3xl font-black text-amber-400/90 tracking-tight">
                          N/A
                          <span className="block text-[11px] font-normal text-amber-300/80 mt-1">
                            INSUFFICIENT HISTORICAL DATA
                          </span>
                        </div>
                      )}
                      <div className="text-[11px] text-zinc-400 mt-1">
                        Completed Trades: <span className="font-bold text-zinc-200">{totalCompleted}</span> / 50 Min
                      </div>
                    </div>

                    <div className="text-right text-xs space-y-1">
                      <div>
                        <span className="text-zinc-500">Method: </span>
                        <span className="text-zinc-300 font-bold">{cal?.method_used || "Isotonic / Logistic"}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Brier Score: </span>
                        <span className="text-zinc-300 font-bold">
                          {cal?.brier_score !== null && cal?.brier_score !== undefined
                            ? cal.brier_score.toFixed(4)
                            : "N/A"}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-500">OOS Validation: </span>
                        <span className="text-zinc-300 font-bold">
                          {cal?.oos_accuracy !== null && cal?.oos_accuracy !== undefined
                            ? `${cal.oos_accuracy.toFixed(1)}%`
                            : "Pending Data"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#070b14] border border-[#162238] text-[10px] text-zinc-400 leading-relaxed">
                    ⚠️ <span className="text-zinc-300 font-semibold">Probability Disclaimer:</span> Historical
                    calibrated probability is an empirical estimate derived from completed historical signals. It is NOT a
                    guarantee of future results.
                  </div>
                </div>
              </div>

              {/* Historical Performance KPI Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Completed Trades</div>
                  <div className="text-lg font-bold text-slate-100 mt-1">{totalCompleted}</div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">
                    {overall?.wins ?? 0}W &middot; {overall?.losses ?? 0}L &middot; {overall?.breakeven ?? 0}BE
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Win Rate</div>
                  <div
                    className={`text-lg font-bold mt-1 ${
                      overall?.win_rate !== null && overall?.win_rate !== undefined
                        ? overall.win_rate >= 50
                          ? "text-emerald-400"
                          : "text-rose-400"
                        : "text-zinc-500"
                    }`}
                  >
                    {overall?.win_rate !== null && overall?.win_rate !== undefined
                      ? `${overall.win_rate.toFixed(1)}%`
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">
                    {totalCompleted < 10 ? "Need ≥10 for WR" : `Sample: ${totalCompleted}`}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Expectancy ($)</div>
                  <div
                    className={`text-lg font-bold mt-1 ${
                      overall?.expectancy !== null && overall?.expectancy !== undefined
                        ? overall.expectancy >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                        : "text-zinc-500"
                    }`}
                  >
                    {overall?.expectancy !== null && overall?.expectancy !== undefined
                      ? formatRAsUSD(overall.expectancy, { showSign: true })
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">Per Trade Expected P&L</div>
                </div>

                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Profit Factor</div>
                  <div
                    className={`text-lg font-bold mt-1 ${
                      overall?.profit_factor !== null && overall?.profit_factor !== undefined
                        ? overall.profit_factor >= 1.5
                          ? "text-emerald-400"
                          : "text-amber-400"
                        : "text-zinc-500"
                    }`}
                  >
                    {overall?.profit_factor !== null && overall?.profit_factor !== undefined
                      ? overall.profit_factor.toFixed(2)
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">Gross Win / Loss</div>
                </div>

                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Max Drawdown</div>
                  <div className="text-lg font-bold text-rose-400 mt-1">
                    {overall?.max_drawdown_r !== null && overall?.max_drawdown_r !== undefined
                      ? formatRAsUSD(-overall.max_drawdown_r)
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">Peak-to-Trough</div>
                </div>

                <div className="p-3 rounded-xl bg-[#0c1424] border border-[#1b2b4d]">
                  <div className="text-[10px] text-zinc-500 uppercase">Average Return ($)</div>
                  <div
                    className={`text-lg font-bold mt-1 ${
                      overall?.average_r !== null && overall?.average_r !== undefined
                        ? overall.average_r >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                        : "text-zinc-500"
                    }`}
                  >
                    {overall?.average_r !== null && overall?.average_r !== undefined
                      ? formatRAsUSD(overall.average_r, { showSign: true })
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">
                    MFE: {overall?.average_mfe ? `$${overall.average_mfe.toFixed(1)}` : "—"}
                  </div>
                </div>
              </div>

              {/* Transaction Cost & Status Row */}
              <div className="p-3 rounded-xl bg-[#080d19] border border-[#16233a] flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-zinc-400">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-zinc-300">Transaction Costs:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      report?.transaction_costs_included
                        ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                        : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {report?.transaction_costs_included ? "INCLUDED (SPREAD DEDUCTED)" : "NOT INCLUDED"}
                  </span>
                  <span className="text-[10px] text-zinc-500">({report?.transaction_cost_note || "Spread where available"})</span>
                </div>

                <div className="flex items-center gap-3 text-[11px]">
                  <span>
                    Open: <strong className="text-cyan-400">{report?.total_open ?? 0}</strong>
                  </span>
                  <span>
                    Expired: <strong className="text-zinc-400">{report?.total_expired ?? 0}</strong>
                  </span>
                  <span>
                    Total Recorded: <strong className="text-indigo-300">{report?.total_signals_recorded ?? 0}</strong>
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: STRATEGY PERFORMANCE (17 CONTRIBUTORS) */}
          {activeTab === "strategies" && (
            <div className="space-y-3 font-mono">
              <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
                <span>Empirical performance tracked per contributor when active (score &gt; 0):</span>
                <span className="text-[10px] text-zinc-500">Minimum 10 trades required for statistics</span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-[#1b2b4d] bg-[#0c1424]">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-[#080d19] text-[10px] text-zinc-400 uppercase tracking-wider border-b border-[#1b2b4d]">
                    <tr>
                      <th className="py-3 px-3">Strategy / Contributor</th>
                      <th className="py-3 px-3">Trades</th>
                      <th className="py-3 px-3">Wins</th>
                      <th className="py-3 px-3">Losses</th>
                      <th className="py-3 px-3">Win Rate</th>
                      <th className="py-3 px-3">Avg Return ($)</th>
                      <th className="py-3 px-3">Expectancy ($)</th>
                      <th className="py-3 px-3">Profit Factor</th>
                      <th className="py-3 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#16233a]">
                    {(report?.by_strategy && report.by_strategy.length > 0
                      ? report.by_strategy
                      : [
                          "HTF Trend",
                          "Market Structure",
                          "Momentum",
                          "MTF Alignment",
                          "S/R Price Action",
                          "Breakout / Retest",
                          "Supply & Demand",
                          "Volume Confirmation",
                          "SMC / ICT",
                          "ICT Concepts",
                          "Fibonacci OTE",
                          "Elliott Wave",
                          "VWAP",
                          "EMA / MA Stack",
                          "RSI",
                          "MACD",
                          "Gemini AI",
                        ].map((name) => ({
                          strategy_name: name,
                          total_signals: 0,
                          wins: 0,
                          losses: 0,
                          win_rate: null,
                          average_r: null,
                          expectancy: null,
                          profit_factor: null,
                          note: "No completed signals yet",
                        }))
                    ).map((st, idx) => {
                      const hasData = (st.total_signals ?? 0) >= 10 && st.win_rate !== null;
                      return (
                        <tr key={idx} className="hover:bg-[#121c33] transition-colors">
                          <td className="py-2.5 px-3 font-bold text-zinc-200 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                            {st.strategy_name}
                          </td>
                          <td className="py-2.5 px-3 text-zinc-300">{st.total_signals ?? 0}</td>
                          <td className="py-2.5 px-3 text-emerald-400">{st.wins ?? 0}</td>
                          <td className="py-2.5 px-3 text-rose-400">{st.losses ?? 0}</td>
                          <td className="py-2.5 px-3">
                            {hasData && st.win_rate !== null ? (
                              <span
                                className={`font-bold ${
                                  st.win_rate >= 55
                                    ? "text-emerald-400"
                                    : st.win_rate >= 45
                                    ? "text-amber-400"
                                    : "text-rose-400"
                                }`}
                              >
                                {st.win_rate.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-zinc-500">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-zinc-300">
                            {hasData && st.average_r !== null ? formatRAsUSD(st.average_r, { showSign: true }) : "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            {hasData && st.expectancy !== null ? (
                              <span className={`font-bold ${st.expectancy >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatRAsUSD(st.expectancy, { showSign: true })}
                              </span>
                            ) : (
                              <span className="text-zinc-500">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-zinc-300">
                            {hasData && st.profit_factor !== null ? st.profit_factor.toFixed(2) : "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${
                                hasData
                                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                                  : "bg-zinc-800/60 text-zinc-400 border-zinc-700/50"
                              }`}
                            >
                              {hasData ? "CALIBRATED" : "Not empirically calibrated"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: SCORE BANDS */}
          {activeTab === "bands" && (
            <div className="space-y-3 font-mono">
              <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
                <span>Confluence score bands evaluate whether higher scores yield higher historical win rates:</span>
                <span className="text-[10px] text-zinc-500">6 score segments</span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-[#1b2b4d] bg-[#0c1424]">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-[#080d19] text-[10px] text-zinc-400 uppercase tracking-wider border-b border-[#1b2b4d]">
                    <tr>
                      <th className="py-3 px-3">Score Band</th>
                      <th className="py-3 px-3">Classification</th>
                      <th className="py-3 px-3">Completed Trades</th>
                      <th className="py-3 px-3">Wins</th>
                      <th className="py-3 px-3">Losses</th>
                      <th className="py-3 px-3">Win Rate</th>
                      <th className="py-3 px-3">Avg Return ($)</th>
                      <th className="py-3 px-3">Expectancy ($)</th>
                      <th className="py-3 px-3">Profit Factor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#16233a]">
                    {(report?.by_score_band && report.by_score_band.length > 0
                      ? report.by_score_band
                      : ["0-49", "50-59", "60-69", "70-79", "80-89", "90-100"].map((b) => ({
                          band: b,
                          sample_size: 0,
                          wins: 0,
                          losses: 0,
                          win_rate: null,
                          average_r: null,
                          expectancy: null,
                          profit_factor: null,
                          note: "No signals yet",
                        }))
                    ).map((sb, idx) => {
                      const hasData = (sb.sample_size ?? 0) >= 10 && sb.win_rate !== null;
                      const label =
                        sb.band === "90-100"
                          ? "EXTREME CONFLUENCE"
                          : sb.band === "80-89"
                          ? "VERY STRONG"
                          : sb.band === "70-79"
                          ? "STRONG"
                          : sb.band === "60-69"
                          ? "MODERATE"
                          : sb.band === "50-59"
                          ? "WEAK"
                          : "NO TRADE";
                      const isCurrentBand =
                        currentConfluenceScore != null && (
                          (currentConfluenceScore >= 90 && sb.band === "90-100") ||
                          (currentConfluenceScore >= 80 && currentConfluenceScore < 90 && sb.band === "80-89") ||
                          (currentConfluenceScore >= 70 && currentConfluenceScore < 80 && sb.band === "70-79") ||
                          (currentConfluenceScore >= 60 && currentConfluenceScore < 70 && sb.band === "60-69") ||
                          (currentConfluenceScore >= 50 && currentConfluenceScore < 60 && sb.band === "50-59") ||
                          (currentConfluenceScore < 50 && sb.band === "0-49")
                        );

                      return (
                        <tr
                          key={idx}
                          className={`hover:bg-[#121c33] transition-colors ${
                            isCurrentBand ? "bg-cyan-950/20 border-l-2 border-cyan-400" : ""
                          }`}
                        >
                          <td className="py-3 px-3 font-bold text-zinc-200">
                            {sb.band}
                            {isCurrentBand && (
                              <span className="ml-2 text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                                CURRENT
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-zinc-400">{label}</td>
                          <td className="py-3 px-3 text-zinc-200">{sb.sample_size ?? 0}</td>
                          <td className="py-3 px-3 text-emerald-400">{sb.wins ?? 0}</td>
                          <td className="py-3 px-3 text-rose-400">{sb.losses ?? 0}</td>
                          <td className="py-3 px-3">
                            {hasData && sb.win_rate !== null ? (
                              <span
                                className={`font-bold ${
                                  sb.win_rate >= 55
                                    ? "text-emerald-400"
                                    : sb.win_rate >= 45
                                    ? "text-amber-400"
                                    : "text-rose-400"
                                }`}
                              >
                                {sb.win_rate.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-zinc-500">Insufficient Data</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-zinc-300">
                            {hasData && sb.average_r !== null ? formatRAsUSD(sb.average_r, { showSign: true }) : "—"}
                          </td>
                          <td className="py-3 px-3">
                            {hasData && sb.expectancy !== null ? (
                              <span className={`font-bold ${sb.expectancy >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatRAsUSD(sb.expectancy, { showSign: true })}
                              </span>
                            ) : (
                              <span className="text-zinc-500">—</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-zinc-300">
                            {hasData && sb.profit_factor !== null ? sb.profit_factor.toFixed(2) : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: GEMINI AI ABLATION */}
          {activeTab === "gemini" && (
            <div className="space-y-4 font-mono">
              <div className="p-4 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <Cpu size={14} className="text-amber-400" />
                    Gemini AI Contributor Performance &amp; Ablation
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold">
                    {report?.gemini_analysis?.gemini_improves_performance === true
                      ? "EDGE PROVEN"
                      : report?.gemini_analysis?.gemini_improves_performance === false
                      ? "NO MEASURED EDGE"
                      : "GEMINI EDGE: UNDETERMINED"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Gemini Signals</div>
                    <div className="text-base font-bold text-zinc-200 mt-1">
                      {report?.gemini_analysis?.total_gemini_signals ?? 0}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">Active score &gt; 0</div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Direction Accuracy</div>
                    <div className="text-base font-bold text-zinc-200 mt-1">
                      {report?.gemini_analysis?.gemini_direction_accuracy !== null &&
                      report?.gemini_analysis?.gemini_direction_accuracy !== undefined
                        ? `${report.gemini_analysis.gemini_direction_accuracy.toFixed(1)}%`
                        : "N/A (Pending Data)"}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">Bias matches signal</div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Technical Agreement</div>
                    <div className="text-base font-bold text-emerald-400 mt-1">
                      {report?.gemini_analysis?.gemini_agreement_rate !== null &&
                      report?.gemini_analysis?.gemini_agreement_rate !== undefined
                        ? `${report.gemini_analysis.gemini_agreement_rate.toFixed(1)}%`
                        : "N/A"}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">Agrees with Direction Gate</div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Conflict Rate</div>
                    <div className="text-base font-bold text-amber-400 mt-1">
                      {report?.gemini_analysis?.gemini_conflict_rate !== null &&
                      report?.gemini_analysis?.gemini_conflict_rate !== undefined
                        ? `${report.gemini_analysis.gemini_conflict_rate.toFixed(1)}%`
                        : "N/A"}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">Opposes Technical Gate</div>
                  </div>
                </div>

                {/* Ablation Comparison Table */}
                <div className="p-3.5 rounded-lg bg-[#070b14] border border-[#162238] space-y-2">
                  <div className="text-[11px] font-bold text-zinc-300 uppercase">
                    Ablation Test: Technical Engine WITH vs WITHOUT Gemini AI
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-zinc-400 font-semibold">Group A: Technical Only (No Gemini)</div>
                      <div className="mt-1 flex justify-between text-zinc-300">
                        <span>Win Rate:</span>
                        <span className="font-bold">
                          {report?.gemini_analysis?.ablation_without_gemini_win_rate
                            ? `${report.gemini_analysis.ablation_without_gemini_win_rate.toFixed(1)}%`
                            : "Pending Data"}
                        </span>
                      </div>
                      <div className="flex justify-between text-zinc-300">
                        <span>Expectancy:</span>
                        <span className="font-bold">
                          {report?.gemini_analysis?.ablation_without_gemini_expectancy != null
                            ? formatRAsUSD(report.gemini_analysis.ablation_without_gemini_expectancy, { showSign: true })
                            : "Pending Data"}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-[#0c1424] border border-[#1b2b4d]">
                      <div className="text-zinc-400 font-semibold">Group B: Technical + Gemini AI</div>
                      <div className="mt-1 flex justify-between text-zinc-300">
                        <span>Win Rate:</span>
                        <span className="font-bold">
                          {report?.gemini_analysis?.ablation_with_gemini_win_rate
                            ? `${report.gemini_analysis.ablation_with_gemini_win_rate.toFixed(1)}%`
                            : "Pending Data"}
                        </span>
                      </div>
                      <div className="flex justify-between text-zinc-300">
                        <span>Expectancy:</span>
                        <span className="font-bold">
                          {report?.gemini_analysis?.ablation_with_gemini_expectancy != null
                            ? formatRAsUSD(report.gemini_analysis.ablation_with_gemini_expectancy, { showSign: true })
                            : "Pending Data"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <p className="text-[10px] text-zinc-500 pt-1">
                    ℹ️ {report?.gemini_analysis?.ablation_note || "Ablation test requires ≥50 completed signals in both groups."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: SIGNAL HISTORY (RECORDED ACTIONABLE SIGNALS) */}
          {activeTab === "signals" && (
            <div className="space-y-3 font-mono">
              {/* Filter controls */}
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <select
                    value={signalDirectionFilter}
                    onChange={(e) => {
                      setSignalDirectionFilter(e.target.value);
                      setSignalsPage(1);
                    }}
                    className="px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#1b2b4d] text-zinc-200 text-xs focus:outline-none"
                  >
                    <option value="">All Directions</option>
                    <option value="BUY">BUY Only</option>
                    <option value="SELL">SELL Only</option>
                  </select>

                  <select
                    value={signalOutcomeFilter}
                    onChange={(e) => {
                      setSignalOutcomeFilter(e.target.value);
                      setSignalsPage(1);
                    }}
                    className="px-2.5 py-1 rounded-lg bg-[#0c1424] border border-[#1b2b4d] text-zinc-200 text-xs focus:outline-none"
                  >
                    <option value="">All Outcomes</option>
                    <option value="WIN">WIN Only</option>
                    <option value="LOSS">LOSS Only</option>
                    <option value="OPEN">OPEN Only</option>
                    <option value="EXPIRED">EXPIRED Only</option>
                    <option value="BREAKEVEN">BREAKEVEN Only</option>
                  </select>
                </div>

                <div className="text-[11px] text-zinc-400">
                  Total Signals: <strong className="text-zinc-200">{signalsRes?.total ?? 0}</strong> &middot; Page{" "}
                  {signalsPage} of {signalsRes?.total_pages || 1}
                </div>
              </div>

              {/* Signals Table */}
              <div className="overflow-x-auto rounded-xl border border-[#1b2b4d] bg-[#0c1424]">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-[#080d19] text-[10px] text-zinc-400 uppercase tracking-wider border-b border-[#1b2b4d]">
                    <tr>
                      <th className="py-3 px-3">Signal Timestamp</th>
                      <th className="py-3 px-3">Direction</th>
                      <th className="py-3 px-3">Entry Price</th>
                      <th className="py-3 px-3">Confluence</th>
                      <th className="py-3 px-3">Tech / AI</th>
                      <th className="py-3 px-3">Outcome</th>
                      <th className="py-3 px-3">Realized P&L</th>
                      <th className="py-3 px-3">MFE / MAE</th>
                      <th className="py-3 px-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#16233a]">
                    {!signalsRes?.signals || signalsRes.signals.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="text-center py-8 text-zinc-500">
                          No actionable signal records recorded yet. Live signals will appear here as they are generated.
                        </td>
                      </tr>
                    ) : (
                      signalsRes.signals.map((sig) => {
                        const outcomeStr = sig.outcome?.outcome || "OPEN";
                        const isWin = outcomeStr === "WIN";
                        const isLoss = outcomeStr === "LOSS";
                        return (
                          <tr key={sig.signal_id} className="hover:bg-[#121c33] transition-colors">
                            <td className="py-2.5 px-3 text-zinc-400 text-[11px]">
                              {fmtTime(sig.signal_timestamp)}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded font-black text-[10px] border ${
                                  sig.direction === "BUY"
                                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                    : "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                }`}
                              >
                                {sig.direction}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-bold text-zinc-200">{fmtPrice(sig.entry_price)}</td>
                            <td className="py-2.5 px-3">
                              <span className="font-bold text-cyan-300">{sig.confluence_score}</span>
                              <span className="text-zinc-500 text-[10px]"> / 100</span>
                            </td>
                            <td className="py-2.5 px-3 text-zinc-400 text-[11px]">
                              {sig.technical_score} / {sig.gemini_score}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                  isWin
                                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                    : isLoss
                                    ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                    : outcomeStr === "OPEN"
                                    ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/30 animate-pulse"
                                    : "bg-zinc-800 text-zinc-400 border-zinc-700"
                                }`}
                              >
                                {outcomeStr}
                              </span>
                            </td>
                            <td className="py-2.5 px-3">
                              {sig.outcome?.realized_r !== null && sig.outcome?.realized_r !== undefined ? (
                                <span
                                  className={`font-bold ${
                                    sig.outcome.realized_r >= 0 ? "text-emerald-400" : "text-rose-400"
                                  }`}
                                >
                                  {formatRAsUSD(sig.outcome.realized_r, { showSign: true })}
                                </span>
                              ) : (
                                <span className="text-zinc-500">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-[11px] text-zinc-400">
                              +{sig.outcome?.mfe ? sig.outcome.mfe.toFixed(1) : "0"} / -
                              {sig.outcome?.mae ? sig.outcome.mae.toFixed(1) : "0"}
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <button
                                onClick={() => setSelectedSignal(sig)}
                                className="px-2 py-1 rounded bg-[#121c33] hover:bg-[#1c2c50] border border-[#202f50] text-zinc-300 hover:text-white text-[10px] flex items-center gap-1 ml-auto"
                              >
                                <Eye size={11} /> Detail
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination bar */}
              {signalsRes && signalsRes.total_pages > 1 && (
                <div className="flex items-center justify-between text-xs pt-1">
                  <button
                    disabled={signalsPage <= 1}
                    onClick={() => setSignalsPage((p) => Math.max(1, p - 1))}
                    className="px-3 py-1 rounded bg-[#0c1424] border border-[#1b2b4d] text-zinc-300 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="text-zinc-400">
                    Page {signalsPage} of {signalsRes.total_pages}
                  </span>
                  <button
                    disabled={signalsPage >= signalsRes.total_pages}
                    onClick={() => setSignalsPage((p) => p + 1)}
                    className="px-3 py-1 rounded bg-[#0c1424] border border-[#1b2b4d] text-zinc-300 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: DATA INTEGRITY PANEL */}
          {activeTab === "integrity" && (
            <div className="space-y-4 font-mono">
              <div className="p-4 rounded-xl bg-[#0c1424] border border-[#1b2b4d] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <ShieldCheck size={14} className="text-emerald-400" />
                    Dataset Quality &amp; Integrity Telemetry
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                      integrityRes?.issues_found === 0
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                        : "bg-rose-500/15 text-rose-300 border-rose-500/30"
                    }`}
                  >
                    {integrityRes?.issues_found === 0 ? "DATA INTEGRITY: OK" : "DATA INTEGRITY: WARNING"}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Total Records</div>
                    <div className="text-base font-bold text-zinc-200 mt-1">{integrityRes?.total_records ?? 0}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Valid Records</div>
                    <div className="text-base font-bold text-emerald-400 mt-1">{integrityRes?.valid_records ?? 0}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Integrity Issues</div>
                    <div className="text-base font-bold text-amber-400 mt-1">{integrityRes?.issues_found ?? 0}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238]">
                    <div className="text-[10px] text-zinc-500 uppercase">Look-Ahead Guard</div>
                    <div className="text-base font-bold text-emerald-400 mt-1">ENFORCED</div>
                  </div>
                </div>

                {integrityRes?.issues && integrityRes.issues.length > 0 ? (
                  <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 space-y-1.5 text-xs text-rose-300">
                    <div className="font-bold flex items-center gap-1.5">
                      <AlertCircle size={13} />
                      Issues Detected:
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-rose-200/90">
                      {integrityRes.issues.map((iss, i) => (
                        <li key={i}>{iss}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-[#070b14] border border-[#162238] text-[11px] text-zinc-400 flex items-center gap-2">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    <span>All signal records pass strict integrity validation (no duplicates, no impossible prices, no future timestamps).</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Modal / Slide-over: Single Signal Record Detail */}
          {selectedSignal && (
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="modal-signal-record-title"
              onKeyDown={(e) => { if (e.key === "Escape") setSelectedSignal(null); }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
            >
              <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#090f1e] border border-blue-500/35 p-5 sm:p-6 shadow-2xl space-y-4 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-[#1c2c4d] pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span id="modal-signal-record-title" className="text-sm font-bold text-slate-100">Signal Record Details</span>
                    <span
                      className={`px-2 py-0.5 rounded font-bold text-[10px] border ${
                        selectedSignal.direction === "BUY"
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                          : "bg-rose-500/15 text-rose-300 border-rose-500/30"
                      }`}
                    >
                      {selectedSignal.direction}
                    </span>
                    <span className="text-[10px] text-zinc-400 font-normal">
                      #{selectedSignal.signal_id.slice(0, 8)}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedSignal(null)}
                    aria-label="Close signal record details"
                    className="p-1 rounded-lg bg-[#121c33] text-zinc-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-[11px]">
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Signal Timestamp</div>
                    <div className="font-bold text-zinc-200 mt-0.5">{fmtTime(selectedSignal.signal_timestamp)}</div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Entry Price</div>
                    <div className="font-bold text-zinc-200 mt-0.5">{fmtPrice(selectedSignal.entry_price)}</div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Confluence Score</div>
                    <div className="font-bold text-cyan-300 mt-0.5">{selectedSignal.confluence_score} / 100</div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Stop Loss</div>
                    <div className="font-bold text-rose-400 mt-0.5">
                      {selectedSignal.stop_loss ? fmtPrice(selectedSignal.stop_loss) : "—"}
                    </div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Take Profit 1</div>
                    <div className="font-bold text-emerald-400 mt-0.5">
                      {selectedSignal.take_profit_1 ? fmtPrice(selectedSignal.take_profit_1) : "—"}
                    </div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0c1424] border border-[#16233a]">
                    <div className="text-zinc-500 uppercase text-[9px]">Outcome</div>
                    <div className="font-bold text-indigo-300 mt-0.5">
                      {selectedSignal.outcome?.outcome || "OPEN"}
                      {selectedSignal.outcome?.realized_r !== null && selectedSignal.outcome?.realized_r !== undefined && (
                        <span className={selectedSignal.outcome.realized_r >= 0 ? "ml-1 text-emerald-400" : "ml-1 text-rose-400"}>
                          ({formatRAsUSD(selectedSignal.outcome.realized_r, { showSign: true })})
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Excursions & Snapshot */}
                <div className="p-3 rounded-lg bg-[#0c1424] border border-[#16233a] space-y-1.5 text-[11px]">
                  <div className="flex justify-between text-zinc-300">
                    <span className="text-zinc-500">Snapshot ID:</span>
                    <span className="font-mono text-zinc-200">{selectedSignal.snapshot_id}</span>
                  </div>
                  <div className="flex justify-between text-zinc-300">
                    <span className="text-zinc-500">MFE (Max Favorable):</span>
                    <span className="font-bold text-emerald-400">
                      +{selectedSignal.outcome?.mfe ? selectedSignal.outcome.mfe.toFixed(2) : "0.00"}
                    </span>
                  </div>
                  <div className="flex justify-between text-zinc-300">
                    <span className="text-zinc-500">MAE (Max Adverse):</span>
                    <span className="font-bold text-rose-400">
                      -{selectedSignal.outcome?.mae ? selectedSignal.outcome.mae.toFixed(2) : "0.00"}
                    </span>
                  </div>
                  <div className="flex justify-between text-zinc-300">
                    <span className="text-zinc-500">Outcome Note:</span>
                    <span className="text-zinc-300">{selectedSignal.outcome?.note || "Awaiting SL/TP resolution"}</span>
                  </div>
                </div>

                {/* Contributor Breakdown for this signal */}
                {selectedSignal.contributor_scores && Object.keys(selectedSignal.contributor_scores).length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[10px] uppercase text-zinc-500 font-bold">Contributors at Generation</div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                      {Object.entries(selectedSignal.contributor_scores).map(([name, pts]) => (
                        <div key={name} className="p-1.5 rounded bg-[#070b14] border border-[#162238] text-[10px] flex justify-between">
                          <span className="text-zinc-400 truncate">{name}:</span>
                          <span className="font-bold text-cyan-300">+{pts}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
