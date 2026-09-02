"""Data models for the Trading Decision Engine output."""
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TradingSignal(str, Enum):
    """Advisory trading signal produced by the decision engine."""
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class DecisionTrend(str, Enum):
    """Consolidated trend direction used in the decision output."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class DecisionRiskLevel(str, Enum):
    """Risk level of the current setup."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EntryZone(BaseModel):
    """Suggested entry price zone for a trade."""
    min: float = Field(description="Lower bound of the suggested entry zone")
    max: float = Field(description="Upper bound of the suggested entry zone")


class ScoreComponent(BaseModel):
    """Individual scoring component contribution."""
    name: str = Field(description="Component name (e.g. '1h Trend')")
    weight: float = Field(description="Configured weight for this component (0-1)")
    raw_score: float = Field(description="Raw score for this component (-1.0 to +1.0)")
    weighted_score: float = Field(description="Weight × raw_score contribution")
    reasoning: str = Field(description="Human-readable explanation of how the score was assigned")


class DecisionScoreBreakdown(BaseModel):
    """Full scoring breakdown for the /decision/explain endpoint."""
    symbol: str = Field(default="XAU/USD")
    timestamp: str
    total_score: float = Field(description="Final composite score (-1.0 to +1.0)")
    signal_candidate: str = Field(description="Raw signal before WAIT overrides are applied")
    final_signal: TradingSignal
    confidence: int = Field(ge=0, le=100)
    components: List[ScoreComponent] = Field(description="Per-component score breakdown")
    wait_overrides_triggered: List[str] = Field(
        default_factory=list,
        description="List of WAIT override rules that were triggered"
    )
    weight_sum: float = Field(description="Sum of all weights (should be ~1.0)")


class TradingDecision(BaseModel):
    """
    Structured advisory trading decision output.

    DISCLAIMER: This is a purely analytical signal for informational purposes only.
    This system does NOT execute trades, connect to brokers, or guarantee any outcome.
    All decisions carry inherent market risk. Never risk funds you cannot afford to lose.
    """
    symbol: str = Field(default="XAU/USD", description="Trading symbol")
    decision: TradingSignal = Field(description="Advisory signal: BUY, SELL, or WAIT")
    confidence: int = Field(ge=0, le=100, description="Decision confidence score (0-100)")
    entry_zone: Optional[EntryZone] = Field(
        default=None,
        description="Suggested entry price zone. None when decision is WAIT."
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description="ATR-based stop-loss level. None when decision is WAIT."
    )
    take_profit_1: Optional[float] = Field(
        default=None,
        description="First take-profit target level. None when decision is WAIT."
    )
    take_profit_2: Optional[float] = Field(
        default=None,
        description="Second take-profit target level. None when decision is WAIT."
    )
    risk_reward_tp1: Optional[float] = Field(
        default=None,
        description="Risk:Reward ratio to TP1. None when decision is WAIT."
    )
    risk_reward_tp2: Optional[float] = Field(
        default=None,
        description="Risk:Reward ratio to TP2. None when decision is WAIT."
    )
    trend: DecisionTrend = Field(description="Consolidated market trend direction")
    risk_level: DecisionRiskLevel = Field(description="Estimated risk level of the current setup")
    composite_score: float = Field(description="Raw composite score (-1.0 to +1.0) before threshold filtering")
    reasons: List[str] = Field(
        default_factory=list,
        description="Human-readable reasons supporting the decision"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Risk warnings and caveats the analyst should be aware of"
    )
    invalid_if: List[str] = Field(
        default_factory=list,
        description="Conditions that would immediately invalidate this signal"
    )
    timestamp: str = Field(description="ISO 8601 timestamp when the decision was produced")
    ai_provider_used: str = Field(default="", description="AI provider that contributed to this decision")

    # Advanced Production & Sizing Metrics
    position_size: Optional[float] = Field(
        default=None,
        description="Suggested position size in Standard Lots (e.g. based on $10k balance and 1% risk)"
    )
    setup_grade: Optional[str] = Field(
        default=None,
        description="Setup quality grade: A+, A, B, or C"
    )
    agreement_score: Optional[int] = Field(
        default=None,
        description="Agreement score (0-100) between Gemini AI bias and technical trend indicators"
    )
    confluence_pct: Optional[int] = Field(
        default=None,
        description="Technical confluence percentage (0-100)"
    )
    confluence_direction: str = Field(
        default="Bullish",
        description="Direction of technical confluence: Bullish or Bearish"
    )
    mtf_confluence_pct: Optional[int] = Field(
        default=None,
        description="MTF confluence percentage (0-100)"
    )
    mtf_alignment_summary: str = Field(
        default="",
        description="MTF alignment description, e.g. '3/4 TF aligned'"
    )

    # Advanced Signal & Liquidity Metrics
    signal_strength: int = Field(default=50, description="Overall signal confidence/strength 0-100")
    buy_score: int = Field(default=0, description="Independent BUY confluence score 0-100")
    sell_score: int = Field(default=0, description="Independent SELL confluence score 0-100")
    signal_contributors: List[dict] = Field(
        default_factory=list,
        description="Structured breakdown of positive strategy point contributors"
    )

    pdh: Optional[float] = Field(default=None, description="Previous Day High price level")
    pdl: Optional[float] = Field(default=None, description="Previous Day Low price level")
    liquidity_status: str = Field(
        default="INSIDE_RANGE",
        description="Liquidity status: INSIDE_RANGE, NEAR_PDH, NEAR_PDL, PDH_SWEPT, PDL_SWEPT"
    )
    sweep_detected: bool = Field(
        default=False,
        description="True ONLY when an actual liquidity sweep occurred"
    )
    sweep_detail: Optional[str] = Field(
        default=None,
        description="Detailed description of liquidity status or sweep event"
    )

    fake_breakout_detected: bool = Field(
        default=False,
        description="Whether a fake breakout was detected recently near support/resistance"
    )
    fake_breakout_details: Optional[str] = Field(
        default=None,
        description="Description of detected fake breakout pattern"
    )
    support_resistance_strengths: Optional[dict] = Field(
        default=None,
        description="Touch counts or strength levels keyed by level value string"
    )
    paper_trading_stats: Optional[dict] = Field(
        default=None,
        description="Consolidated paper-trading metrics (win rate, profit factor, drawdown, etc.)"
    )
    trade_history: Optional[List[dict]] = Field(
        default=None,
        description="List of recently logged paper trades for dashboard visualizer"
    )

    # -----------------------------------------------------------------------
    # Confluence Engine Extended Fields (all Optional — backward compatible)
    # -----------------------------------------------------------------------
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Synchronized snapshot ID linking all contributors to one data point"
    )
    technical_score: Optional[int] = Field(
        default=None,
        description="Technical-only confluence score (0-90, excludes Gemini AI contributor)"
    )
    gemini_score: Optional[int] = Field(
        default=None,
        description="Gemini AI contributor score (0-10)"
    )
    final_confluence: Optional[int] = Field(
        default=None,
        description="Final 100-point confluence score (technical + gemini)"
    )
    data_quality: Optional[str] = Field(
        default=None,
        description="Data quality rating: HIGH | MEDIUM | LOW"
    )
    data_completeness: Optional[str] = Field(
        default=None,
        description="Contributor availability summary e.g. '14/17 contributors available'"
    )
    market_regime: Optional[str] = Field(
        default=None,
        description="Market regime: TRENDING_BULLISH | TRENDING_BEARISH | RANGING | HIGH_VOLATILITY | UNCLEAR"
    )
    conflicts: Optional[List[str]] = Field(
        default=None,
        description="List of detected conflicting evidence strings"
    )
    top_confirmations: Optional[List[str]] = Field(
        default=None,
        description="Strongest bullish or bearish confirmations in current cycle"
    )
    entry_quality: Optional[str] = Field(
        default=None,
        description="Entry quality rating: GOOD | FAIR | POOR | WAIT"
    )
    invalidation_conditions: Optional[List[str]] = Field(
        default=None,
        description="Conditions that immediately invalidate this signal (alias for invalid_if)"
    )
    calibration_note: Optional[str] = Field(
        default="Not empirically calibrated — advisory only",
        description="Calibration status disclaimer"
    )
    spread_status: Optional[str] = Field(
        default=None,
        description="Spread status: NORMAL | HIGH_SPREAD | UNAVAILABLE"
    )
    news_status: Optional[str] = Field(
        default="NEWS_DATA_UNAVAILABLE",
        description="News feed status (no live news feed integrated)"
    )
    gate_direction: Optional[str] = Field(
        default=None,
        description="Direction gate result: BULLISH | BEARISH | NONE"
    )
    gate_passed: Optional[bool] = Field(
        default=None,
        description="Whether the direction gate was satisfied (≥2 of HTF/Structure/MTF agree)"
    )

    # -----------------------------------------------------------------------
    # Automated Historical Evidence & Learning Layer (Additive)
    # -----------------------------------------------------------------------
    historical_evidence_status: Optional[str] = Field(
        default="NOT_AVAILABLE",
        description="Historical evidence availability: AVAILABLE | LIMITED | INSUFFICIENT | STALE | NOT_AVAILABLE"
    )
    historical_sample_size: Optional[int] = Field(
        default=None,
        description="Total completed backtested historical trades matching this asset/setup"
    )
    historical_win_rate: Optional[float] = Field(
        default=None,
        description="Empirical win rate percentage (0-100) from completed historical trades"
    )
    calibrated_probability: Optional[float] = Field(
        default=None,
        description="Validated empirical probability (0-100) calibrated via isotonic/logistic regression"
    )
    historical_expectancy: Optional[float] = Field(
        default=None,
        description="Empirical trade expectancy in R-multiples (e.g. +0.28R)"
    )
    historical_profit_factor: Optional[float] = Field(
        default=None,
        description="Empirical profit factor (Gross Win R / Gross Loss R)"
    )
    historical_drawdown: Optional[float] = Field(
        default=None,
        description="Maximum historical drawdown in R-multiples"
    )
    similar_setup_count: Optional[int] = Field(
        default=None,
        description="Number of historical setups matching current fingerprint (score band, regime, MTF)"
    )
    historical_wins: Optional[int] = Field(
        default=None,
        description="Total winning trades in similar setup sample"
    )
    historical_losses: Optional[int] = Field(
        default=None,
        description="Total losing trades in similar setup sample"
    )
    score_band_win_rate: Optional[float] = Field(
        default=None,
        description="Empirical win rate percentage for the current score band (e.g. 80-89)"
    )
    win_rate_ci_lower: Optional[float] = Field(
        default=None,
        description="Lower bound of 95% Wilson confidence interval for win rate"
    )
    win_rate_ci_upper: Optional[float] = Field(
        default=None,
        description="Upper bound of 95% Wilson confidence interval for win rate"
    )
    buy_strength: Optional[int] = Field(
        default=None,
        description="Historical evidence strength supporting BUY direction (0-100%)"
    )
    sell_strength: Optional[int] = Field(
        default=None,
        description="Historical evidence strength supporting SELL direction (0-100%)"
    )
    similarity_strength: Optional[int] = Field(
        default=None,
        description="Pattern similarity strength percentage (0-100%) based on matching historical features"
    )
    historical_bias: Optional[str] = Field(
        default=None,
        description="Synthesized historical bias: BUY | SELL | WAIT"
    )
    strategy_confirmations: Optional[List[str]] = Field(
        default=None,
        description="List of active strategy confirmations (e.g. SMC bullish, EMA aligned)"
    )
    strategy_conflicts: Optional[List[str]] = Field(
        default=None,
        description="List of active strategy conflicts"
    )
    historical_confirmations: Optional[List[str]] = Field(
        default=None,
        description="Empirical historical confirmations (e.g. BTC BUY 80-89 historically 64.5% WR)"
    )
    historical_conflicts: Optional[List[str]] = Field(
        default=None,
        description="Empirical historical risk caveats or failure patterns"
    )
    recommendation_strength: Optional[str] = Field(
        default="MEDIUM",
        description="Signal recommendation strength interpretation: LOW | MEDIUM | HIGH"
    )
    overall_reasoning: Optional[str] = Field(
        default=None,
        description="Evidence-integrated synthesis reasoning combining live market + historical empirical data"
    )
    evidence_refresh_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC timestamp when historical evidence was last updated"
    )
    dataset_version: Optional[str] = Field(
        default=None,
        description="Version ID of historical dataset used for evidence"
    )
    backtest_run_id: Optional[str] = Field(
        default=None,
        description="Run ID of backtest generating empirical statistics"
    )
    evidence_quality: Optional[str] = Field(
        default=None,
        description="Quality grade of historical evidence: STRONG | VALID | EXPLORATORY | LOW_SAMPLE | INSUFFICIENT"
    )
    top_success_reasons: Optional[List[str]] = Field(
        default=None,
        description="Top empirical reasons for winning trades on matching setups"
    )
    top_failure_reasons: Optional[List[str]] = Field(
        default=None,
        description="Top empirical reasons for losing trades on matching setups"
    )
    success_matches_count: Optional[int] = Field(
        default=None,
        description="Total winning trades in similar setup sample"
    )
    failure_matches_count: Optional[int] = Field(
        default=None,
        description="Total losing trades in similar setup sample"
    )

    # -----------------------------------------------------------------------
    # Validated Strategy Layer (Advisory Only — Zero Gating)
    # -----------------------------------------------------------------------
    validated_strategy: Optional["ValidatedStrategyEvaluation"] = Field(
        default=None,
        description="Real-time evaluation against empirically validated research strategies"
    )
    degradation_monitoring: Optional["DegradationMonitoringReport"] = Field(
        default=None,
        description="Advisory strategy degradation and calibration drift monitor"
    )

    # -----------------------------------------------------------------------
    # 3-Layer AI Trading Signal System & Hourly Opportunity Tracking
    # -----------------------------------------------------------------------
    historical_signal: Optional["HistoricalMarketSignal"] = Field(
        default=None,
        description="Layer 1: Empirical historical market analysis signal"
    )
    now_signal: Optional["NowMarketSignal"] = Field(
        default=None,
        description="Layer 2: Real-time current market analysis signal"
    )
    overall_signal: Optional["OverallTradingSignal"] = Field(
        default=None,
        description="Layer 3: Evidence fusion combining Historical + Now signals (Primary)"
    )
    hourly_strong_signal: Optional["HourlyStrongSignal"] = Field(
        default=None,
        description="Hourly strongest valid opportunity tracker (up to 1 per hour, zero forced)"
    )

    disclaimer: str = Field(
        default=(
            "ADVISORY ONLY. This is not financial advice. This system does not execute trades, "
            "connect to brokers, or guarantee any outcome. Past performance does not guarantee future results."
        ),
        description="Mandatory risk disclaimer"
    )


class HistoricalMarketSignal(BaseModel):
    """Layer 1: Empirical historical market analysis signal."""
    signal: str = Field(default="WAIT", description="BUY | SELL | WAIT")
    percentage: Optional[int] = Field(default=None, description="0-100% or None if insufficient sample")
    strength: str = Field(default="MODERATE", description="WEAK | MODERATE | STRONG | VERY STRONG")
    status: str = Field(default="INSUFFICIENT_SAMPLE", description="AVAILABLE | LIMITED | INSUFFICIENT_SAMPLE")
    sample_size: int = Field(default=0, description="Matching historical trade count")
    win_rate: Optional[float] = Field(default=None, description="Historical win rate percentage")
    calibrated_probability: Optional[float] = Field(default=None, description="Calibrated probability percentage")
    expectancy: Optional[float] = Field(default=None, description="Historical expectancy in R-multiples")
    reasons: List[str] = Field(default_factory=list, description="Historical supporting reasons")


class NowMarketSignal(BaseModel):
    """Layer 2: Real-time current market analysis signal."""
    signal: str = Field(default="WAIT", description="BUY | SELL | WAIT")
    percentage: int = Field(default=50, description="0-100% current confluence / technical strength")
    strength: str = Field(default="MODERATE", description="WEAK | MODERATE | STRONG | VERY STRONG")
    technical_score: int = Field(default=50, description="Technical score 0-100")
    gemini_score: int = Field(default=0, description="Gemini score 0-10")
    mtf_alignment: str = Field(default="", description="MTF alignment description")
    market_regime: str = Field(default="UNCLEAR", description="Current market regime")
    reasons: List[str] = Field(default_factory=list, description="Current market supporting reasons")


class OverallTradingSignal(BaseModel):
    """Layer 3: Evidence fusion combining Historical + Now signals (Primary)."""
    signal: str = Field(default="WAIT", description="BUY | SELL | WAIT")
    percentage: int = Field(default=50, description="0-100% combined evidence percentage")
    strength: str = Field(default="MODERATE", description="WEAK | MODERATE | STRONG | VERY STRONG")
    conflict_detected: bool = Field(default=False, description="True if Historical and Now signals conflict")
    primary_highlight: bool = Field(default=True, description="Primary visual hierarchy flag")
    reasons: List[str] = Field(default_factory=list, description="Combined evidence reasoning")


class HourlyStrongSignal(BaseModel):
    """Hourly strongest valid opportunity tracker (up to 1 per hour, zero forced)."""
    hour_window: str = Field(default="", description="UTC hour window e.g. 2026-09-02T01:00:00Z")
    status: str = Field(default="NO_QUALIFYING_SETUP", description="ACTIVE_OPPORTUNITY | NO_QUALIFYING_SETUP")
    signal: str = Field(default="WAIT", description="BUY | SELL | WAIT")
    strength: Optional[int] = Field(default=None, description="Confluence strength of strongest setup")
    confidence: Optional[int] = Field(default=None, description="Decision confidence")
    timestamp: Optional[str] = Field(default=None, description="Time opportunity occurred")
    asset: str = Field(default="", description="Asset symbol")
    reasons: List[str] = Field(default_factory=list, description="Reasons for hourly signal")


class ValidatedStrategyEvaluation(BaseModel):
    """
    Real-time setup evaluation against empirically validated research strategies.
    DISCLAIMER: Advisory analytical layer only. Zero automated gating.
    """
    strategy_id: str = Field(default="NONE", description="Strategy identifier (e.g. BTC-SELL-P40-REGIME_LOW_VOL)")
    strategy_name: str = Field(default="NONE", description="Human-readable strategy name")
    qualified: bool = Field(default=False, description="Whether all core qualification criteria are satisfied")
    qualification_status: str = Field(
        default="NOT_QUALIFIED",
        description="QUALIFIED | NOT_QUALIFIED | INSUFFICIENT_DATA | CONFLICT"
    )
    direction: str = Field(default="NONE", description="Validated direction: BUY | SELL | NONE")
    confirmation_score: int = Field(default=0, ge=0, le=4, description="Count of passed confirmation conditions")
    max_confirmation_score: int = Field(default=4, description="Maximum possible confirmation score")
    probability: float = Field(default=0.0, description="Point-in-time calibrated probability (0.0 to 1.0)")
    regime: str = Field(default="UNKNOWN", description="Current market volatility regime")
    confirmations: List[str] = Field(default_factory=list, description="List of passed confirmation conditions")
    failed_conditions: List[str] = Field(default_factory=list, description="List of failed qualification conditions")
    research_expectancy_r: float = Field(default=0.0, description="Historical research expectancy in R-multiples")
    research_win_rate_pct: float = Field(default=0.0, description="Historical research win rate percentage")
    research_profit_factor: float = Field(default=0.0, description="Historical research profit factor")
    validation_score: int = Field(default=0, description="Research validation score out of 100")
    degradation_status: str = Field(default="NORMAL", description="Degradation health: NORMAL | WATCH | DEGRADED")
    conflict_reason: Optional[str] = Field(default=None, description="Detailed explanation if conflict detected")
    disclaimer: str = Field(
        default="Research expectancy is historical evidence, NOT a guarantee of future performance.",
        description="Advisory research disclaimer"
    )


class DegradationMonitoringReport(BaseModel):
    """
    Advisory strategy degradation and calibration drift monitor.
    DISCLAIMER: Strictly advisory. Never halts trading or modifies position sizing.
    """
    status: str = Field(default="NORMAL", description="Monitoring state: NORMAL | WATCH | DEGRADED")
    rolling_expectancy_r: float = Field(default=0.0, description="Rolling trade expectancy in R-multiples")
    rolling_profit_factor: float = Field(default=1.0, description="Rolling profit factor")
    current_drawdown_r: float = Field(default=0.0, description="Current sequential drawdown in R-multiples")
    max_historical_drawdown_r: float = Field(default=0.0, description="Maximum historical drawdown in R-multiples")
    calibration_drift_ece: float = Field(default=0.0, description="Expected Calibration Error drift metric")
    regime_distribution: Dict[str, float] = Field(default_factory=dict, description="Recent market regime breakdown")
    alerts: List[str] = Field(default_factory=list, description="Advisory degradation warning alerts")


TradingDecision.model_rebuild()
