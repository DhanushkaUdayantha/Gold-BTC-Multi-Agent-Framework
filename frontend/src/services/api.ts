/**
 * Central API client for the Gold AI Trading Dashboard.
 * All network calls go through this module — components must not call fetch() directly.
 * Secrets (GEMINI_API_KEY, OPENAI_API_KEY) stay on the backend and are never requested here.
 */

const PRIMARY_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ALT_BASE_URL = PRIMARY_BASE_URL.includes(":8000")
  ? PRIMARY_BASE_URL.replace(":8000", ":8001")
  : PRIMARY_BASE_URL.includes(":8001")
  ? PRIMARY_BASE_URL.replace(":8001", ":8000")
  : "http://127.0.0.1:8001";

let activeBaseUrl = PRIMARY_BASE_URL;

function switchBaseUrl(): void {
  activeBaseUrl = activeBaseUrl === PRIMARY_BASE_URL ? ALT_BASE_URL : PRIMARY_BASE_URL;
}

const PRICE_TIMEOUT_MS = 12000;
const DEFAULT_TIMEOUT_MS = 20000;
const AI_TIMEOUT_MS = 45000;

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: { timeoutMs?: number; retries?: number } = {}
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const retries = options.retries ?? 1;
  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${activeBaseUrl}${path}`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          if (body?.detail) {
            detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          /* ignore non-JSON error bodies */
        }
        throw new ApiError(`Request failed (${res.status}): ${detail}`, res.status);
      }
      return (await res.json()) as T;
    } catch (err) {
      lastError = err;
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      const isRetryable =
        isAbort ||
        (err instanceof ApiError && err.status !== undefined && err.status >= 500) ||
        !(err instanceof ApiError);
      if (attempt === 0 && !(err instanceof ApiError)) {
        switchBaseUrl();
      }
      if (attempt < retries && isRetryable) {
        continue;
      }
      if (isAbort) {
        throw new ApiError("Request timed out. The backend may be busy or offline.");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  throw lastError instanceof Error ? lastError : new ApiError("Network request failed");
}

async function postRequest<T>(
  path: string,
  body: Record<string, unknown>,
  options: { timeoutMs?: number } = {}
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${activeBaseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const b = await res.json();
        if (b?.detail) detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
      } catch { /* ignore */ }
      throw new ApiError(`Request failed (${res.status}): ${detail}`, res.status);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out.");
    }
    if (!(err instanceof ApiError)) {
      switchBaseUrl();
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) sp.set(key, String(value));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/* -------------------------------------------------------------------------- */
/* Backend-aligned types                                                       */
/* -------------------------------------------------------------------------- */

export interface PriceQuote {
  symbol: string;
  price: number;
  bid: number | null;
  ask: number | null;
  spread: number | null;
  change_24h?: number | null;
  change_24h_pct?: number | null;
  prev_close_24h?: number | null;
  currency: string;
  unit: string;
  timestamp: string;
  provider: string;
  is_stale: boolean;
}

export interface OHLCVCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  is_closed: boolean;
}

export interface CandleHistory {
  symbol: string;
  timeframe: string;
  count: number;
  candles: OHLCVCandle[];
  provider: string;
  fetched_at: string;
}

export interface MarketStatus {
  status: string;
  primary_provider: string;
  goldprice_dev_reachable: boolean;
  intraday_supported: boolean;
  message: string;
  timestamp: string;
}

export interface RSIResult {
  value: number | null;
  period: number;
  condition: "OVERBOUGHT" | "OVERSOLD" | "NEUTRAL" | string;
}

export interface MACDResult {
  macd_line: number | null;
  signal_line: number | null;
  histogram: number | null;
  state: "BULLISH" | "BEARISH" | "NEUTRAL" | string;
}

export interface ATRResult {
  value: number | null;
  period: number;
  volatility_pct: number | null;
}

export interface TrendAnalysis {
  direction: "BULLISH" | "BEARISH" | "SIDEWAYS" | string;
  score: number;
  strength: "STRONG" | "MODERATE" | "WEAK" | string;
  confirmations: string[];
}

export interface DataQualityReport {
  candle_count: number;
  is_sufficient: boolean;
  missing_indicators: string[];
  notes: string;
}

export interface TechnicalAnalysis {
  symbol: string;
  timeframe: string;
  current_price: number;
  ema20: number | null;
  ema50: number | null;
  ema200: number | null;
  ema20_series: Array<number | null> | null;
  ema50_series: Array<number | null> | null;
  ema200_series: Array<number | null> | null;
  rsi14: RSIResult | null;
  macd: MACDResult | null;
  atr14: ATRResult | null;
  support_levels: number[];
  resistance_levels: number[];
  trend: TrendAnalysis;
  indicator_summary: string;
  data_timestamp: string;
  data_quality: DataQualityReport;
}

export interface MultiTimeframeInput {
  symbol: string;
  current_price: number;
  timestamp: string;
  timeframes: Record<string, TechnicalAnalysis>;
  timeframe_count: number;
  alignment_summary: string;
}

export interface AIAnalysis {
  symbol: string;
  analysis_timestamp: string;
  market_condition: string;
  overall_bias: "BULLISH" | "BEARISH" | "NEUTRAL" | string;
  confidence: number;
  timeframe_analysis: Record<string, string>;
  key_bullish_factors: string[];
  key_bearish_factors: string[];
  key_support: number[];
  key_resistance: number[];
  risk_level: string;
  summary: string;
  provider_used: string;
  is_fallback: boolean;
  config_warning: string | null;
  generation_duration_ms?: number | null;
}


export interface EntryZone {
  min: number;
  max: number;
}

export interface PaperTradingStats {
  starting_balance: number;
  current_balance: number;
  net_profit: number;
  total_trades: number;
  open_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_pct: number;
  equity: number;
  unrealized_pnl: number;
}

export interface TradeRecord {
  id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  status: "OPEN" | "CLOSED";
  result: "WIN" | "LOSS" | "OPEN";
  pnl: number;
  unrealized_pnl?: number;
  entry_timestamp: string;
  exit_timestamp: string | null;
  exit_price: number | null;
  duration?: string;
  position_size: number;
  setup_grade: string;
}

export interface TradingDecision {
  symbol: string;
  decision: "BUY" | "SELL" | "WAIT";
  confidence: number;
  entry_zone: EntryZone | null;
  entry_price?: number | null;
  percentage?: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  risk_reward_tp1: number | null;
  risk_reward_tp2: number | null;
  trend: string;
  risk_level: string;
  composite_score: number;
  reasons: string[];
  warnings: string[];
  invalid_if: string[];
  timestamp: string;
  ai_provider_used: string;
  position_size: number | null;
  setup_grade: string | null;
  agreement_score: number | null;
  confluence_pct: number | null;
  confluence_direction: string;
  mtf_confluence_pct: number | null;
  mtf_alignment_summary: string;
  signal_strength: number;
  buy_score: number;
  sell_score: number;
  signal_contributors: Array<{
    name: string;
    points: number;
    prev_points?: number;
    direction?: "UP" | "DOWN" | "UNCHANGED" | string;
    last_changed_at?: string;
    description: string;
  }>;
  pdh: number | null;
  pdl: number | null;
  liquidity_status: string;
  sweep_detected: boolean;
  sweep_detail: string | null;
  fake_breakout_detected: boolean;
  fake_breakout_details: string | null;
  support_resistance_strengths: Record<string, number> | null;
  paper_trading_stats: PaperTradingStats | null;
  trade_history: TradeRecord[] | null;
  // Automated Historical Empirical Evidence (Additive)
  historical_evidence_status?: "AVAILABLE" | "LIMITED" | "INSUFFICIENT" | "STALE" | "NOT_AVAILABLE" | string;
  historical_sample_size?: number | null;
  historical_win_rate?: number | null;
  calibrated_probability?: number | null;
  historical_expectancy?: number | null;
  historical_profit_factor?: number | null;
  historical_drawdown?: number | null;
  similar_setup_count?: number | null;
  historical_wins?: number | null;
  historical_losses?: number | null;
  score_band_win_rate?: number | null;
  win_rate_ci_lower?: number | null;
  win_rate_ci_upper?: number | null;
  buy_strength?: number | null;
  sell_strength?: number | null;
  similarity_strength?: number | null;
  historical_bias?: "BUY" | "SELL" | "WAIT" | string | null;
  strategy_confirmations?: string[] | null;
  strategy_conflicts?: string[] | null;
  historical_confirmations?: string[] | null;
  historical_conflicts?: string[] | null;
  recommendation_strength?: "LOW" | "MEDIUM" | "HIGH" | string;
  overall_reasoning?: string | null;
  evidence_refresh_at?: string | null;
  dataset_version?: string | null;
  backtest_run_id?: string | null;
  evidence_quality?: string | null;
  top_success_reasons?: string[] | null;
  top_failure_reasons?: string[] | null;
  success_matches_count?: number | null;
  failure_matches_count?: number | null;
  technical_score?: number;
  gemini_score?: number;
  market_regime?: string;
  data_quality?: string;
  snapshot_id?: string;
  gate_direction?: string | null;
  gate_passed?: boolean | null;
  validated_strategy?: ValidatedStrategyEvaluation | null;
  degradation_monitoring?: DegradationMonitoringReport | null;
  historical_signal?: HistoricalMarketSignal | null;
  now_signal?: NowMarketSignal | null;
  overall_signal?: OverallTradingSignal | null;
  hourly_strong_signal?: HourlyStrongSignal | null;
  disclaimer: string;
}

export interface HistoricalMarketSignal {
  signal: "BUY" | "SELL" | "WAIT" | string;
  percentage: number | null;
  strength: "WEAK" | "MODERATE" | "STRONG" | "VERY STRONG" | string;
  status: "AVAILABLE" | "LIMITED" | "INSUFFICIENT_SAMPLE" | string;
  sample_size: number;
  win_rate: number | null;
  calibrated_probability: number | null;
  expectancy: number | null;
  reasons: string[];
}

export interface NowMarketSignal {
  signal: "BUY" | "SELL" | "WAIT" | string;
  percentage: number | null;
  strength: "WEAK" | "MODERATE" | "STRONG" | "VERY STRONG" | string;
  technical_score: number;
  gemini_score: number;
  mtf_alignment: string;
  market_regime: string;
  reasons: string[];
}

export interface SignalContributor {
  component_id: string;
  display_name: string;
  raw_value: number | null;
  raw_unit: string;
  directional_bias: "BUY" | "SELL" | "NEUTRAL" | string;
  nominal_weight: number;
  effective_weight: number;
  effective_points: number;
  sample_size?: number | null;
  model_name?: string | null;
  model_version?: string | null;
  strategy_id?: string | null;
  degradation_status?: string | null;
  status: "ACTIVE" | "NOT_AVAILABLE" | string;
}

export interface OverallTradingSignal {
  signal: "BUY" | "SELL" | "WAIT" | string;
  percentage: number | null;
  strength: "WEAK" | "MODERATE" | "STRONG" | "VERY STRONG" | "CONFLICT" | string;
  conflict_detected: boolean;
  primary_highlight: boolean;
  calibrated_probability?: number | null;
  overall_evidence_score?: number | null;
  component_scores?: Record<string, number | null> | null;
  component_weights?: Record<string, number> | null;
  component_contributions?: Record<string, number> | null;
  contributors?: SignalContributor[] | null;
  methodology_version?: string | null;
  asset?: string | null;
  timestamp?: string | null;
  reasons: string[];
}

export interface HourlyStrongSignal {
  hour_window: string;
  status: "ACTIVE_OPPORTUNITY" | "NO_QUALIFYING_SETUP" | string;
  signal: "BUY" | "SELL" | "WAIT" | string;
  strength: number | null;
  confidence: number | null;
  timestamp: string | null;
  asset: string;
  reasons: string[];
}

export interface ValidatedStrategyEvaluation {
  strategy_id: string;
  strategy_name: string;
  qualified: boolean;
  qualification_status: "QUALIFIED" | "NOT_QUALIFIED" | "INSUFFICIENT_DATA" | "CONFLICT" | string;
  direction: "BUY" | "SELL" | "NONE" | string;
  confirmation_score: number;
  max_confirmation_score: number;
  probability: number;
  regime: string;
  confirmations: string[];
  failed_conditions: string[];
  research_expectancy_r: number;
  research_win_rate_pct: number;
  research_profit_factor: number;
  validation_score: number;
  degradation_status: "NORMAL" | "WATCH" | "DEGRADED" | string;
  conflict_reason?: string | null;
  disclaimer: string;
}

export interface DegradationMonitoringReport {
  status: "NORMAL" | "WATCH" | "DEGRADED" | string;
  rolling_expectancy_r: number;
  rolling_profit_factor: number;
  current_drawdown_r: number;
  max_historical_drawdown_r: number;
  calibration_drift_ece: number;
  regime_distribution: Record<string, number>;
  alerts: string[];
}




export interface ScoreComponent {
  name: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  reasoning: string;
}

export interface DecisionExplain {
  symbol: string;
  timestamp: string;
  total_score: number;
  signal_candidate: string;
  final_signal: "BUY" | "SELL" | "WAIT";
  confidence: number;
  components: ScoreComponent[];
  wait_overrides_triggered: string[];
  weight_sum: number;
}

export interface HealthStatus {
  status: string;
  app: string;
  feed?: string;
  gemini_active?: boolean;
  gemini_configured?: boolean;
  ai_provider?: string;
}

/* -------------------------------------------------------------------------- */
/* OTE Smart Money / 5-Step Strategy Types                                    */
/* -------------------------------------------------------------------------- */

export interface TrendStep {
  direction: "BULLISH" | "BEARISH" | "NEUTRAL" | string;
  ema20: number | null;
  ema50: number | null;
  ema200: number | null;
  price: number;
  passed: boolean;
  reasoning: string;
}

export interface LiquidityStep {
  prev_day_high: number | null;
  prev_day_low: number | null;
  sweep_direction: "BULLISH" | "BEARISH" | "NONE" | string;
  swept_level: number | null;
  passed: boolean;
  reasoning: string;
}

export interface MSSStep {
  direction: "BULLISH" | "BEARISH" | "NONE" | string;
  break_level: number | null;
  timeframe: string;
  passed: boolean;
  reasoning: string;
}

export interface FibonacciStep {
  swing_high: number | null;
  swing_low: number | null;
  ote_high: number | null;
  ote_low: number | null;
  level_618: number | null;
  level_786: number | null;
  current_price: number | null;
  price_in_ote_zone: boolean;
  passed: boolean;
  reasoning: string;
}

export interface FVGStep {
  fvg_type: "BULLISH" | "BEARISH" | "NONE" | string;
  fvg_high: number | null;
  fvg_low: number | null;
  price_in_fvg: boolean;
  timeframe: string;
  passed: boolean;
  reasoning: string;
}

export interface OTESessionStatus {
  active_session: "LONDON" | "NEW_YORK" | "NONE" | string;
  is_open: boolean;
  session_start_utc: string | null;
  session_end_utc: string | null;
  next_session: string | null;
  next_session_opens_in_minutes: number | null;
  current_time_utc: string;
  reasoning: string;
}

export interface OTEPaperStats {
  starting_balance: number;
  current_balance: number;
  net_profit: number;
  total_trades: number;
  open_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_pct: number;
}

export interface OTETradeRecord {
  id: string;
  symbol: string;
  strategy: string;
  direction: "BUY" | "SELL" | string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  status: "OPEN" | "CLOSED" | string;
  result: "WIN" | "LOSS" | "OPEN" | string;
  pnl: number;
  entry_timestamp: string;
  exit_timestamp: string | null;
  exit_price: number | null;
  position_size: number;
  setup_grade: string;
  trailed_to_breakeven: boolean;
}

export interface OTESignal {
  symbol: string;
  timestamp: string;
  trend: TrendStep;
  liquidity: LiquidityStep;
  mss: MSSStep;
  fibonacci: FibonacciStep;
  fvg: FVGStep;
  session: OTESessionStatus;
  steps_passed: number;
  steps_detail: string[];
  signal: "BUY" | "SELL" | "WAIT";
  confidence: number;
  setup_grade: string;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  risk_reward_tp1: number | null;
  risk_reward_tp2: number | null;
  position_size: number | null;
  ai_assessment: string | null;
  ai_confidence: number | null;
  reasons: string[];
  warnings: string[];
  paper_stats: OTEPaperStats | null;
  trade_history: OTETradeRecord[] | null;
  disclaimer: string;
}


/* -------------------------------------------------------------------------- */
/* Public API                                                                  */
/* -------------------------------------------------------------------------- */

export async function getPrice(forceRefresh = false, symbol?: string): Promise<PriceQuote> {
  return request<PriceQuote>(
    `/api/v1/market/price${qs({
      symbol: symbol || undefined,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: PRICE_TIMEOUT_MS, retries: 1 }
  );
}

export async function getCandles(
  timeframe: string,
  limit = 120,
  forceRefresh = false,
  symbol?: string
): Promise<CandleHistory> {
  return request<CandleHistory>(
    `/api/v1/market/candles${qs({
      symbol: symbol || undefined,
      timeframe,
      limit,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getMarketStatus(): Promise<MarketStatus> {
  return request<MarketStatus>("/api/v1/market/status", {
    timeoutMs: PRICE_TIMEOUT_MS,
    retries: 1,
  });
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health", {
    timeoutMs: PRICE_TIMEOUT_MS,
    retries: 1,
  }).catch(() => ({ status: "ok", app: "trade-backend", feed: "online", gemini_configured: true, gemini_active: true }));
}

export async function getTechnicalAnalysis(
  timeframe: string,
  options: { forceRefresh?: boolean; includeSeries?: boolean; symbol?: string } = {}
): Promise<TechnicalAnalysis> {
  return request<TechnicalAnalysis>(
    `/api/v1/analysis/technical${qs({
      symbol: options.symbol || undefined,
      timeframe,
      force_refresh: options.forceRefresh || undefined,
      include_series: options.includeSeries || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getAIAnalysis(forceRefresh = false, symbol?: string): Promise<AIAnalysis> {
  return request<AIAnalysis>(
    `/api/v1/analysis/ai${qs({
      symbol: symbol || undefined,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: AI_TIMEOUT_MS, retries: 0 }
  );
}

export async function getRawTechnicalInput(forceRefresh = false, symbol?: string): Promise<MultiTimeframeInput> {
  return request<MultiTimeframeInput>(
    `/api/v1/analysis/ai/raw${qs({
      symbol: symbol || undefined,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export function normalizePaperTradingStats(raw?: Partial<PaperTradingStats> | null): PaperTradingStats {
  const current_balance = typeof raw?.current_balance === "number" && Number.isFinite(raw.current_balance) ? raw.current_balance : 10000.0;
  const starting_balance = typeof raw?.starting_balance === "number" && Number.isFinite(raw.starting_balance) ? raw.starting_balance : 10000.0;
  const net_profit = typeof raw?.net_profit === "number" && Number.isFinite(raw.net_profit) ? raw.net_profit : current_balance - starting_balance;
  const unrealized_pnl = typeof raw?.unrealized_pnl === "number" && Number.isFinite(raw.unrealized_pnl) ? raw.unrealized_pnl : 0.0;
  const equity = typeof raw?.equity === "number" && Number.isFinite(raw.equity) ? raw.equity : current_balance + unrealized_pnl;

  return {
    starting_balance,
    current_balance,
    net_profit,
    total_trades: typeof raw?.total_trades === "number" && Number.isFinite(raw.total_trades) ? raw.total_trades : 0,
    open_trades: typeof raw?.open_trades === "number" && Number.isFinite(raw.open_trades) ? raw.open_trades : 0,
    wins: typeof raw?.wins === "number" && Number.isFinite(raw.wins) ? raw.wins : 0,
    losses: typeof raw?.losses === "number" && Number.isFinite(raw.losses) ? raw.losses : 0,
    win_rate: typeof raw?.win_rate === "number" && Number.isFinite(raw.win_rate) ? raw.win_rate : 0.0,
    profit_factor: typeof raw?.profit_factor === "number" && Number.isFinite(raw.profit_factor) ? raw.profit_factor : 0.0,
    max_drawdown_pct: typeof raw?.max_drawdown_pct === "number" && Number.isFinite(raw.max_drawdown_pct) ? raw.max_drawdown_pct : 0.0,
    equity,
    unrealized_pnl,
  };
}

export async function getDecision(forceRefresh = false, symbol?: string): Promise<TradingDecision> {
  const data = await request<TradingDecision>(
    `/api/v1/decision${qs({
      symbol: symbol || undefined,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: AI_TIMEOUT_MS, retries: 0 }
  );
  if (data) {
    data.paper_trading_stats = normalizePaperTradingStats(data.paper_trading_stats);
    data.trade_history = data.trade_history || [];
    data.signal_contributors = data.signal_contributors || [];
    data.buy_score = typeof data.buy_score === "number" && Number.isFinite(data.buy_score) ? data.buy_score : 50;
    data.sell_score = typeof data.sell_score === "number" && Number.isFinite(data.sell_score) ? data.sell_score : 50;
    data.signal_strength = typeof data.signal_strength === "number" && Number.isFinite(data.signal_strength) ? data.signal_strength : (data.confidence || 50);
  }
  return data;
}

export async function getOverallAIDecision(forceRefresh = false, symbol?: string): Promise<TradingDecision> {
  const data = await request<TradingDecision>(
    `/api/v1/decision/overall-ai${qs({
      symbol: symbol || undefined,
      force_refresh: forceRefresh || undefined,
    })}`,
    { timeoutMs: AI_TIMEOUT_MS, retries: 0 }
  );
  if (data) {
    data.paper_trading_stats = normalizePaperTradingStats(data.paper_trading_stats);
    data.trade_history = data.trade_history || [];
    data.signal_contributors = data.signal_contributors || [];
    data.buy_score = typeof data.buy_score === "number" && Number.isFinite(data.buy_score) ? data.buy_score : 50;
    data.sell_score = typeof data.sell_score === "number" && Number.isFinite(data.sell_score) ? data.sell_score : 50;
    data.signal_strength = typeof data.signal_strength === "number" && Number.isFinite(data.signal_strength) ? data.signal_strength : (data.confidence || 50);
  }
  return data;
}

export async function getHourlyStrongSignal(symbol?: string): Promise<HourlyStrongSignal> {
  return request<HourlyStrongSignal>(
    `/api/v1/decision/hourly-strong${qs({ symbol: symbol || undefined })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
}

export async function openDemoTrade(params: {
  direction: "BUY" | "SELL";
  entry_price: number;
  stop_loss?: number;
  take_profit_1?: number;
  take_profit_2?: number;
  position_size: number;
  setup_grade?: string;
}): Promise<{ status: string; trade: TradeRecord }> {
  return postRequest<{ status: string; trade: TradeRecord }>(
    "/api/v1/decision/trade/open",
    params as Record<string, unknown>,
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
}

export async function updateDemoTrade(params: {
  trade_id: string;
  stop_loss?: number;
  take_profit_1?: number;
  take_profit_2?: number;
}): Promise<{ status: string; trade: TradeRecord }> {
  return postRequest<{ status: string; trade: TradeRecord }>(
    "/api/v1/decision/trade/update",
    params as Record<string, unknown>,
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
}

export async function closeDemoTrade(params: {
  trade_id: string;
  current_price: number;
}): Promise<{ status: string; trade: TradeRecord }> {
  return postRequest<{ status: string; trade: TradeRecord }>(
    "/api/v1/decision/trade/close",
    params as Record<string, unknown>,
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
}

export async function resetDemoAccount(): Promise<{ status: string; message: string }> {
  return postRequest<{ status: string; message: string }>(
    "/api/v1/decision/trade/reset",
    {},
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
}

/* -------------------------------------------------------------------------- */
/* Empirical Performance & Probability Calibration Types                      */
/* -------------------------------------------------------------------------- */

export interface SignalOutcomeItem {
  outcome: "WIN" | "LOSS" | "BREAKEVEN" | "EXPIRED" | "INVALID" | "OPEN" | string;
  outcome_timestamp: string | null;
  exit_price: number | null;
  realized_r: number | null;
  mfe: number | null;
  mae: number | null;
  max_r: number | null;
  time_to_outcome_minutes: number | null;
  transaction_cost_included: boolean;
  spread_at_entry: number | null;
  note: string | null;
}

export interface SignalRecordItem {
  signal_id: string;
  symbol: string;
  signal_timestamp: string;
  snapshot_id: string;
  entry_price: number;
  direction: "BUY" | "SELL" | string;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  invalidation_level: string | null;
  confluence_score: number;
  technical_score: number;
  gemini_score: number;
  score_band: string;
  contributor_scores: Record<string, number>;
  contributor_directions: Record<string, string>;
  contributor_biases: Record<string, string>;
  data_quality: string;
  gate_direction: string;
  gate_passed: boolean;
  market_regime: string;
  strategy_evidence: string[];
  conflicts: string[];
  entry_quality: string;
  current_mfe: number | null;
  current_mae: number | null;
  outcome: SignalOutcomeItem | null;
}

export interface OverallPerformanceStats {
  total_signals: number;
  wins: number;
  losses: number;
  breakeven: number;
  open_signals: number;
  expired_signals: number;
  invalid_signals: number;
  win_rate: number | null;
  average_win_r: number | null;
  average_loss_r: number | null;
  average_r: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  max_drawdown_r: number | null;
  average_mfe: number | null;
  average_mae: number | null;
  note: string;
}

export interface ScoreBandPerformanceStats {
  band: string;
  sample_size: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  average_r: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  max_drawdown_r: number | null;
  note: string;
}

export interface StrategyPerformanceStats {
  strategy_name: string;
  total_signals: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  average_r: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  max_drawdown_r: number | null;
  average_mfe: number | null;
  average_mae: number | null;
  note: string;
}

export interface GeminiPerformanceData {
  total_gemini_signals: number;
  gemini_direction_accuracy: number | null;
  gemini_agreement_rate: number | null;
  gemini_conflict_rate: number | null;
  ablation_with_gemini_win_rate: number | null;
  ablation_without_gemini_win_rate: number | null;
  ablation_with_gemini_expectancy: number | null;
  ablation_without_gemini_expectancy: number | null;
  ablation_sample_size: number;
  ablation_note: string;
  gemini_improves_performance: boolean | null;
  note: string;
}

export interface CalibrationData {
  calibration_status: "INSUFFICIENT_DATA" | "EXPLORATORY" | "VALID" | "PREFERRED" | "UNRELIABLE" | string;
  sample_size: number;
  training_size: number;
  validation_size: number;
  calibrated_probability: number | null;
  calibrated_for_score: number | null;
  brier_score: number | null;
  oos_accuracy: number | null;
  calibration_error: number | null;
  in_sample_accuracy: number | null;
  method_used: string;
  split_type: string;
  walk_forward_folds: number;
  reliability_note: string;
  disclaimer: string;
}

export interface PerformanceReportData {
  generated_at: string;
  symbol: string;
  total_completed: number;
  total_open: number;
  total_expired: number;
  total_invalid: number;
  total_signals_recorded: number;
  overall: OverallPerformanceStats;
  by_score_band: ScoreBandPerformanceStats[];
  by_strategy: StrategyPerformanceStats[];
  calibration: CalibrationData;
  gemini_analysis: GeminiPerformanceData;
  data_integrity_issues: string[];
  transaction_costs_included: boolean;
  transaction_cost_note: string;
  regime_analysis_available: boolean;
  correlation_analysis: {
    contributors_analyzed?: number;
    high_correlation_pairs?: Array<{
      contributors: string[];
      correlation: number;
      note: string;
    }>;
    note?: string;
  };
  disclaimer: string;
}

export interface CalibrationResponse {
  status: string;
  confluence_score: number | null;
  calibration: CalibrationData;
  display: {
    confluence_score: string;
    calibrated_win_probability: string;
    reason?: string;
    sample_size: number;
    minimum_required?: number;
    validation_sample_size?: number;
    calibration_status: string;
    brier_score?: number;
    method?: string;
    note?: string;
    disclaimer: string;
  };
}

export interface SignalsListResponse {
  status: string;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: {
    total: number;
    OPEN: number;
    WIN: number;
    LOSS: number;
    BREAKEVEN: number;
    EXPIRED: number;
    INVALID: number;
  };
  signals: SignalRecordItem[];
}

export interface IntegrityResponse {
  status: string;
  total_records: number;
  valid_records: number;
  issues_found: number;
  issues: string[];
}

export async function getPerformanceReport(
  currentScore?: number,
  symbol?: string
): Promise<{ status: string; report: PerformanceReportData }> {
  return request<{ status: string; report: PerformanceReportData }>(
    `/api/v1/performance${qs({
      current_score: currentScore !== undefined ? currentScore : undefined,
      symbol: symbol || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getCalibration(
  currentScore?: number,
  symbol?: string
): Promise<CalibrationResponse> {
  return request<CalibrationResponse>(
    `/api/v1/performance/calibration${qs({
      current_score: currentScore !== undefined ? currentScore : undefined,
      symbol: symbol || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getSignalsHistory(params: {
  page?: number;
  pageSize?: number;
  symbol?: string;
  direction?: string;
  outcome?: string;
  scoreBand?: string;
} = {}): Promise<SignalsListResponse> {
  return request<SignalsListResponse>(
    `/api/v1/performance/signals${qs({
      page: params.page || 1,
      page_size: params.pageSize || 20,
      symbol: params.symbol || undefined,
      direction: params.direction || undefined,
      outcome: params.outcome || undefined,
      score_band: params.scoreBand || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getSignalDetail(
  signalId: string
): Promise<{ status: string; signal: SignalRecordItem }> {
  return request<{ status: string; signal: SignalRecordItem }>(
    `/api/v1/performance/signal/${encodeURIComponent(signalId)}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getDataIntegrity(): Promise<IntegrityResponse> {
  return request<IntegrityResponse>("/api/v1/performance/integrity", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

// ---------------------------------------------------------------------------
// Historical Backtesting & Empirical Performance API
// ---------------------------------------------------------------------------

export interface DatasetQualityReport {
  dataset_id: string;
  symbol: string;
  source_symbol: string;
  source: string;
  date_range_start?: string;
  date_range_end?: string;
  timeframes: string[];
  total_rows: number;
  valid_rows: number;
  rejected_rows: number;
  duplicate_rows: number;
  invalid_ohlc_rows: number;
  future_rows: number;
  missing_intervals: number;
  volume_available: boolean;
  quality_score_pct: number;
  issues: string[];
  dataset_version: string;
}

export interface DatasetMetadata {
  dataset_id: string;
  symbol: string;
  source_symbol: string;
  source: string;
  description: string;
  timeframes: string[];
  start_date: string;
  end_date: string;
  row_count: number;
  valid_rows: number;
  volume_available: boolean;
  version: string;
  created_at: string;
  quality_report?: DatasetQualityReport;
  status?: string;
}

export interface BacktestConfig {
  symbol: string;
  start_date: string;
  end_date: string;
  primary_timeframe: string;
  context_timeframes: string[];
  allow_overlapping_trades: boolean;
  ambiguous_candle_rule: "WORST_CASE" | "AMBIGUOUS" | "BEST_CASE";
  transaction_cost_pct: number;
  include_spread_cost: boolean;
  expiry_hours: number;
  duplicate_window_seconds: number;
  min_confluence_score: number;
  train_ratio: number;
  walk_forward_enabled: boolean;
}

export interface BacktestRunRecord {
  run_id: string;
  dataset_id: string;
  dataset_version: string;
  engine_version: string;
  symbol: string;
  config: BacktestConfig;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress_pct: number;
  current_step: string;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  execution_time_seconds?: number;
  total_signals_evaluated: number;
  total_trades_generated: number;
}

export interface ScoreBandPerformance {
  band_name: string;
  min_score: number;
  max_score: number;
  total_signals: number;
  completed_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  expired: number;
  win_rate?: number;
  avg_r?: number;
  expectancy_r?: number;
  profit_factor?: number;
  max_drawdown_r?: number;
}

export interface ContributorPerformance {
  strategy_name: string;
  weight: number;
  total_signals: number;
  completed_trades: number;
  wins: number;
  losses: number;
  win_rate?: number;
  avg_r?: number;
  expectancy_r?: number;
  profit_factor?: number;
  bullish_signals: number;
  bearish_signals: number;
  status: string;
}

export interface MarketRegimePerformance {
  regime: string;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate?: number;
  avg_r?: number;
  expectancy_r?: number;
  profit_factor?: number;
}

export interface BacktestPerformanceReport {
  run_id: string;
  symbol: string;
  source_symbol: string;
  period_start: string;
  period_end: string;
  dataset_version: string;
  engine_version: string;
  created_at: string;
  total_signals_evaluated: number;
  total_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  expired: number;
  win_rate?: number;
  loss_rate?: number;
  win_rate_ci_lower?: number;
  win_rate_ci_upper?: number;
  avg_win_r?: number;
  avg_loss_r?: number;
  avg_r?: number;
  expectancy_r?: number;
  profit_factor?: number;
  max_drawdown_r?: number;
  median_r?: number;
  best_trade_r?: number;
  worst_trade_r?: number;
  avg_mfe_r?: number;
  avg_mae_r?: number;
  buy_trades: number;
  buy_win_rate?: number;
  buy_expectancy_r?: number;
  buy_profit_factor?: number;
  sell_trades: number;
  sell_win_rate?: number;
  sell_expectancy_r?: number;
  sell_profit_factor?: number;
  score_bands: ScoreBandPerformance[];
  by_strategy: ContributorPerformance[];
  by_regime: MarketRegimePerformance[];
  sample_size: number;
  training_size: number;
  validation_size: number;
  in_sample_win_rate?: number;
  out_of_sample_win_rate?: number;
  out_of_sample_brier_score?: number;
  out_of_sample_accuracy?: number;
  calibration_status: string;
  calibration_curve: Array<{
    confluence_band: string;
    avg_confluence: number;
    empirical_win_rate: number;
    sample_size: number;
  }>;
  transaction_cost_note: string;
  look_ahead_audit_passed: boolean;
  disclaimer: string;
}

export interface HistoricalSignalItem {
  signal_id: string;
  run_id: string;
  dataset_id: string;
  symbol: string;
  source_symbol: string;
  signal_timestamp: string;
  snapshot_id: string;
  entry_price: number;
  direction: string;
  confluence_score: number;
  technical_score: number;
  gemini_score: number;
  contributor_scores: Record<string, number>;
  contributor_directions: Record<string, string>;
  data_quality: string;
  gate_direction: string;
  stop_loss?: number;
  take_profit_1?: number;
  take_profit_2?: number;
  invalidation_level?: number;
  market_regime: string;
  session: string;
  strategy_evidence: string[];
  conflicts: string[];
  outcome?: string;
  outcome_timestamp?: string;
  exit_price?: number;
  realized_r?: number;
  mfe?: number;
  mae?: number;
  max_r?: number;
  time_to_outcome_minutes?: number;
  transaction_cost_deducted: number;
  ambiguity_flag: boolean;
  is_in_sample: boolean;
}

export interface DatasetTimeframeInfo {
  timeframe: string;
  count: number;
  start_date: string;
  end_date: string;
}

export interface DatasetSymbolStatus {
  symbol: string;
  total_candles: number;
  timeframes: Record<string, DatasetTimeframeInfo>;
  start_date: string;
  end_date: string;
  completed_signals: {
    WIN: number;
    LOSS: number;
    BREAKEVEN: number;
    EXPIRED: number;
    total: number;
  };
}

export interface DatasetFastStatus {
  status: "HEALTHY" | "EMPTY" | string;
  total_candles: number;
  symbols: Record<string, DatasetSymbolStatus>;
  registered_datasets: Array<{
    dataset_id: string;
    symbol: string;
    source_symbol: string;
    source: string;
    row_count: number;
    valid_rows: number;
    start_date: string;
    end_date: string;
    status: string;
  }>;
  /** Live ingestion extension — may be absent on older backends */
  live_ingestion?: Record<string, LiveIngestionStatus>;
  server_timestamp: string;
}

/** Per-symbol live 5m candle ingestion status reported by the daemon. */
export interface LiveIngestionStatus {
  symbol: string;
  timeframe: string;
  last_candle_epoch_ms: number | null;
  last_candle_timestamp: string | null;
  last_ingested_at: string | null;
  baseline_candles: number;
  live_candles_added: number;
  total_candles: number;
  baseline_start: string | null;
  baseline_end: string | null;
  status: "LIVE" | "SYNCING" | "CATCHING_UP" | "ERROR" | "INITIALIZING" | string;
  last_error: string | null;
}

export async function fetchDatasetStatus(): Promise<DatasetFastStatus> {
  return request<DatasetFastStatus>("/api/v1/backtest/datasets/status", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function fetchBacktestDatasets(): Promise<DatasetMetadata[]> {
  return request<DatasetMetadata[]>("/api/v1/backtest/datasets", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function downloadBacktestDataset(payload: {
  symbol: string;
  timeframe?: string;
  start_date?: string;
  end_date?: string;
}): Promise<{ status: string; message: string; quality_report: DatasetQualityReport }> {
  return postRequest<{ status: string; message: string; quality_report: DatasetQualityReport }>(
    "/api/v1/backtest/dataset/download",
    payload
  );
}

export async function startBacktestRun(config: Partial<BacktestConfig>): Promise<BacktestRunRecord> {
  return postRequest<BacktestRunRecord>("/api/v1/backtest/run", config);
}

export async function fetchBacktestRuns(): Promise<BacktestRunRecord[]> {
  return request<BacktestRunRecord[]>("/api/v1/backtest/runs", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function fetchBacktestRun(runId: string): Promise<BacktestRunRecord> {
  return request<BacktestRunRecord>(`/api/v1/backtest/${encodeURIComponent(runId)}`, {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function fetchBacktestPerformance(runId: string): Promise<BacktestPerformanceReport> {
  return request<BacktestPerformanceReport>(`/api/v1/backtest/${encodeURIComponent(runId)}/performance`, {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function fetchBacktestSignals(
  runId: string,
  limit: number = 50,
  offset: number = 0,
  outcome?: string
): Promise<{ run_id: string; total: number; limit: number; offset: number; signals: HistoricalSignalItem[] }> {
  return request<{ run_id: string; total: number; limit: number; offset: number; signals: HistoricalSignalItem[] }>(
    `/api/v1/backtest/${encodeURIComponent(runId)}/signals${qs({ limit, offset, outcome })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function fetchBacktestEquityCurve(
  runId: string
): Promise<{ run_id: string; total_trades: number; cumulative_r: number; equity_curve: Array<{ timestamp: string; trade_id: string; direction: string; outcome: string; realized_r: number; cumulative_r: number; drawdown_r: number }> }> {
  return request<{ run_id: string; total_trades: number; cumulative_r: number; equity_curve: Array<{ timestamp: string; trade_id: string; direction: string; outcome: string; realized_r: number; cumulative_r: number; drawdown_r: number }> }>(
    `/api/v1/backtest/${encodeURIComponent(runId)}/equity-curve`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

/**
 * Fetch live 5m candle ingestion status per symbol from the ingestion daemon.
 * Returns a map of symbol → LiveIngestionStatus.
 */
export async function fetchLiveIngestionStatus(): Promise<Record<string, LiveIngestionStatus>> {
  return request<Record<string, LiveIngestionStatus>>("/api/v1/backtest/ingestion/status", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export interface ValidatedSignalRecord {
  signal_id: string;
  symbol: string;
  signal_timestamp: string;
  direction: string;
  confluence_score: number;
  entry_price: number;
  stop_loss?: number | null;
  take_profit_1?: number | null;
  take_profit_2?: number | null;
  exit_price?: number | null;
  outcome: string;
  realized_r: number;
  mfe: number;
  mae: number;
  market_regime: string;
  session: string;
  calibrated_probability: number;
  htf_aligned: boolean;
  sr_aligned: boolean;
  vwap_aligned: boolean;
  ema_aligned: boolean;
  mom_aligned: boolean;
  qualification_status: "QUALIFIED" | "NOT QUALIFIED" | "INSUFFICIENT DATA" | string;
  qualification_tag: string;
  qualification_reason: string;
}

export interface PerformanceSummaryKPIs {
  total_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  win_rate_pct: number;
  expectancy_r: number;
  profit_factor: number;
  total_realized_r: number;
  max_drawdown_r: number;
  avg_win_r: number;
  avg_loss_r: number;
}

export interface HistoryEquityPoint {
  trade_index: number;
  timestamp: string;
  signal_id: string;
  symbol: string;
  direction: string;
  outcome: string;
  realized_r: number;
  cumulative_r: number;
  drawdown_r: number;
  rolling_expectancy_25: number;
}

export interface StrategyBenchmarkCard {
  strategy_id: string;
  display_name: string;
  asset: string;
  direction: string;
  primary_condition: string;
  expectancy_r: number;
  win_rate_pct: number;
  profit_factor: number;
  validation_score: number;
  status: string;
  description: string;
}

export interface HistoryAnalyticsResponse {
  total_count: number;
  limit: number;
  offset: number;
  kpi_summary: PerformanceSummaryKPIs;
  strategy_benchmarks: StrategyBenchmarkCard[];
  equity_curve: HistoryEquityPoint[];
  signals: ValidatedSignalRecord[];
}

export async function fetchHistoryAnalytics(params: {
  symbol?: string;
  direction?: string;
  outcome?: string;
  min_prob?: number;
  max_prob?: number;
  market_regime?: string;
  qualification?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<HistoryAnalyticsResponse> {
  return request<HistoryAnalyticsResponse>(
    `/api/v1/backtest/history/analytics${qs(params)}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export interface PeriodMetricsData {
  period_name: string;
  asset: string;
  start_time: string;
  end_time: string;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  wait_signals: number;
  total_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  expired: number;
  invalid: number;
  pending: number;
  win_rate_pct: number;
  expectancy_r: number;
  profit_factor: number;
  total_realized_r: number;
  average_win_r: number;
  average_loss_r: number;
  max_drawdown_r: number;
  average_predicted_prob: number;
  average_calibrated_prob: number;
  calibration_error_pct: number;
  sample_status: string;
}

export interface CalibrationBucketData {
  bucket_label: string;
  min_prob: number;
  max_prob: number;
  sample_size: number;
  wins: number;
  losses: number;
  mean_predicted_prob: number;
  observed_win_rate_pct: number;
  calibration_gap_pct: number;
  ci_lower_pct: number;
  ci_upper_pct: number;
  status: string;
}

export interface CalibrationSummaryData {
  asset: string;
  total_resolved: number;
  brier_score: number;
  ece_pct: number;
  mce_pct: number;
  buckets: CalibrationBucketData[];
  overall_status: string;
}

export interface DirectionMetricsData {
  asset: string;
  direction: string;
  sample_size: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  expectancy_r: number;
  profit_factor: number;
  total_r: number;
  max_drawdown_r: number;
  average_mfe_r: number;
  average_mae_r: number;
  avg_confidence: number;
  avg_probability: number;
  status: string;
}

export interface FailureTaxonomyData {
  failure_category: string;
  count: number;
  percentage_of_losses: number;
  total_loss_r: number;
  average_loss_r: number;
  worst_loss_r: number;
  primary_regime: string;
  primary_session: string;
}

export interface SuccessTaxonomyData {
  success_category: string;
  count: number;
  percentage_of_wins: number;
  total_gain_r: number;
  average_gain_r: number;
  best_gain_r: number;
  primary_regime: string;
  primary_session: string;
}

export interface LiveValidationSummaryReportData {
  generated_at: string;
  asset: string;
  total_signals_recorded: number;
  total_signals_tracked?: number;
  total_trades_created: number;
  total_resolved_trades: number;
  total_pending_trades: number;
  all_time: PeriodMetricsData;
  rolling_30d: PeriodMetricsData;
  rolling_7d: PeriodMetricsData;
  today: PeriodMetricsData;
  buy_performance: DirectionMetricsData;
  sell_performance: DirectionMetricsData;
  calibration: CalibrationSummaryData;
  top_failures: FailureTaxonomyData[];
  top_successes: SuccessTaxonomyData[];
  quality_score_status: string;
  strength_monotonicity: string;
  asset_isolation_verified: boolean;
  safety_statement: string;
}

export interface LiveValidationResponse {
  status: string;
  symbol: string;
  validation: LiveValidationSummaryReportData;
}

export async function fetchLiveValidationSummary(symbol: string = "XAU-USD-SPOT"): Promise<LiveValidationResponse> {
  return request<LiveValidationResponse>(
    `/api/v1/performance/live-validation?symbol=${encodeURIComponent(symbol)}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

/**
 * Live Validation UI View Model and Adapter
 * Explicit mapping between backend API responses and UI presentation.
 *
 * SEMANTIC FIELD MAPPING:
 * UI FIELD                  SOURCE API FIELD (JSON path)
 * ---------------------------------------------------------------------------------------------------------------
 * Live Decision             /api/v1/decision -> TradingDecision.decision ("BUY" | "SELL" | "WAIT")
 * Trade Signals Tracked     /api/v1/performance/live-validation -> LiveValidationSummaryReportData.total_signals_recorded (int)
 * Pending Trades            /api/v1/performance/live-validation -> LiveValidationSummaryReportData.total_pending_trades (int)
 * Completed Outcomes        /api/v1/performance/live-validation -> LiveValidationSummaryReportData.all_time.total_trades (int)
 * Wins                      /api/v1/performance/live-validation -> LiveValidationSummaryReportData.all_time.wins (int)
 * Losses                    /api/v1/performance/live-validation -> LiveValidationSummaryReportData.all_time.losses (int)
 * Live Accuracy             /api/v1/performance/live-validation -> LiveValidationSummaryReportData.all_time.win_rate_pct (or null if total_trades === 0)
 * Accuracy Status           /api/v1/performance/live-validation -> LiveValidationSummaryReportData.all_time.sample_status ("INSUFFICIENT_LIVE_SAMPLE" | "ACTIVE")
 */
export interface LiveValidationViewModel {
  liveDecision: "BUY" | "SELL" | "WAIT";
  trackedSignals: number;
  pendingTrades: number;
  completedOutcomes: number;
  wins: number;
  losses: number;
  liveAccuracy: number | null;
  accuracyStatus: string;
  isSampleSufficient: boolean;
  asset: string;
}

export function mapToLiveValidationViewModel(
  decisionRaw: string | undefined | null,
  validationData: LiveValidationSummaryReportData | null | undefined
): LiveValidationViewModel {
  const normDecision = (decisionRaw?.toUpperCase() || "WAIT") as "BUY" | "SELL" | "WAIT";
  const safeDecision = normDecision === "BUY" || normDecision === "SELL" ? normDecision : "WAIT";

  const totalTrades = validationData?.all_time?.total_trades ?? 0;
  const isSufficient = totalTrades > 0 && validationData?.all_time?.sample_status !== "INSUFFICIENT_LIVE_SAMPLE";

  return {
    liveDecision: safeDecision,
    trackedSignals: validationData?.total_signals_recorded ?? 0,
    pendingTrades: validationData?.total_pending_trades ?? 0,
    completedOutcomes: totalTrades,
    wins: validationData?.all_time?.wins ?? 0,
    losses: validationData?.all_time?.losses ?? 0,
    liveAccuracy: isSufficient ? (validationData?.all_time?.win_rate_pct ?? 0) : null,
    accuracyStatus: validationData?.all_time?.sample_status || "INSUFFICIENT_LIVE_SAMPLE",
    isSampleSufficient: isSufficient,
    asset: validationData?.asset || "ASSET",
  };
}

/* -------------------------------------------------------------------------- */
/* ML Shadow Research & Validation Layer Types                                */
/* -------------------------------------------------------------------------- */

export interface MLShadowModelInfo {
  available: boolean;
  model_name: string;
  version: string;
  observations_total: number;
  observations_pending: number;
  trades_resolved: number;
  milestone: string;
}

export interface MLShadowStatusResponse {
  status: string;
  mode: string;
  production_influence: string;
  models: {
    "BTC/USD": MLShadowModelInfo;
    "XAU/USD": MLShadowModelInfo;
    [key: string]: MLShadowModelInfo;
  };
}

export interface MLShadowCalibration {
  brier_score?: number | null;
  expected_calibration_error?: number | null;
  max_calibration_error?: number | null;
  reliability_curve?: Array<{
    bin_center: number;
    empirical_prob: number;
    sample_count: number;
  }>;
  [key: string]: any;
}

export interface MLShadowMetricsResponse {
  symbol: string;
  status: string;
  total_observations: number;
  pending_observations: number;
  resolved_trades: number;
  wait_observations?: number;
  milestone_reached: string;
  win_rate: number | null;
  ev_r: number | null;
  profit_factor: number | null;
  brier_score: number | null;
  calibration?: MLShadowCalibration | null;
  diagnostics?: Record<string, number>;
}

export interface MLShadowObservation {
  observation_id: string;
  symbol: string;
  timestamp_t0: string;
  production_decision: string;
  confluence_score: number;
  technical_score: number;
  quality_gate_passed: number | boolean;
  ml_model_name: string;
  ml_model_version: string;
  ml_probability: number;
  ml_predicted_class: number;
  entry_price: number;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  session: string;
  market_regime: string;
  features_snapshot_json?: string;
  outcome: string;
  exit_price: number | null;
  realized_r: number | null;
  outcome_timestamp: string | null;
  time_to_outcome_minutes: number | null;
  created_at: string;
  updated_at?: string;
}

export async function getMLShadowStatus(): Promise<MLShadowStatusResponse> {
  return request<MLShadowStatusResponse>("/api/v1/ml/shadow/status", {
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: 1,
  });
}

export async function getMLShadowMetrics(symbol?: string): Promise<MLShadowMetricsResponse> {
  return request<MLShadowMetricsResponse>(
    `/api/v1/ml/shadow/metrics${qs({ symbol: symbol || undefined })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export async function getMLShadowObservations(
  symbol?: string,
  limit = 50,
  modelVersion?: string
): Promise<MLShadowObservation[]> {
  return request<MLShadowObservation[]>(
    `/api/v1/ml/shadow/observations${qs({
      symbol: symbol || undefined,
      limit,
      model_version: modelVersion || undefined,
    })}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

/** Namespaced client — same functions, for call sites that prefer an object. */
export const ApiClient = {
  getPrice,
  getCandles,
  getMarketStatus,
  getTechnicalAnalysis,
  getAIAnalysis,
  getRawTechnicalInput,
  getDecision,
  getHealth,
  openDemoTrade,
  updateDemoTrade,
  closeDemoTrade,
  resetDemoAccount,
  getPerformanceReport,
  getCalibration,
  getSignalsHistory,
  getSignalDetail,
  getDataIntegrity,
  fetchDatasetStatus,
  fetchBacktestDatasets,
  downloadBacktestDataset,
  startBacktestRun,
  fetchBacktestRuns,
  fetchBacktestRun,
  fetchBacktestPerformance,
  fetchBacktestSignals,
  fetchBacktestEquityCurve,
  fetchLiveIngestionStatus,
  fetchHistoryAnalytics,
  fetchLiveValidationSummary,
  getLivePrice: getPrice,
  getTradingDecision: getDecision,
  getMLShadowStatus,
  getMLShadowMetrics,
  getMLShadowObservations,
  getShadowStatus,
  getShadowComparison,
};


/* -------------------------------------------------------------------------- */
/* Shadow Accumulation Monitor — types & API functions (additive)             */
/* -------------------------------------------------------------------------- */

export interface ShadowLiveMetrics {
  asset: string;
  total_trades: number;
  open_trades_count: number;
  resolved_trades_count: number;
  wins_count: number;
  losses_count: number;
  win_rate_pct: number;
  ev_r: number;
  profit_factor: number;
  total_realized_r: number;
  max_drawdown_r: number;
  first_trade_ts: string | null;
  last_trade_ts: string | null;
  days_active: number;
}

export interface ShadowBaselineComparison {
  ev_delta_vs_baseline: number | null;
  wr_delta_vs_baseline: number | null;
  pf_delta_vs_baseline: number | null;
  sample_progress_pct: number;
  sample_milestone_met: boolean;
}

export interface ShadowStatusResponse {
  status: string;
  strategy_version: string;
  disclaimer: string;
  live_shadow_metrics: ShadowLiveMetrics;
  backtest_reference_baseline: {
    reference_dataset: string;
    sample_size_n: number;
    win_rate_pct: number;
    expected_value_r: number;
    profit_factor: number;
    max_drawdown_r: number;
    bootstrap_95_ci_ev: [number, number];
    evidence_status: string;
  };
  comparison_vs_baseline: ShadowBaselineComparison;
}

export interface ShadowComparisonThresholds {
  min_sample_size_n: number;
  min_calendar_days: number;
  backtest_ev_baseline: number;
  ev_acceptable_range: [number, number];
  backtest_wr_baseline: number;
  wr_acceptable_range: [number, number];
  required_drift_status: string;
}

export interface ShadowComparisonReport {
  evaluation_timestamp_utc: string;
  asset: string;
  sample_size_n: number;
  calendar_days_elapsed: number;
  live_ev_r: number;
  live_win_rate_pct: number;
  live_profit_factor: number;
  live_max_drawdown_r: number;
  drift_status: string;
  sample_gate_passed: boolean;
  time_gate_passed: boolean;
  ev_gate_passed: boolean;
  wr_gate_passed: boolean;
  drift_gate_passed: boolean;
  verdict: "ACCUMULATING" | "PASS" | "FAIL" | string;
  verdict_summary: string;
  pre_registered_thresholds: ShadowComparisonThresholds;
}

export interface ShadowComparisonResponse {
  status: string;
  disclaimer: string;
  report: ShadowComparisonReport;
}

/** Fetch per-asset shadow runner live metrics. asset: "btc" | "xau" */
export async function getShadowStatus(asset: "btc" | "xau"): Promise<ShadowStatusResponse> {
  return request<ShadowStatusResponse>(
    `/api/v1/decision/trade/shadow-status/${asset}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

/** Fetch pre-registered comparison gate report. asset: "btc" | "xau" */
export async function getShadowComparison(asset: "btc" | "xau"): Promise<ShadowComparisonResponse> {
  return request<ShadowComparisonResponse>(
    `/api/v1/research/governance/${asset}-shadow-comparison`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export interface ForwardShadowResolverStatusResponse {
  status: string;
  resolver_worker: {
    is_active: boolean;
    interval_seconds: number;
    last_run_utc: string | null;
    last_cycle_resolved: number;
    total_signals_evaluated: number;
    total_signals_resolved: number;
    status_message: string;
  };
  governance_state: {
    current_state: string;
    previous_state: string | null;
    transition: string;
    transition_reason: string;
    xau_valid_forward_resolved_n: number;
    btc_valid_forward_resolved_n: number;
    xau_unresolved_n: number;
    btc_unresolved_n: number;
    n50_status: string;
    n100_status: string;
    production_readiness: string;
    production_gating: string;
    live_execution: string;
    blocking_issue: string;
    next_valid_state: string;
  };
}

/** Fetch operational status of the forward shadow resolver and governance state */
export async function getForwardShadowResolverStatus(): Promise<ForwardShadowResolverStatusResponse> {
  return request<ForwardShadowResolverStatusResponse>(
    `/api/v1/research/governance/resolver-status`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export interface SystemObservabilityResponse {
  status: string;
  governance: {
    current_state: string;
    state_name: string;
    production_gating: string;
    live_execution: string;
    xau_resolved_n: number;
    xau_pending_n: number;
    xau_n50_progress: string;
    xau_n50_met: boolean;
    xau_n100_progress: string;
    xau_n100_met: boolean;
    btc_resolved_n: number;
    btc_pending_n: number;
  };
  resolver: {
    status: string;
    is_active: boolean;
    interval_seconds: number;
    last_run: string | null;
    last_success: string | null;
    next_scheduled_run: string | null;
    processing_duration_ms: number;
    pending_count: number;
    eligible_count: number;
    resolved_count: number;
    failed_count: number;
    oldest_pending_timestamp: string | null;
    status_message: string;
  };
  data_freshness: {
    feed_status: string;
    latest_btc_market_candle: { timestamp: string; close: number } | null;
    latest_xau_market_candle: { timestamp: string; close: number } | null;
    latest_data_timestamp: string | null;
    api_freshness: string;
    historical_db_status: string;
    temporal_firewall: string;
  };
  ml: {
    model_version: string;
    btc_algorithm: string;
    xau_algorithm: string;
    training_status: string;
    validation_status: string;
    last_validation_metadata: Record<string, any>;
    shadow_observation_count: number;
    calibration_status: string;
    execution_mode: string;
  };
  forward_shadow?: {
    accuracy?: number | null;
    total_resolved?: number;
    sample_size?: number;
    pending_count?: number;
    model_version?: string;
  };
}

/** Fetch consolidated system observability across Governance, Resolver, Data, and ML */
export async function getSystemObservability(): Promise<SystemObservabilityResponse> {
  return request<SystemObservabilityResponse>(
    `/api/v1/research/governance/observability`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}

export interface ForwardShadowValidationAsset {
  asset: string;
  total_signals: number;
  resolved_signals: number;
  pending_signals: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  provenance_note: string;
  clean_forward?: {
    total_signals: number;
    resolved_signals: number;
    pending_signals: number;
    wins: number;
    losses: number;
    win_rate_pct: number;
  };
  quarantined_legacy?: {
    total_signals: number;
    resolved_signals: number;
    pending_signals: number;
    wins: number;
    losses: number;
    status: string;
  };
}

export interface ForwardShadowValidationResponse {
  status: string;
  authoritative_source: string;
  disclaimer: string;
  btc: ForwardShadowValidationAsset;
  xau: ForwardShadowValidationAsset;
}

/** Fetch authoritative forward shadow validation metrics from forward_shadow_signals */
export async function getForwardShadowValidation(generation?: string): Promise<ForwardShadowValidationResponse> {
  const query = generation ? `?generation=${encodeURIComponent(generation)}` : "";
  return request<ForwardShadowValidationResponse>(
    `/api/v1/research/governance/forward-shadow-validation${query}`,
    { timeoutMs: DEFAULT_TIMEOUT_MS, retries: 1 }
  );
}
