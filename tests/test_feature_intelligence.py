"""
Unit tests for FeatureIntelligenceEngine — Phase 4.
"""
import pytest
from src.research.feature_intelligence import (
    FeatureIntelligenceEngine,
    ProbabilityQualityReport,
    StrengthQualityReport,
)
from src.research.signal_research_record import (
    SignalResearchRecord,
    MTFSnapshot,
    IndicatorSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    OutcomeLabel,
)


def _make_dummy_records(n=100) -> list:
    records = []
    for i in range(n):
        is_win = (i % 2 == 0)
        real_r = 1.5 if is_win else -1.0
        prob = 0.65 if is_win else 0.45
        confluence = 75 if is_win else 55
        records.append(SignalResearchRecord(
            signal_id=f"SIG_{i:04d}",
            asset="BTC/USD" if i % 2 == 0 else "XAU/USD",
            signal_timestamp=f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
            decision="BUY" if i % 3 != 0 else "SELL",
            outcome=OutcomeLabel.WIN if is_win else OutcomeLabel.LOSS,
            realized_r=real_r,
            mae_r=0.3 if is_win else 1.1,
            mfe_r=2.0 if is_win else 0.4,
            indicators=IndicatorSnapshot(
                vwap_aligned=is_win,
                ema_aligned=is_win,
                sr_aligned=is_win,
                momentum_aligned=is_win,
                smc_aligned=is_win,
            ),
            mtf=MTFSnapshot(htf_aligned=is_win, alignment_score=3 if is_win else 0),
            strategy_scores=StrategyScoreSnapshot(confluence_score=confluence, confirmation_score=3 if is_win else 1),
            ai=AISnapshot(ai_probability=prob, ai_confidence="HIGH" if is_win else "LOW"),
        ))
    return records


class TestFeatureIntelligence:
    def test_evaluate_feature_contributions(self):
        records = _make_dummy_records(100)
        results = FeatureIntelligenceEngine.evaluate_feature_contributions(records)
        assert len(results) >= 8
        htf_res = next((r for r in results if r.feature_name == "HTF_ALIGNMENT"), None)
        assert htf_res is not None
        assert htf_res.sample_size == 50
        assert htf_res.win_rate_pct == 100.0
        assert htf_res.classification in ("STRONG POSITIVE", "POSITIVE")

    def test_evaluate_feature_interactions(self):
        records = _make_dummy_records(100)
        results = FeatureIntelligenceEngine.evaluate_feature_interactions(records)
        assert len(results) >= 5
        for r in results:
            assert r.classification in ("ROBUST INTERACTION", "PROMISING INTERACTION", "NO VALUE", "HARMFUL", "UNSTABLE INTERACTION")

    def test_evaluate_probability_quality(self):
        records = _make_dummy_records(100)
        report = FeatureIntelligenceEngine.evaluate_probability_quality(records)
        assert isinstance(report, ProbabilityQualityReport)
        assert report.total_trades == 100
        assert 0.0 <= report.brier_score <= 0.5
        assert 0.0 <= report.ece <= 1.0
        assert len(report.buckets) == 10

    def test_evaluate_strength_quality(self):
        records = _make_dummy_records(100)
        report = FeatureIntelligenceEngine.evaluate_strength_quality(records)
        assert isinstance(report, StrengthQualityReport)
        assert report.total_trades == 100
        assert len(report.bands) == 6
