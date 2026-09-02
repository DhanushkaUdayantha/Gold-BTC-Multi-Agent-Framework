"""
Data models for the Empirical Backtesting & Probability Calibration layer.

These are ADDITIVE models — they do not replace or modify any existing model.
All existing TradingDecision / ConfluenceResult models remain 100% unchanged.

DISCLAIMER: All performance metrics are based on simulated advisory signals.
No real trades are executed. Past performance does not guarantee future results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Signal Outcome
# ---------------------------------------------------------------------------

class SignalOutcome(BaseModel):
    """
    Labels the empirical result of a historical SignalRecord.
    Populated ONLY from price data timestamped AFTER signal_timestamp.
    """
    outcome: str = Field(
        description="WIN | LOSS | BREAKEVEN | EXPIRED | INVALID | OPEN"
    )
    outcome_timestamp: Optional[str] = Field(
        default=None, description="ISO 8601 UTC when outcome was determined"
    )
    exit_price: Optional[float] = Field(
        default=None, description="Price at which the outcome was resolved"
    )
    realized_r: Optional[float] = Field(
        default=None,
        description=(
            "Realized R-multiple. Positive = profit in units of initial risk. "
            "WIN → realized_r ≈ +RR, LOSS → realized_r ≈ -1.0"
        ),
    )
    mfe: Optional[float] = Field(
        default=None,
        description="Maximum Favorable Excursion — best unrealized profit (price units)",
    )
    mae: Optional[float] = Field(
        default=None,
        description="Maximum Adverse Excursion — worst unrealized loss (price units)",
    )
    max_r: Optional[float] = Field(
        default=None,
        description="Maximum R achieved before resolution (MFE / initial risk)",
    )
    time_to_outcome_minutes: Optional[int] = Field(
        default=None, description="Minutes from signal_timestamp to outcome"
    )
    bars_to_resolution: Optional[int] = Field(
        default=None, description="Number of candles from entry to resolution"
    )
    exit_reason: Optional[str] = Field(
        default=None, description="TP1_HIT | TP2_HIT | SL_HIT | EXPIRED | BREAKEVEN | INVALID"
    )
    success_reason: Optional[str] = Field(
        default=None, description="Attributed primary reason for winning trade"
    )
    failure_reason: Optional[str] = Field(
        default=None, description="Attributed primary failure reason"
    )
    failure_category: Optional[str] = Field(
        default=None, description="Detailed failure taxonomy"
    )
    transaction_cost_included: bool = Field(
        default=False,
        description="True if spread/commission were deducted from realized_r",
    )
    spread_at_entry: Optional[float] = Field(
        default=None, description="Bid-ask spread captured at signal generation time"
    )
    note: Optional[str] = Field(
        default=None, description="Human-readable note (e.g. 'Expired without SL/TP hit')"
    )


# ---------------------------------------------------------------------------
# Signal Record (immutable after creation)
# ---------------------------------------------------------------------------

class SignalRecord(BaseModel):
    """
    Immutable record created for each actionable BUY/SELL signal.
    All fields are sealed at signal-generation time.
    outcome is None until labeled from future price data.
    """
    signal_id: str = Field(description="UUID4 — unique identifier for this signal")
    symbol: str
    signal_timestamp: str = Field(
        description="ISO 8601 UTC — sealed at signal generation. Acts as look-ahead barrier."
    )
    snapshot_id: str = Field(description="Confluence snapshot ID that produced this signal")

    # ---- Entry / Risk levels (from existing DecisionEngine — no duplication) ----
    entry_price: float
    direction: str = Field(description="BUY | SELL")
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    invalidation_level: Optional[Any] = None

    # ---- Confluence scores & Probabilities (sealed at generation) ----
    confluence_score: int = Field(description="0–100 total confluence score")
    technical_score: int = Field(description="0–90 technical-only score")
    gemini_score: int = Field(description="0–10 Gemini AI score")
    score_band: str = Field(description="0-49 | 50-59 | 60-69 | 70-79 | 80-89 | 90-100")
    raw_probability: Optional[float] = Field(default=None, description="Raw model probability 0.0–1.0")
    calibrated_probability: Optional[float] = Field(default=None, description="Calibrated probability 0.0–1.0")
    signal_strength: Optional[int] = Field(default=None, description="Signal strength 0–100")
    quality_score: Optional[float] = Field(default=None, description="Signal quality score 0–100")
    setup_grade: Optional[str] = Field(default=None, description="A | B | C | MANUAL")

    # ---- Per-contributor data (sealed at generation) ----
    contributor_scores: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of contributor name → score at signal generation",
    )
    contributor_directions: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of contributor name → UP/DOWN/UNCHANGED",
    )
    contributor_biases: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of contributor name → BULLISH/BEARISH/NEUTRAL/UNAVAILABLE",
    )

    # ---- Signal context (sealed at generation) ----
    data_quality: str = Field(description="HIGH | MEDIUM | LOW")
    gate_direction: str = Field(description="BULLISH | BEARISH | NONE")
    gate_passed: bool = False
    market_regime: str = Field(default="UNCLEAR")
    market_session: Optional[str] = Field(default=None, description="ASIA | LONDON | NEW_YORK | OVERLAP")
    mtf_alignment: Optional[str] = Field(default=None, description="MTF alignment summary")
    timeframe: Optional[str] = Field(default="15m", description="Primary signal timeframe")
    strategy_evidence: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    entry_quality: str = Field(default="WAIT")

    # ---- Tracking fields (updated as outcome is observed) ----
    current_mfe: Optional[float] = Field(
        default=None, description="Running MFE updated each price observation"
    )
    current_mae: Optional[float] = Field(
        default=None, description="Running MAE updated each price observation"
    )

    # ---- Outcome (None until labeled — never look-ahead) ----
    outcome: Optional[SignalOutcome] = None


def _score_band(score: int) -> str:
    """Map a 0–100 confluence score to its performance band string."""
    if score < 50:
        return "0-49"
    elif score < 60:
        return "50-59"
    elif score < 70:
        return "60-69"
    elif score < 80:
        return "70-79"
    elif score < 90:
        return "80-89"
    return "90-100"


# ---------------------------------------------------------------------------
# Performance statistics sub-models
# ---------------------------------------------------------------------------

class OverallStats(BaseModel):
    total_signals: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    open_signals: int = 0
    expired_signals: int = 0
    invalid_signals: int = 0
    win_rate: Optional[float] = None          # None if < 10 completed
    average_win_r: Optional[float] = None
    average_loss_r: Optional[float] = None
    average_r: Optional[float] = None
    expectancy: Optional[float] = None        # (WR * avgWin) - (LR * avgLoss)
    profit_factor: Optional[float] = None
    max_drawdown_r: Optional[float] = None
    average_mfe: Optional[float] = None
    average_mae: Optional[float] = None
    note: str = ""


class ScoreBandStats(BaseModel):
    band: str
    sample_size: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: Optional[float] = None
    average_r: Optional[float] = None
    expectancy: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown_r: Optional[float] = None
    note: str = ""


class StrategyStats(BaseModel):
    strategy_name: str
    total_signals: int = 0          # signals where this contributor was active (score > 0)
    wins: int = 0
    losses: int = 0
    win_rate: Optional[float] = None
    average_r: Optional[float] = None
    expectancy: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown_r: Optional[float] = None
    average_mfe: Optional[float] = None
    average_mae: Optional[float] = None
    note: str = ""


class GeminiPerformanceStats(BaseModel):
    """Tracks Gemini AI contributor independently for ablation analysis."""
    total_gemini_signals: int = 0       # signals where gemini_score > 0
    gemini_direction_accuracy: Optional[float] = None
    gemini_agreement_rate: Optional[float] = None  # % agreement with technical signal
    gemini_conflict_rate: Optional[float] = None

    # Ablation: compare WITH vs WITHOUT Gemini contribution
    ablation_with_gemini_win_rate: Optional[float] = None
    ablation_without_gemini_win_rate: Optional[float] = None
    ablation_with_gemini_expectancy: Optional[float] = None
    ablation_without_gemini_expectancy: Optional[float] = None
    ablation_sample_size: int = 0
    ablation_note: str = "Ablation requires ≥50 completed signals"

    gemini_improves_performance: Optional[bool] = None  # None until proven
    note: str = "Gemini performance tracking requires completed signal outcomes"


class CalibrationResult(BaseModel):
    """Output of the probability calibrator."""
    calibration_status: str = Field(
        description=(
            "INSUFFICIENT_DATA | EXPLORATORY | VALID | PREFERRED | UNRELIABLE"
        )
    )
    sample_size: int = 0
    training_size: int = 0
    validation_size: int = 0

    # Calibrated probability for a HYPOTHETICAL signal at the current confluence score
    # None unless status is EXPLORATORY or better
    calibrated_probability: Optional[float] = None
    calibrated_for_score: Optional[int] = None   # what score was used

    # Quality metrics
    brier_score: Optional[float] = None          # lower = better (0.25 = no-skill)
    oos_accuracy: Optional[float] = None
    calibration_error: Optional[float] = None    # mean absolute calibration error
    in_sample_accuracy: Optional[float] = None

    method_used: str = "N/A"                     # isotonic | logistic | N/A
    split_type: str = "chronological_70_30"
    walk_forward_folds: int = 0
    reliability_note: str = ""
    disclaimer: str = (
        "Calibrated probability is estimated from historical advisory signals. "
        "It is NOT a guarantee. Sample size severely limits reliability at low counts."
    )


class DataIntegrityIssue(BaseModel):
    signal_id: str
    issue_type: str    # DUPLICATE | IMPOSSIBLE_PRICE | FUTURE_TIMESTAMP | INVALID_R | MISSING_OUTCOME
    detail: str


class PerformanceReport(BaseModel):
    """
    Full empirical performance report.
    Calibrated probability is shown separately from the confluence score.
    The confluence score is NEVER presented as a probability.
    """
    generated_at: str
    symbol: str

    total_completed: int = 0
    total_open: int = 0
    total_expired: int = 0
    total_invalid: int = 0
    total_signals_recorded: int = 0

    overall: OverallStats
    by_score_band: List[ScoreBandStats] = Field(default_factory=list)
    by_strategy: List[StrategyStats] = Field(default_factory=list)
    calibration: CalibrationResult
    gemini_analysis: GeminiPerformanceStats

    data_integrity_issues: List[str] = Field(default_factory=list)
    transaction_costs_included: bool = False
    transaction_cost_note: str = "Transaction costs not included"

    regime_analysis_available: bool = False
    correlation_analysis: Dict[str, Any] = Field(default_factory=dict)

    disclaimer: str = (
        "ADVISORY ONLY. All performance metrics are computed from simulated advisory signals. "
        "No real trades were executed. Past performance does not guarantee future results. "
        "Calibrated probabilities require large sample sizes to be reliable."
    )
