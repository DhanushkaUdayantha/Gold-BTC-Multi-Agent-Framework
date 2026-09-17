"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getPrice,
  getCandles,
  getMarketStatus,
  getTechnicalAnalysis,
  getAIAnalysis,
  getRawTechnicalInput,
  getDecision,
  getHealth,
  PriceQuote,
  CandleHistory,
  MarketStatus,
  TechnicalAnalysis,
  AIAnalysis,
  MultiTimeframeInput,
  TradingDecision,
  HealthStatus,
  OHLCVCandle,
} from "@/services/api";
import { fmtTime } from "@/lib/format";

const PRICE_MS = 2500;
const TECH_MS = 8000;
const DECISION_MS = 120000;

export interface DashboardErrors {
  price: string | null;
  candles: string | null;
  technical: string | null;
  mtf: string | null;
  ai: string | null;
  decision: string | null;
  status: string | null;
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error";
}

export function useDashboardData(timeframe: string, symbol: string = "XAU-USD-SPOT") {
  const [price, setPrice] = useState<PriceQuote | null>(null);
  const [candles, setCandles] = useState<OHLCVCandle[]>([]);
  const [candleMeta, setCandleMeta] = useState<CandleHistory | null>(null);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [technical, setTechnical] = useState<TechnicalAnalysis | null>(null);
  const [mtf, setMtf] = useState<MultiTimeframeInput | null>(null);
  const [ai, setAi] = useState<AIAnalysis | null>(null);
  const [decision, setDecision] = useState<TradingDecision | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const [errors, setErrors] = useState<DashboardErrors>({
    price: null,
    candles: null,
    technical: null,
    mtf: null,
    ai: null,
    decision: null,
    status: null,
  });

  const [loadedSymbol, setLoadedSymbol] = useState(symbol);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tfSwitching, setTfSwitching] = useState(false);
  const [assetSwitching, setAssetSwitching] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("");
  const [lastAiUpdated, setLastAiUpdated] = useState("");

  const tfRef = useRef(timeframe);
  tfRef.current = timeframe;
  const prevTfRef = useRef(timeframe);
  const symRef = useRef(symbol);
  symRef.current = symbol;
  const prevSymbolRef = useRef(symbol);
  const mounted = useRef(true);
  const activeRequestIdRef = useRef(0);

  const loadPrice = useCallback(async (force = false, sym = symRef.current) => {
    try {
      const data = await getPrice(force, sym);
      if (!mounted.current || sym !== symRef.current) return;
      setPrice(data);
      if (data?.timestamp) {
        setLastUpdated(data.timestamp);
      } else {
        setLastUpdated("");
      }
      setErrors((e) => ({ ...e, price: null }));
    } catch (err) {
      if (!mounted.current || sym !== symRef.current) return;
      setErrors((e) => ({ ...e, price: errMsg(err) }));
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const [status, h] = await Promise.all([
        getMarketStatus().catch(() => null),
        getHealth().catch(() => null),
      ]);
      if (!mounted.current) return;
      if (status) setMarketStatus(status);
      if (h) setHealth(h);
      setErrors((e) => ({ ...e, status: null }));
    } catch (err) {
      if (!mounted.current) return;
      setErrors((e) => ({ ...e, status: errMsg(err) }));
    }
  }, []);

  const loadCandlesAndTech = useCallback(async (tf: string, force = false, sym = symRef.current) => {
    const [cRes, tRes] = await Promise.allSettled([
      getCandles(tf, 120, force, sym),
      getTechnicalAnalysis(tf, { forceRefresh: force, includeSeries: true, symbol: sym }),
    ]);
    if (!mounted.current || sym !== symRef.current) return;

    if (cRes.status === "fulfilled") {
      setCandles(cRes.value.candles || []);
      setCandleMeta(cRes.value);
      setErrors((e) => ({ ...e, candles: null }));
    } else {
      setErrors((e) => ({ ...e, candles: errMsg(cRes.reason) }));
    }

    if (tRes.status === "fulfilled") {
      setTechnical(tRes.value);
      setErrors((e) => ({ ...e, technical: null }));
    } else {
      setErrors((e) => ({ ...e, technical: errMsg(tRes.reason) }));
    }
  }, []);

  const loadMtf = useCallback(async (force = false, sym = symRef.current) => {
    try {
      const data = await getRawTechnicalInput(force, sym);
      if (!mounted.current || sym !== symRef.current) return;
      setMtf(data);
      setErrors((e) => ({ ...e, mtf: null }));
    } catch (err) {
      if (!mounted.current || sym !== symRef.current) return;
      setErrors((e) => ({ ...e, mtf: errMsg(err) }));
    }
  }, []);

  const loadAiAndDecision = useCallback(async (force = false, sym = symRef.current) => {
    const [aiRes, dRes] = await Promise.allSettled([
      getAIAnalysis(force, sym),
      getDecision(force, sym),
    ]);
    if (!mounted.current || sym !== symRef.current) return;

    if (aiRes.status === "fulfilled") {
      setAi(aiRes.value);
      if (aiRes.value?.analysis_timestamp) {
        setLastAiUpdated(aiRes.value.analysis_timestamp);
      } else {
        setLastAiUpdated("");
      }
      setErrors((e) => ({ ...e, ai: null }));
    } else {
      setErrors((e) => ({ ...e, ai: errMsg(aiRes.reason) }));
    }

    if (dRes.status === "fulfilled") {
      setDecision(dRes.value);
      setErrors((e) => ({ ...e, decision: null }));
    } else {
      setErrors((e) => ({ ...e, decision: errMsg(dRes.reason) }));
    }
  }, []);

  const loadAll = useCallback(
    async (force = false, sym = symRef.current) => {
      const requestId = ++activeRequestIdRef.current;
      setRefreshing(true);
      try {
        const pStatus = loadStatus();
        const pPrice = loadPrice(force, sym);
        const pCandles = loadCandlesAndTech(tfRef.current, force, sym);
        const pMtf = loadMtf(force, sym);
        const pAi = loadAiAndDecision(force, sym);

        // Release initial loading as soon as core price & candle data arrives
        Promise.all([pPrice, pCandles]).then(() => {
          if (mounted.current && requestId === activeRequestIdRef.current && sym === symRef.current) {
            setInitialLoading(false);
            setAssetSwitching(false);
          }
        });

        await Promise.allSettled([pStatus, pPrice, pCandles, pMtf, pAi]);
      } finally {
        if (mounted.current && requestId === activeRequestIdRef.current && sym === symRef.current) {
          setLoadedSymbol(sym);
          setInitialLoading(false);
          setRefreshing(false);
          setAssetSwitching(false);
        }
      }
    },
    [loadStatus, loadPrice, loadCandlesAndTech, loadMtf, loadAiAndDecision]
  );

  useEffect(() => {
    mounted.current = true;

    // If symbol changed, immediately clear stale state and flag asset switching
    if (prevSymbolRef.current !== symbol) {
      prevSymbolRef.current = symbol;
      setAssetSwitching(true);
      setPrice(null);
      setCandles([]);
      setCandleMeta(null);
      setTechnical(null);
      setMtf(null);
      setAi(null);
      setDecision(null);
      setLastUpdated("");
      setLastAiUpdated("");
    }

    loadAll(false, symbol);

    const priceTimer = setInterval(() => {
      loadPrice(false, symRef.current);
    }, PRICE_MS);

    const techTimer = setInterval(() => {
      loadCandlesAndTech(tfRef.current, false, symRef.current);
      loadMtf(false, symRef.current);
      loadStatus();
    }, TECH_MS);

    const decisionTimer = setInterval(() => {
      loadAiAndDecision(false, symRef.current);
    }, DECISION_MS);

    return () => {
      mounted.current = false;
      clearInterval(priceTimer);
      clearInterval(techTimer);
      clearInterval(decisionTimer);
    };
  }, [loadAll, loadPrice, loadCandlesAndTech, loadMtf, loadStatus, loadAiAndDecision, symbol]);

  useEffect(() => {
    // Only fetch if timeframe has actually changed to prevent duplicate requests on mount / asset switch
    if (prevTfRef.current === timeframe) {
      return;
    }
    prevTfRef.current = timeframe;
    setTfSwitching(true);
    loadCandlesAndTech(timeframe, false, symbol).finally(() => {
      if (mounted.current) {
        setInitialLoading(false);
        setTfSwitching(false);
      }
    });
  }, [timeframe, symbol, loadCandlesAndTech]);

  const isAssetSwitching = assetSwitching || symbol !== loadedSymbol;

  return {
    price,
    candles,
    candleMeta,
    marketStatus,
    technical,
    mtf,
    ai,
    decision,
    health,
    errors,
    initialLoading,
    refreshing,
    tfSwitching,
    assetSwitching: isAssetSwitching,
    loadedSymbol,
    lastUpdated,
    lastAiUpdated,
    refresh: () => loadAll(true, symbol),
  };
}

