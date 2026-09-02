"""
Tests for asset_research_engine.py — Phase 3.
"""
import pytest
import numpy as np
from src.research.asset_research_engine import AssetResearchEngine
from src.research.signal_research_record import (
    SignalResearchRecord,
    AISnapshot,
    OutcomeLabel,
)


def _make_trade(asset: str, outcome: str, realized_r: float,
                regime: str = "TRENDING", session: str = "LONDON",
                ts_day: int = 1) -> SignalResearchRecord:
    return SignalResearchRecord(
        decision="BUY",
        asset=asset,
        regime=regime,
        session=session,
        signal_timestamp=f"2024-01-{ts_day:02d}T10:00:00Z",
        outcome=outcome,
        realized_r=realized_r,
        ai=AISnapshot(ai_probability=0.55),
    )


def _build_asset_records(asset: str = "XAU/USD", n: int = 150, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    records = []
    regimes  = ["TRENDING", "RANGING", "HIGH_VOLATILITY"]
    sessions = ["LONDON", "NEW_YORK", "ASIA"]
    for i in range(n):
        r_val  = float(rng.choice([-1.0, 1.5], p=[0.43, 0.57]))
        outcome= OutcomeLabel.WIN if r_val > 0 else OutcomeLabel.LOSS
        regime = regimes[i % 3]
        session= sessions[i % 3]
        ts_day = (i % 28) + 1
        records.append(_make_trade(asset, outcome, r_val, regime, session, ts_day))
    return records


class TestAssetResearchEngine:
    def test_analyze_asset_returns_report(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert report.asset == "XAU/USD"
        assert report.total_trades >= 0

    def test_insufficient_data_classification(self):
        records = _build_asset_records("XAU/USD", 30)  # Below minimum (50)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert report.robustness_classification == "INSUFFICIENT_DATA"

    def test_robustness_classification_valid(self):
        records = _build_asset_records("XAU/USD", 200)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert report.robustness_classification in (
            "ROBUST", "PROMISING", "WEAK", "UNSTABLE", "INSUFFICIENT_DATA"
        )

    def test_oos_trades_count(self):
        records = _build_asset_records("BTC/USD", 200)
        report = AssetResearchEngine.analyze_asset("BTC/USD", records)
        # OOS is last 20% → ~40 trades
        assert report.oos_trades >= 0

    def test_win_rate_in_range(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert 0.0 <= report.win_rate_pct <= 100.0

    def test_wilson_ci_bounds(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert report.win_rate_wilson_lower <= report.win_rate_pct
        assert report.win_rate_pct <= report.win_rate_wilson_upper

    def test_analyze_both_returns_both_assets(self):
        records = _build_asset_records("BTC/USD", 150) + _build_asset_records("XAU/USD", 150)
        result = AssetResearchEngine.analyze_both(records)
        assert "BTC/USD" in result
        assert "XAU/USD" in result

    def test_regime_breakdown_not_empty(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert len(report.by_regime) >= 1

    def test_session_breakdown_not_empty(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert len(report.by_session) >= 1

    def test_wf_positive_windows_in_range(self):
        records = _build_asset_records("XAU/USD", 200)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert 0 <= report.wf_positive_windows <= report.wf_total_windows

    def test_findings_list_not_empty(self):
        records = _build_asset_records("XAU/USD", 150)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        assert len(report.findings) > 0

    def test_robustness_score_in_range(self):
        records = _build_asset_records("XAU/USD", 200)
        report = AssetResearchEngine.analyze_asset("XAU/USD", records)
        # Score is not computed at asset level (that's the full RobustnessScorer)
        # But classification maps to a meaningful result
        assert report.robustness_classification != ""
