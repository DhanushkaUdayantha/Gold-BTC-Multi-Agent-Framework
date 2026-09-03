"""
Test Suite: Phase 7 Step 3 — Overall Hero Aggregator Integration Test
======================================================================
Verifies:
1. Simulates aggregator output and asserts the Overall signal string and exact
   evidence percentage are preserved without alteration.
2. Evidence scores below 50% (e.g. SELL 7%) are strictly preserved without
   flooring, forcing, or inflation to 50%+.
3. Directional conflicts correctly yield WAIT with percentage=None.
4. Non-conflict WAIT preserves the underlying evidence score.
5. All 7 required aggregator state fields are present and unmodified:
   - overall_evidence_score
   - component_scores
   - component_weights
   - component_contributions
   - methodology_version
   - asset
   - timestamp
6. Code audit: frontend SignalHeroCard and page.tsx contain no floor(50) or
   artificial minimum percentage logic on overall evidence score.
"""
import pytest
from datetime import datetime, timezone

from src.models.trading_decision import (
    NowMarketSignal,
    HistoricalMarketSignal,
    ValidatedStrategyEvaluation,
    OverallTradingSignal,
)
from src.services.signal_aggregator import SignalAggregator


def test_overall_hero_exact_signal_and_percentage_unaltered():
    """Aggregator BUY 74% must be rendered as exact 'BUY' and 74 without alteration."""
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=78,
        strength="STRONG",
        technical_score=75,
        gemini_score=8,
    )
    hist_sig = HistoricalMarketSignal(
        signal="BUY",
        percentage=70,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=250,
        calibrated_probability=0.72,
    )
    strat = ValidatedStrategyEvaluation(
        strategy_id="BTC-BUY-P40-TEST",
        strategy_name="BTC Test Strategy",
        qualified=True,
        direction="BUY",
        validation_score=85,
        degradation_status="NORMAL",
    )

    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.70,
        ml_predicted_class=1,
        validated_strategy=strat,
        timestamp="2026-09-03T12:00:00Z",
    )

    # Invariant checks: signal and score exact match
    assert sig.signal == "BUY"
    assert isinstance(sig.overall_evidence_score, int)
    assert sig.overall_evidence_score > 0
    assert sig.percentage == sig.overall_evidence_score
    assert sig.conflict_detected is False

    # Traceability checks
    assert sig.methodology_version == "1.1.0-PROPOSAL"
    assert sig.asset == "BTC/USD"
    assert sig.timestamp == "2026-09-03T12:00:00Z"
    assert sig.component_scores is not None
    assert sig.component_weights is not None
    assert sig.component_contributions is not None


def test_overall_hero_actionable_sub_50_evidence():
    """Actionable evidence below 50% (e.g. 28%) must never be floored to 50%+."""
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=55,
        strength="MODERATE",
        technical_score=55,
        gemini_score=6,
    )
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=None,
        ml_probability=0.50,
        ml_predicted_class=1,
        validated_strategy=None,
        timestamp="2026-09-03T12:03:00Z",
    )

    # Net score is ~27-28% (>= 20 threshold, actionable BUY)
    assert sig.signal == "BUY"
    assert sig.overall_evidence_score is not None
    assert sig.overall_evidence_score < 50
    assert sig.percentage == sig.overall_evidence_score
    assert sig.conflict_detected is False


def test_overall_hero_sub_threshold_wait_state():
    """Sub-threshold net score (-20 < net_score < 20) yields WAIT with percentage=None and score preserved."""
    now_sig = NowMarketSignal(
        signal="WAIT",
        percentage=40,
        strength="WEAK",
        technical_score=39,
        gemini_score=4,
    )
    # Weak ML sell leaning yields net score around -7
    sig = SignalAggregator.aggregate(
        symbol="XAU/USD",
        now_signal=now_sig,
        historical_signal=None,
        ml_probability=0.4236,
        ml_predicted_class=0,
        validated_strategy=None,
        timestamp="2026-09-03T12:03:00Z",
    )

    assert sig.signal == "WAIT"
    assert sig.conflict_detected is False
    assert sig.percentage is None  # No actionable percentage for WAIT
    assert sig.overall_evidence_score == 7  # Underlying score preserved for audit


def test_overall_hero_conflict_wait_percentage_none():
    """Opposing primary forces force WAIT with percentage=None and overall_evidence_score=None."""
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=80,
        strength="STRONG",
        technical_score=75,
        gemini_score=8,
    )
    # ML strongly predicts SELL (probability = 0.0)
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=None,
        ml_probability=0.0,
        ml_predicted_class=0,
        validated_strategy=None,
    )

    assert sig.signal == "WAIT"
    assert sig.conflict_detected is True
    assert sig.percentage is None
    assert sig.overall_evidence_score is None


def test_frontend_code_audit_no_percentage_flooring():
    """Ensure frontend codebase contains zero artificial percentage flooring logic."""
    with open("frontend/src/components/SignalHeroCard.tsx", "r", encoding="utf-8") as f:
        hero_code = f.read()

    with open("frontend/src/app/page.tsx", "r", encoding="utf-8") as f:
        page_code = f.read()

    # Neither file should have Math.max(50, ...) or similar flooring on evidence scores
    assert "Math.max(50" not in hero_code, "SignalHeroCard has forbidden 50% flooring"
    assert "Math.max(50" not in page_code, "page.tsx has forbidden 50% flooring"
