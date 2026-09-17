"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  BarChart3,
  Calendar,
  Layers,
  Zap,
  TrendingUp,
  TrendingDown,
  Clock,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Filter,
  Sliders,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Percent,
  RefreshCw,
  Scale,
  Award,
  ChevronLeft,
  ChevronRight,
  Check,
  Search,
  Activity,
  Compass,
} from "lucide-react";
import {
  ApiClient,
  ValidatedSignalRecord,
  PerformanceSummaryKPIs,
  HistoryEquityPoint,
  StrategyBenchmarkCard,
  HistoryAnalyticsResponse,
} from "@/services/api";
import { fmtNumber, fmtPct, formatRAsUSD } from "@/lib/format";

export function HistoricalBacktestTab({ symbol }: { symbol?: string } = {}) {
  // ── Filter State ─────────────────────────────────────────────────────────
  const isBtcActive = symbol ? symbol.toUpperCase().includes("BTC") : false;
  const isGoldActive = symbol ? !isBtcActive : false;
  const defaultSymbol = symbol ? (isBtcActive ? "BTC/USD" : "XAU/USD") : "ALL";
  const [symbolFilter, setSymbolFilter] = useState<string>(defaultSymbol);

  useEffect(() => {
    if (symbol) {
      const activeSym = symbol.toUpperCase().includes("BTC") ? "BTC/USD" : "XAU/USD";
      setSymbolFilter(activeSym);
      setPage(1);
    }
  }, [symbol]);
  const [directionFilter, setDirectionFilter] = useState<string>("ALL");
  const [outcomeFilter, setOutcomeFilter] = useState<string>("ALL");
  const [minProbFilter, setMinProbFilter] = useState<number | undefined>(undefined);
  const [regimeFilter, setRegimeFilter] = useState<string>("ALL");
  const [qualificationFilter, setQualificationFilter] = useState<string>("ALL");
  const [startDateFilter, setStartDateFilter] = useState<string>("");
  const [endDateFilter, setEndDateFilter] = useState<string>("");
  const [dedupUniqueBars, setDedupUniqueBars] = useState<boolean>(false);

  // ── Pagination State ─────────────────────────────────────────────────────
  const [page, setPage] = useState<number>(1);
  const pageSize = 50;

  // ── Data State ───────────────────────────────────────────────────────────
  const [loading, setLoading] = useState<boolean>(true);
  const [data, setData] = useState<HistoryAnalyticsResponse | null>(null);
  const [selectedSignalDetail, setSelectedSignalDetail] = useState<ValidatedSignalRecord | null>(null);
  const [activeChartMetric, setActiveChartMetric] = useState<"CUMULATIVE_R" | "DRAWDOWN" | "ROLLING_EXP">("CUMULATIVE_R");

  const displayedSignals = useMemo(() => {
    if (!data?.signals) return [];
    if (!dedupUniqueBars) return data.signals;
    const seen = new Set<string>();
    return data.signals.filter((s) => {
      const key = `${s.symbol}_${s.signal_timestamp}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [data?.signals, dedupUniqueBars]);

  // ── Fetch Filtered Analytics ─────────────────────────────────────────────
  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const res = await ApiClient.fetchHistoryAnalytics({
        symbol: symbolFilter !== "ALL" ? symbolFilter : undefined,
        direction: directionFilter !== "ALL" ? directionFilter : undefined,
        outcome: outcomeFilter !== "ALL" ? outcomeFilter : undefined,
        min_prob: minProbFilter,
        market_regime: regimeFilter !== "ALL" ? regimeFilter : undefined,
        qualification: qualificationFilter !== "ALL" ? qualificationFilter : undefined,
        start_date: startDateFilter ? startDateFilter : undefined,
        end_date: endDateFilter ? endDateFilter : undefined,
        limit: pageSize,
        offset,
      });
      setData(res);
    } catch (err) {
      console.error("Failed to load historical strategy analytics:", err);
    } finally {
      setLoading(false);
    }
  }, [
    symbolFilter,
    directionFilter,
    outcomeFilter,
    minProbFilter,
    regimeFilter,
    qualificationFilter,
    startDateFilter,
    endDateFilter,
    page,
    pageSize,
  ]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Reset page when any filter changes
  const handleFilterChange = (setter: (val: any) => void, val: any) => {
    setter(val);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSymbolFilter(defaultSymbol);
    setDirectionFilter("ALL");
    setOutcomeFilter("ALL");
    setMinProbFilter(undefined);
    setRegimeFilter("ALL");
    setQualificationFilter("ALL");
    setStartDateFilter("");
    setEndDateFilter("");
    setPage(1);
  };

  // Quick Preset Handlers
  const applyPresetBtcLowVol = () => {
    setSymbolFilter("BTC/USD");
    setDirectionFilter("SELL");
    setMinProbFilter(0.40);
    setRegimeFilter("LOW_VOLATILITY");
    setQualificationFilter("QUALIFIED");
    setOutcomeFilter("ALL");
    setPage(1);
  };

  const applyPresetXauVwap = () => {
    setSymbolFilter("XAU/USD");
    setDirectionFilter("BUY");
    setMinProbFilter(0.42);
    setRegimeFilter("ALL");
    setQualificationFilter("QUALIFIED");
    setOutcomeFilter("ALL");
    setPage(1);
  };

  // ── SVG Equity Curve Builder ─────────────────────────────────────────────
  const equitySvg = useMemo(() => {
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return null;
    const pts = data.equity_curve;
    const n = pts.length;
    const width = 800;
    const height = 240;
    const padX = 45;
    const padY = 30;

    let minVal = 0;
    let maxVal = 0;

    if (activeChartMetric === "CUMULATIVE_R") {
      const vals = pts.map((p) => p.cumulative_r);
      minVal = Math.min(0, ...vals);
      maxVal = Math.max(1, ...vals);
    } else if (activeChartMetric === "DRAWDOWN") {
      const vals = pts.map((p) => p.drawdown_r);
      minVal = 0;
      maxVal = Math.max(1, ...vals);
    } else {
      // Rolling Expectancy
      const vals = pts.map((p) => p.rolling_expectancy_25);
      minVal = Math.min(-0.5, ...vals);
      maxVal = Math.max(0.5, ...vals);
    }

    const range = maxVal - minVal || 1;

    const coords = pts.map((p, i) => {
      const x = padX + (i / Math.max(1, n - 1)) * (width - 2 * padX);
      let val = p.cumulative_r;
      if (activeChartMetric === "DRAWDOWN") val = p.drawdown_r;
      if (activeChartMetric === "ROLLING_EXP") val = p.rolling_expectancy_25;

      const y = height - padY - ((val - minVal) / range) * (height - 2 * padY);
      return { x, y, val, point: p };
    });

    const zeroY = height - padY - ((0 - minVal) / range) * (height - 2 * padY);

    const pathD = coords.reduce(
      (acc, c, idx) => (idx === 0 ? `M ${c.x} ${c.y}` : `${acc} L ${c.x} ${c.y}`),
      ""
    );

    const areaD = `${pathD} L ${coords[coords.length - 1].x} ${zeroY} L ${coords[0].x} ${zeroY} Z`;

    return {
      width,
      height,
      pathD,
      areaD,
      zeroY,
      coords,
      minVal,
      maxVal,
      totalPoints: n,
    };
  }, [data, activeChartMetric]);

  const kpis: PerformanceSummaryKPIs = data?.kpi_summary || {
    total_trades: 0,
    wins: 0,
    losses: 0,
    breakevens: 0,
    win_rate_pct: 0,
    expectancy_r: 0,
    profit_factor: 0,
    total_realized_r: 0,
    max_drawdown_r: 0,
    avg_win_r: 0,
    avg_loss_r: 0,
  };

  const totalPages = Math.max(1, Math.ceil((data?.total_count || 0) / pageSize));

  return (
    <div className="space-y-6 font-mono text-zinc-100">
      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 1. STRATEGY COMPARISON & BENCHMARK CARDS                              */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className={`grid grid-cols-1 ${!symbol ? "lg:grid-cols-2" : ""} gap-4`}>
        {/* BTC Champion Card */}
        {(!symbol || isBtcActive) && (
          <div className="relative overflow-hidden bg-[#071330]/95 border border-sky-500/40 rounded-2xl p-5 shadow-[0_0_24px_rgba(56,189,248,0.12)] backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between border-b border-sky-500/20 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center font-bold text-rose-300">
                  <TrendingDown size={18} />
                </div>
                <div>
                  <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <span>BTC SELL LOW-VOL</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                      QUALIFIED FOR PAPER TRADING
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400">Validated Empirical Research Champion</div>
                </div>
              </div>
              <button
                onClick={applyPresetBtcLowVol}
                className="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-200 hover:text-white border border-sky-500/40 text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-sm"
              >
                <Sparkles size={13} className="text-amber-400" />
                Apply Preset
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Expectancy ($)</div>
                <div className="text-lg font-black text-emerald-400">+$0.47</div>
                <div className="text-[9px] text-zinc-500">Per trade</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Win Rate</div>
                <div className="text-lg font-black text-emerald-300">58.9%</div>
                <div className="text-[9px] text-zinc-500">N = 258</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Profit Factor</div>
                <div className="text-lg font-black text-cyan-300">2.15</div>
                <div className="text-[9px] text-zinc-500">Gross Gain/Loss</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Score</div>
                <div className="text-lg font-black text-amber-300">95 / 100</div>
                <div className="text-[9px] text-zinc-500">100% Rolling Pos</div>
              </div>
            </div>

            <div className="text-[11px] text-zinc-400 leading-relaxed bg-[#050e24]/60 p-2.5 rounded-xl border border-sky-500/10">
              • <strong className="text-zinc-200">Rule:</strong> BTC/USD + SELL + Calibrated Probability ≥ 40% + <span className="text-sky-300">LOW_VOLATILITY</span> regime.
            </div>
          </div>
        )}

        {/* XAU Champion Card */}
        {(!symbol || isGoldActive) && (
          <div className="relative overflow-hidden bg-[#071330]/95 border border-sky-500/40 rounded-2xl p-5 shadow-[0_0_24px_rgba(56,189,248,0.12)] backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between border-b border-sky-500/20 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center font-bold text-emerald-300">
                  <TrendingUp size={18} />
                </div>
                <div>
                  <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <span>XAU BUY VWAP</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                      QUALIFIED FOR PAPER TRADING
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400">Validated Gold Institutional Confluence Champion</div>
                </div>
              </div>
              <button
                onClick={applyPresetXauVwap}
                className="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-200 hover:text-white border border-sky-500/40 text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-sm"
              >
                <Sparkles size={13} className="text-amber-400" />
                Apply Preset
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Expectancy ($)</div>
                <div className="text-lg font-black text-emerald-400">+$0.20</div>
                <div className="text-[9px] text-zinc-500">Per trade</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Win Rate</div>
                <div className="text-lg font-black text-emerald-300">48.2%</div>
                <div className="text-[9px] text-zinc-500">N = 517</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Profit Factor</div>
                <div className="text-lg font-black text-cyan-300">1.39</div>
                <div className="text-[9px] text-zinc-500">Gross Gain/Loss</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#050e24] border border-sky-500/20">
                <div className="text-[10px] text-zinc-400 uppercase">Score</div>
                <div className="text-lg font-black text-amber-300">84 / 100</div>
                <div className="text-[9px] text-zinc-500">4/4 Walk-Forward</div>
              </div>
            </div>

            <div className="text-[11px] text-zinc-400 leading-relaxed bg-[#050e24]/60 p-2.5 rounded-xl border border-sky-500/10">
              • <strong className="text-zinc-200">Rule:</strong> XAU/USD + BUY + Calibrated Probability ≥ 42% + <span className="text-sky-300">VWAP Aligned</span>.
            </div>
          </div>
        )}
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 2. DYNAMIC PERFORMANCE KPI SUMMARY DASHBOARD                          */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* 1. Total Trades */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">TOTAL TRADES</div>
          <div className="text-xl font-black font-mono text-white mt-0.5">{kpis.total_trades}</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">{kpis.wins}W / {kpis.losses}L</div>
        </div>

        {/* 2. Win Rate */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">WIN RATE</div>
          <div className="text-xl font-black font-mono text-emerald-300 mt-0.5">{kpis.win_rate_pct}%</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">{kpis.wins} Total Wins</div>
        </div>

        {/* 3. Expectancy */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">EXPECTANCY ($)</div>
          <div className={`text-xl font-black font-mono mt-0.5 ${kpis.expectancy_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {formatRAsUSD(kpis.expectancy_r, { showSign: true })}
          </div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Per trade edge</div>
        </div>

        {/* 4. Profit Factor */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">PROFIT FACTOR</div>
          <div className="text-xl font-black font-mono text-cyan-300 mt-0.5">{kpis.profit_factor}</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Gross Gain / Loss</div>
        </div>

        {/* 5. Total Realized ($) */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">TOTAL REALIZED ($)</div>
          <div className={`text-xl font-black font-mono mt-0.5 ${kpis.total_realized_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {formatRAsUSD(kpis.total_realized_r, { showSign: true })}
          </div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Net Cumulative Return</div>
        </div>

        {/* 6. Max Drawdown */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">MAX DRAWDOWN</div>
          <div className="text-xl font-black font-mono text-rose-400 mt-0.5">{formatRAsUSD(-kpis.max_drawdown_r)}</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Peak-to-Trough</div>
        </div>

        {/* 7. Avg Win ($) */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">AVG WIN ($)</div>
          <div className="text-xl font-black font-mono text-emerald-400 mt-0.5">{formatRAsUSD(kpis.avg_win_r, { showSign: true })}</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Average Win ($)</div>
        </div>

        {/* 8. Avg Loss ($) */}
        <div className="bg-[#071330]/90 border border-sky-500/25 rounded-xl p-3 backdrop-blur-md">
          <div className="text-[10px] font-mono text-zinc-400 uppercase">AVG LOSS ($)</div>
          <div className="text-xl font-black font-mono text-rose-400 mt-0.5">{formatRAsUSD(-kpis.avg_loss_r)}</div>
          <div className="text-[9px] text-zinc-500 mt-0.5">Average Loss ($)</div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 3. MULTI-FACTOR INTERACTIVE FILTER BAR                                */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-5 shadow-xl backdrop-blur-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-sky-500/20">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-sky-400" />
            <h3 className="text-xs font-bold font-mono text-white uppercase tracking-wider">
              MULTI-DIMENSIONAL STRATEGY & HISTORICAL FILTERS
            </h3>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-zinc-400 font-mono">
              Filtered: <strong className="text-white">{data?.total_count ?? 0}</strong> Trades
            </span>
            <button
              onClick={handleResetFilters}
              className="px-2.5 py-1 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-white text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <RotateCcw size={12} />
              Reset
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 text-xs font-mono">
          {/* 1. Symbol Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Symbol</label>
            <select
              value={symbolFilter}
              onChange={(e) => handleFilterChange(setSymbolFilter, e.target.value)}
              disabled={Boolean(symbol)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold disabled:opacity-80"
            >
              {symbol ? (
                <option value={defaultSymbol}>{defaultSymbol}</option>
              ) : (
                <>
                  <option value="ALL">ALL ASSETS</option>
                  <option value="BTC/USD">BTC/USD</option>
                  <option value="XAU/USD">XAU/USD</option>
                </>
              )}
            </select>
          </div>

          {/* 2. Direction Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Direction</label>
            <select
              value={directionFilter}
              onChange={(e) => handleFilterChange(setDirectionFilter, e.target.value)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold"
            >
              <option value="ALL">ALL DIRECTIONS</option>
              <option value="BUY">BUY ONLY</option>
              <option value="SELL">SELL ONLY</option>
            </select>
          </div>

          {/* 3. Outcome Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Outcome</label>
            <select
              value={outcomeFilter}
              onChange={(e) => handleFilterChange(setOutcomeFilter, e.target.value)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold"
            >
              <option value="ALL">ALL OUTCOMES</option>
              <option value="WIN">WIN ONLY</option>
              <option value="LOSS">LOSS ONLY</option>
              <option value="BREAKEVEN">BREAKEVEN</option>
            </select>
          </div>

          {/* 4. Probability Range Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Calibrated Prob</label>
            <select
              value={minProbFilter === undefined ? "ALL" : minProbFilter.toString()}
              onChange={(e) =>
                handleFilterChange(
                  setMinProbFilter,
                  e.target.value === "ALL" ? undefined : parseFloat(e.target.value)
                )
              }
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold"
            >
              <option value="ALL">ALL PROBABILITIES</option>
              <option value="0.38">Prob ≥ 38%</option>
              <option value="0.40">Prob ≥ 40% (BTC)</option>
              <option value="0.42">Prob ≥ 42% (XAU)</option>
              <option value="0.45">Prob ≥ 45%</option>
              <option value="0.50">Prob ≥ 50%</option>
            </select>
          </div>

          {/* 5. Market Regime Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Market Regime</label>
            <select
              value={regimeFilter}
              onChange={(e) => handleFilterChange(setRegimeFilter, e.target.value)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold"
            >
              <option value="ALL">ALL REGIMES</option>
              <option value="LOW_VOLATILITY">LOW_VOLATILITY</option>
              <option value="TRENDING">TRENDING</option>
              <option value="RANGING">RANGING</option>
              <option value="HIGH_VOLATILITY">HIGH_VOLATILITY</option>
            </select>
          </div>

          {/* 6. Strategy Qualification Filter */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">Qualification</label>
            <select
              value={qualificationFilter}
              onChange={(e) => handleFilterChange(setQualificationFilter, e.target.value)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2.5 py-1.5 text-sky-200 focus:border-sky-400 font-bold"
            >
              <option value="ALL">ALL SIGNALS</option>
              <option value="QUALIFIED">QUALIFIED ONLY</option>
              <option value="NOT_QUALIFIED">NOT QUALIFIED</option>
            </select>
          </div>

          {/* 7. Start Date */}
          <div className="space-y-1">
            <label className="text-[10px] text-zinc-400 uppercase font-bold">From Date</label>
            <input
              type="date"
              value={startDateFilter}
              onChange={(e) => handleFilterChange(setStartDateFilter, e.target.value)}
              className="w-full bg-[#050e24] border border-sky-500/30 rounded-lg px-2 py-1.5 text-sky-200 text-xs focus:border-sky-400"
            />
          </div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 4. CUMULATIVE R REALIZED EQUITY & ROLLING EXPECTANCY VISUALIZATION    */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      {equitySvg && (
        <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-sky-500/20">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-sky-400" />
              <h3 className="text-xs font-bold font-mono text-white uppercase tracking-wider">
                FILTERED EQUITY CURVE & PERFORMANCE TRAJECTORY
              </h3>
            </div>

            {/* Metric Switcher */}
            <div className="flex items-center gap-1.5 bg-[#050e24] p-1 rounded-xl border border-sky-500/20 text-xs font-mono">
              <button
                onClick={() => setActiveChartMetric("CUMULATIVE_R")}
                className={`px-3 py-1 rounded-lg font-bold transition-all ${
                  activeChartMetric === "CUMULATIVE_R"
                    ? "bg-sky-500/30 text-sky-200 border border-sky-500/40"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Cumulative ($)
              </button>
              <button
                onClick={() => setActiveChartMetric("DRAWDOWN")}
                className={`px-3 py-1 rounded-lg font-bold transition-all ${
                  activeChartMetric === "DRAWDOWN"
                    ? "bg-rose-500/30 text-rose-200 border border-rose-500/40"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Drawdown ($)
              </button>
              <button
                onClick={() => setActiveChartMetric("ROLLING_EXP")}
                className={`px-3 py-1 rounded-lg font-bold transition-all ${
                  activeChartMetric === "ROLLING_EXP"
                    ? "bg-emerald-500/30 text-emerald-200 border border-emerald-500/40"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Rolling-25 Exp ($)
              </button>
            </div>
          </div>

          <div className="w-full overflow-x-auto">
            <svg viewBox={`0 0 ${equitySvg.width} ${equitySvg.height}`} className="w-full h-64">
              {/* Zero Line */}
              <line
                x1={40}
                y1={equitySvg.zeroY}
                x2={equitySvg.width - 40}
                y2={equitySvg.zeroY}
                stroke="rgba(255,255,255,0.15)"
                strokeDasharray="4 4"
              />

              {/* Shaded Area */}
              <path
                d={equitySvg.areaD}
                fill={
                  activeChartMetric === "DRAWDOWN"
                    ? "rgba(244,63,94,0.15)"
                    : activeChartMetric === "ROLLING_EXP"
                    ? "rgba(16,185,129,0.12)"
                    : "rgba(56,189,248,0.12)"
                }
              />

              {/* Equity / Metric Line */}
              <path
                d={equitySvg.pathD}
                fill="none"
                stroke={
                  activeChartMetric === "DRAWDOWN"
                    ? "#f43f5e"
                    : activeChartMetric === "ROLLING_EXP"
                    ? "#10b981"
                    : "#38bdf8"
                }
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Samples Points */}
              {equitySvg.coords.map((c, i) => {
                if (i % Math.max(1, Math.floor(equitySvg.totalPoints / 60)) !== 0) return null;
                return (
                  <circle
                    key={i}
                    cx={c.x}
                    cy={c.y}
                    r={3}
                    fill={c.point.realized_r >= 0 ? "#10b981" : "#f43f5e"}
                    stroke="#071330"
                    strokeWidth="1.5"
                  />
                );
              })}
            </svg>
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-400 px-2 pt-2 border-t border-sky-500/10">
            <div>
              Start: <span className="text-zinc-200">{data?.equity_curve[0]?.timestamp.slice(0, 10)}</span>
            </div>
            <div className="text-center font-bold">
              {activeChartMetric === "CUMULATIVE_R" && (
                <span className="text-sky-300">Terminal Cumulative Return: {formatRAsUSD(kpis.total_realized_r, { showSign: true })}</span>
              )}
              {activeChartMetric === "DRAWDOWN" && (
                <span className="text-rose-300">Maximum Drawdown: {formatRAsUSD(-kpis.max_drawdown_r)}</span>
              )}
              {activeChartMetric === "ROLLING_EXP" && (
                <span className="text-emerald-300">Average Rolling Expectancy: {formatRAsUSD(kpis.expectancy_r, { showSign: true })}</span>
              )}
            </div>
            <div>
              End: <span className="text-zinc-200">{data?.equity_curve[data?.equity_curve.length - 1]?.timestamp.slice(0, 10)}</span>
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 5. HISTORICAL TRADE TABLE WITH VALIDATED STRATEGY QUALIFICATION       */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      <div className="bg-[#071330]/90 border border-sky-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-sky-500/20">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-400" />
            <h3 className="text-xs font-bold font-mono text-white uppercase tracking-wider">
              HISTORICAL TRADE LOG & VALIDATED STRATEGY ANALYTICS ({data?.total_count ?? 0} SIGNALS)
            </h3>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <label className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={dedupUniqueBars}
                onChange={(e) => setDedupUniqueBars(e.target.checked)}
                className="rounded border-sky-500/40 bg-[#050e24] text-sky-500 focus:ring-0 cursor-pointer"
              />
              <span>Deduplicate Multi-Run Timestamps</span>
            </label>

            {/* Pagination Top */}
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-zinc-400">
                Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || loading}
                  className="p-1 rounded bg-[#050e24] border border-sky-500/30 text-sky-200 hover:text-white disabled:opacity-40"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || loading}
                  className="p-1 rounded bg-[#050e24] border border-sky-500/30 text-sky-200 hover:text-white disabled:opacity-40"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Trade Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono text-left">
            <thead>
              <tr className="border-b border-sky-500/20 text-zinc-400 text-[11px]">
                <th className="pb-3 px-2.5">SIGNAL ID</th>
                <th className="pb-3 px-2.5">TIMESTAMP</th>
                <th className="pb-3 px-2.5">ASSET</th>
                <th className="pb-3 px-2.5">DIR</th>
                <th className="pb-3 px-2.5">PROB</th>
                <th className="pb-3 px-2.5">REGIME</th>
                <th className="pb-3 px-2.5">HTF</th>
                <th className="pb-3 px-2.5">S/R</th>
                <th className="pb-3 px-2.5">VWAP</th>
                <th className="pb-3 px-2.5">EMA</th>
                <th className="pb-3 px-2.5">OUTCOME</th>
                <th className="pb-3 px-2.5">REALIZED P&L</th>
                <th className="pb-3 px-2.5">STRATEGY QUALIFICATION</th>
                <th className="pb-3 px-2.5 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sky-500/10">
              {loading ? (
                <tr>
                  <td colSpan={14} className="py-12 text-center text-sky-300 animate-pulse">
                    Loading historical signals & point-in-time strategy analytics...
                  </td>
                </tr>
              ) : displayedSignals && displayedSignals.length > 0 ? (
                displayedSignals.map((s) => (
                  <tr key={s.signal_id} className="hover:bg-sky-500/10 transition-colors">
                    {/* Signal ID */}
                    <td className="py-2.5 px-2.5 font-mono text-[10px] text-sky-400" title={s.signal_id}>
                      <span className="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 font-bold">
                        {s.signal_id ? s.signal_id.replace(/^SIG-/, "").slice(0, 16) : "--"}
                      </span>
                    </td>
                    {/* Timestamp */}
                    <td className="py-2.5 px-2.5 text-zinc-300">
                      {s.signal_timestamp?.replace("T", " ")?.slice(0, 16)}
                    </td>

                    {/* Asset */}
                    <td className="py-2.5 px-2.5 font-bold text-white">
                      {s.symbol}
                    </td>

                    {/* Direction */}
                    <td className="py-2.5 px-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          s.direction === "BUY"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                        }`}
                      >
                        {s.direction}
                      </span>
                    </td>

                    {/* Calibrated Probability */}
                    <td className="py-2.5 px-2.5 font-bold text-sky-300">
                      {(s.calibrated_probability * 100).toFixed(1)}%
                    </td>

                    {/* Market Regime */}
                    <td className="py-2.5 px-2.5 text-zinc-300 text-[11px]">
                      {s.market_regime}
                    </td>

                    {/* HTF Alignment */}
                    <td className="py-2.5 px-2.5">
                      {s.htf_aligned ? (
                        <span className="text-emerald-400 font-bold flex items-center gap-1">
                          <Check size={13} />
                        </span>
                      ) : (
                        <span className="text-zinc-600 font-bold flex items-center gap-1">
                          ✕
                        </span>
                      )}
                    </td>

                    {/* S/R Alignment */}
                    <td className="py-2.5 px-2.5">
                      {s.sr_aligned ? (
                        <span className="text-emerald-400 font-bold flex items-center gap-1">
                          <Check size={13} />
                        </span>
                      ) : (
                        <span className="text-zinc-600 font-bold flex items-center gap-1">
                          ✕
                        </span>
                      )}
                    </td>

                    {/* VWAP Alignment */}
                    <td className="py-2.5 px-2.5">
                      {s.vwap_aligned ? (
                        <span className="text-emerald-400 font-bold flex items-center gap-1">
                          <Check size={13} />
                        </span>
                      ) : (
                        <span className="text-zinc-600 font-bold flex items-center gap-1">
                          ✕
                        </span>
                      )}
                    </td>

                    {/* EMA Alignment */}
                    <td className="py-2.5 px-2.5">
                      {s.ema_aligned ? (
                        <span className="text-emerald-400 font-bold flex items-center gap-1">
                          <Check size={13} />
                        </span>
                      ) : (
                        <span className="text-zinc-600 font-bold flex items-center gap-1">
                          ✕
                        </span>
                      )}
                    </td>

                    {/* Outcome */}
                    <td className="py-2.5 px-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          s.outcome === "WIN"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : s.outcome === "LOSS"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : "bg-zinc-500/20 text-zinc-400 border border-zinc-500/40"
                        }`}
                      >
                        {s.outcome || "PENDING"}
                      </span>
                    </td>

                    {/* Realized P&L */}
                    <td
                      className={`py-2.5 px-2.5 font-bold ${
                        (s.realized_r ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {formatRAsUSD(s.realized_r, { showSign: true })}
                    </td>

                    {/* Strategy Qualification Tag */}
                    <td className="py-2.5 px-2.5">
                      {s.qualification_status === "QUALIFIED" ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 w-fit">
                          <CheckCircle2 size={11} className="text-emerald-400" />
                          {s.qualification_tag}
                        </span>
                      ) : s.qualification_status === "INSUFFICIENT DATA" ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1 w-fit">
                          <AlertTriangle size={11} className="text-amber-400" />
                          INSUFFICIENT DATA
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-zinc-800/80 text-zinc-400 border border-zinc-700/60 flex items-center gap-1 w-fit">
                          <XCircle size={11} className="text-zinc-500" />
                          NOT QUALIFIED
                        </span>
                      )}
                    </td>

                    {/* Details Action Button */}
                    <td className="py-2.5 px-2.5 text-right">
                      <button
                        onClick={() => setSelectedSignalDetail(s)}
                        className="px-2.5 py-1 rounded bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 text-[10px] font-bold transition-all border border-sky-500/30"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={14} className="py-8 text-center text-zinc-500 italic">
                    No historical signals match the active filter configuration.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bottom */}
        <div className="flex items-center justify-between pt-3 border-t border-sky-500/20 text-xs font-mono">
          <div className="text-zinc-400">
            Showing signals <strong className="text-white">{(page - 1) * pageSize + 1}</strong> to{" "}
            <strong className="text-white">{Math.min(page * pageSize, data?.total_count || 0)}</strong> of{" "}
            <strong className="text-white">{data?.total_count || 0}</strong>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="px-3 py-1 rounded-lg bg-[#050e24] border border-sky-500/30 text-sky-200 hover:text-white disabled:opacity-40 font-bold transition-all"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="px-3 py-1 rounded-lg bg-[#050e24] border border-sky-500/30 text-sky-200 hover:text-white disabled:opacity-40 font-bold transition-all"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════ */}
      {/* 6. SIGNAL INSPECTOR MODAL                                             */}
      {/* ═════════════════════════════════════════════════════════════════════ */}
      {selectedSignalDetail && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-signal-inspector-title"
          onKeyDown={(e) => { if (e.key === "Escape") setSelectedSignalDetail(null); }}
          className="fixed inset-0 z-[200] bg-black/75 backdrop-blur-md flex items-center justify-center p-4"
        >
          <div className="bg-[#071330] border border-sky-500/40 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-sky-500/20">
              <h3 id="modal-signal-inspector-title" className="text-sm font-bold text-white flex items-center gap-2">
                <span>SIGNAL INSPECTOR — {selectedSignalDetail.signal_id}</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    selectedSignalDetail.direction === "BUY"
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                  }`}
                >
                  {selectedSignalDetail.direction}
                </span>
              </h3>
              <button
                type="button"
                onClick={() => setSelectedSignalDetail(null)}
                aria-label="Close signal inspector modal"
                className="text-zinc-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-zinc-300 bg-[#050e24] p-4 rounded-xl border border-sky-500/20">
              <div>
                Timestamp: <span className="text-white">{selectedSignalDetail.signal_timestamp}</span>
              </div>
              <div>
                Asset: <span className="text-white font-bold">{selectedSignalDetail.symbol}</span>
              </div>
              <div>
                Confluence Score:{" "}
                <span className="text-sky-300 font-bold">{selectedSignalDetail.confluence_score} pts</span>
              </div>
              <div>
                Calibrated Probability:{" "}
                <span className="text-emerald-400 font-bold">
                  {(selectedSignalDetail.calibrated_probability * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                Entry Price: <span className="text-white">${selectedSignalDetail.entry_price?.toLocaleString()}</span>
              </div>
              <div>
                Exit Price:{" "}
                <span className="text-white">
                  ${selectedSignalDetail.exit_price?.toLocaleString() ?? "—"}
                </span>
              </div>
              <div>
                Stop Loss:{" "}
                <span className="text-rose-400">
                  ${selectedSignalDetail.stop_loss?.toLocaleString() ?? "—"}
                </span>
              </div>
              <div>
                Take Profit:{" "}
                <span className="text-emerald-400">
                  ${selectedSignalDetail.take_profit_1?.toLocaleString() ?? "—"}
                </span>
              </div>
              <div>
                Outcome:{" "}
                <span className="text-emerald-300 font-bold">
                  {selectedSignalDetail.outcome ?? "PENDING"}
                </span>
              </div>
              <div>
                Realized Return:{" "}
                <span
                  className={`font-bold ${
                    (selectedSignalDetail.realized_r ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {formatRAsUSD(selectedSignalDetail.realized_r, { showSign: true })}
                </span>
              </div>
              <div>
                Regime: <span className="text-zinc-300">{selectedSignalDetail.market_regime}</span>
              </div>
              <div>
                Session: <span className="text-zinc-300">{selectedSignalDetail.session}</span>
              </div>
            </div>

            {/* Strategy Qualification Rationale */}
            <div className="p-3 rounded-xl bg-[#050e24] border border-sky-500/20 space-y-1">
              <div className="text-[10px] text-zinc-400 font-bold uppercase">
                Strategy Qualification Assessment:
              </div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] ${
                    selectedSignalDetail.qualification_status === "QUALIFIED"
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                  }`}
                >
                  {selectedSignalDetail.qualification_status}
                </span>
                <span className="text-sky-300">{selectedSignalDetail.qualification_tag}</span>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed pt-1">
                {selectedSignalDetail.qualification_reason}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
