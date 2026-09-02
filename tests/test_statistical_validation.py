"""
Unit tests for statistical validation and bootstrap engine.
"""
from src.research.statistical_validation import (
    StatisticalValidator,
    compute_bootstrap_difference_ci,
    compute_bootstrap_expectancy_ci,
    compute_permutation_test,
    compute_wilson_score_interval,
)


def test_wilson_score_interval():
    ci = compute_wilson_score_interval(successes=50, total=100)
    assert ci.point_estimate == 50.0
    assert 40.0 < ci.ci_lower < 50.0
    assert 50.0 < ci.ci_upper < 60.0


def test_bootstrap_expectancy_ci():
    r_series = [1.0, 1.0, 1.0, -1.0, 1.0] * 20  # 100 trades, exp = 0.60R
    ci = compute_bootstrap_expectancy_ci(r_series, n_iterations=1000, seed=42)
    assert ci.point_estimate == 0.60
    assert 0.40 < ci.ci_lower < 0.60
    assert 0.60 < ci.ci_upper < 0.80


def test_statistical_validator_report():
    base_r = [-1.0, 1.0, -1.0, -1.0, 1.0] * 40   # 200 trades, 40% WR, exp = -0.20R
    shadow_r = [1.0, 1.0, -1.0, 1.0, 1.0] * 40    # 200 trades, 80% WR, exp = +0.60R

    report = StatisticalValidator.evaluate_statistics(base_r, shadow_r, seed=42)
    assert report.is_statistically_significant is True
    assert report.permutation_p_value < 0.01
    assert report.cohens_d > 0.5
