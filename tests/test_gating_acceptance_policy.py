"""
Unit tests for fixed gating acceptance policy v1.0.
"""
from src.research.gating_acceptance_policy import (
    GATING_RESEARCH_POLICY_VERSION,
    GovernanceClassification,
    PolicyThresholds,
    ThresholdStatus,
    evaluate_acceptance_policy,
)


def test_acceptance_policy_all_pass():
    # Ideal robust strategy results
    res = evaluate_acceptance_policy(
        sample_size=800,
        expectancy_r=0.25,
        profit_factor=1.50,
        total_realized_r=200.0,
        max_drawdown_r=10.0,
        rolling_50_negative_ratio=0.05,
        median_rolling_exp=0.22,
        walk_forward_pos_ratio=1.0,
        holdout_expectancy_r=0.20,
        winner_retention_ratio=0.45,
        loser_reduction_ratio=0.65,
        expectancy_at_010_slippage=0.15,
    )
    assert res.overall_status == GovernanceClassification.PROMOTE_TO_GATING_RESEARCH
    assert res.failed_count == 0
    assert len(res.critical_failures) == 0


def test_acceptance_policy_drawdown_failure_keep_advisory():
    # Positive expectancy but drawdown exceeds allowable benchmark limit (10.5 * 1.25 = 13.125R)
    res = evaluate_acceptance_policy(
        sample_size=900,
        expectancy_r=0.23,
        profit_factor=1.45,
        total_realized_r=210.0,
        max_drawdown_r=30.0,  # Fails 13.125R benchmark
        rolling_50_negative_ratio=0.0,
        median_rolling_exp=0.23,
        walk_forward_pos_ratio=1.0,
        holdout_expectancy_r=0.17,
        winner_retention_ratio=0.42,
        loser_reduction_ratio=0.67,
        expectancy_at_010_slippage=0.13,
    )
    assert res.overall_status == GovernanceClassification.KEEP_ADVISORY
    assert "max_drawdown" in res.checks
    assert res.checks["max_drawdown"]["status"] == ThresholdStatus.FAILED


def test_acceptance_policy_severe_failure_reject():
    # Negative expectancy, low profit factor
    res = evaluate_acceptance_policy(
        sample_size=200,  # Fails N
        expectancy_r=-0.05,  # Fails exp
        profit_factor=0.90,  # Fails PF
        total_realized_r=-10.0,
        max_drawdown_r=50.0,
        rolling_50_negative_ratio=0.40,
        median_rolling_exp=-0.05,
        walk_forward_pos_ratio=0.25,
        holdout_expectancy_r=-0.10,
        winner_retention_ratio=0.10,
        loser_reduction_ratio=0.20,
        expectancy_at_010_slippage=-0.15,
    )
    assert res.overall_status == GovernanceClassification.REJECT
    assert len(res.critical_failures) >= 5
