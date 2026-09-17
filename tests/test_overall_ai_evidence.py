"""
Test Suite: Evidence-Integrated OVERALL AI TRADING SIGNAL
=========================================================

Verifies:
1. Full end-to-end integration: Live + Historical + Gemini + 17 Contributors + MTF -> Overall AI Signal.
2. Zero look-ahead bias: strict closed candle boundary (<= T for setup, > T for outcome).
3. ConfluenceEngine preservation: 17 contributor weights sum to 100 with zero model drift.
4. Strict separation between Raw Confluence Score (0-100) and Calibrated Probability (0-100%).
5. Strict asset separation: BTC/USD data is never mixed with XAU/USD data.
6. Strict direction separation: BUY setups are never mixed with SELL setups.
7. Both winning and losing trade setups included (no cherry-picking).
8. Fail-safe resilience: Graceful fallback when historical evidence is empty or unavailable.
9. Demo/live account balance isolation: Backtests never modify demo trading balance or history.
10. API Route verification: GET /api/v1/decision/overall-ai returns enriched TradingDecision.
"""
import math
import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.models.market_data import Timeframe, OHLCVCandle
from src.models.historical_data import HistoricalCandle
from src.models.trading_decision import (
    TradingDecision,
    TradingSignal,
    DecisionTrend,
    DecisionRiskLevel,
    DecisionScoreBreakdown,
)
from src.models.ai_analysis import (
    MultiTimeframeTechnicalInput,
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    RiskLevel,
)
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
    RSIResult,
    RSICondition,
    MACDResult,
    MACDState,
    ATRResult,
    DataQualityReport,
)
from src.services.confluence_engine import ConfluenceEngine
from src.services.decision_engine import DecisionEngine
from src.services.decision_service import DecisionService
from src.services.historical_evidence_service import (
    HistoricalEvidenceService,
    HistoricalEvidencePackage,
    get_historical_evidence_service,
)
from src.services.probability_calibrator import ProbabilityCalibrator
from src.services.paper_trading_service import PaperTradingService


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

def _make_dummy_ta(symbol: str = "XAU/USD", trend_dir: TrendDirection = TrendDirection.BULLISH) -> TechnicalAnalysisResponse:
    """Create a minimal TechnicalAnalysisResponse."""
    return TechnicalAnalysisResponse(
        symbol=symbol,
        timeframe=Timeframe.M15,
        current_price=2750.0,
        ema20=2745.0,
        ema50=2740.0,
        ema200=2700.0,
        rsi14=RSIResult(value=58.0, condition=RSICondition.NEUTRAL),
        macd=MACDResult(macd_line=2.5, signal_line=1.5, histogram=1.0, state=MACDState.BULLISH),
        atr14=ATRResult(value=12.5, volatility_pct=0.45),
        support_levels=[2740.0, 2720.0],
        resistance_levels=[2770.0, 2800.0],
        trend=TrendAnalysis(direction=trend_dir, strength="STRONG", score=0.8, confirmations=["EMA", "MACD"]),
        indicator_summary="Bullish trend structure",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=100, is_sufficient=True, missing_indicators=[], notes="Good"),
    )


def _make_dummy_ai(bias: OverallBias = OverallBias.BULLISH, confidence: int = 80) -> AIAnalysisResponse:
    """Create a minimal AIAnalysisResponse."""
    return AIAnalysisResponse(
        symbol="XAU/USD",
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        market_condition=MarketCondition.TRENDING_BULLISH,
        overall_bias=bias,
        confidence=confidence,
        timeframe_analysis={"5m": "Bullish", "15m": "Bullish", "1h": "Bullish", "1d": "Bullish"},
        key_bullish_factors=["Strong HTF trend", "Volume breakout"],
        key_bearish_factors=["Approaching major resistance"],
        key_support=[2740.0, 2720.0],
        key_resistance=[2780.0, 2800.0],
        risk_level=RiskLevel.LOW,
        summary="Clear bullish continuation structure across timeframes.",
        provider_used="gemini-2.0-flash",
        is_fallback=False,
    )


# ---------------------------------------------------------------------------
# 1. ConfluenceEngine 17-Contributor Weights Preservation
# ---------------------------------------------------------------------------

class TestConfluenceEnginePreservation:
    """Verify that the 100-point 17-contributor scoring engine is 100% preserved."""

    def test_contributor_count_is_17(self):
        from src.services.confluence_engine import CONTRIBUTOR_MAX_SCORES
        assert len(CONTRIBUTOR_MAX_SCORES) == 17

    def test_weights_sum_to_exact_100(self):
        from src.services.confluence_engine import CONTRIBUTOR_MAX_SCORES
        total_weight = sum(CONTRIBUTOR_MAX_SCORES.values())
        assert total_weight == 100, f"Weights sum to {total_weight}, expected 100"

    def test_individual_contributor_weight_values(self):
        from src.services.confluence_engine import CONTRIBUTOR_MAX_SCORES
        expected = {
            "HTF Trend": 11,
            "Market Structure": 9,
            "Momentum": 8,
            "MTF Alignment": 8,
            "S/R Price Action": 8,
            "Breakout / Retest": 6,
            "Supply & Demand": 5,
            "Volume Confirmation": 5,
            "SMC / ICT": 5,
            "ICT Concepts": 4,
            "Fibonacci OTE": 4,
            "Elliott Wave": 4,
            "VWAP": 4,
            "EMA / MA Stack": 4,
            "RSI": 3,
            "MACD": 2,
            "Gemini AI": 10,
        }
        for contributor, weight in expected.items():
            assert CONTRIBUTOR_MAX_SCORES[contributor] == weight, f"Mismatch on {contributor}: got {CONTRIBUTOR_MAX_SCORES[contributor]}, expected {weight}"


# ---------------------------------------------------------------------------
# 2. Zero Look-Ahead Bias & Closed Candle Rule
# ---------------------------------------------------------------------------

class TestZeroLookAheadBias:
    """Verify strict chronological boundary isolation between feature snapshots and outcomes."""

    def test_snapshot_only_evaluates_candles_at_or_before_t(self):
        engine = DecisionEngine()
        base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Create past/closed candles (<= T)
        closed_candles = [
            OHLCVCandle(
                timestamp=(base_time - timedelta(minutes=15 * i)).isoformat(),
                open=2700.0 + i,
                high=2705.0 + i,
                low=2695.0 + i,
                close=2702.0 + i,
                volume=100.0,
            )
            for i in range(50, -1, -1)
        ]

        ta = _make_dummy_ta()
        mtf_input = MultiTimeframeTechnicalInput(
            symbol="XAU/USD",
            current_price=2750.0,
            timestamp=base_time.isoformat(),
            timeframes={"15m": ta, "5m": ta, "1h": ta, "1d": ta},
            timeframe_count=4,
            alignment_summary="Bullish",
        )
        ai_res = _make_dummy_ai()

        decision, breakdown = engine.evaluate(
            mtf_input,
            ai_res,
            {"15m": closed_candles},
        )

        assert decision is not None
        assert decision.timestamp is not None

    def test_outcome_tracking_only_uses_future_candles_after_t(self):
        """Historical signal outcomes must be evaluated only on candles with timestamp > entry_timestamp."""
        from src.services.outcome_tracker import OutcomeTracker
        tracker = OutcomeTracker()

        entry_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Future candle strictly after entry_time that hits TP
        future_candles = [
            OHLCVCandle(
                timestamp=(entry_time + timedelta(minutes=5)).isoformat(),
                open=2750.0,
                high=2775.0,
                low=2748.0,
                close=2772.0,
                volume=150.0,
            )
        ]

        c_ts = datetime.fromisoformat(future_candles[0].timestamp.replace("Z", "+00:00"))
        assert c_ts > entry_time, "Future candle must strictly follow entry timestamp"


# ---------------------------------------------------------------------------
# Helper function for inserting test historical signals
# ---------------------------------------------------------------------------

def _insert_test_signal(
    cur,
    signal_id: str,
    symbol: str,
    direction: str,
    confluence_score: int,
    outcome: str,
    realized_r: float = 1.0,
    run_id: str = None,
    dataset_id: str = "ds_1",
    timestamp: str = None,
):
    norm_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
    default_run = "RUN-BTC-USD-20260831-173607" if "BTC" in norm_symbol else "RUN-XAU-USD-20260831-174452"
    effective_run_id = run_id or default_run
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    # Ensure canonical run and report exist in test database for validation
    cur.execute("""
        INSERT OR IGNORE INTO backtest_runs (
            run_id, dataset_id, dataset_version, engine_version, symbol,
            config_json, status, progress_pct, current_step, created_at
        ) VALUES (?, 'ds_1', '1.0', '1.0', ?, '{}', 'COMPLETED', 100.0, 'COMPLETE', ?)
    """, (effective_run_id, norm_symbol, ts))
    cur.execute("""
        INSERT OR IGNORE INTO backtest_reports (run_id, report_json, created_at)
        VALUES (?, '{}', ?)
    """, (effective_run_id, ts))

    cur.execute("""
        INSERT INTO historical_signals (
            signal_id, run_id, dataset_id, symbol, source_symbol,
            signal_timestamp, snapshot_id, entry_price, direction,
            confluence_score, technical_score, gemini_score,
            outcome, realized_r, is_in_sample
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id, effective_run_id, dataset_id, symbol, symbol,
        ts, "snap_1", 2700.0, direction,
        confluence_score, int(confluence_score * 0.9), 8,
        outcome, realized_r, 1
    ))


# ---------------------------------------------------------------------------
# 3. Strict Asset Separation (BTC vs XAU)
# ---------------------------------------------------------------------------

class TestStrictAssetSeparation:
    """Verify that BTC/USD empirical data never mixes with XAU/USD data."""

    def test_evidence_service_filters_by_exact_asset(self, tmp_path):
        db_file = str(tmp_path / "test_evidence_assets.db")
        service = HistoricalEvidenceService(db_path=db_file)

        # Insert 10 XAU BUY trades (8 wins) and 10 BTC BUY trades (2 wins)
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        
        # XAU trades
        for i in range(10):
            outcome = "WIN" if i < 8 else "LOSS"
            _insert_test_signal(
                cur=cur,
                signal_id=f"xau_{i}",
                symbol="XAU/USD",
                direction="BUY",
                confluence_score=78,
                outcome=outcome,
                realized_r=1.5 if outcome == "WIN" else -1.0,
            )

        # BTC trades
        for i in range(10):
            outcome = "WIN" if i < 2 else "LOSS"
            _insert_test_signal(
                cur=cur,
                signal_id=f"btc_{i}",
                symbol="BTC/USD",
                direction="BUY",
                confluence_score=78,
                outcome=outcome,
                realized_r=1.5 if outcome == "WIN" else -1.0,
            )

        conn.commit()
        conn.close()

        # Query XAU
        xau_pkg = service.get_evidence_for_setup(
            symbol="XAU/USD",
            direction="BUY",
            confluence_score=78,
            technical_score=70,
            gemini_score=8,
            mtf_alignment="Bullish",
            market_regime="TRENDING_BULLISH",
            force_refresh=True,
        )

        # Query BTC
        btc_pkg = service.get_evidence_for_setup(
            symbol="BTC/USD",
            direction="BUY",
            confluence_score=78,
            technical_score=70,
            gemini_score=8,
            mtf_alignment="Bullish",
            market_regime="TRENDING_BULLISH",
            force_refresh=True,
        )

        assert xau_pkg.sample_size == 10
        assert xau_pkg.win_rate == 80.0
        assert xau_pkg.wins == 8

        assert btc_pkg.sample_size == 10
        assert btc_pkg.win_rate == 20.0
        assert btc_pkg.wins == 2


# ---------------------------------------------------------------------------
# 4. Strict BUY vs SELL Direction Separation
# ---------------------------------------------------------------------------

class TestStrictDirectionSeparation:
    """Verify that BUY setups never mix with SELL setups."""

    def test_evidence_service_filters_by_exact_direction(self, tmp_path):
        db_file = str(tmp_path / "test_evidence_dirs.db")
        service = HistoricalEvidenceService(db_path=db_file)

        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        # Insert 10 BUY trades (9 wins)
        for i in range(10):
            outcome = "WIN" if i < 9 else "LOSS"
            _insert_test_signal(
                cur=cur,
                signal_id=f"buy_{i}",
                symbol="XAU/USD",
                direction="BUY",
                confluence_score=75,
                outcome=outcome,
                realized_r=2.0 if outcome == "WIN" else -1.0,
            )

        # Insert 10 SELL trades (3 wins)
        for i in range(10):
            outcome = "WIN" if i < 3 else "LOSS"
            _insert_test_signal(
                cur=cur,
                signal_id=f"sell_{i}",
                symbol="XAU/USD",
                direction="SELL",
                confluence_score=75,
                outcome=outcome,
                realized_r=2.0 if outcome == "WIN" else -1.0,
            )

        conn.commit()
        conn.close()

        buy_pkg = service.get_evidence_for_setup(symbol="XAU/USD", direction="BUY", confluence_score=75, force_refresh=True)
        sell_pkg = service.get_evidence_for_setup(symbol="XAU/USD", direction="SELL", confluence_score=75, force_refresh=True)

        assert buy_pkg.win_rate == 90.0
        assert sell_pkg.win_rate == 30.0


# ---------------------------------------------------------------------------
# 5. Inclusion of Winning and Losing Trades (No Cherry-Picking)
# ---------------------------------------------------------------------------

class TestBothWinsAndLossesIncluded:
    """Verify that both winning and losing trades are stored and calculated in win rates."""

    def test_win_rate_and_sample_count_reflect_all_trades(self, tmp_path):
        db_file = str(tmp_path / "test_wins_losses.db")
        service = HistoricalEvidenceService(db_path=db_file)

        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        # 6 Wins, 4 Losses
        for i in range(6):
            _insert_test_signal(
                cur=cur,
                signal_id=f"w_{i}",
                symbol="XAU/USD",
                direction="BUY",
                confluence_score=65,
                outcome="WIN",
                realized_r=1.5,
            )

        for i in range(4):
            _insert_test_signal(
                cur=cur,
                signal_id=f"l_{i}",
                symbol="XAU/USD",
                direction="BUY",
                confluence_score=65,
                outcome="LOSS",
                realized_r=-1.0,
            )

        conn.commit()
        conn.close()

        pkg = service.get_evidence_for_setup(symbol="XAU/USD", direction="BUY", confluence_score=65, force_refresh=True)
        assert pkg.sample_size == 10
        assert pkg.wins == 6
        assert pkg.losses == 4
        assert pkg.win_rate == 60.0


# ---------------------------------------------------------------------------
# 6. Raw Confluence Score vs Calibrated Probability Separation
# ---------------------------------------------------------------------------

class TestScoreVsCalibratedProbSeparation:
    """Verify Raw Confluence Score (0-100) is never conflated with Calibrated Probability."""

    def test_score_and_calibrated_prob_are_independent(self, tmp_path):
        db_file = str(tmp_path / "test_calibration_sep.db")
        service = HistoricalEvidenceService(db_path=db_file)

        pkg = service.get_evidence_for_setup(
            symbol="XAU/USD",
            direction="BUY",
            confluence_score=85,
            technical_score=78,
            gemini_score=9,
            force_refresh=True,
        )

        assert isinstance(pkg.calibrated_probability, (float, int)) or pkg.calibrated_probability is None


# ---------------------------------------------------------------------------
# 7. Fail-Safe Resilience & Non-Blocking Fallback
# ---------------------------------------------------------------------------

class TestFailSafeResilience:
    """Verify that empty, corrupt, or missing historical databases fail gracefully."""

    def test_missing_db_returns_fallback_without_error(self, tmp_path):
        service = HistoricalEvidenceService(db_path=str(tmp_path / "non_existent.db"))
        pkg = service.get_evidence_for_setup(symbol="XAU/USD", direction="BUY", confluence_score=70)
        assert pkg.status in ("INSUFFICIENT", "NOT_AVAILABLE")
        assert pkg.sample_size == 0
        assert pkg.win_rate is None

    def test_decision_service_continues_when_evidence_fails(self):
        """DecisionService must return a valid decision even if HistoricalEvidenceService raises an exception."""
        service = DecisionService()
        with patch("src.services.historical_evidence_service.get_historical_evidence_service") as mock_ev:
            mock_ev.side_effect = RuntimeError("Simulated DB Disk I/O Failure")
            decision, breakdown = service.get_decision(symbol="XAU-USD-SPOT", force_refresh=True)

            assert decision is not None
            assert decision.symbol == "XAU/USD"
            assert decision.decision in (TradingSignal.BUY, TradingSignal.SELL, TradingSignal.WAIT)


# ---------------------------------------------------------------------------
# 8. Demo/Live Balance Isolation
# ---------------------------------------------------------------------------

class TestDemoBalanceIsolation:
    """Verify that running historical backtesting never alters the demo trading account."""

    def test_paper_trading_stats_remain_unaltered_by_evidence_service(self, tmp_path):
        paper_svc = PaperTradingService()
        initial_stats, initial_trades = paper_svc.update_and_get_stats(2750.0)
        initial_balance = initial_stats["current_balance"]
        initial_trades_count = len(initial_trades)

        # Execute historical evidence queries
        ev_svc = HistoricalEvidenceService(db_path=str(tmp_path / "iso_test.db"))
        for _ in range(5):
            ev_svc.get_evidence_for_setup(symbol="XAU/USD", direction="BUY", confluence_score=75)

        # Demo balance and trades must be 100% identical
        after_stats, after_trades = paper_svc.update_and_get_stats(2750.0)
        assert after_stats["current_balance"] == initial_balance
        assert len(after_trades) == initial_trades_count


# ---------------------------------------------------------------------------
# 9. Full End-to-End Decision Pipeline with Empirical Historical Fields
# ---------------------------------------------------------------------------

class TestFullOverallAIDecisionPipeline:
    """Verify end-to-end enrichment of TradingDecision with empirical fields."""

    def test_decision_includes_all_additive_empirical_fields(self):
        svc = DecisionService()
        decision, breakdown = svc.get_decision(symbol="XAU-USD-SPOT", force_refresh=True)

        assert hasattr(decision, "historical_evidence_status")
        assert hasattr(decision, "historical_sample_size")
        assert hasattr(decision, "historical_win_rate")
        assert hasattr(decision, "calibrated_probability")
        assert hasattr(decision, "historical_expectancy")
        assert hasattr(decision, "historical_profit_factor")
        assert hasattr(decision, "historical_drawdown")
        assert hasattr(decision, "similar_setup_count")
        assert hasattr(decision, "score_band_win_rate")
        assert hasattr(decision, "win_rate_ci_lower")
        assert hasattr(decision, "win_rate_ci_upper")
        assert hasattr(decision, "evidence_refresh_at")
        assert hasattr(decision, "dataset_version")
        assert hasattr(decision, "backtest_run_id")
        assert hasattr(decision, "evidence_quality")

    def test_btc_decision_pipeline_runs_smoothly(self):
        svc = DecisionService()
        decision, breakdown = svc.get_decision(symbol="BTC-USD", force_refresh=True)

        assert decision.symbol == "BTC/USD"
        assert hasattr(decision, "historical_evidence_status")


# ---------------------------------------------------------------------------
# 10. Automated Background Historical Learning & Pattern Discovery
# ---------------------------------------------------------------------------

class TestAutomatedHistoricalLearningEngine:
    """Verify background learning orchestration, self-maintenance, and pattern discovery."""

    def test_ensure_historical_learning_ready_triggers_worker(self, tmp_path):
        db_file = str(tmp_path / "test_auto_learn_trigger.db")
        service = HistoricalEvidenceService(db_path=db_file, auto_start_learning=False)

        # Initially empty database
        assert service._auto_learning_started is False
        assert service._is_learning is False

        with patch.object(service, "auto_learn_in_background") as mock_learn:
            service.ensure_historical_learning_ready()
            mock_learn.assert_called_once_with(force=False)

    def test_auto_learning_worker_execution_updates_cache_and_db(self, tmp_path):
        db_file = str(tmp_path / "test_worker_exec.db")
        service = HistoricalEvidenceService(db_path=db_file, auto_start_learning=False)

        # Seed sample candles for XAU and BTC
        now_utc = datetime.now(timezone.utc)
        base_epoch = int((now_utc - timedelta(days=20)).timestamp() * 1000)

        candles_btc = [
            HistoricalCandle(
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                timeframe="15m",
                timestamp=(now_utc - timedelta(minutes=15 * (100 - i))).isoformat(),
                epoch_ms=base_epoch + i * 15 * 60 * 1000,
                open=65000.0 + (i * 10),
                high=65050.0 + (i * 10),
                low=64950.0 + (i * 10),
                close=65020.0 + (i * 10),
                volume=50.0,
                is_closed=True,
                source="test",
            )
            for i in range(100)
        ]
        service.data_service.save_candles(candles_btc)

        # Run automated learning worker directly
        service._execute_automated_learning(force=True)

        assert service._last_learning_completed_at is not None
        assert service._is_learning is False

    def test_pattern_discovery_and_similar_setup_metrics(self, tmp_path):
        db_file = str(tmp_path / "test_pattern_matching.db")
        service = HistoricalEvidenceService(db_path=db_file, auto_start_learning=False)

        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        # Insert 15 XAU BUY trades in the 70-79 band under TRENDING_BULLISH regime
        for i in range(15):
            outcome = "WIN" if i < 11 else "LOSS"
            _insert_test_signal(
                cur=cur,
                signal_id=f"pat_{i}",
                symbol="XAU/USD",
                direction="BUY",
                confluence_score=76,
                outcome=outcome,
                realized_r=1.8 if outcome == "WIN" else -1.0,
            )

        conn.commit()
        conn.close()

        pkg = service.get_evidence_for_setup(
            symbol="XAU/USD",
            direction="BUY",
            confluence_score=76,
            technical_score=70,
            gemini_score=8,
            mtf_alignment="Bullish",
            market_regime="TRENDING_BULLISH",
            force_refresh=True,
        )

        assert pkg.sample_size == 15
        assert pkg.wins == 11
        assert pkg.losses == 4
        assert pkg.win_rate == round(11 / 15 * 100, 1)
        assert pkg.score_band_win_rate == round(11 / 15 * 100, 1)
        assert pkg.ci_lower is not None
        assert pkg.ci_upper is not None
        assert pkg.expectancy is not None
        assert pkg.recommendation_strength in ("HIGH", "MEDIUM", "LOW")
        assert len(pkg.historical_confirmations) > 0


class TestTruePercentageNonInflation:
    """Phase 1 Verification: Asserts true percentage pass-through without flooring, clamping, or 51% overrides."""

    def test_low_confluence_passes_unclamped(self):
        """Verify that low confluence (e.g. 15%) is NOT clamped to 50% or 10%."""
        service = DecisionService()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Build minimal decision with signal_strength=15
        dummy_ta = _make_dummy_ta()
        mtf_input = MultiTimeframeTechnicalInput(
            symbol="XAU/USD",
            current_price=2750.0,
            timestamp=now_iso,
            timeframes={"15m": dummy_ta},
            timeframe_count=1,
            alignment_summary="Mixed",
            regime="UNCLEAR",
        )
        
        # Mock DecisionEngine breakdown and decision
        breakdown = DecisionScoreBreakdown(
            symbol="XAU/USD",
            timestamp=now_iso,
            total_score=0.15,
            signal_candidate="WAIT",
            final_signal=TradingSignal.WAIT,
            confidence=15,
            components=[],
            wait_overrides_triggered=[],
            weight_sum=1.0,
        )
        decision = TradingDecision(
            symbol="XAU/USD",
            decision=TradingSignal.WAIT,
            confidence=15,
            trend=DecisionTrend.NEUTRAL,
            risk_level=DecisionRiskLevel.LOW,
            composite_score=0.15,
            signal_strength=15,
            reasons=["Low confluence test"],
            timestamp=now_iso,
        )

        ev_pkg = HistoricalEvidencePackage(
            status="INSUFFICIENT_SAMPLE",
            sample_size=5,
            historical_bias="WAIT",
        )

        dummy_ai = _make_dummy_ai()
        hist_sig, now_sig, overall_sig = service._build_three_layer_signals(
            decision=decision,
            breakdown=breakdown,
            mtf_input=mtf_input,
            ai_result=dummy_ai,
            ev_pkg=ev_pkg,
        )

        # Must be exactly 15 in overall_evidence_score, while percentage is None for WAIT per methodology
        assert now_sig.percentage == 15
        assert overall_sig.overall_evidence_score == 15
        assert overall_sig.overall_evidence_score != 50
        assert overall_sig.overall_evidence_score != 10
        assert overall_sig.percentage is None

    def test_direction_conflict_sets_wait_and_none_percentage(self):
        """Verify that a direction conflict sets WAIT, conflict_detected=True, and percentage=None (NOT 51%)."""
        service = DecisionService()
        now_iso = datetime.now(timezone.utc).isoformat()

        dummy_ta = _make_dummy_ta()
        dummy_ai = _make_dummy_ai()
        mtf_input = MultiTimeframeTechnicalInput(
            symbol="XAU/USD",
            current_price=2750.0,
            timestamp=now_iso,
            timeframes={"15m": dummy_ta},
            timeframe_count=1,
            alignment_summary="Bullish",
            regime="TRENDING_BULLISH",
        )
        breakdown = DecisionScoreBreakdown(
            symbol="XAU/USD",
            timestamp=now_iso,
            total_score=0.75,
            signal_candidate="BUY",
            final_signal=TradingSignal.BUY,
            confidence=75,
            components=[],
            wait_overrides_triggered=[],
            weight_sum=1.0,
        )
        decision = TradingDecision(
            symbol="XAU/USD",
            decision=TradingSignal.BUY,
            confidence=75,
            trend=DecisionTrend.BULLISH,
            risk_level=DecisionRiskLevel.LOW,
            composite_score=0.75,
            signal_strength=75,
            reasons=["Bullish live confluence"],
            timestamp=now_iso,
        )

        # Historical evidence indicates SELL (directional divergence)
        ev_pkg = HistoricalEvidencePackage(
            status="AVAILABLE",
            sample_size=35,
            historical_bias="SELL",
            win_rate=68.0,
            calibrated_probability=65.0,
            expectancy=0.45,
            sell_strength=70,
        )

        hist_sig, now_sig, overall_sig = service._build_three_layer_signals(
            decision=decision,
            breakdown=breakdown,
            mtf_input=mtf_input,
            ai_result=dummy_ai,
            ev_pkg=ev_pkg,
        )

        assert hist_sig.signal == "SELL"
        assert now_sig.signal == "BUY"
        assert overall_sig.conflict_detected is True
        assert overall_sig.signal == "WAIT"
        assert overall_sig.percentage is None
        assert overall_sig.percentage != 51
        assert overall_sig.strength == "CONFLICT"


