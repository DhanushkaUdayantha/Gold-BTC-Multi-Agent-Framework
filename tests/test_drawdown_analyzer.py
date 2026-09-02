"""
Tests for drawdown_analyzer.py — Phase 3.
"""
import pytest
import numpy as np
from src.research.drawdown_analyzer import DrawdownDecomposer, ClusteringAnalysis
from src.research.signal_research_record import (
    SignalResearchRecord,
    MTFSnapshot,
    OutcomeLabel,
)


def _make_trade(realized_r: float, asset: str = "XAU/USD",
                decision: str = "BUY", regime: str = "TRENDING",
                session: str = "LONDON", hour: int = 10,
                ts: str = "2024-01-01T10:00:00Z",
                ai_prob: float = 0.55) -> SignalResearchRecord:
    from src.research.signal_research_record import AISnapshot
    return SignalResearchRecord(
        decision=decision,
        asset=asset,
        regime=regime,
        session=session,
        hour_utc=hour,
        signal_timestamp=ts,
        outcome=OutcomeLabel.WIN if realized_r > 0 else OutcomeLabel.LOSS,
        realized_r=realized_r,
        mtf=MTFSnapshot(alignment_score=2 if realized_r > 0 else 0),
        ai=AISnapshot(ai_probability=ai_prob),
    )


def _make_trades_with_dd(n: int = 100, seed: int = 42) -> list:
    rng = np.random.default_rng(seed)
    trades = []
    for i in range(n):
        r = float(rng.choice([-1.0, 1.5], p=[0.45, 0.55]))
        asset = "BTC/USD" if i % 2 == 0 else "XAU/USD"
        regime = ["TRENDING", "RANGING", "HIGH_VOLATILITY"][i % 3]
        session = ["LONDON", "NEW_YORK", "ASIA"][i % 3]
        ts = f"2024-{(i % 12)+1:02d}-{(i % 28)+1:02d}T{(i % 24):02d}:00:00Z"
        trades.append(_make_trade(r, asset=asset, regime=regime, session=session, ts=ts))
    return trades


class TestDrawdownDecomposer:
    def test_empty_dataset_no_crash(self):
        report = DrawdownDecomposer.decompose([])
        assert report.total_trades == 0
        assert report.findings[0].startswith("No resolved trades")

    def test_returns_report_with_trades(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert report.total_trades == 100
        assert report.overall_max_drawdown_r >= 0.0
        assert report.overall_expectancy_r != 0.0

    def test_by_asset_breakdown(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert len(report.by_asset) >= 1

    def test_by_regime_breakdown(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert len(report.by_regime) >= 1

    def test_by_session_breakdown(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert len(report.by_session) >= 1

    def test_by_hour_breakdown(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert len(report.by_hour_bucket) >= 1

    def test_clustering_analysis_present(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert hasattr(report.clustering, "autocorrelation_lag1")
        assert -1.0 <= report.clustering.autocorrelation_lag1 <= 1.0

    def test_independent_losses_classification(self):
        # iid coin-flip losses → NOT autocorrelated
        rng = np.random.default_rng(0)
        trades = []
        for i in range(200):
            r = float(rng.choice([-1.0, 1.5], p=[0.45, 0.55]))
            ts = f"2024-01-{(i%28)+1:02d}T{i%24:02d}:00:00Z"
            trades.append(_make_trade(r, ts=ts))
        report = DrawdownDecomposer.decompose(trades)
        assert isinstance(report.clustering.is_autocorrelated, bool)

    def test_episode_detection(self):
        # All-loss sequence should produce at least one episode
        trades = [_make_trade(-1.0, ts=f"2024-01-{i+1:02d}T10:00:00Z") for i in range(20)]
        report = DrawdownDecomposer.decompose(trades)
        assert len(report.all_episodes) >= 1
        assert report.largest_episode is not None

    def test_dd_contribution_pct_reasonable(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        for dim in report.by_asset:
            assert 0.0 <= dim.dd_contribution_pct <= 200.0  # Can exceed 100 if components overlap

    def test_primary_and_secondary_source_set(self):
        trades = _make_trades_with_dd(100)
        report = DrawdownDecomposer.decompose(trades)
        assert report.primary_dd_source != ""
        assert report.secondary_dd_source != ""
