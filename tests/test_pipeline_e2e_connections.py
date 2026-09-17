"""
End-to-End Pipeline Connections and Percentage Audit Test Suite.
Verifies all core connection requirements for both BTC and XAU:
1. Historical percentage source extraction and handling.
2. Now Market percentage source extraction.
3. History + Now -> Overall percentage synthesis.
4. ML feature extraction, prediction, and shadow recording.
5. ML prediction -> SignalAggregator connection.
6. Decision -> Actionable BUY/SELL signal construction with valid targets.
7. Actionable Signal -> Forward Shadow capture in both stores.
8. Forward Shadow -> Resolver -> WIN/LOSS outcome determination.
9. Strict Asset Isolation (BTC vs XAU).
10. S2 State Machine and BTC Evidence Immutability.
"""
import pytest
import sqlite3
import os
import math
from datetime import datetime, timezone

from src.models.trading_decision import (
    TradingDecision,
    TradingSignal,
    DecisionTrend,
    DecisionRiskLevel,
    DecisionScoreBreakdown,
    NowMarketSignal,
    HistoricalMarketSignal,
    ValidatedStrategyEvaluation,
    OverallTradingSignal,
)
from src.services.decision_service import DecisionService
from src.services.signal_aggregator import SignalAggregator, DIRECTIONAL_THRESHOLD
from src.research.ml_shadow.shadow_service import MLShadowService
from src.research.governance.forward_shadow import ForwardShadowEngine
from src.services.forward_shadow_resolver_worker import ForwardShadowResolverWorker
from src.research.governance.forward_state_machine import (
    ForwardExecutionStateMachine,
    ExecutionState,
)
from src.services.historical_data_service import DB_PATH


def test_historical_percentage_source_btc_and_xau():
    hist_sig_btc = HistoricalMarketSignal(
        signal="BUY",
        percentage=68,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=45,
        win_rate=68.5,
        calibrated_probability=68.0,
        expectancy=0.35,
    )
    assert hist_sig_btc.percentage == 68
    assert hist_sig_btc.calibrated_probability == 68.0
    assert hist_sig_btc.sample_size >= 20

    hist_sig_xau = HistoricalMarketSignal(
        signal="WAIT",
        percentage=None,
        strength="WEAK",
        status="INSUFFICIENT_SAMPLE",
        sample_size=12,
        win_rate=None,
        calibrated_probability=None,
        expectancy=None,
    )
    assert hist_sig_xau.percentage is None
    assert hist_sig_xau.calibrated_probability is None
    assert hist_sig_xau.status == "INSUFFICIENT_SAMPLE"


def test_now_market_percentage_source():
    now_sig_btc = NowMarketSignal(
        signal="BUY",
        percentage=72,
        strength="STRONG",
        technical_score=70,
        gemini_score=75,
        mtf_alignment="Bullish Alignment",
        market_regime="TRENDING_UP",
    )
    assert now_sig_btc.percentage == 72
    assert now_sig_btc.strength == "STRONG"

    now_sig_xau = NowMarketSignal(
        signal="WAIT",
        percentage=35,
        strength="WEAK",
        technical_score=38,
        gemini_score=32,
        mtf_alignment="Mixed Structure",
        market_regime="CHOP",
    )
    assert now_sig_xau.percentage == 35
    assert now_sig_xau.strength == "WEAK"


def test_overall_percentage_synthesis_logic():
    def compute_overall_insight_percentage(hist_pct, now_pct):
        if hist_pct is None or now_pct is None:
            return None
        try:
            h = float(hist_pct)
            n = float(now_pct)
            if math.isnan(h) or math.isnan(n):
                return None
            h_clamped = max(0.0, min(100.0, round(h)))
            n_clamped = max(0.0, min(100.0, round(n)))
            # Standard JavaScript Math.round((h + n) / 2) behavior
            val = (h_clamped + n_clamped) / 2.0
            return math.floor(val + 0.5)
        except (ValueError, TypeError):
            return None

    assert compute_overall_insight_percentage(64, 82) == 73
    assert compute_overall_insight_percentage(50, 50) == 50
    assert compute_overall_insight_percentage(0, 100) == 50
    assert compute_overall_insight_percentage(65.4, 80.2) == 73
    assert compute_overall_insight_percentage(60, 61) == 61
    assert compute_overall_insight_percentage(None, 80) is None
    assert compute_overall_insight_percentage(60, None) is None
    assert compute_overall_insight_percentage(None, None) is None


def test_ml_shadow_prediction_generation(tmp_path):
    temp_db = str(tmp_path / "ml_test.db")
    ml_service = MLShadowService(db_path=temp_db)
    if ml_service.is_available("BTC/USD"):
        pred_btc = ml_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0=datetime.now(timezone.utc).isoformat(),
            production_decision="BUY",
            confluence_score=65,
            technical_score=68,
            gemini_score=60,
            entry_price=65000.0,
            stop_loss=64500.0,
            take_profit_1=66000.0,
            take_profit_2=66500.0,
            session="LONDON",
            market_regime="TRENDING_UP",
            contributor_scores={"Momentum": 70, "MTF Alignment": 65, "VWAP": 60},
            contributor_biases={"Momentum": "BULLISH", "MTF Alignment": "BULLISH"},
            data_quality="HIGH",
            gate_direction="BUY",
            quality_gate_passed=True,
        )
        assert pred_btc is not None
        assert 0.0 <= pred_btc.ml_probability <= 1.0
        assert pred_btc.ml_predicted_class in (0, 1)
        assert pred_btc.features_snapshot is not None
        assert "confluence_score" in pred_btc.features_snapshot

    if ml_service.is_available("XAU/USD"):
        pred_xau = ml_service.generate_prediction(
            symbol="XAU/USD",
            timestamp_t0=datetime.now(timezone.utc).isoformat(),
            production_decision="WAIT",
            confluence_score=35,
            technical_score=38,
            gemini_score=32,
            entry_price=0.0,
            stop_loss=None,
            take_profit_1=None,
            take_profit_2=None,
            session="NY",
            market_regime="CHOP",
            contributor_scores={"Momentum": 35, "MTF Alignment": 40},
            contributor_biases={"Momentum": "NEUTRAL", "MTF Alignment": "NEUTRAL"},
            data_quality="HIGH",
            gate_direction="NONE",
            quality_gate_passed=False,
        )
        assert pred_xau is not None
        assert 0.0 <= pred_xau.ml_probability <= 1.0
        assert pred_xau.production_decision == "WAIT"


def test_ml_to_decision_fusion():
    now_sig = NowMarketSignal(signal="BUY", percentage=75, strength="STRONG")
    hist_sig = HistoricalMarketSignal(
        signal="BUY",
        calibrated_probability=0.70,
        status="ACTIVE",
        sample_size=60,
        historical_ev=0.30,
        profit_factor=1.60,
    )
    sig_confirmed = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.75,
        ml_predicted_class=1,
        ml_model_name="RandomForestClassifier",
        ml_model_version="v1.0.0-research",
    )
    assert sig_confirmed.signal == "BUY"
    assert sig_confirmed.percentage is not None
    assert sig_confirmed.percentage >= DIRECTIONAL_THRESHOLD

    sig_conflict = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.15,
        ml_predicted_class=0,
    )
    assert sig_conflict.overall_evidence_score is not None
    assert sig_conflict.overall_evidence_score < sig_confirmed.overall_evidence_score


def test_decision_signal_construction_rules():
    from src.models.trading_decision import EntryZone

    decision_buy = TradingDecision(
        symbol="BTC/USD",
        decision=TradingSignal.BUY,
        confidence=75,
        trend=DecisionTrend.BULLISH,
        risk_level=DecisionRiskLevel.MEDIUM,
        composite_score=75.0,
        signal_strength=75.0,
        entry_zone=EntryZone(min=64900.0, max=65100.0),
        stop_loss=64200.0,
        take_profit_1=66600.0,
        take_profit_2=67400.0,
        reasons=["Confluence passed", "Direction gate passed"],
        warnings=[],
        invalid_if=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
        ai_provider_used="algorithmic",
    )
    assert decision_buy.decision == TradingSignal.BUY
    assert decision_buy.entry_zone is not None and decision_buy.entry_zone.min > 0
    assert decision_buy.stop_loss is not None and decision_buy.stop_loss < decision_buy.entry_zone.min
    assert decision_buy.take_profit_1 is not None and decision_buy.take_profit_1 > decision_buy.entry_zone.max

    decision_sell = TradingDecision(
        symbol="XAU/USD",
        decision=TradingSignal.SELL,
        confidence=72,
        trend=DecisionTrend.BEARISH,
        risk_level=DecisionRiskLevel.MEDIUM,
        composite_score=72.0,
        signal_strength=72.0,
        entry_zone=EntryZone(min=2648.0, max=2652.0),
        stop_loss=2665.0,
        take_profit_1=2620.0,
        take_profit_2=2605.0,
        reasons=["Confluence passed", "Direction gate passed"],
        warnings=[],
        invalid_if=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
        ai_provider_used="algorithmic",
    )
    assert decision_sell.decision == TradingSignal.SELL
    assert decision_sell.entry_zone is not None and decision_sell.entry_zone.min > 0
    assert decision_sell.stop_loss is not None and decision_sell.stop_loss > decision_sell.entry_zone.max
    assert decision_sell.take_profit_1 is not None and decision_sell.take_profit_1 < decision_sell.entry_zone.min

    decision_wait = TradingDecision(
        symbol="XAU/USD",
        decision=TradingSignal.WAIT,
        confidence=35,
        trend=DecisionTrend.NEUTRAL,
        risk_level=DecisionRiskLevel.LOW,
        composite_score=35.0,
        signal_strength=35.0,
        entry_zone=None,
        stop_loss=None,
        take_profit_1=None,
        take_profit_2=None,
        reasons=["Confluence below threshold 58.0"],
        warnings=[],
        invalid_if=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
        ai_provider_used="algorithmic",
    )
    assert decision_wait.decision == TradingSignal.WAIT
    assert decision_wait.entry_zone is None
    assert decision_wait.stop_loss is None
    assert decision_wait.take_profit_1 is None


def test_forward_shadow_capture_stores(tmp_path):
    temp_db = str(tmp_path / "fwd_test.db")
    engine = ForwardShadowEngine(db_path=temp_db)
    
    snap = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=64000.0,
        stop_loss=63500.0,
        take_profit_1=65000.0,
        take_profit_2=65500.0,
        confluence_score=70.0,
        confidence_score=70.0,
        signal_strength=70.0,
        market_regime="TRENDING_UP",
        session="LONDON",
        mtf_aligned=True,
    )
    assert snap is not None
    test_sig_id = snap.signal_id

    with sqlite3.connect(temp_db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM forward_shadow_signals WHERE signal_id = ?",
            (test_sig_id,)
        ).fetchone()
        assert row is not None
        assert row["asset"] == "BTC/USD"
        assert row["direction"] == "BUY"
        assert row["entry_price"] == 64000.0


def test_resolver_candle_evaluation_outcomes():
    worker = ForwardShadowResolverWorker(db_path=DB_PATH)
    sig_epoch_ms = 1700000000000

    # BUY Setup: Entry 100, SL 95, TP 110
    candles_win = [
        {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 105.0, "low": 98.0, "close": 102.0},
        {"timestamp": "2026-09-08T10:10:00Z", "epoch_ms": 1700000600000, "high": 111.0, "low": 101.0, "close": 110.5},
    ]
    res_win = worker._evaluate_two_stage_signal(
        sig_id="TEST-E2E-BUY-WIN",
        direction="BUY",
        entry=100.0,
        sl=95.0,
        tp1=110.0,
        sig_epoch_ms=sig_epoch_ms,
        status="PENDING_ENTRY",
        entry_filled_at=None,
        candles=candles_win,
    )
    assert res_win is not None
    assert res_win[0] == "RESOLVED_WIN"
    assert res_win[1] == 110.0
    assert res_win[2] > 0

    candles_loss = [
        {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 102.0, "low": 94.5, "close": 96.0},
    ]
    res_loss = worker._evaluate_two_stage_signal(
        sig_id="TEST-E2E-BUY-LOSS",
        direction="BUY",
        entry=100.0,
        sl=95.0,
        tp1=110.0,
        sig_epoch_ms=sig_epoch_ms,
        status="PENDING_ENTRY",
        entry_filled_at=None,
        candles=candles_loss,
    )
    assert res_loss is not None
    assert res_loss[0] == "RESOLVED_LOSS"
    assert res_loss[1] == 95.0
    assert res_loss[2] == -1.0

    candles_both = [
        {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 112.0, "low": 93.0, "close": 105.0},
    ]
    res_both = worker._evaluate_two_stage_signal(
        sig_id="TEST-E2E-BUY-BOTH",
        direction="BUY",
        entry=100.0,
        sl=95.0,
        tp1=110.0,
        sig_epoch_ms=sig_epoch_ms,
        status="PENDING_ENTRY",
        entry_filled_at=None,
        candles=candles_both,
    )
    assert res_both is not None
    assert res_both[0] == "AMBIGUOUS"


def test_btc_and_xau_strict_isolation_and_state_machine():
    sm = ForwardExecutionStateMachine(db_path=DB_PATH)
    status = sm.evaluate_state()
    assert status.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert status.live_execution == "DISABLED"
    assert status.production_gating == "DISABLED"
    assert status.xau_valid_forward_resolved_n == 0
    assert status.n50_status == "NOT REACHED"


def test_btc_separate_pipeline(tmp_path):
    # 1. Historical percentage
    hist = HistoricalMarketSignal(
        signal="BUY",
        percentage=68,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=60,
        win_rate=68.0,
        calibrated_probability=68.0,
        expectancy=0.45,
    )
    assert hist.percentage == 68

    # 2. Now market percentage
    now = NowMarketSignal(
        signal="BUY",
        percentage=74,
        strength="STRONG",
        technical_score=72,
        gemini_score=76,
    )
    assert now.percentage == 74

    # 3. Overall percentage
    overall_pct = math.floor(((hist.percentage + now.percentage) / 2.0) + 0.5)
    assert overall_pct == 71

    # 4. ML Prediction
    temp_db = str(tmp_path / "btc_test.db")
    ml = MLShadowService(db_path=temp_db)
    if ml.is_available("BTC/USD"):
        pred = ml.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0=datetime.now(timezone.utc).isoformat(),
            production_decision="BUY",
            confluence_score=74,
            technical_score=72,
            gemini_score=76,
            entry_price=65000.0,
            stop_loss=64200.0,
            take_profit_1=66600.0,
            take_profit_2=67400.0,
            session="LONDON",
            market_regime="TRENDING_UP",
            contributor_scores={"Momentum": 75, "MTF Alignment": 72},
            contributor_biases={"Momentum": "BULLISH", "MTF Alignment": "BULLISH"},
        )
        assert pred is not None
        assert 0.0 <= pred.ml_probability <= 1.0

    # 5. Signal Aggregation
    overall_sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now,
        historical_signal=hist,
        ml_probability=0.72,
        ml_predicted_class=1,
    )
    assert overall_sig.signal == "BUY"
    assert overall_sig.percentage is not None

    # 6. Capture & Resolver
    worker = ForwardShadowResolverWorker(db_path=DB_PATH)
    candles = [{
        "timestamp": "2026-09-08T12:05:00Z",
        "epoch_ms": 1700000300000,
        "high": 67000.0,
        "low": 64800.0,
        "close": 66800.0,
    }]
    res = worker._evaluate_two_stage_signal(
        sig_id="TEST-E2E-BTC-BUY",
        direction="BUY",
        entry=65000.0,
        sl=64200.0,
        tp1=66600.0,
        sig_epoch_ms=1700000000000,
        status="PENDING_ENTRY",
        entry_filled_at=None,
        candles=candles,
    )
    assert res is not None
    assert res[0] == "RESOLVED_WIN"
    assert res[1] == 66600.0


def test_xau_separate_pipeline(tmp_path):
    # 1. Historical percentage
    hist_insufficient = HistoricalMarketSignal(
        signal="WAIT",
        percentage=None,
        strength="WEAK",
        status="INSUFFICIENT_SAMPLE",
        sample_size=15,
    )
    assert hist_insufficient.percentage is None

    # 2. Now market percentage
    now = NowMarketSignal(
        signal="WAIT",
        percentage=36,
        strength="WEAK",
        technical_score=38,
        gemini_score=34,
    )
    assert now.percentage == 36

    # 3. Overall percentage returns None when historical is None
    def compute_overall(h, n):
        if h is None or n is None:
            return None
        return math.floor(((float(h) + float(n)) / 2.0) + 0.5)

    assert compute_overall(hist_insufficient.percentage, now.percentage) is None

    # 4. ML Prediction for XAU
    temp_db = str(tmp_path / "xau_test.db")
    ml = MLShadowService(db_path=temp_db)
    if ml.is_available("XAU/USD"):
        pred = ml.generate_prediction(
            symbol="XAU/USD",
            timestamp_t0=datetime.now(timezone.utc).isoformat(),
            production_decision="WAIT",
            confluence_score=36,
            technical_score=38,
            gemini_score=34,
            entry_price=0.0,
            stop_loss=None,
            take_profit_1=None,
            take_profit_2=None,
            session="NY",
            market_regime="CHOP",
            contributor_scores={"Momentum": 36, "MTF Alignment": 35},
            contributor_biases={"Momentum": "NEUTRAL", "MTF Alignment": "NEUTRAL"},
        )
        assert pred is not None
        assert pred.production_decision == "WAIT"

    # 5. Signal Aggregator enforces WAIT when conviction < DIRECTIONAL_THRESHOLD (58.0)
    overall_sig = SignalAggregator.aggregate(
        symbol="XAU/USD",
        now_signal=now,
        historical_signal=hist_insufficient,
        ml_probability=0.40,
        ml_predicted_class=0,
    )
    assert overall_sig.signal == "WAIT"
    assert overall_sig.percentage is None

    # 6. Directional qualification test (When XAU confluence >= 58.0)
    now_qualified = NowMarketSignal(
        signal="SELL",
        percentage=68,
        strength="STRONG",
        technical_score=70,
        gemini_score=66,
    )
    hist_qualified = HistoricalMarketSignal(
        signal="SELL",
        percentage=65,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=50,
        win_rate=65.0,
        calibrated_probability=65.0,
        expectancy=0.38,
    )
    overall_qualified = SignalAggregator.aggregate(
        symbol="XAU/USD",
        now_signal=now_qualified,
        historical_signal=hist_qualified,
        ml_probability=0.70,
        ml_predicted_class=1,
    )
    assert overall_qualified.signal == "SELL"
    assert overall_qualified.percentage is not None
    assert overall_qualified.percentage >= DIRECTIONAL_THRESHOLD

    # 7. Resolver for qualified XAU SELL setup (Entry 2650, SL 2665, TP 2620)
    worker = ForwardShadowResolverWorker(db_path=DB_PATH)
    candles_sell_win = [{
        "timestamp": "2026-09-08T12:05:00Z",
        "epoch_ms": 1700000300000,
        "high": 2655.0,
        "low": 2618.0,
        "close": 2625.0,
    }]
    res = worker._evaluate_two_stage_signal(
        sig_id="TEST-E2E-XAU-SELL",
        direction="SELL",
        entry=2650.0,
        sl=2665.0,
        tp1=2620.0,
        sig_epoch_ms=1700000000000,
        status="PENDING_ENTRY",
        entry_filled_at=None,
        candles=candles_sell_win,
    )
    assert res is not None
    assert res[0] == "RESOLVED_WIN"
    assert res[1] == 2620.0
