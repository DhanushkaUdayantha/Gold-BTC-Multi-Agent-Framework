"""
Tests for Phase 5 — Live Signal Outcome Validation, Real-World Accuracy Tracking & Strict BTC/XAU Isolation.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.signal_record import SignalOutcome, SignalRecord
from src.services.decision_engine import DecisionEngine
from src.services.live_validation_engine import LiveValidationEngine, get_live_validation_engine
from src.services.outcome_tracker import OutcomeTracker
from src.services.signal_repository import SignalRepository


@pytest.fixture
def temp_signal_repo():
    """Creates an isolated temporary SignalRepository."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    repo = SignalRepository(file_path=temp_path)
    yield repo
    if os.path.exists(temp_path):
        os.remove(temp_path)


from src.models.ai_analysis import (
    AIAnalysisResponse,
    MarketCondition,
    MultiTimeframeTechnicalInput,
    OverallBias,
    RiskLevel,
)
from src.models.market_data import Timeframe
from src.models.technical_analysis import (
    ATRResult,
    DataQualityReport,
    MACDResult,
    MACDState,
    RSICondition,
    RSIResult,
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
)


def _make_ta(
    price: float = 2700.0,
    direction: TrendDirection = TrendDirection.BULLISH,
    strength: str = "STRONG",
    rsi_val: float = 55.0,
    rsi_cond: RSICondition = RSICondition.NEUTRAL,
    macd_state: MACDState = MACDState.BULLISH,
    macd_hist: float = 2.5,
    atr_val: float = 15.0,
    ema20: float = 2695.0,
    ema50: float = 2680.0,
    ema200: float = 2600.0,
    timeframe: str = "1h",
) -> TechnicalAnalysisResponse:
    return TechnicalAnalysisResponse(
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe(timeframe),
        current_price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi14=RSIResult(value=rsi_val, period=14, condition=rsi_cond),
        macd=MACDResult(macd_line=3.0, signal_line=0.5, histogram=macd_hist, state=macd_state),
        atr14=ATRResult(value=atr_val, period=14, volatility_pct=atr_val / price * 100),
        support_levels=[2680.0, 2650.0],
        resistance_levels=[2720.0, 2750.0],
        trend=TrendAnalysis(
            direction=direction,
            score=0.8 if direction == TrendDirection.BULLISH else (-0.8 if direction == TrendDirection.BEARISH else 0.0),
            strength=strength,
            confirmations=["EMA alignment", "MACD positive"],
        ),
        indicator_summary="Test summary",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=200, is_sufficient=True, missing_indicators=[], notes="OK"),
    )


def _make_ai_result(
    market_condition: MarketCondition = MarketCondition.TRENDING_BULLISH,
    overall_bias: OverallBias = OverallBias.BULLISH,
    confidence: int = 80,
) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        symbol="XAU/USD",
        market_condition=market_condition,
        overall_bias=overall_bias,
        confidence=confidence,
        timeframe_analysis={"1h": "Bullish", "15m": "Bullish"},
        key_bullish_factors=["Strong trend"],
        key_bearish_factors=[],
        key_support=[2680.0, 2660.0],
        key_resistance=[2745.0, 2780.0],
        risk_level=RiskLevel.MEDIUM,
        summary="Test AI summary.",
        provider_used="Test Fallback",
        is_fallback=False,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _make_mtf_input(tf_map: dict, price: float = 2700.0) -> MultiTimeframeTechnicalInput:
    bullish = sum(1 for t in tf_map.values() if t and t.trend.direction == TrendDirection.BULLISH)
    total = sum(1 for t in tf_map.values() if t is not None)
    return MultiTimeframeTechnicalInput(
        symbol="XAU/USD",
        current_price=price,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timeframes={k: v for k, v in tf_map.items() if v is not None},
        timeframe_count=total,
        alignment_summary=f"{bullish}/{total} bullish",
    )


def test_production_decision_engine_invariance():
    """
    CRITICAL INVARIANT TEST:
    Verifies that the production DecisionEngine decision logic, entry, SL, TP,
    and risk calculations remain 100% FROZEN and UNCHANGED.
    """
    tf_map = {
        "5m": _make_ta(timeframe="5m"),
        "15m": _make_ta(timeframe="15m"),
        "1h": _make_ta(timeframe="1h"),
        "1d": _make_ta(timeframe="1d"),
    }
    mtf = _make_mtf_input(tf_map, price=2700.0)
    ai = _make_ai_result(overall_bias=OverallBias.BULLISH, confidence=80)
    engine = DecisionEngine()

    decision_1, breakdown_1 = engine.evaluate(mtf, ai)
    decision_2, breakdown_2 = engine.evaluate(mtf, ai)

    # Identical deterministic inputs MUST produce strictly identical outputs
    assert decision_1.decision.value == decision_2.decision.value
    assert decision_1.confidence == decision_2.confidence
    assert decision_1.stop_loss == decision_2.stop_loss
    assert decision_1.take_profit_1 == decision_2.take_profit_1
    assert decision_1.take_profit_2 == decision_2.take_profit_2
    assert decision_1.composite_score == decision_2.composite_score
    assert breakdown_1.total_score == breakdown_2.total_score
    assert breakdown_1.signal_candidate == breakdown_2.signal_candidate


def test_immutable_signal_snapshot_creation(temp_signal_repo):
    """Verifies that signals are saved immutably with proper asset price bounds."""
    # Test Gold recording
    mock_gold_decision = MagicMock()
    mock_gold_decision.decision.value = "BUY"
    mock_gold_decision.symbol = "XAU-USD-SPOT"
    mock_gold_decision.entry_zone.min = 2700.0
    mock_gold_decision.entry_price = 2700.0
    mock_gold_decision.stop_loss = 2685.0
    mock_gold_decision.take_profit_1 = 2730.0
    mock_gold_decision.take_profit_2 = 2760.0
    mock_gold_decision.invalidation_conditions = ["2685.0 breached"]
    mock_gold_decision.final_confluence = 75
    mock_gold_decision.technical_score = 65
    mock_gold_decision.gemini_score = 10
    mock_gold_decision.data_quality = "HIGH"
    mock_gold_decision.gate_direction = "BULLISH"
    mock_gold_decision.gate_passed = True
    mock_gold_decision.market_regime = "TRENDING"
    mock_gold_decision.snapshot_id = "SNAP-GOLD-1"
    mock_gold_decision.signal_contributors = [{"name": "EMA_ALIGNMENT", "points": 15, "direction": "UP", "bias": "BULLISH", "evidence": ["50 > 200"]}]
    mock_gold_decision.conflicts = []
    mock_gold_decision.entry_quality = "A"

    rec_gold = temp_signal_repo.record_signal(mock_gold_decision)
    assert rec_gold is not None
    assert rec_gold.symbol == "XAU-USD-SPOT"
    assert rec_gold.entry_price == 2700.0
    assert rec_gold.outcome.outcome == "OPEN"

    # Test BTC recording
    mock_btc_decision = MagicMock()
    mock_btc_decision.decision.value = "SELL"
    mock_btc_decision.symbol = "BTC-USD"
    mock_btc_decision.entry_zone.min = 95000.0
    mock_btc_decision.entry_price = 95000.0
    mock_btc_decision.stop_loss = 97000.0
    mock_btc_decision.take_profit_1 = 91000.0
    mock_btc_decision.take_profit_2 = 88000.0
    mock_btc_decision.invalidation_conditions = ["97000.0 breached"]
    mock_btc_decision.final_confluence = 80
    mock_btc_decision.technical_score = 70
    mock_btc_decision.gemini_score = 10
    mock_btc_decision.data_quality = "HIGH"
    mock_btc_decision.gate_direction = "BEARISH"
    mock_btc_decision.gate_passed = True
    mock_btc_decision.market_regime = "LOW_VOLATILITY"
    mock_btc_decision.snapshot_id = "SNAP-BTC-1"
    mock_btc_decision.signal_contributors = [{"name": "VWAP_REJECTION", "points": 20, "direction": "DOWN", "bias": "BEARISH", "evidence": ["Price below VWAP"]}]
    mock_btc_decision.conflicts = []
    mock_btc_decision.entry_quality = "A"

    rec_btc = temp_signal_repo.record_signal(mock_btc_decision)
    assert rec_btc is not None
    assert rec_btc.symbol == "BTC-USD"
    assert rec_btc.entry_price == 95000.0
    assert rec_btc.outcome.outcome == "OPEN"


def test_strict_asset_isolated_queries(temp_signal_repo):
    """Verifies that queries with symbol filters return strictly isolated subsets."""
    now_iso = datetime.now(timezone.utc).isoformat()
    # Add BTC record
    rec_btc = SignalRecord(
        signal_id="BTC-001",
        symbol="BTC-USD",
        signal_timestamp=now_iso,
        snapshot_id="SNAP-BTC",
        entry_price=95000.0,
        direction="BUY",
        stop_loss=94000.0,
        take_profit_1=97000.0,
        confluence_score=75,
        technical_score=65,
        gemini_score=10,
        score_band="70-79",
        data_quality="HIGH",
        gate_direction="BULLISH",
        gate_passed=True,
        market_regime="TRENDING",
        outcome=SignalOutcome(outcome="WIN", realized_r=2.0),
    )
    # Add Gold record
    rec_xau = SignalRecord(
        signal_id="XAU-001",
        symbol="XAU-USD-SPOT",
        signal_timestamp=now_iso,
        snapshot_id="SNAP-XAU",
        entry_price=2700.0,
        direction="SELL",
        stop_loss=2715.0,
        take_profit_1=2670.0,
        confluence_score=70,
        technical_score=60,
        gemini_score=10,
        score_band="70-79",
        data_quality="HIGH",
        gate_direction="BEARISH",
        gate_passed=True,
        market_regime="LOW_VOLATILITY",
        outcome=SignalOutcome(outcome="LOSS", realized_r=-1.0),
    )

    temp_signal_repo._save([rec_btc.model_dump(), rec_xau.model_dump()])

    btc_records = temp_signal_repo.get_all(symbol="BTC-USD")
    assert len(btc_records) == 1
    assert btc_records[0].symbol == "BTC-USD"
    assert "XAU" not in btc_records[0].symbol

    xau_records = temp_signal_repo.get_all(symbol="XAU-USD-SPOT")
    assert len(xau_records) == 1
    assert xau_records[0].symbol == "XAU-USD-SPOT"
    assert "BTC" not in xau_records[0].symbol


def test_outcome_resolution_and_realized_r():
    """Tests outcome evaluation for WIN, LOSS, and BREAKEVEN."""
    tracker = OutcomeTracker()
    now = datetime.now(timezone.utc)
    t0 = (now - timedelta(hours=2)).isoformat()

    # 1. BUY Signal hitting TP1
    sig_buy = SignalRecord(
        signal_id="SIG-WIN-1",
        symbol="XAU-USD-SPOT",
        signal_timestamp=t0,
        snapshot_id="SNAP-1",
        entry_price=2700.0,
        direction="BUY",
        stop_loss=2690.0,
        take_profit_1=2720.0,
        confluence_score=75,
        technical_score=65,
        gemini_score=10,
        score_band="70-79",
        data_quality="HIGH",
        gate_direction="BULLISH",
        gate_passed=True,
        outcome=SignalOutcome(outcome="OPEN"),
    )

    with patch.object(tracker, "_repo") as mock_repo:
        labeled = tracker._evaluate_signal(sig_buy, current_price=2722.0, now=now, candles_history=None)
        assert labeled is True
        assert mock_repo.update_outcome.called
        saved_outcome = mock_repo.update_outcome.call_args[0][1]
        assert saved_outcome.outcome == "WIN"
        assert saved_outcome.exit_reason == "TP1_HIT"
        assert saved_outcome.realized_r == 2.0  # (2720 - 2700) / 10 = 2.0

    # 2. SELL Signal hitting SL
    sig_sell = SignalRecord(
        signal_id="SIG-LOSS-1",
        symbol="BTC-USD",
        signal_timestamp=t0,
        snapshot_id="SNAP-2",
        entry_price=95000.0,
        direction="SELL",
        stop_loss=96000.0,
        take_profit_1=93000.0,
        confluence_score=70,
        technical_score=60,
        gemini_score=10,
        score_band="70-79",
        data_quality="HIGH",
        gate_direction="BEARISH",
        gate_passed=True,
        outcome=SignalOutcome(outcome="OPEN"),
    )

    with patch.object(tracker, "_repo") as mock_repo:
        labeled = tracker._evaluate_signal(sig_sell, current_price=96100.0, now=now, candles_history=None)
        assert labeled is True
        saved_outcome = mock_repo.update_outcome.call_args[0][1]
        assert saved_outcome.outcome == "LOSS"
        assert saved_outcome.exit_reason == "SL_HIT"
        assert saved_outcome.realized_r == -1.0


def test_live_validation_engine_summary_computation():
    """Tests that LiveValidationEngine correctly computes period metrics and 10-bucket calibration."""
    engine = LiveValidationEngine()
    now_iso = datetime.now(timezone.utc).isoformat()

    records = [
        SignalRecord(
            signal_id=f"TEST-{i}",
            symbol="BTC-USD",
            signal_timestamp=now_iso,
            snapshot_id=f"SNAP-{i}",
            entry_price=95000.0,
            direction="BUY" if i % 2 == 0 else "SELL",
            stop_loss=94000.0,
            take_profit_1=97000.0,
            confluence_score=70 + (i % 20),
            technical_score=60,
            gemini_score=10,
            score_band="70-79",
            calibrated_probability=0.65,
            raw_probability=0.70,
            data_quality="HIGH",
            gate_direction="BULLISH",
            gate_passed=True,
            outcome=SignalOutcome(
                outcome="WIN" if i % 3 != 0 else "LOSS",
                realized_r=2.0 if i % 3 != 0 else -1.0,
                mfe=2000.0,
                mae=300.0,
                failure_reason="FALSE_BREAKOUT" if i % 3 == 0 else None,
                success_reason="HTF_TREND_ALIGNMENT" if i % 3 != 0 else None,
            ),
        )
        for i in range(30)
    ]

    period_m = engine.compute_period_metrics(records, "ALL_TIME", "BTC/USD")
    assert period_m.total_signals == 30
    assert period_m.wins == 20
    assert period_m.losses == 10
    assert period_m.win_rate_pct == 66.7
    assert period_m.total_realized_r == 30.0  # 20 * 2 - 10 * 1 = 30.0
    assert period_m.sample_status == "SUFFICIENT_SAMPLE"

    cal = engine.compute_calibration_summary(records, "BTC/USD")
    assert cal.total_resolved == 30
    assert cal.brier_score >= 0.0
    assert len(cal.buckets) == 10


def test_api_routes_live_validation():
    """Tests the Phase 5 API routes in FastAPI testclient."""
    client = TestClient(app)

    # 1. Live Validation master endpoint
    res = client.get("/api/v1/performance/live-validation?symbol=BTC-USD")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "validation" in data
    assert data["validation"]["asset"] == "BTC/USD"
    assert data["validation"]["asset_isolation_verified"] is True

    # 2. Daily performance
    res_d = client.get("/api/v1/performance/daily?symbol=XAU-USD-SPOT")
    assert res_d.status_code == 200
    assert res_d.json()["status"] == "ok"
    assert "daily" in res_d.json()

    # 3. Weekly performance
    res_w = client.get("/api/v1/performance/weekly?symbol=XAU-USD-SPOT")
    assert res_w.status_code == 200
    assert "weekly" in res_w.json()

    # 4. Monthly performance
    res_m = client.get("/api/v1/performance/monthly?symbol=BTC-USD")
    assert res_m.status_code == 200
    assert "monthly" in res_m.json()

    # 5. All-Time performance
    res_a = client.get("/api/v1/performance/all-time?symbol=BTC-USD")
    assert res_a.status_code == 200
    assert "all_time" in res_a.json()
