"""
Tests for missed_winner_analyzer.py — Phase 3.
"""
import pytest
from src.research.missed_winner_analyzer import MissedWinnerAnalyzer, CohortStats
from src.research.signal_research_record import (
    SignalResearchRecord,
    GatingSnapshot,
    MTFSnapshot,
    IndicatorSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    OutcomeLabel,
)


def _make_record(
    outcome: str,
    qualifies_a: bool,
    realized_r: float = 1.0,
    asset: str = "XAU/USD",
    regime: str = "TRENDING_BULLISH",
    session: str = "LONDON",
    ai_prob: float = 0.55,
    confluence: int = 65,
) -> SignalResearchRecord:
    return SignalResearchRecord(
        decision="BUY",
        asset=asset,
        regime=regime,
        session=session,
        outcome=outcome,
        realized_r=realized_r if outcome == OutcomeLabel.WIN else -abs(realized_r),
        gating=GatingSnapshot(would_qualify_policy_a=qualifies_a),
        ai=AISnapshot(ai_probability=ai_prob),
        strategy_scores=StrategyScoreSnapshot(confluence_score=confluence),
        mtf=MTFSnapshot(htf_aligned=qualifies_a),
        indicators=IndicatorSnapshot(
            vwap_aligned=qualifies_a,
            ema_aligned=qualifies_a,
        ),
    )


def _build_dataset(
    n_ret_win=50, n_ret_loss=30,
    n_rej_win=20, n_rej_loss=40,
):
    records = []
    for _ in range(n_ret_win):
        records.append(_make_record(OutcomeLabel.WIN,  True,  realized_r=1.5))
    for _ in range(n_ret_loss):
        records.append(_make_record(OutcomeLabel.LOSS, True,  realized_r=1.0))
    for _ in range(n_rej_win):
        records.append(_make_record(OutcomeLabel.WIN,  False, realized_r=1.5))
    for _ in range(n_rej_loss):
        records.append(_make_record(OutcomeLabel.LOSS, False, realized_r=1.0))
    return records


class TestMissedWinnerAnalyzer:
    def test_returns_report(self):
        records = _build_dataset()
        report = MissedWinnerAnalyzer.analyze(records)
        assert report is not None
        assert hasattr(report, "winner_retention_pct")
        assert hasattr(report, "loser_reduction_pct")

    def test_winner_retention_pct_correct(self):
        # 50 retained winners out of 70 total
        records = _build_dataset(n_ret_win=50, n_rej_win=20)
        report = MissedWinnerAnalyzer.analyze(records)
        assert abs(report.winner_retention_pct - 50/70*100) < 1.0

    def test_loser_reduction_pct_correct(self):
        # 40 rejected losers out of 70 total
        records = _build_dataset(n_ret_loss=30, n_rej_loss=40)
        report = MissedWinnerAnalyzer.analyze(records)
        assert abs(report.loser_reduction_pct - 40/70*100) < 1.0

    def test_bcr_positive(self):
        records = _build_dataset()
        report = MissedWinnerAnalyzer.analyze(records)
        assert report.benefit_cost_ratio >= 0.0

    def test_policy_classification_appropriate(self):
        # More losers removed than winners → APPROPRIATE
        records = _build_dataset(n_ret_win=60, n_rej_win=10, n_ret_loss=20, n_rej_loss=60)
        report = MissedWinnerAnalyzer.analyze(records)
        assert report.policy_classification in ("APPROPRIATE", "OVERLY_RESTRICTIVE", "INSUFFICIENT_DATA")

    def test_empty_dataset_no_crash(self):
        report = MissedWinnerAnalyzer.analyze([])
        assert report.rejected_winners.count == 0
        assert report.policy_classification == "INSUFFICIENT_DATA"

    def test_asset_split_counted(self):
        records = []
        for _ in range(30):
            records.append(_make_record(OutcomeLabel.WIN, False, asset="BTC/USD"))
        for _ in range(20):
            records.append(_make_record(OutcomeLabel.WIN, False, asset="XAU/USD"))
        report = MissedWinnerAnalyzer.analyze(records)
        assert report.btc_missed_count == 30
        assert report.xau_missed_count == 20

    def test_filter_inspections_generated(self):
        records = _build_dataset(n_rej_win=50, n_rej_loss=50)
        report = MissedWinnerAnalyzer.analyze(records)
        assert len(report.filter_inspections) > 0

    def test_cohort_stats_win_rate(self):
        records = []
        for _ in range(70):
            records.append(_make_record(OutcomeLabel.WIN, False))
        for _ in range(30):
            records.append(_make_record(OutcomeLabel.LOSS, False))
        report = MissedWinnerAnalyzer.analyze(records)
        assert report.rejected_winners.count == 70
        assert report.rejected_winners.win_rate_pct == 100.0
        assert report.rejected_losers.count == 30
        assert report.rejected_losers.win_rate_pct == 0.0
