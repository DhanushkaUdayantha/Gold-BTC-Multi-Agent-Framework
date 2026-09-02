"""
Tests for robustness_score.py — Phase 3.
"""
import pytest
from src.research.robustness_score import (
    RobustnessScorer,
    TOTAL_MAX,
    MAX_SCORES,
)


class TestRobustnessScorer:
    def test_total_max_points_is_100(self):
        assert TOTAL_MAX == 100

    def test_perfect_strategy_scores_high(self):
        score_res = RobustnessScorer.score(
            strategy_label="Perfect_Strategy",
            expectancy_r=0.30,
            profit_factor=2.0,
            max_drawdown_r=5.0,
            oos_expectancy=0.25,
            wf_positive_ratio=1.0,
            wf_median_expectancy=0.20,
            calibration_brier=0.15,
            calibration_ece=0.03,
            regime_positive_pct=0.90,
            asset_max_dd_ratio=0.95,
            session_positive_pct=0.90,
            stress_passes_slippage=True,
            stress_passes_execution=True,
            p_value=0.0001,
            sample_size=300,
            overfitting_risk="LOW",
        )
        assert score_res.total_score >= 85.0
        assert score_res.grade == "A"
        assert len(score_res.strong_areas) > 0
        assert len(score_res.weak_areas) == 0

    def test_failing_strategy_scores_low(self):
        score_res = RobustnessScorer.score(
            strategy_label="Failing_Strategy",
            expectancy_r=-0.10,
            profit_factor=0.8,
            max_drawdown_r=45.0,
            oos_expectancy=-0.15,
            wf_positive_ratio=0.2,
            wf_median_expectancy=-0.05,
            calibration_brier=0.28,
            calibration_ece=0.15,
            regime_positive_pct=0.20,
            asset_max_dd_ratio=0.2,
            session_positive_pct=0.20,
            stress_passes_slippage=False,
            stress_passes_execution=False,
            p_value=0.50,
            sample_size=300,
            overfitting_risk="CRITICAL",
        )
        assert score_res.total_score < 40.0
        assert score_res.grade == "F"
        assert len(score_res.weak_areas) > 0

    def test_overfitting_penalty_applied(self):
        base_kwargs = dict(
            strategy_label="Test_Penalty",
            expectancy_r=0.20,
            profit_factor=1.4,
            max_drawdown_r=12.0,
            oos_expectancy=0.10,
            wf_positive_ratio=0.8,
            wf_median_expectancy=0.10,
            calibration_brier=0.18,
            calibration_ece=0.05,
            regime_positive_pct=0.80,
            asset_max_dd_ratio=0.85,
            session_positive_pct=0.80,
            stress_passes_slippage=True,
            stress_passes_execution=True,
            p_value=0.005,
            sample_size=200,
        )
        score_low = RobustnessScorer.score(**base_kwargs, overfitting_risk="LOW")
        score_crit = RobustnessScorer.score(**base_kwargs, overfitting_risk="CRITICAL")
        # 10 point penalty for CRITICAL
        assert score_low.total_score - score_crit.total_score == pytest.approx(10.0, abs=0.1)

    def test_all_11_dimensions_evaluated(self):
        score_res = RobustnessScorer.score(
            strategy_label="Dimension_Check",
            expectancy_r=0.15,
            profit_factor=1.3,
            max_drawdown_r=15.0,
            oos_expectancy=0.08,
            wf_positive_ratio=0.75,
            wf_median_expectancy=0.05,
            calibration_brier=0.20,
            calibration_ece=0.08,
            regime_positive_pct=0.70,
            asset_max_dd_ratio=0.80,
            session_positive_pct=0.70,
            stress_passes_slippage=True,
            stress_passes_execution=True,
            p_value=0.02,
            sample_size=150,
            overfitting_risk="LOW",
        )
        assert len(score_res.dimensions) == 11
        dim_names = {d.dimension for d in score_res.dimensions}
        assert dim_names == set(MAX_SCORES.keys())
