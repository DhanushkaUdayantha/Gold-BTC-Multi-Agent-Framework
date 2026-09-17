"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  Line,
  Bar,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, RefreshCw, Move } from "lucide-react";
import { OHLCVCandle, TechnicalAnalysis, TradeRecord } from "@/services/api";
import { fmtPrice, isPresent } from "@/lib/format";

type ChartRow = {
  time: string;
  fullTime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  ema20: number | null;
  ema50: number | null;
  ema200: number | null;
  hl: [number, number];
};

type CandleShapeProps = {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: ChartRow;
};

function CandleShape(props: any) {
  const { x = 0, y = 0, width = 0, height = 0, payload } = props;
  const item: ChartRow | undefined = payload?.payload || payload;
  if (!item || height <= 0 || width <= 0) return null;
  const { open, close, high, low } = item;
  const range = high - low || 1;
  const isBull = close >= open;
  const color = isBull ? "#10b981" : "#ef4444";
  const bodyTop = Math.max(open, close);
  const bodyBot = Math.min(open, close);
  const bodyY = y + ((high - bodyTop) / range) * height;
  const bodyH = Math.max(((bodyTop - bodyBot) / range) * height, 1.5);
  const wickX = x + width / 2;
  const bodyW = Math.max(width - 2, 2);

  return (
    <g>
      <line x1={wickX} y1={y} x2={wickX} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={x + (width - bodyW) / 2} y={bodyY} width={bodyW} height={bodyH} fill={color} stroke={color} strokeWidth={0.5} />
    </g>
  );
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartRow }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const isBull = d.close >= d.open;
  return (
    <div className="bg-[#0c0c0f]/95 backdrop-blur-md border border-[#27272a] px-3 py-2 rounded-md text-[11px] font-mono space-y-0.5 shadow-2xl z-50 pointer-events-none">
      <p className="text-zinc-400 mb-1 font-bold">{d.fullTime}</p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        <p>O: <span className="text-zinc-200">{fmtPrice(d.open)}</span></p>
        <p>H: <span className="text-zinc-200">{fmtPrice(d.high)}</span></p>
        <p>L: <span className="text-zinc-200">{fmtPrice(d.low)}</span></p>
        <p>C: <span className={isBull ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{fmtPrice(d.close)}</span></p>
      </div>
      {isPresent(d.volume) && d.volume! > 0 && (
        <p className="text-zinc-400 pt-0.5">Vol: <span>{d.volume?.toLocaleString() ?? "—"}</span></p>
      )}
      <div className="pt-1 border-t border-zinc-800/80 flex flex-wrap gap-x-2 text-[10px]">
        {isPresent(d.ema20) && <span className="text-blue-400">EMA20: {fmtPrice(d.ema20)}</span>}
        {isPresent(d.ema50) && <span className="text-orange-400">EMA50: {fmtPrice(d.ema50)}</span>}
        {isPresent(d.ema200) && <span className="text-violet-400">EMA200: {fmtPrice(d.ema200)}</span>}
      </div>
    </div>
  );
}

function sliceSeries(series: Array<number | null> | null | undefined, count: number): Array<number | null> {
  if (!series || series.length === 0) return [];
  return series.slice(-count);
}

function formatTick(iso: string, timeframe: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  if (timeframe === "1d") {
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
  }
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function CandleChart({
  candles,
  technical,
  timeframe,
  loading,
  error,
  currentPrice,
  activeTrades = [],
}: {
  candles: OHLCVCandle[];
  technical: TechnicalAnalysis | null;
  timeframe: string;
  loading: boolean;
  error: string | null;
  currentPrice?: number;
  activeTrades?: TradeRecord[];
}) {
  const [zoomCandles, setZoomCandles] = useState<number>(60);
  const [panOffset, setPanOffset] = useState<number>(0);
  const [yOffset, setYOffset] = useState<number>(0);
  const [crosshairActive, setCrosshairActive] = useState<boolean>(true);

  // Indicators: All 4 OFF by default as requested
  const [showEMA20, setShowEMA20] = useState<boolean>(false);
  const [showEMA50, setShowEMA50] = useState<boolean>(false);
  const [showEMA200, setShowEMA200] = useState<boolean>(false);
  const [showSR, setShowSR] = useState<boolean>(false);

  // Mouse & Drag State for Crosshair and Pan
  const [mousePos, setMousePos] = useState<{ x: number; y: number; price?: number } | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number; initialPan: number; initialYOffset: number } | null>(null);
  const chartContainerRef = useRef<HTMLDivElement | null>(null);

  const handleZoomIn = () => {
    setZoomCandles((prev) => Math.max(20, prev - 15));
  };

  const handleZoomOut = () => {
    setZoomCandles((prev) => Math.min(candles.length || 200, prev + 20));
  };

  const handleResetZoom = () => {
    setZoomCandles(60);
    setPanOffset(0);
    setYOffset(0);
  };

  // Compute sliced candles considering panOffset
  const rawVisible = useMemo(() => {
    if (candles.length === 0) return [];
    const maxOffset = Math.max(0, candles.length - zoomCandles);
    const clampedOffset = Math.max(0, Math.min(maxOffset, panOffset));
    const endIdx = candles.length - clampedOffset;
    const startIdx = Math.max(0, endIdx - zoomCandles);
    return candles.slice(startIdx, endIdx);
  }, [candles, zoomCandles, panOffset]);

  const visibleCandles = useMemo(() => {
    return rawVisible.map((c, idx) => {
      // Only attach live price to the latest candle if we are not panned into history
      if (panOffset === 0 && idx === rawVisible.length - 1 && currentPrice && currentPrice > 0) {
        return {
          ...c,
          close: currentPrice,
          high: Math.max(c.high, currentPrice),
          low: Math.min(c.low, currentPrice),
        };
      }
      return c;
    });
  }, [rawVisible, currentPrice, panOffset]);

  const data: ChartRow[] = useMemo(() => {
    const ema20s = sliceSeries(technical?.ema20_series, visibleCandles.length);
    const ema50s = sliceSeries(technical?.ema50_series, visibleCandles.length);
    const ema200s = sliceSeries(technical?.ema200_series, visibleCandles.length);

    return visibleCandles.map((c, i) => ({
      time: formatTick(c.timestamp, timeframe),
      fullTime: new Date(c.timestamp).toLocaleString(),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      volume: c.volume,
      ema20: ema20s[i] ?? null,
      ema50: ema50s[i] ?? null,
      ema200: ema200s[i] ?? null,
      hl: [c.low, c.high],
    }));
  }, [visibleCandles, technical, timeframe]);

  const livePrice = currentPrice || (candles.length > 0 ? candles[candles.length - 1].close : 0);

  const yDomain = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const d of data) {
      if (d.low < min) min = d.low;
      if (d.high > max) max = d.high;
      if (showEMA20 && d.ema20 && d.ema20 < min) min = d.ema20;
      if (showEMA20 && d.ema20 && d.ema20 > max) max = d.ema20;
      if (showEMA50 && d.ema50 && d.ema50 < min) min = d.ema50;
      if (showEMA50 && d.ema50 && d.ema50 > max) max = d.ema50;
      if (showEMA200 && d.ema200 && d.ema200 < min) min = d.ema200;
      if (showEMA200 && d.ema200 && d.ema200 > max) max = d.ema200;
    }
    if (livePrice > 0 && panOffset === 0) {
      if (livePrice < min) min = livePrice;
      if (livePrice > max) max = livePrice;
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) return ["auto", "auto"];
    const pad = (max - min) * 0.08 || 5;
    return [Math.floor(min - pad + yOffset), Math.ceil(max + pad + yOffset)];
  }, [data, livePrice, showEMA20, showEMA50, showEMA200, panOffset, yOffset]);

  // Mouse Drag / Pan Event Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return; // Primary left button only
    setIsDragging(true);
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      initialPan: panOffset,
      initialYOffset: yOffset,
    });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = chartContainerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Calculate estimated price at y position within chart area
    const chartHeight = rect.height - 14;
    let currentHoverPrice: number | undefined;
    if (typeof yDomain[0] === "number" && typeof yDomain[1] === "number") {
      const minP = yDomain[0];
      const maxP = yDomain[1];
      const normY = Math.max(0, Math.min(1, (y - 14) / Math.max(1, chartHeight - 14)));
      currentHoverPrice = maxP - normY * (maxP - minP);
    }

    setMousePos({ x, y, price: currentHoverPrice });

    // Handle interactive pan/drag
    if (isDragging && dragStart) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;

      // Horizontal candle shift
      const chartWidth = Math.max(100, rect.width - 90);
      const candleWidth = Math.max(3, chartWidth / zoomCandles);
      const candleShift = Math.round(dx / candleWidth);
      const maxOffset = Math.max(0, candles.length - zoomCandles);
      const newPan = Math.max(0, Math.min(maxOffset, dragStart.initialPan + candleShift));
      setPanOffset(newPan);

      // Vertical price shift
      if (typeof yDomain[0] === "number" && typeof yDomain[1] === "number") {
        const priceRange = (yDomain[1] as number) - (yDomain[0] as number);
        const priceShift = (dy / rect.height) * priceRange * 0.8;
        setYOffset(dragStart.initialYOffset + priceShift);
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setDragStart(null);
    setMousePos(null);
  };

  if (loading && candles.length === 0) {
    return (
      <div className="h-[420px] flex flex-col items-center justify-center gap-3 text-blue-400 font-mono">
        <RefreshCw size={26} className="animate-spin text-blue-400 drop-shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
        <span className="text-xs font-bold tracking-wider text-blue-200 uppercase">
          Loading Candlestick Feed...
        </span>
      </div>
    );
  }

  if (error && candles.length === 0) {
    return (
      <div className="h-[420px] flex items-center justify-center text-xs font-mono text-rose-400 px-6 text-center">
        {error}
      </div>
    );
  }

  if (candles.length === 0) {
    return (
      <div className="h-[420px] flex items-center justify-center text-xs font-mono text-zinc-500">
        No candle data available for this timeframe.
      </div>
    );
  }

  const hasVolume = data.some((d) => isPresent(d.volume) && d.volume > 0);

  // Key Support & Resistance (sorted)
  const supports = [...(technical?.support_levels || [])]
    .sort((a, b) => b - a)
    .slice(0, 2);
  const resistances = [...(technical?.resistance_levels || [])]
    .sort((a, b) => a - b)
    .slice(0, 2);

  return (
    <div className="space-y-2">
      {/* Chart Interactive Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1.5 bg-[#101015] border border-[#1e1e26] rounded-lg text-[11px] font-mono">
        <div className="flex flex-wrap items-center gap-2">
          {livePrice > 0 && (
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-yellow-500/15 border border-yellow-500/40 text-yellow-300 font-bold text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-ping" />
              NOW: {fmtPrice(livePrice)}
            </div>
          )}
          {panOffset > 0 && (
            <button
              onClick={() => { setPanOffset(0); setYOffset(0); }}
              className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-500/40 text-sky-300 font-bold text-[10px] flex items-center gap-1 hover:bg-sky-500/30 transition-colors"
            >
              <Move size={10} /> Back to Live
            </button>
          )}
        </div>

        {/* Indicators Visibility Toggles (S/R & EMAs - All OFF by default) */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setShowSR(!showSR)}
            title="Toggle S/R Levels (S1, S2, R1, R2)"
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all flex items-center gap-1 border ${
              showSR
                ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300 shadow-sm"
                : "bg-[#181822] border-zinc-700 text-zinc-500 opacity-60 hover:opacity-100"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${showSR ? "bg-emerald-400" : "bg-zinc-600"}`} />
            S/R Lines
          </button>

          <button
            onClick={() => setShowEMA20(!showEMA20)}
            title="Toggle EMA 20 (Blue Line)"
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all flex items-center gap-1 border ${
              showEMA20
                ? "bg-blue-500/15 border-blue-500/40 text-blue-300 shadow-sm"
                : "bg-[#181822] border-zinc-700 text-zinc-500 opacity-60 hover:opacity-100"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${showEMA20 ? "bg-blue-400" : "bg-zinc-600"}`} />
            EMA 20
          </button>

          <button
            onClick={() => setShowEMA50(!showEMA50)}
            title="Toggle EMA 50 (Orange Line)"
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all flex items-center gap-1 border ${
              showEMA50
                ? "bg-orange-500/15 border-orange-500/40 text-orange-300 shadow-sm"
                : "bg-[#181822] border-zinc-700 text-zinc-500 opacity-60 hover:opacity-100"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${showEMA50 ? "bg-orange-400" : "bg-zinc-600"}`} />
            EMA 50
          </button>

          <button
            onClick={() => setShowEMA200(!showEMA200)}
            title="Toggle EMA 200 (Purple Line)"
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all flex items-center gap-1 border ${
              showEMA200
                ? "bg-purple-500/15 border-purple-500/40 text-purple-300 shadow-sm"
                : "bg-[#181822] border-zinc-700 text-zinc-500 opacity-60 hover:opacity-100"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${showEMA200 ? "bg-purple-400" : "bg-zinc-600"}`} />
            EMA 200
          </button>
        </div>

        {/* Zoom & Crosshair Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleZoomIn}
            title="Zoom In"
            aria-label="Zoom in on candlestick chart"
            className="p-1 rounded bg-[#181822] hover:bg-[#272736] border border-zinc-700 text-zinc-300 transition-colors"
          >
            <ZoomIn size={13} />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            title="Zoom Out"
            aria-label="Zoom out on candlestick chart"
            className="p-1 rounded bg-[#181822] hover:bg-[#272736] border border-zinc-700 text-zinc-300 transition-colors"
          >
            <ZoomOut size={13} />
          </button>
          <button
            type="button"
            onClick={handleResetZoom}
            title="Reset Zoom & Pan"
            aria-label="Reset chart zoom and pan"
            className="p-1 rounded bg-[#181822] hover:bg-[#272736] border border-zinc-700 text-zinc-300 transition-colors flex items-center gap-1 text-[10px] px-1.5"
          >
            <RotateCcw size={11} /> Reset
          </button>
          <button
            type="button"
            onClick={() => setCrosshairActive(!crosshairActive)}
            title="Toggle Crosshair Cursor"
            aria-label="Toggle crosshair cursor"
            className={`p-1 rounded border transition-colors ${
              crosshairActive
                ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
                : "bg-[#181822] border-zinc-700 text-zinc-500"
            }`}
          >
            <Crosshair size={13} />
          </button>
        </div>
      </div>

      {/* Interactive Chart Container with Crosshair and Drag/Pan */}
      <div
        ref={chartContainerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        className={`relative select-none ${hasVolume ? "h-[370px]" : "h-[430px]"} ${
          isDragging ? "cursor-grabbing" : crosshairActive ? "cursor-crosshair" : "cursor-default"
        }`}
      >
        {/* Horizontal & Vertical Crosshair Guide Lines Overlay */}
        {crosshairActive && mousePos && mousePos.x >= 0 && mousePos.x <= (chartContainerRef.current?.clientWidth || 9999) - 78 && (
          <div className="absolute inset-0 pointer-events-none z-30 overflow-hidden">
            {/* Vertical Guide Line */}
            <div
              className="absolute top-0 bottom-0 border-l border-dashed border-zinc-400/50"
              style={{ left: `${mousePos.x}px` }}
            />
            {/* Horizontal Guide Line */}
            <div
              className="absolute left-0 right-[78px] border-t border-dashed border-zinc-400/50"
              style={{ top: `${mousePos.y}px` }}
            />
            {/* Price Tag badge on Y-Axis */}
            {mousePos.price && (
              <div
                className="absolute right-0 px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-600 text-zinc-100 text-[10px] font-mono font-bold shadow-lg"
                style={{ top: `${Math.max(2, Math.min((chartContainerRef.current?.clientHeight || 400) - 22, mousePos.y - 10))}px` }}
              >
                ${mousePos.price.toFixed(2)}
              </div>
            )}
          </div>
        )}

        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 14, right: 90, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#1e1e24" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="time" stroke="#52525b" fontSize={10} tickLine={false} minTickGap={24} />
            <YAxis
              domain={yDomain}
              stroke="#52525b"
              fontSize={10}
              tickLine={false}
              orientation="right"
              width={78}
              tickFormatter={(v: number) => v.toFixed(1)}
            />
            <Tooltip
              content={<ChartTooltip />}
              cursor={false}
            />

            {/* Support Levels with labels */}
            {showSR && supports.map((level, idx) => (
              <ReferenceLine
                key={`s-${level}`}
                y={level}
                stroke="#10b981"
                strokeDasharray="4 4"
                strokeWidth={1.2}
                strokeOpacity={0.85}
                label={{
                  value: `S${idx + 1} $${level.toFixed(1)}`,
                  position: "right",
                  fill: "#34d399",
                  fontSize: 10,
                  fontWeight: 600,
                  offset: 5,
                }}
              />
            ))}

            {/* Resistance Levels with labels */}
            {showSR && resistances.map((level, idx) => (
              <ReferenceLine
                key={`r-${level}`}
                y={level}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.2}
                strokeOpacity={0.85}
                label={{
                  value: `R${idx + 1} $${level.toFixed(1)}`,
                  position: "right",
                  fill: "#f87171",
                  fontSize: 10,
                  fontWeight: 600,
                  offset: 5,
                }}
              />
            ))}

            {/* Live Spot Price line (Yellow Line / Support indicator) */}
            {livePrice > 0 && (
              <ReferenceLine
                y={livePrice}
                stroke="#eab308"
                strokeDasharray="4 2"
                strokeWidth={1.8}
                strokeOpacity={0.95}
                label={{
                  value: `▶ NOW: $${livePrice.toFixed(2)}`,
                  position: "right",
                  fill: "#facc15",
                  fontSize: 10,
                  fontWeight: 700,
                  offset: 6,
                }}
              />
            )}

            {/* Active Demo Trade Positions (Entry, SL, TP) */}
            {activeTrades.map((trade) => {
              const isBuy = trade.direction === "BUY";
              return (
                <React.Fragment key={`trade-group-${trade.id}`}>
                  {/* Entry Line */}
                  <ReferenceLine
                    y={trade.entry_price}
                    stroke={isBuy ? "#38bdf8" : "#fb7185"}
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    label={{
                      value: `DEMO ${trade.direction} @ $${trade.entry_price.toFixed(1)}`,
                      position: "insideTopLeft",
                      fill: isBuy ? "#38bdf8" : "#fb7185",
                      fontSize: 10,
                      fontWeight: "bold",
                    }}
                  />
                  {/* Stop Loss Line if set */}
                  {trade.stop_loss > 0 && (
                    <ReferenceLine
                      y={trade.stop_loss}
                      stroke="#f43f5e"
                      strokeWidth={1}
                      strokeDasharray="2 4"
                      label={{
                        value: `SL $${trade.stop_loss.toFixed(1)}`,
                        position: "insideBottomLeft",
                        fill: "#f43f5e",
                        fontSize: 9,
                      }}
                    />
                  )}
                  {/* TP Line if set */}
                  {trade.take_profit_1 > 0 && (
                    <ReferenceLine
                      y={trade.take_profit_1}
                      stroke="#10b981"
                      strokeWidth={1}
                      strokeDasharray="2 4"
                      label={{
                        value: `TP $${trade.take_profit_1.toFixed(1)}`,
                        position: "insideTopLeft",
                        fill: "#10b981",
                        fontSize: 9,
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}

            {showEMA20 && <Line type="monotone" dataKey="ema20" stroke="#3b82f6" strokeWidth={1.25} dot={false} connectNulls={false} isAnimationActive={false} />}
            {showEMA50 && <Line type="monotone" dataKey="ema50" stroke="#f97316" strokeWidth={1.25} dot={false} connectNulls={false} isAnimationActive={false} />}
            {showEMA200 && <Line type="monotone" dataKey="ema200" stroke="#a855f7" strokeWidth={1.25} dot={false} connectNulls={false} isAnimationActive={false} />}
            <Bar key="candlestick-bars" dataKey="hl" shape={<CandleShape />} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {hasVolume && (
        <div className="h-[75px] pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 0, right: 90, left: 0, bottom: 0 }}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Bar dataKey="volume" fill="#3b82f6" fillOpacity={0.3} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
