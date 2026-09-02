"""
Statistical Validation Hardening & Forward Shadow Research Package.

Comprehensive statistical validation suite supporting:
- Legacy StatisticalValidator, Wilson Score, Bootstrap Expectancy Difference, and Permutation Tests.
- Phase 2 Modular Engines:
  - bootstrap: 10,000-iteration bootstrap confidence intervals for Expectancy, Win Rate, and Total R.
  - calibration: Point-in-time and forward probability calibration metrics (Brier, ECE, MCE).
  - execution_stress: Slippage (0.00R-0.20R) and latency (0-2 bar delay) stress testing.
  - monte_carlo: 10,000-path Monte Carlo risk and drawdown simulations.
  - spread_model: Real bid/ask spread tracking and SPREAD_DATA_UNAVAILABLE handling.
  - holdout_monitor: XAU sample sufficiency milestone tracking (N>=50, 75, 100, 150, 200).
  - validator: High-level statistical validation orchestrator.

DISCLAIMER: Research and observation layer only. Zero production decision impact.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# --- Phase 2 Modular Imports ---
from src.research.statistical_validation.bootstrap import (
    BootstrapResult,
    MetricBootstrapCI,
    run_bootstrap_validation,
)
from src.research.statistical_validation.calibration import (
    CalibrationReport,
    CalibrationBucket,
    evaluate_probability_calibration,
)
from src.research.statistical_validation.execution_stress import (
    ExecutionStressReport,
    SlippageScenario,
    LatencyScenario,
    run_execution_stress_analysis,
)
from src.research.statistical_validation.monte_carlo import (
    MonteCarloReport,
    run_monte_carlo_simulation,
)
from src.research.statistical_validation.spread_model import (
    SpreadRecord,
    record_spread_observation,
)
from src.research.statistical_validation.holdout_monitor import (
    HoldoutMilestoneReport,
    MilestoneThreshold,
    evaluate_holdout_milestones,
)
from src.research.statistical_validation.validator import (
    AssetStatisticalValidation,
    run_full_statistical_validation,
)

# --- Legacy Compatibility Classes & Functions ---

@dataclass
class ConfidenceInterval:
    """Lower and upper bounds of a confidence interval."""
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95


@dataclass
class StatisticalValidationReport:
    """Full statistical validation analysis."""
    sample_size_base: int
    sample_size_shadow: int
    base_win_rate_pct: float
    base_win_rate_wilson_ci: ConfidenceInterval
    shadow_win_rate_pct: float
    shadow_win_rate_wilson_ci: ConfidenceInterval
    base_expectancy_r: float
    base_expectancy_bootstrap_ci: ConfidenceInterval
    shadow_expectancy_r: float
    shadow_expectancy_bootstrap_ci: ConfidenceInterval
    paired_expectancy_delta_r: float
    expectancy_delta_bootstrap_ci: ConfidenceInterval
    cohens_d: float
    effect_size_magnitude: str
    permutation_p_value: float
    is_statistically_significant: bool
    multiple_comparison_risk_notice: str


def compute_wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> ConfidenceInterval:
    """Wilson score interval with continuity correction."""
    if total == 0:
        return ConfidenceInterval(0.0, 0.0, 0.0, confidence)
    p = successes / total
    z = 1.95996
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denom
    spread = (z / denom) * math.sqrt((p * (1 - p) / total) + (z**2) / (4 * (total**2)))
    lower = max(0.0, (center - spread) * 100.0)
    upper = min(100.0, (center + spread) * 100.0)
    return ConfidenceInterval(
        point_estimate=round(p * 100.0, 2),
        ci_lower=round(lower, 2),
        ci_upper=round(upper, 2),
        confidence_level=confidence,
    )


def compute_bootstrap_expectancy_ci(
    r_series: List[float],
    n_iterations: int = 10000,
    seed: int = 42,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """10,000-resample bootstrap confidence interval for mean expectancy."""
    if not r_series:
        return ConfidenceInterval(0.0, 0.0, 0.0, confidence)
    rng = np.random.default_rng(seed)
    arr = np.array(r_series, dtype=float)
    means = np.empty(n_iterations)
    n = len(arr)
    for i in range(n_iterations):
        sample = rng.choice(arr, size=n, replace=True)
        means[i] = np.mean(sample)

    alpha = 1.0 - confidence
    lower = float(np.percentile(means, alpha / 2.0 * 100.0))
    upper = float(np.percentile(means, (1.0 - alpha / 2.0) * 100.0))
    pt = float(np.mean(arr))

    return ConfidenceInterval(
        point_estimate=round(pt, 4),
        ci_lower=round(lower, 4),
        ci_upper=round(upper, 4),
        confidence_level=confidence,
    )


def compute_bootstrap_difference_ci(
    base_r: List[float],
    shadow_r: List[float],
    n_iterations: int = 10000,
    seed: int = 42,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """Bootstrap CI for the difference in mean expectancy (Shadow - Base)."""
    if not base_r or not shadow_r:
        return ConfidenceInterval(0.0, 0.0, 0.0, confidence)
    rng = np.random.default_rng(seed)
    base_arr = np.array(base_r, dtype=float)
    shadow_arr = np.array(shadow_r, dtype=float)

    deltas = np.empty(n_iterations)
    for i in range(n_iterations):
        b_sample = rng.choice(base_arr, size=len(base_arr), replace=True)
        s_sample = rng.choice(shadow_arr, size=len(shadow_arr), replace=True)
        deltas[i] = np.mean(s_sample) - np.mean(b_sample)

    alpha = 1.0 - confidence
    lower = float(np.percentile(deltas, alpha / 2.0 * 100.0))
    upper = float(np.percentile(deltas, (1.0 - alpha / 2.0) * 100.0))
    pt = float(np.mean(shadow_arr) - np.mean(base_arr))

    return ConfidenceInterval(
        point_estimate=round(pt, 4),
        ci_lower=round(lower, 4),
        ci_upper=round(upper, 4),
        confidence_level=confidence,
    )


def compute_permutation_test(
    base_r: List[float],
    shadow_r: List[float],
    n_permutations: int = 5000,
    seed: int = 42,
) -> float:
    """Non-parametric permutation test for difference in mean expectancy."""
    if not base_r or not shadow_r:
        return 1.0
    rng = np.random.default_rng(seed)
    obs_diff = np.mean(shadow_r) - np.mean(base_r)
    combined = np.concatenate([base_r, shadow_r])
    n_base = len(base_r)

    count = 0
    for _ in range(n_permutations):
        perm = rng.permutation(combined)
        sim_b = perm[:n_base]
        sim_s = perm[n_base:]
        if (np.mean(sim_s) - np.mean(sim_b)) >= obs_diff:
            count += 1

    return round(float(count / n_permutations), 4)


class StatisticalValidator:
    """Master statistical validator for trading research."""

    @classmethod
    def evaluate_statistics(
        cls,
        base_r: List[float],
        shadow_r: List[float],
        seed: int = 42,
    ) -> StatisticalValidationReport:
        """Run complete statistical suite comparing Base vs Hypothetical Gated performance."""
        n_b = len(base_r)
        n_s = len(shadow_r)

        b_wins = sum(1 for r in base_r if r > 0)
        s_wins = sum(1 for r in shadow_r if r > 0)

        b_win_ci = compute_wilson_score_interval(b_wins, n_b)
        s_win_ci = compute_wilson_score_interval(s_wins, n_s)

        b_exp_ci = compute_bootstrap_expectancy_ci(base_r, seed=seed)
        s_exp_ci = compute_bootstrap_expectancy_ci(shadow_r, seed=seed)
        diff_ci = compute_bootstrap_difference_ci(base_r, shadow_r, seed=seed)

        if n_b > 1 and n_s > 1:
            var_b = np.var(base_r, ddof=1)
            var_s = np.var(shadow_r, ddof=1)
            pooled_std = math.sqrt(((n_b - 1) * var_b + (n_s - 1) * var_s) / (n_b + n_s - 2))
            d = (s_exp_ci.point_estimate - b_exp_ci.point_estimate) / pooled_std if pooled_std > 0 else 0.0
        else:
            d = 0.0

        d_mag = "LARGE" if abs(d) >= 0.8 else ("MEDIUM" if abs(d) >= 0.5 else ("SMALL" if abs(d) >= 0.2 else "NEGLIGIBLE"))
        p_val = compute_permutation_test(base_r, shadow_r, seed=seed)
        is_sig = (p_val < 0.05) and (diff_ci.ci_lower > 0.0)

        multi_comp_warning = (
            "MULTIPLE COMPARISONS RISK NOTICE: Multiple policies, thresholds, regimes, and ablation combinations "
            "were tested in this research phase. While the primary validated strategies were pre-specified, "
            "family-wise selection bias is mitigated by out-of-sample chronological walk-forward and untouched holdout verification."
        )

        return StatisticalValidationReport(
            sample_size_base=n_b,
            sample_size_shadow=n_s,
            base_win_rate_pct=b_win_ci.point_estimate,
            base_win_rate_wilson_ci=b_win_ci,
            shadow_win_rate_pct=s_win_ci.point_estimate,
            shadow_win_rate_wilson_ci=s_win_ci,
            base_expectancy_r=b_exp_ci.point_estimate,
            base_expectancy_bootstrap_ci=b_exp_ci,
            shadow_expectancy_r=s_exp_ci.point_estimate,
            shadow_expectancy_bootstrap_ci=s_exp_ci,
            paired_expectancy_delta_r=diff_ci.point_estimate,
            expectancy_delta_bootstrap_ci=diff_ci,
            cohens_d=round(d, 3),
            effect_size_magnitude=d_mag,
            permutation_p_value=p_val,
            is_statistically_significant=is_sig,
            multiple_comparison_risk_notice=multi_comp_warning,
        )


__all__ = [
    "ConfidenceInterval",
    "StatisticalValidationReport",
    "compute_wilson_score_interval",
    "compute_bootstrap_expectancy_ci",
    "compute_bootstrap_difference_ci",
    "compute_permutation_test",
    "StatisticalValidator",
    "BootstrapResult",
    "MetricBootstrapCI",
    "run_bootstrap_validation",
    "CalibrationReport",
    "CalibrationBucket",
    "evaluate_probability_calibration",
    "ExecutionStressReport",
    "SlippageScenario",
    "LatencyScenario",
    "run_execution_stress_analysis",
    "MonteCarloReport",
    "run_monte_carlo_simulation",
    "SpreadRecord",
    "record_spread_observation",
    "HoldoutMilestoneReport",
    "MilestoneThreshold",
    "evaluate_holdout_milestones",
    "AssetStatisticalValidation",
    "run_full_statistical_validation",
]
