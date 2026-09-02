"""
Historical Backtesting Data Models.

Defines schemas for:
- HistoricalCandle (normalized multi-timeframe historical candle)
- DatasetQualityReport (validation audit trail, integrity counts, volume status)
- DatasetMetadata (versioning, instrument proxy description, date coverage)
- BacktestConfig (reproducible parameters, overlap mode, cost model, ambiguity rule)
- BacktestRunRecord (job execution status, progress, timing, summary)
- HistoricalSignalRecord (immutable point-in-time signal snapshot + future outcome)
- BacktestPerformanceReport (comprehensive empirical performance, score bands, strategies, regimes, calibration)

DISCLAIMER: Research and analytical modeling only. No real trades are executed.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AmbiguousCandleRule(str, Enum):
    WORST_CASE = "WORST_CASE"
    AMBIGUOUS = "AMBIGUOUS"
    BEST_CASE = "BEST_CASE"


class BacktestStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class HistoricalCandle(BaseModel):
    """Normalized historical candle model with UTC timestamps."""
    symbol: str                              # e.g. "BTC/USD" or "XAU/USD"
    source_symbol: str                       # e.g. "BTCUSDT" or "GC=F"
    timeframe: str                           # "1m", "5m", "15m", "1h", "4h", "1d"
    timestamp: str                           # ISO 8601 UTC
    epoch_ms: int                            # Unix millisecond timestamp for fast binary search
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = 0.0
    is_closed: bool = True
    source: str = "binance"                  # "binance", "yahoo", "goldprice", "csv"


class DatasetQualityReport(BaseModel):
    """Validation report generated upon dataset import/audit."""
    dataset_id: str
    symbol: str
    source_symbol: str
    source: str
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    timeframes: List[str] = []
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    duplicate_rows: int = 0
    invalid_ohlc_rows: int = 0
    future_rows: int = 0
    missing_intervals: int = 0
    volume_available: bool = True
    quality_score_pct: float = 100.0
    issues: List[str] = []
    dataset_version: str = "v1.0"


class DatasetMetadata(BaseModel):
    """Registered historical dataset metadata."""
    dataset_id: str
    symbol: str
    source_symbol: str
    source: str
    description: str
    timeframes: List[str]
    start_date: str
    end_date: str
    row_count: int
    valid_rows: int
    volume_available: bool
    version: str
    created_at: str
    quality_report: Optional[DatasetQualityReport] = None
    status: str = "READY"


class BacktestConfig(BaseModel):
    """Configuration for reproducible historical backtest execution."""
    symbol: str = "BTC/USD"                  # "BTC/USD", "XAU/USD", or "ALL"
    start_date: str = "2023-01-01"           # ISO date YYYY-MM-DD
    end_date: str = "2026-08-30"             # ISO date YYYY-MM-DD
    primary_timeframe: str = "15m"           # Timeframe to evaluate signals on
    context_timeframes: List[str] = ["5m", "15m", "1h", "4h", "1d"]
    allow_overlapping_trades: bool = False   # False = max 1 active trade at a time
    ambiguous_candle_rule: AmbiguousCandleRule = AmbiguousCandleRule.WORST_CASE
    transaction_cost_pct: float = 0.0        # Assumed round-trip cost if actual spread is unavailable
    include_spread_cost: bool = True
    expiry_hours: int = 72                   # Max duration before signal outcome is labeled EXPIRED
    duplicate_window_seconds: int = 60       # Minimum cooldown between identical signals
    min_confluence_score: int = 55           # Minimum confluence score required to generate action
    train_ratio: float = 0.70                # 70% chronological train, 30% validation
    walk_forward_enabled: bool = True


class BacktestRunRecord(BaseModel):
    """Metadata and execution lifecycle state of a backtest run."""
    run_id: str
    dataset_id: str
    dataset_version: str
    engine_version: str = "ConfluenceEngine-v2.0"
    symbol: str
    config: BacktestConfig
    status: BacktestStatus = BacktestStatus.PENDING
    progress_pct: float = 0.0                # 0.0 to 100.0
    current_step: str = "Queued"             # e.g. "Building historical snapshots..."
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    total_signals_evaluated: int = 0
    total_trades_generated: int = 0


class HistoricalSignalRecord(BaseModel):
    """Point-in-time signal record generated strictly using closed historical candles <= T."""
    signal_id: str
    run_id: str
    dataset_id: str
    symbol: str
    source_symbol: str
    signal_timestamp: str                    # Decision timestamp T (UTC ISO 8601)
    snapshot_id: str
    entry_price: float
    direction: str                           # "BUY" or "SELL"
    confluence_score: int                    # 0–100
    technical_score: int                     # 0–90
    gemini_score: int                        # 0–10
    contributor_scores: Dict[str, int] = {}
    contributor_directions: Dict[str, str] = {}
    data_quality: str = "HIGH"
    gate_direction: str = "NONE"
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    invalidation_level: Optional[float] = None
    market_regime: str = "UNKNOWN"
    session: str = "UNKNOWN"
    strategy_evidence: List[str] = []
    conflicts: List[str] = []
    # Future outcome fields (populated strictly from future candles > T)
    outcome: Optional[str] = None            # "WIN", "LOSS", "BREAKEVEN", "EXPIRED", "OPEN"
    outcome_timestamp: Optional[str] = None
    exit_price: Optional[float] = None
    realized_r: Optional[float] = None
    mfe: Optional[float] = None              # Maximum Favorable Excursion
    mae: Optional[float] = None              # Maximum Adverse Excursion
    max_r: Optional[float] = None
    time_to_outcome_minutes: Optional[float] = None
    transaction_cost_deducted: float = 0.0
    ambiguity_flag: bool = False
    is_in_sample: bool = True                # True if in 70% train split, False if in 30% val split
    success_reason: Optional[str] = None
    failure_reason: Optional[str] = None


class ScoreBandPerformance(BaseModel):
    """Performance metrics for a specific confluence score band."""
    band_name: str                           # e.g. "80–89"
    min_score: int
    max_score: int
    total_signals: int
    completed_trades: int
    wins: int
    losses: int
    breakevens: int
    expired: int
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    expectancy_r: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown_r: Optional[float] = None


class ContributorPerformance(BaseModel):
    """Performance metrics for one of the 17 signal contributors."""
    strategy_name: str
    weight: int
    total_signals: int
    completed_trades: int
    wins: int
    losses: int
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    expectancy_r: Optional[float] = None
    profit_factor: Optional[float] = None
    bullish_signals: int = 0
    bearish_signals: int = 0
    status: str = "INSUFFICIENT_DATA"        # "CALIBRATED", "EXPLORATORY", "INSUFFICIENT_DATA"


class MarketRegimePerformance(BaseModel):
    """Performance metrics segmented by mechanically detected market regime."""
    regime: str                              # "TRENDING", "RANGING", "HIGH_VOLATILITY", "LOW_VOLATILITY"
    total_trades: int
    wins: int
    losses: int
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    expectancy_r: Optional[float] = None
    profit_factor: Optional[float] = None


class BacktestPerformanceReport(BaseModel):
    """Comprehensive performance analytics report for a historical backtest run."""
    run_id: str
    symbol: str
    source_symbol: str
    period_start: str
    period_end: str
    dataset_version: str
    engine_version: str
    created_at: str

    # Overall Metrics
    total_signals_evaluated: int
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    expired: int
    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None
    win_rate_ci_lower: Optional[float] = None # 95% Confidence Interval
    win_rate_ci_upper: Optional[float] = None
    avg_win_r: Optional[float] = None
    avg_loss_r: Optional[float] = None
    avg_r: Optional[float] = None
    expectancy_r: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown_r: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    median_r: Optional[float] = None
    best_trade_r: Optional[float] = None
    worst_trade_r: Optional[float] = None
    avg_mfe_r: Optional[float] = None
    avg_mae_r: Optional[float] = None

    # Directional Breakdown
    buy_trades: int = 0
    buy_win_rate: Optional[float] = None
    buy_expectancy_r: Optional[float] = None
    buy_profit_factor: Optional[float] = None
    sell_trades: int = 0
    sell_win_rate: Optional[float] = None
    sell_expectancy_r: Optional[float] = None
    sell_profit_factor: Optional[float] = None

    # Granular Analyses
    score_bands: List[ScoreBandPerformance] = []
    by_strategy: List[ContributorPerformance] = []
    by_regime: List[MarketRegimePerformance] = []
    session_analysis: Dict[str, Dict[str, Any]] = {}
    correlation_matrix: Dict[str, Dict[str, float]] = {}
    double_counting_alerts: List[str] = []

    # Gemini Ablation Analysis
    gemini_ablation_available: bool = False
    technical_only_win_rate: Optional[float] = None
    technical_plus_gemini_win_rate: Optional[float] = None
    gemini_accuracy_pct: Optional[float] = None
    gemini_status_note: str = "GEMINI HISTORICAL PERFORMANCE NOT EMPIRICALLY CALIBRATED"

    # Calibration & Out-of-Sample Metrics
    sample_size: int = 0
    training_size: int = 0
    validation_size: int = 0
    in_sample_win_rate: Optional[float] = None
    out_of_sample_win_rate: Optional[float] = None
    out_of_sample_brier_score: Optional[float] = None
    out_of_sample_accuracy: Optional[float] = None
    calibration_status: str = "INSUFFICIENT_DATA" # "INSUFFICIENT_DATA", "EXPLORATORY", "VALID", "PREFERRED", "UNRELIABLE"
    calibration_curve: List[Dict[str, Any]] = [] # [{predicted_prob, empirical_prob, sample_size}]
    walk_forward_reports: List[Dict[str, Any]] = []

    # Disclosures & Integrity
    transaction_cost_note: str = "TRANSACTION COSTS NOT INCLUDED"
    look_ahead_audit_passed: bool = True
    disclaimer: str = (
        "Historical Win Rate is based on completed backtest trades. "
        "It is NOT a guarantee of future performance. Past performance does not guarantee future results. "
        "Confluence Score is NOT a probability. Calibrated probability is displayed only after sufficient validated historical data."
    )
