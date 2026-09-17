"""
Deterministic Invariant Tests: Percentage Truth & Decision Semantics.
Verifies:
- Any WAIT state (conflict, weak directional conviction, direction gate failure) MUST have percentage=None.
- Directional signals (BUY/SELL) have percentage >= 20 and overall_evidence_score >= 20.
- Zero fake 50% or directional padding on indeterminate market states.
"""
import pytest
from src.services.signal_aggregator import (
    SignalAggregator, DIRECTIONAL_THRESHOLD, CONFLICT_WEIGHT_THRESHOLD
)
from src.models.trading_decision import (
    NowMarketSignal, HistoricalMarketSignal, ValidatedStrategyEvaluation, OverallTradingSignal
)

def test_conflict_wait_enforces_percentage_none():
    """Verify strong directional conflict forces WAIT with percentage=None and conflict_detected=True."""
    # Bullish Now Market vs Bearish Historical Evidence
    now_sig = NowMarketSignal(signal="BUY", percentage=85, strength="STRONG")
    hist_sig = HistoricalMarketSignal(
        signal="SELL",
        calibrated_probability=0.75,
        status="ACTIVE",
        sample_size=120,
        historical_ev=0.35,
        profit_factor=1.65,
    )
    
    sig = SignalAggregator.aggregate(
        symbol="XAU/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.50,
        ml_predicted_class=None,
        validated_strategy=None
    )
    
    assert sig.signal == "WAIT"
    assert sig.conflict_detected is True
    assert sig.percentage is None
    assert sig.overall_evidence_score is None
    assert sig.strength == "CONFLICT"

def test_sub_threshold_weak_conviction_enforces_percentage_none():
    """Verify weak directional score below DIRECTIONAL_THRESHOLD enforces WAIT with percentage=None."""
    # Very weak technical percentage (10%), below 20.0 directional threshold
    now_sig = NowMarketSignal(signal="BUY", percentage=10, strength="WEAK")
    
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=None,
        ml_probability=None,
        validated_strategy=None
    )
    
    assert sig.signal == "WAIT"
    assert sig.percentage is None
    assert sig.overall_evidence_score is not None
    assert sig.overall_evidence_score < DIRECTIONAL_THRESHOLD

def test_directional_conviction_has_valid_percentage():
    """Verify valid BUY signal above threshold produces truthful non-zero percentage matching net score."""
    now_sig = NowMarketSignal(signal="BUY", percentage=80, strength="STRONG")
    hist_sig = HistoricalMarketSignal(
        signal="BUY",
        calibrated_probability=0.75,
        status="ACTIVE",
        sample_size=150,
        historical_ev=0.40,
        profit_factor=1.75,
    )
    strat = ValidatedStrategyEvaluation(
        strategy_id="STRAT-BTC-v2.1",
        qualified=True,
        direction="BUY",
        validation_score=85,
        degradation_status="NORMAL",
    )
    
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.72,
        ml_predicted_class=1,
        validated_strategy=strat
    )
    
    assert sig.signal == "BUY"
    assert sig.conflict_detected is False
    assert sig.percentage is not None
    assert sig.percentage >= DIRECTIONAL_THRESHOLD
    assert sig.percentage == sig.overall_evidence_score
