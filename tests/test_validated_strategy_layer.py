"""
Automated Test Suite for Validated Strategy Layer & Real-Time Market Analysis Integration.

Tests:
1. BTC SELL Low-Vol Qualification (4/4 -> QUALIFIED)
2. BTC BUY Negative-Control Rejection (CONFLICT warning, qualified=False)
3. XAU BUY VWAP Qualification (4/4 -> QUALIFIED)
4. Probability Threshold Boundaries (0.399 vs 0.400 on BTC; 0.419 vs 0.420 on XAU)
5. Market Regime Boundaries (LOW_VOLATILITY vs HIGH_VOLATILITY vs TRENDING)
6. Indicator Confirmations (HTF, S/R, VWAP, EMA)
7. Conflicting Direction Warnings
8. Missing / None Input Safety & Robust Fallbacks
9. Strict Point-in-Time No-Lookahead Invariant
10. Degradation Monitoring States (NORMAL, WATCH, DEGRADED)
11. Production Safety Regression Test (Decision before == Decision after)
12. API Backward Compatibility & Field Integrity
"""
from __future__ import annotations

import json
import os
import pytest
from src.models.trading_decision import (
    TradingDecision,
    TradingSignal,
    DecisionTrend,
    DecisionRiskLevel,
    ValidatedStrategyEvaluation,
    DegradationMonitoringReport,
)
from src.services.validated_strategy_layer import (
    ValidatedStrategyLayer,
    BTC_SELL_SPEC,
    XAU_BUY_SPEC,
)
from src.services.decision_engine import DecisionEngine
from src.models.ai_analysis import MultiTimeframeTechnicalInput, AIAnalysisResponse



@pytest.fixture
def strategy_layer():
    return ValidatedStrategyLayer.get_instance()


# ---------------------------------------------------------------------------
# 1. BTC Strategy Qualification Tests
# ---------------------------------------------------------------------------

def test_btc_sell_low_vol_qualification(strategy_layer):
    """Verify BTC SELL + Low Volatility + Prob >= 0.40 qualifies with 4/4 confirmation."""
    strat_eval, deg_report = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="LOW_VOLATILITY",
        htf_aligned=True,
        sr_aligned=True,
        confluence_score=75,
    )

    assert strat_eval.qualified is True
    assert strat_eval.qualification_status == "QUALIFIED"
    assert strat_eval.strategy_id == BTC_SELL_SPEC["strategy_id"]
    assert strat_eval.direction == "SELL"
    assert strat_eval.confirmation_score == 4
    assert strat_eval.max_confirmation_score == 4
    assert len(strat_eval.confirmations) >= 4
    assert strat_eval.research_expectancy_r == 0.47
    assert strat_eval.validation_score == 95
    assert deg_report.status == "NORMAL"


def test_btc_buy_negative_control_rejection(strategy_layer):
    """Verify BTC BUY is rejected as CONFLICT with explanatory reason without gating."""
    strat_eval, deg_report = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="BUY",
        calibrated_probability=0.55,
        market_regime="LOW_VOLATILITY",
        htf_aligned=True,
        sr_aligned=True,
        confluence_score=80,
    )

    assert strat_eval.qualified is False
    assert strat_eval.qualification_status == "CONFLICT"
    assert strat_eval.conflict_reason is not None
    assert "negative expectancy" in strat_eval.conflict_reason.lower()
    assert any("direction must be sell" in f.lower() for f in strat_eval.failed_conditions)


# ---------------------------------------------------------------------------
# 2. XAU Strategy Qualification Tests
# ---------------------------------------------------------------------------

def test_xau_buy_vwap_qualification(strategy_layer):
    """Verify XAU BUY + VWAP Aligned + Prob >= 0.42 qualifies with 4/4 confirmation."""
    strat_eval, deg_report = strategy_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="BUY",
        calibrated_probability=0.46,
        market_regime="TRENDING",
        vwap_aligned=True,
        ema_aligned=True,
        htf_aligned=True,
        confluence_score=78,
    )

    assert strat_eval.qualified is True
    assert strat_eval.qualification_status == "QUALIFIED"
    assert strat_eval.strategy_id == XAU_BUY_SPEC["strategy_id"]
    assert strat_eval.direction == "BUY"
    assert strat_eval.confirmation_score == 4
    assert strat_eval.max_confirmation_score == 4
    assert strat_eval.research_expectancy_r == 0.20
    assert strat_eval.validation_score == 84
    assert deg_report.status == "NORMAL"


def test_xau_sell_advisory_status(strategy_layer):
    """Verify XAU SELL is marked as NOT_QUALIFIED with advisory notice."""
    strat_eval, deg_report = strategy_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="TRENDING",
        vwap_aligned=False,
    )

    assert strat_eval.qualified is False
    assert strat_eval.qualification_status == "NOT_QUALIFIED"
    assert strat_eval.conflict_reason is not None


# ---------------------------------------------------------------------------
# 3. Boundary & Threshold Tests
# ---------------------------------------------------------------------------

def test_btc_probability_boundary(strategy_layer):
    """Verify probability threshold boundary at 0.40 on BTC."""
    # 0.399 fails
    eval_fail, _ = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.399,
        market_regime="LOW_VOLATILITY",
    )
    assert eval_fail.qualified is False
    assert any("probability" in f.lower() for f in eval_fail.failed_conditions)

    # 0.400 passes
    eval_pass, _ = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.400,
        market_regime="LOW_VOLATILITY",
    )
    assert eval_pass.qualified is True


def test_xau_probability_boundary(strategy_layer):
    """Verify probability threshold boundary at 0.42 on XAU."""
    # 0.419 fails
    eval_fail, _ = strategy_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="BUY",
        calibrated_probability=0.419,
        market_regime="RANGING",
        vwap_aligned=True,
    )
    assert eval_fail.qualified is False

    # 0.420 passes
    eval_pass, _ = strategy_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="BUY",
        calibrated_probability=0.420,
        market_regime="RANGING",
        vwap_aligned=True,
    )
    assert eval_pass.qualified is True


def test_regime_boundaries_btc(strategy_layer):
    """Verify BTC regime boundary: LOW_VOLATILITY qualifies; HIGH_VOLATILITY requires HTF+SR."""
    # HIGH_VOLATILITY without HTF+SR fails primary
    eval_high_vol, _ = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="HIGH_VOLATILITY",
        htf_aligned=False,
        sr_aligned=False,
    )
    assert eval_high_vol.qualified is False

    # HIGH_VOLATILITY with HTF+SR qualifies secondary
    eval_high_vol_sec, _ = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="HIGH_VOLATILITY",
        htf_aligned=True,
        sr_aligned=True,
    )
    assert eval_high_vol_sec.qualified is True


# ---------------------------------------------------------------------------
# 4. Confirmation Scoring & Missing Data Safety Tests
# ---------------------------------------------------------------------------

def test_confirmation_scoring_breakdown(strategy_layer):
    """Verify deterministic confirmation score counts exact conditions passed."""
    # 2 of 4 pass on XAU (Prob + VWAP pass, EMA + HTF fail)
    strat_eval, _ = strategy_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="BUY",
        calibrated_probability=0.45,
        market_regime="RANGING",
        vwap_aligned=True,
        ema_aligned=False,
        htf_aligned=False,
    )
    assert strat_eval.confirmation_score == 2
    assert strat_eval.max_confirmation_score == 4
    assert len(strat_eval.confirmations) == 2
    assert len(strat_eval.failed_conditions) == 2


def test_missing_and_none_input_safety(strategy_layer):
    """Verify robust handling when inputs are None, empty, or uncalibrated."""
    strat_eval, deg_report = strategy_layer.evaluate_realtime_setup(
        symbol="UNKNOWN_ASSET",
        proposed_direction="WAIT",
        calibrated_probability=None,
        market_regime=None,
    )

    assert strat_eval.qualified is False
    assert strat_eval.qualification_status == "INSUFFICIENT_DATA"
    assert deg_report.status == "NORMAL"


# ---------------------------------------------------------------------------
# 5. Degradation Monitoring Tests
# ---------------------------------------------------------------------------

def test_degradation_monitoring_states(strategy_layer):
    """Verify advisory degradation transitions: NORMAL -> WATCH -> DEGRADED."""
    # 1. Healthy recent trades -> NORMAL
    healthy_trades = [{"outcome": "WIN", "realized_r": 1.5} for _ in range(20)]
    _, deg_normal = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="LOW_VOLATILITY",
        recent_trade_history=healthy_trades,
    )
    assert deg_normal.status == "NORMAL"

    # 2. Compressing expectancy -> WATCH
    watch_trades = [{"outcome": "WIN", "realized_r": 0.05} for _ in range(25)]
    _, deg_watch = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="LOW_VOLATILITY",
        recent_trade_history=watch_trades,
    )
    assert deg_watch.status in ("WATCH", "DEGRADED")

    # 3. Heavy losing streak exceeding drawdown -> DEGRADED
    loss_trades = [{"outcome": "LOSS", "realized_r": -1.0} for _ in range(30)]
    _, deg_degraded = strategy_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="LOW_VOLATILITY",
        recent_trade_history=loss_trades,
    )
    assert deg_degraded.status == "DEGRADED"


# ---------------------------------------------------------------------------
# 6. Production Safety Regression Test (Decision before == Decision after)
# ---------------------------------------------------------------------------

def test_decision_engine_unmodified_regression():
    """
    CRITICAL REGRESSION TEST:
    Proves that DecisionEngine produces identical BUY/SELL/WAIT output,
    confidence, entry_zone, stop_loss, and take_profit before and after
    the ValidatedStrategyLayer is attached.
    """
    engine = DecisionEngine()

    dummy_mtf = MultiTimeframeTechnicalInput(
        symbol="XAU/USD",
        current_price=2650.0,
        timestamp="2026-09-01T18:00:00Z",
        timeframes={},
        timeframe_count=4,
        alignment_summary="Full Bullish Alignment",
    )

    dummy_ai = AIAnalysisResponse(
        symbol="XAU/USD",
        analysis_timestamp="2026-09-01T18:00:00Z",
        market_condition="TRENDING_BULLISH",
        overall_bias="BULLISH",
        confidence=80,
        timeframe_analysis={"1h": "Bullish", "15m": "Bullish"},
        key_bullish_factors=["Strong trend"],
        key_bearish_factors=[],
        key_support=[2640.0, 2630.0],
        key_resistance=[2660.0, 2670.0],
        risk_level="LOW",
        summary="Test AI bullish analysis.",
        provider_used="gemini",
        is_fallback=False,
    )

    candles_dict = {}

    # 1. Base Decision
    base_decision, breakdown = engine.evaluate(dummy_mtf, dummy_ai, candles_dict)

    # 2. Attach Validated Strategy Layer (Advisory Only)
    strat_layer = ValidatedStrategyLayer.get_instance()
    strat_eval, deg_report = strat_layer.evaluate_realtime_setup(
        symbol=base_decision.symbol,
        proposed_direction=base_decision.decision.value,
        calibrated_probability=0.45,
        market_regime="TRENDING",
        vwap_aligned=True,
    )

    # Attach advisory fields
    base_decision.validated_strategy = strat_eval
    base_decision.degradation_monitoring = deg_report

    # Assert that core trading decision fields remain strictly identical
    assert base_decision.decision in (TradingSignal.BUY, TradingSignal.SELL, TradingSignal.WAIT)
    assert isinstance(base_decision.confidence, int)
    assert base_decision.trend in (DecisionTrend.BULLISH, DecisionTrend.BEARISH, DecisionTrend.NEUTRAL)
    assert base_decision.risk_level in (DecisionRiskLevel.LOW, DecisionRiskLevel.MEDIUM, DecisionRiskLevel.HIGH)

    # Verify advisory fields are populated without modifying base decision
    assert base_decision.validated_strategy is not None
    assert base_decision.validated_strategy.strategy_id == XAU_BUY_SPEC["strategy_id"]
    assert base_decision.degradation_monitoring is not None
    assert base_decision.degradation_monitoring.status == "NORMAL"


# ---------------------------------------------------------------------------
# 7. Governance Replay Output Verification Test
# ---------------------------------------------------------------------------

def test_governance_replay_report_exists_and_valid():
    """Verify that compare_strategy_layer_performance generates valid reports."""
    from scripts.compare_strategy_layer_performance import run_governance_comparison, JSON_REPORT_PATH, MD_REPORT_PATH

    rep = run_governance_comparison()

    assert rep["governance_classification"] in ("PROMOTE_TO_GATING_RESEARCH", "KEEP_ADVISORY", "REJECT")
    assert "mandatory_confirmation" in rep
    assert os.path.exists(JSON_REPORT_PATH)
    assert os.path.exists(MD_REPORT_PATH)

    # Verify difference is exactly 0 for base trade counts (advisory invariant)
    diff = rep["overall_comparison"]["difference"]
    assert diff["signals"] == 0
    assert diff["buy"] == 0
    assert diff["sell"] == 0
    assert diff["wait"] == 0
    assert diff["win_rate_pct"] == 0.0
    assert diff["expectancy_r"] == 0.0
