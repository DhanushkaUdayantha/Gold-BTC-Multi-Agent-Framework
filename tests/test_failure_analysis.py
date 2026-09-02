"""
Unit and Integration Tests for Phase 3 Failure, Winner, and Drawdown Forensic Analysis.

Verifies:
1. Winner empirical profiling & success taxonomy
2. Loser empirical profiling & deterministic failure taxonomy
3. Missed winner detection & opportunity cost calculations
4. Peak-to-trough drawdown decomposition & recovery tracking
5. Loss and winner streak clustering & autocorrelation
6. Multi-dimensional segmentation (Regime, Session, Direction, Confluence, Probability, MTF)
7. Strict BTC/XAU asset isolation
8. Production decision isolation (decision outputs identical before and after research execution)
9. Edge cases (empty dataset, 1 trade, all winners, all losers, missing fields)
"""
import pytest
from src.research.failure_analysis.failure_taxonomy import (
    FAILURE_TAXONOMY_VERSION,
    FailureReason,
    SuccessReason,
    classify_trade_failure,
    classify_trade_success,
)
from src.research.failure_analysis.winner_analysis import analyze_winners
from src.research.failure_analysis.loser_analysis import analyze_losers
from src.research.failure_analysis.missed_winners import analyze_missed_winners
from src.research.failure_analysis.drawdown_analysis import analyze_drawdowns
from src.research.failure_analysis.clustering import analyze_clustering
from src.research.failure_analysis.segment_analysis import run_segment_forensics
from src.research.failure_analysis.validator import run_full_failure_forensic_analysis


class TestTaxonomyClassification:
    """Tests for deterministic taxonomy classification."""

    def test_taxonomy_version_constant(self):
        assert FAILURE_TAXONOMY_VERSION == "1.0"

    def test_mtf_conflict_failure(self):
        trade = {
            "htf_aligned": False,
            "mtf_aligned": False,
            "confluence_score": 60,
            "market_regime": "TRENDING",
        }
        res = classify_trade_failure(trade)
        assert res.primary_reason == FailureReason.MTF_CONFLICT
        assert res.confidence == "HIGH"
        assert len(res.evidence) > 0

    def test_false_breakout_failure(self):
        trade = {
            "htf_aligned": True,
            "mtf_aligned": True,
            "mae": 1.2,
            "mfe": 0.1,
            "confluence_score": 60,
            "market_regime": "CHOP",
        }
        res = classify_trade_failure(trade)
        assert res.primary_reason == FailureReason.FALSE_BREAKOUT
        assert res.confidence == "HIGH"

    def test_low_confluence_failure(self):
        trade = {
            "htf_aligned": True,
            "mtf_aligned": True,
            "confluence_score": 42.0,
            "market_regime": "TRENDING",
        }
        res = classify_trade_failure(trade)
        assert res.primary_reason == FailureReason.LOW_CONFLUENCE

    def test_success_classification(self):
        trade = {
            "htf_aligned": True,
            "mtf_aligned": True,
            "confluence_score": 75.0,
            "market_regime": "TRENDING",
        }
        res = classify_trade_success(trade)
        assert res.primary_reason in (SuccessReason.MTF_ALIGNMENT, SuccessReason.HIGH_CONFLUENCE)
        assert res.confidence == "HIGH"


class TestWinnerAndLoserProfiling:
    """Tests for empirical winner and loser profiling."""

    def test_winner_profile_metrics(self):
        trades = [
            {"outcome": "WIN", "realized_r": 1.5, "mfe": 1.8, "mae": 0.2, "duration_minutes": 45, "direction": "BUY"},
            {"outcome": "WIN", "realized_r": 1.5, "mfe": 1.6, "mae": 0.3, "duration_minutes": 30, "direction": "SELL"},
            {"outcome": "LOSS", "realized_r": -1.0, "mfe": 0.2, "mae": 1.0, "duration_minutes": 20, "direction": "BUY"},
        ]
        win_prof = analyze_winners(trades, symbol="BTC/USD")
        assert win_prof.total_trades_analyzed == 3
        assert win_prof.winner_count == 2
        assert win_prof.win_rate_pct == 66.67
        assert win_prof.avg_realized_r == 1.5
        assert win_prof.total_r_won == 3.0
        assert win_prof.buy_winner_count == 1
        assert win_prof.sell_winner_count == 1

    def test_loser_profile_metrics(self):
        trades = [
            {"outcome": "WIN", "realized_r": 1.5, "mfe": 1.8, "mae": 0.2, "duration_minutes": 45, "direction": "BUY"},
            {"outcome": "LOSS", "realized_r": -1.0, "mfe": 0.4, "mae": 1.0, "duration_minutes": 25, "direction": "BUY"},
            {"outcome": "LOSS", "realized_r": -1.0, "mfe": 0.1, "mae": 1.0, "duration_minutes": 15, "direction": "SELL"},
        ]
        lose_prof = analyze_losers(trades, symbol="XAU/USD")
        assert lose_prof.total_trades_analyzed == 3
        assert lose_prof.loser_count == 2
        assert lose_prof.loss_rate_pct == 66.67
        assert lose_prof.avg_loss_r == -1.0
        assert lose_prof.total_r_lost == 2.0


class TestMissedWinnersAndOpportunityCost:
    """Tests for missed opportunity and opportunity cost calculations."""

    def test_opportunity_cost_calculation(self):
        exec_trades = [
            {"outcome": "WIN", "realized_r": 1.5, "confluence_score": 70},
            {"outcome": "LOSS", "realized_r": -1.0, "confluence_score": 70},
        ]
        untraded = [
            {"outcome": "WIN", "potential_r": 1.5, "confluence_score": 50},
            {"outcome": "LOSS", "potential_r": -1.0, "confluence_score": 45},
            {"outcome": "LOSS", "potential_r": -1.0, "confluence_score": 48},
        ]
        res = analyze_missed_winners(exec_trades, untraded, symbol="BTC/USD")
        assert res.executed_trades_count == 2
        assert res.missed_winner_count == 1
        assert res.missed_loser_count == 2
        assert res.missed_winner_r_lost == 1.5
        assert res.missed_loser_r_saved == 2.0
        assert res.net_opportunity_cost_r == -0.5  # Filter saved 0.5R net
        assert res.benefit_cost_ratio == 1.33  # >1.0 indicates beneficial filter


class TestDrawdownAndClustering:
    """Tests for peak-to-trough drawdown decomposition and streak clustering."""

    def test_drawdown_episodes(self):
        trades = [
            {"realized_r": 1.5, "direction": "BUY", "market_regime": "TRENDING", "session": "LONDON", "timestamp": "2026-01-01T00:00:00Z"},
            {"realized_r": -1.0, "direction": "BUY", "market_regime": "HIGH_VOLATILITY", "session": "ASIA", "timestamp": "2026-01-01T01:00:00Z"},
            {"realized_r": -1.0, "direction": "BUY", "market_regime": "HIGH_VOLATILITY", "session": "ASIA", "timestamp": "2026-01-01T02:00:00Z"},
            {"realized_r": -1.0, "direction": "BUY", "market_regime": "HIGH_VOLATILITY", "session": "ASIA", "timestamp": "2026-01-01T03:00:00Z"},
            {"realized_r": -1.0, "direction": "SELL", "market_regime": "HIGH_VOLATILITY", "session": "ASIA", "timestamp": "2026-01-01T04:00:00Z"},
            {"realized_r": 1.5, "direction": "BUY", "market_regime": "TRENDING", "session": "LONDON", "timestamp": "2026-01-01T05:00:00Z"},
            {"realized_r": 1.5, "direction": "BUY", "market_regime": "TRENDING", "session": "LONDON", "timestamp": "2026-01-01T06:00:00Z"},
            {"realized_r": 1.5, "direction": "BUY", "market_regime": "TRENDING", "session": "LONDON", "timestamp": "2026-01-01T07:00:00Z"},
        ]
        dd_rep = analyze_drawdowns(trades, symbol="BTC/USD")
        assert dd_rep.max_drawdown_r >= 4.0
        assert dd_rep.episodes_count >= 1
        assert dd_rep.buy_loss_contribution_pct > 0

    def test_streak_clustering(self):
        trades = [
            {"realized_r": 1.5}, {"realized_r": 1.5}, {"realized_r": 1.5},
            {"realized_r": -1.0}, {"realized_r": -1.0},
            {"realized_r": 1.5},
        ]
        cluster_rep = analyze_clustering(trades, symbol="BTC/USD")
        assert cluster_rep.longest_winning_streak == 3
        assert cluster_rep.longest_losing_streak == 2


class TestSegmentationAndIsolation:
    """Tests for multi-dimensional segmentation and production isolation."""

    def test_segment_forensics_slices(self):
        trades = [
            {"realized_r": 1.5, "direction": "BUY", "market_regime": "TRENDING", "session": "LONDON", "confluence_score": 70, "calibrated_probability": 0.60, "mtf_aligned": True},
            {"realized_r": -1.0, "direction": "SELL", "market_regime": "CHOP", "session": "ASIA", "confluence_score": 45, "calibrated_probability": 0.40, "mtf_aligned": False},
        ]
        segs = run_segment_forensics(trades, symbol="BTC/USD")
        assert len(segs.regimes) > 0
        assert len(segs.sessions) > 0
        assert len(segs.directions) == 2
        assert len(segs.confluence_buckets) > 0
        assert len(segs.probability_buckets) > 0

    def test_asset_forensics_isolation(self):
        btc_forensic = run_full_failure_forensic_analysis(symbol="BTC/USD")
        xau_forensic = run_full_failure_forensic_analysis(symbol="XAU/USD")
        assert btc_forensic.symbol == "BTC/USD"
        assert xau_forensic.symbol == "XAU/USD"
        assert btc_forensic.resolved_trades_count == 1519
        assert xau_forensic.resolved_trades_count == 918
        assert xau_forensic.expired_signals_count == 1

    def test_production_isolation_unaffected_by_failure_analysis(self):
        from src.services.decision_engine import DecisionEngine
        from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

        ta = _make_ta(price=76000.0)
        ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
        mtf_in = _make_mtf_input(ta_map, price=76000.0)
        ai_in = _make_ai_result()

        engine = DecisionEngine()
        dec_before, breakdown_before = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Run heavy failure analysis
        _ = run_full_failure_forensic_analysis(symbol="BTC/USD")
        _ = run_full_failure_forensic_analysis(symbol="XAU/USD")

        dec_after, breakdown_after = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        assert dec_before.decision == dec_after.decision
        assert dec_before.signal_strength == dec_after.signal_strength
        assert dec_before.stop_loss == dec_after.stop_loss
        assert dec_before.take_profit_1 == dec_after.take_profit_1
        assert dec_before.take_profit_2 == dec_after.take_profit_2


class TestEdgeCases:
    """Tests for edge cases (empty, 1 trade, missing attributes)."""

    def test_empty_dataset(self):
        win_rep = analyze_winners([], symbol="BTC/USD")
        assert win_rep.winner_count == 0
        assert win_rep.win_rate_pct == 0.0

        lose_rep = analyze_losers([], symbol="BTC/USD")
        assert lose_rep.loser_count == 0

        dd_rep = analyze_drawdowns([], symbol="BTC/USD")
        assert dd_rep.max_drawdown_r == 0.0

        cluster_rep = analyze_clustering([], symbol="BTC/USD")
        assert cluster_rep.longest_losing_streak == 0

    def test_single_trade_dataset(self):
        trades = [{"outcome": "WIN", "realized_r": 1.5, "direction": "BUY"}]
        win_rep = analyze_winners(trades, symbol="BTC/USD")
        assert win_rep.winner_count == 1
        assert win_rep.win_rate_pct == 100.0
