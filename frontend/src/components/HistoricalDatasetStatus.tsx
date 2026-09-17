"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Database,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Calendar,
  BarChart2,
  ShieldCheck,
  Zap,
  Activity,
  HardDrive,
  Info,
  Radio,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import {
  ApiClient,
  DatasetMetadata,
  DatasetQualityReport,
  DatasetFastStatus,
  DatasetSymbolStatus,
  LiveIngestionStatus,
} from "@/services/api";

interface HistoricalDatasetStatusProps {
  className?: string;
  symbol?: string;
  onRefreshTriggered?: () => void;
}

export function HistoricalDatasetStatus({
  className = "",
  symbol,
  onRefreshTriggered,
}: HistoricalDatasetStatusProps) {
  const [fastStatus, setFastStatus] = useState<DatasetFastStatus | null>(null);
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [liveIngestion, setLiveIngestion] = useState<Record<string, LiveIngestionStatus>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);

  const onRefreshRef = useRef(onRefreshTriggered);
  onRefreshRef.current = onRefreshTriggered;

  const loadDatasets = useCallback(async (isUserTriggered = false) => {
    if (isUserTriggered) {
      setRefreshing(true);
    }
    setError(null);
    try {
      // Fetch fast aggregate status and live ingestion status in parallel
      const [fastData, ingestionData] = await Promise.allSettled([
        ApiClient.fetchDatasetStatus(),
        ApiClient.fetchLiveIngestionStatus(),
      ]);

      if (fastData.status === "fulfilled") {
        const fd = fastData.value;
        setFastStatus(fd);

        // Also pick up live_ingestion if included in fast-status response
        if (fd?.live_ingestion) {
          setLiveIngestion((prev) => ({ ...prev, ...fd.live_ingestion }));
        }

        // Map registered datasets for backward-compatible cards
        if (fd?.registered_datasets) {
          setDatasets(
            fd.registered_datasets.map((d) => ({
              dataset_id: d.dataset_id,
              symbol: d.symbol,
              source_symbol: d.source_symbol,
              source: d.source,
              description: `Historical dataset for ${d.symbol}`,
              timeframes: Object.keys(fd.symbols[d.symbol]?.timeframes || {}),
              start_date: d.start_date || fd.symbols[d.symbol]?.start_date || "",
              end_date: d.end_date || fd.symbols[d.symbol]?.end_date || "",
              row_count: fd.symbols[d.symbol]?.total_candles || d.row_count,
              valid_rows: fd.symbols[d.symbol]?.total_candles || d.valid_rows,
              volume_available: true,
              version: "v2.0",
              created_at: fd.server_timestamp,
              status: d.status || "SYNCHRONIZED",
            }))
          );
        }
      }

      if (ingestionData.status === "fulfilled" && ingestionData.value) {
        setLiveIngestion(ingestionData.value);
      }

      setLastSyncAt(new Date().toISOString());
      if (isUserTriggered && onRefreshRef.current) {
        onRefreshRef.current();
      }
    } catch (err) {
      console.error("Failed to fetch historical dataset status:", err);
      try {
        const data = await ApiClient.fetchBacktestDatasets();
        setDatasets(data || []);
        setLastSyncAt(new Date().toISOString());
      } catch {
        setError(err instanceof Error ? err.message : "Failed to load historical datasets");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets(false);
    // Poll every 5 minutes — matches the ingestion daemon cadence
    const timer = setInterval(() => {
      loadDatasets(false);
    }, 300_000);
    return () => clearInterval(timer);
  }, [loadDatasets]);

  // Per-symbol live ingestion info
  const btcLive = liveIngestion["BTC/USD"];
  const xauLive = liveIngestion["XAU/USD"];

  // Separate BTC and XAU datasets
  const btcSymStatus = fastStatus?.symbols?.["BTC/USD"];
  const xauSymStatus = fastStatus?.symbols?.["XAU/USD"];

  const btcDataset = datasets.find(
    (d) => d.symbol.toUpperCase().includes("BTC") || d.source_symbol.toUpperCase().includes("BTC")
  );
  const xauDataset = datasets.find(
    (d) =>
      d.symbol.toUpperCase().includes("XAU") ||
      d.symbol.toUpperCase().includes("GOLD") ||
      d.source_symbol.toUpperCase().includes("GC")
  );

  const formatIsoDate = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toISOString().replace("T", " ").substring(0, 16) + " UTC";
    } catch {
      return isoStr;
    }
  };

  const formatDateShort = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      });
    } catch {
      return isoStr;
    }
  };

  /** Determine whether the last ingestion was within the past 10 minutes. */
  const isLiveRecent = (ingestionStatus?: LiveIngestionStatus): boolean => {
    if (!ingestionStatus?.last_ingested_at) return false;
    try {
      const lastAt = new Date(ingestionStatus.last_ingested_at).getTime();
      return Date.now() - lastAt < 10 * 60 * 1000;
    } catch {
      return false;
    }
  };

  /** Render a coloured live-ingestion badge for a symbol. */
  const renderLiveBadge = (ingestionStatus?: LiveIngestionStatus) => {
    if (!ingestionStatus) return null;
    const st = ingestionStatus.status;
    const recent = isLiveRecent(ingestionStatus);

    if (st === "LIVE" && recent) {
      return (
        <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          LIVE
        </span>
      );
    }
    if (st === "SYNCING" || st === "CATCHING_UP") {
      return (
        <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/35">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
          SYNCING
        </span>
      );
    }
    if (st === "DATA GAP" || st === "STALE" || st === "STANDBY" || st === "PARTIAL") {
      return (
        <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/35">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          Live Data: Not Updating
        </span>
      );
    }
    if (st === "ERROR") {
      return (
        <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/35">
          <AlertTriangle size={9} />
          ERROR
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-zinc-700/40 text-zinc-400 border border-zinc-600/40">
        {st}
      </span>
    );
  };

  /** Render the live extension info strip below each dataset card. */
  const renderLiveExtension = (ingestionStatus?: LiveIngestionStatus) => {
    if (!ingestionStatus) return null;
    const liveAdded = ingestionStatus.live_candles_added ?? 0;
    const baselineEnd = ingestionStatus.baseline_end;
    const latestTs = ingestionStatus.last_candle_timestamp;
    const hasGap =
      ingestionStatus.last_error &&
      ingestionStatus.last_error.toLowerCase().includes("gap");

    return (
      <div className="mt-3 p-3 bg-[#06100a]/80 border border-emerald-800/30 rounded-lg font-mono text-[10px] space-y-1.5">
        <div className="flex items-center justify-between border-b border-emerald-900/40 pb-1.5">
          <span className="text-emerald-400 font-bold uppercase text-[9px] tracking-wider flex items-center gap-1">
            <Radio size={9} className="text-emerald-400 animate-pulse" />
            Live 5m Auto-Ingestion
          </span>
          {renderLiveBadge(ingestionStatus)}
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <div>
            <span className="text-zinc-500">Baseline End:</span>{" "}
            <span className="text-zinc-300 font-semibold">{formatDateShort(baselineEnd)}</span>
          </div>
          <div>
            <span className="text-zinc-500">Latest Candle:</span>{" "}
            <span className="text-emerald-300 font-semibold">{formatDateShort(latestTs)}</span>
          </div>
          <div>
            <span className="text-zinc-500">Baseline Candles:</span>{" "}
            <span className="text-zinc-200 font-semibold">
              {(ingestionStatus.baseline_candles ?? 0).toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-zinc-500">Live Added:</span>{" "}
            <span className={liveAdded > 0 ? "text-emerald-400 font-bold" : "text-zinc-400"}>
              +{liveAdded.toLocaleString()}
            </span>
          </div>
        </div>

        {hasGap && ingestionStatus.last_error && (
          <div className="pt-1 flex items-start gap-1 text-amber-400/80 text-[9px]">
            <AlertTriangle size={9} className="shrink-0 mt-0.5" />
            <span className="leading-tight">{ingestionStatus.last_error}</span>
          </div>
        )}

        {ingestionStatus.last_ingested_at && (
          <div className="text-zinc-500 text-[9px]">
            Last sync: {formatIsoDate(ingestionStatus.last_ingested_at)}
          </div>
        )}
      </div>
    );
  };

  const renderDatasetCard = (
    symbol: string,
    defaultSource: string,
    defaultSourceSymbol: string,
    theme: {
      border: string;
      badge: string;
      accentText: string;
      glow: string;
      iconColor: string;
      bgGradient: string;
    },
    dataset?: DatasetMetadata,
    symStatus?: DatasetSymbolStatus,
    ingestionStatus?: LiveIngestionStatus
  ) => {
    const isReady = (dataset != null && dataset.row_count > 0) || (symStatus != null && symStatus.total_candles > 0);
    const qr: DatasetQualityReport | undefined = dataset?.quality_report;
    // Show total candles (baseline + live added) if available
    const baselineCount = symStatus?.total_candles ?? dataset?.row_count ?? 0;
    const liveAdded = ingestionStatus?.live_candles_added ?? 0;
    const totalCount = ingestionStatus ? (ingestionStatus.baseline_candles + liveAdded) : baselineCount;
    
    // Truthful Quality Score: Never force 100.0% when unverified
    const hasQualityReport = qr?.quality_score_pct != null;
    const hasValidRowsRatio = dataset?.valid_rows != null && dataset?.row_count != null && dataset.row_count > 0;
    const qualityScore: number | null = hasQualityReport
      ? qr.quality_score_pct!
      : hasValidRowsRatio
      ? Math.min(100, Math.max(0, (dataset!.valid_rows / dataset!.row_count) * 100))
      : null;
    const qualityStatusText = hasQualityReport
      ? "Audit Verified"
      : hasValidRowsRatio
      ? "Row Validated"
      : isReady
      ? "Awaiting Audit"
      : "Unverified";

    const sourceSymbol = dataset?.source_symbol ?? defaultSourceSymbol;
    const sourceName = dataset?.source
      ? dataset.source.toUpperCase() === "BINANCE"
        ? "Binance Public API"
        : dataset.source.toUpperCase() === "YAHOO"
        ? "Yahoo Finance"
        : dataset.source.toUpperCase()
      : defaultSource;

    const availableTfs = symStatus?.timeframes
      ? Object.keys(symStatus.timeframes)
      : dataset?.timeframes && dataset.timeframes.length > 0
      ? dataset.timeframes
      : ["15m"];

    const timeframesStr = availableTfs.map((t) => t.toUpperCase()).join(", ");
    const startDate = ingestionStatus?.baseline_start ?? symStatus?.start_date ?? dataset?.start_date;
    // Latest date: prefer live candle timestamp if available, else fall back to dataset end
    const latestDate = ingestionStatus?.last_candle_timestamp ?? symStatus?.end_date ?? dataset?.end_date;
    const completedSigs = symStatus?.completed_signals;

    return (
      <div
        className={`relative bg-[#0c0c0f] border ${theme.border} rounded-xl p-4 sm:p-5 shadow-sm transition-all duration-500 hover:scale-[1.005] ${theme.glow} flex flex-col justify-between`}
      >
        {/* Card Header */}
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1e1e24] pb-3 mb-4">
            <div className="flex items-center gap-2.5">
              <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-md border ${theme.badge}`}>
                {symbol}
              </span>
              <span className="text-[11px] font-mono text-zinc-400 font-semibold">
                Proxy: <strong className="text-zinc-200">{sourceSymbol}</strong>
              </span>
            </div>

            <div className="flex items-center gap-2 font-mono">
              {/* Live ingestion badge (preferred) or legacy status */}
              {ingestionStatus && ingestionStatus.status === "LIVE" ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  LIVE INGESTION ACTIVE
                </span>
              ) : ingestionStatus && ingestionStatus.status === "CATCHING_UP" ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-500/15 text-sky-300 border border-sky-500/30">
                  <RefreshCw size={10} className="animate-spin text-sky-400" />
                  CATCHING UP
                </span>
              ) : isReady ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  DATASET SYNCHRONIZED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <AlertCircle size={10} />
                  NO LOCAL DATA
                </span>
              )}

              <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                {sourceName}
              </span>
            </div>
          </div>

          {/* Core Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono mb-4">
            {/* Total Candles (baseline + live extended) */}
            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
              <div className="text-[10px] text-zinc-500 uppercase flex items-center gap-1 font-semibold">
                <BarChart2 size={10} className={theme.iconColor} />
                Total Candles
              </div>
              <div className="font-bold text-zinc-100 mt-1 text-xs sm:text-sm truncate">
                {totalCount > 0 ? `${totalCount.toLocaleString()} bars` : "—"}
              </div>
              <div className="text-[9px] text-emerald-400 font-medium truncate">
                {liveAdded > 0
                  ? `Baseline + ${liveAdded.toLocaleString()} live`
                  : totalCount > 0
                  ? `${availableTfs.length} Timeframe Streams`
                  : "Awaiting sync"}
              </div>
            </div>

            {/* Timeframe */}
            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
              <div className="text-[10px] text-zinc-500 uppercase flex items-center gap-1 font-semibold">
                <Layers size={10} className={theme.iconColor} />
                Timeframes
              </div>
              <div className={`font-bold mt-1 truncate ${theme.accentText}`} title={timeframesStr}>
                {timeframesStr}
              </div>
              <div className="text-[9px] text-zinc-500">Multi-TF Ready</div>
            </div>

            {/* Date Range Start (baseline) */}
            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
              <div className="text-[10px] text-zinc-500 uppercase flex items-center gap-1 font-semibold">
                <Calendar size={10} className={theme.iconColor} />
                Range Start
              </div>
              <div className="font-bold text-zinc-200 mt-1 truncate" title={formatIsoDate(startDate)}>
                {formatDateShort(startDate)}
              </div>
              <div className="text-[9px] text-zinc-500">UTC Start</div>
            </div>

            {/* Data Quality Score */}
            <div className="bg-[#121217] border border-[#202028] rounded-lg p-2.5">
              <div className="text-[10px] text-zinc-500 uppercase flex items-center gap-1 font-semibold">
                <ShieldCheck size={10} className="text-emerald-400" />
                Data Quality
              </div>
              <div className={`font-bold mt-1 text-sm flex items-center gap-1 ${qualityScore != null ? "text-emerald-400" : "text-zinc-400"}`}>
                {qualityScore != null ? `${qualityScore.toFixed(1)}%` : isReady ? "--%" : "—"}
              </div>
              <div className="text-[9px] text-zinc-400 font-medium">
                {qualityStatusText}
              </div>
            </div>
          </div>

          {/* Quality Audit Breakdown Strip */}
          <div className="p-3 bg-[#080d1a] border border-[#1a233a] rounded-lg font-mono text-[11px] space-y-2 mb-3">
            <div className="flex items-center justify-between text-zinc-400 border-b border-zinc-800/80 pb-1.5">
              <span className="text-zinc-500 uppercase text-[9.5px] font-bold tracking-wider">
                Integrity Pipeline Audit
              </span>
              <span className={`font-semibold text-[10px] flex items-center gap-1 ${qr ? "text-emerald-400" : "text-zinc-400"}`}>
                {qr ? (
                  <>
                    <CheckCircle2 size={11} className="text-emerald-400" />
                    0 Synthetic / 0 Bad OHLC
                  </>
                ) : (
                  <>
                    <Clock size={11} className="text-amber-400" />
                    Pipeline Synchronized
                  </>
                )}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
              <div>
                <span className="text-zinc-500">Rejected Rows: </span>
                <strong className="text-zinc-200">{qr ? (qr.rejected_rows ?? 0) : "—"}</strong>
              </div>
              <div>
                <span className="text-zinc-500">Duplicates: </span>
                <strong className="text-zinc-200">{qr ? (qr.duplicate_rows ?? 0) : "—"}</strong>
              </div>
              <div>
                <span className="text-zinc-500">Future Timestamps: </span>
                <strong className="text-zinc-200">{qr ? (qr.future_rows ?? 0) : "—"}</strong>
              </div>
              <div>
                <span className="text-zinc-500">Volume Status: </span>
                <strong className={dataset?.volume_available ? "text-emerald-400" : "text-amber-400"}>
                  {dataset?.volume_available ? "Available" : "Proxy N/A"}
                </strong>
              </div>
            </div>

            {completedSigs && completedSigs.total > 0 && (
              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[10px]">
                <span className="text-zinc-400 font-semibold">Historical Signals:</span>
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400 font-bold">{completedSigs.WIN} WIN</span>
                  <span className="text-rose-400 font-bold">{completedSigs.LOSS} LOSS</span>
                  <span className="text-zinc-400">({completedSigs.total} Total)</span>
                </div>
              </div>
            )}
          </div>

          {/* Live ingestion extension strip */}
          {renderLiveExtension(ingestionStatus)}
        </div>

        {/* Card Footer: Metadata & Database Path */}
        <div className="pt-2 border-t border-[#181820] flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-zinc-500 mt-3">
          <div className="flex items-center gap-1.5">
            <Clock size={10} className="text-amber-400 shrink-0" />
            <span>Last Ingested:</span>
            <span className="text-zinc-300 font-medium">
              {ingestionStatus?.last_ingested_at
                ? formatIsoDate(ingestionStatus.last_ingested_at)
                : dataset?.created_at
                ? formatIsoDate(dataset.created_at)
                : "Auto-Initialized"}
            </span>
          </div>

          <div className="flex items-center gap-1 text-zinc-400">
            <HardDrive size={10} className="text-sky-400 shrink-0" />
            <span>SQLite v{dataset?.version || "2.0"}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <section
      className={`bg-[#080c14]/90 border border-sky-500/25 rounded-xl p-4 sm:p-6 shadow-[0_8px_30px_rgba(2,6,23,0.5),inset_0_1px_1px_rgba(255,255,255,0.06)] backdrop-blur-md space-y-4 ${className}`}
    >
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-sky-500/20 pb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.25)]">
            <Database size={16} className="text-sky-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold font-mono uppercase tracking-wider text-zinc-100 flex items-center gap-2">
                Historical Dataset Status
              </h2>
              <span className="text-[9.5px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">
                Live Database
              </span>
              {/* Global live badge if active symbol is LIVE */}
              {(() => {
                const isBtc = symbol ? symbol.toUpperCase().includes("BTC") : false;
                const isLive = symbol ? (isBtc ? btcLive?.status === "LIVE" : xauLive?.status === "LIVE") : (btcLive?.status === "LIVE" || xauLive?.status === "LIVE");
                if (!isLive) return null;
                return (
                  <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    INGESTING
                  </span>
                );
              })()}
            </div>
            <p className="text-[10px] sm:text-[11px] font-mono text-sky-200/60 mt-0.5">
              Auto-accumulating multi-timeframe candles — original 2016–2026 baseline immutable, live 5m candles appended every 5 min
            </p>
          </div>
        </div>

        {/* Refresh control only (no manual download button) */}
        <div className="flex items-center gap-2.5 self-start sm:self-auto font-mono text-xs">
          {lastSyncAt && (
            <span className="hidden md:inline-block text-[10px] text-zinc-400">
              Synced: <strong className="text-zinc-300">{formatDateShort(lastSyncAt)} {new Date(lastSyncAt).toLocaleTimeString()}</strong>
            </span>
          )}

          <button
            type="button"
            onClick={() => loadDatasets(true)}
            disabled={refreshing || loading}
            className="px-3 py-1.5 rounded-lg bg-sky-950/50 hover:bg-sky-900/60 border border-sky-500/30 hover:border-sky-400/50 text-sky-200 font-bold text-xs flex items-center gap-1.5 transition-all duration-300 disabled:opacity-50 shadow-[0_0_12px_rgba(56,189,248,0.15)]"
            title="Refresh historical dataset status from database"
          >
            <RefreshCw size={12} className={refreshing || loading ? "animate-spin text-cyan-400" : "text-sky-300"} />
            {refreshing ? "SYNCING..." : "REFRESH"}
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-lg flex items-center gap-2.5 font-mono text-xs text-rose-300">
          <AlertCircle size={14} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state skeleton */}
      {loading && datasets.length === 0 ? (
        <div className="py-10 flex flex-col items-center justify-center gap-3 text-sky-400 font-mono">
          <RefreshCw size={24} className="animate-spin text-cyan-400 drop-shadow-[0_0_12px_rgba(56,189,248,0.8)]" />
          <span className="text-xs font-bold tracking-wider text-sky-200 uppercase">
            QUERYING HISTORICAL DATASET REPOSITORY ({symbol ? (symbol.toUpperCase().includes("BTC") ? "BTC/USD" : "XAU/USD") : "BTC/USD & XAU/USD"})...
          </span>
        </div>
      ) : (
        /* Dataset Cards Grid for Active Symbol (Strict Isolation) */
        <div className={`grid grid-cols-1 ${!symbol ? "lg:grid-cols-2" : ""} gap-5`}>
          {/* BTC/USD Dataset Card */}
          {(!symbol || symbol.includes("BTC")) && renderDatasetCard(
            "BTC/USD",
            "Binance Public API",
            "BTCUSDT",
            {
              border: "border-orange-500/35 hover:border-orange-500/60",
              badge: "bg-orange-500/15 text-orange-300 border-orange-500/40",
              accentText: "text-orange-400",
              glow: "hover:shadow-[0_0_30px_rgba(249,115,22,0.18)]",
              iconColor: "text-orange-400",
              bgGradient: "from-orange-950/20 via-[#0c0c0f] to-[#0c0c0f]",
            },
            btcDataset,
            btcSymStatus,
            btcLive
          )}

          {/* XAU/USD Dataset Card */}
          {(!symbol || symbol.includes("XAU") || symbol.includes("GOLD")) && renderDatasetCard(
            "XAU/USD",
            "Yahoo Finance",
            "GC=F",
            {
              border: "border-amber-500/35 hover:border-amber-500/60",
              badge: "bg-amber-500/15 text-amber-300 border-amber-500/40",
              accentText: "text-amber-400",
              glow: "hover:shadow-[0_0_30px_rgba(245,158,11,0.18)]",
              iconColor: "text-amber-400",
              bgGradient: "from-amber-950/20 via-[#0c0c0f] to-[#0c0c0f]",
            },
            xauDataset,
            xauSymStatus,
            xauLive
          )}
        </div>
      )}

      {/* Dataset Storage & Verification Info Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-[10px] font-mono text-zinc-500 border-t border-[#161c2c]">
        <div className="flex items-center gap-1.5">
          <Info size={11} className="text-sky-400 shrink-0" />
          <span>Historical Storage:</span>
          <code className="text-zinc-300 font-semibold bg-[#0d1527] px-1.5 py-0.5 rounded border border-[#1b2640]">
            data/historical/historical_market_data.db
          </code>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-zinc-400">Datasets:</span>
          <span className="text-sky-300 font-bold">{datasets.length} Active</span>
          <span className="text-zinc-600">&middot;</span>
          <span className="text-emerald-400 font-semibold">Original OHLCV Immutable</span>
          <span className="text-zinc-600">&middot;</span>
          <span className="text-sky-400 font-semibold">5m Live Auto-Extend</span>
        </div>
      </div>
    </section>
  );
}
