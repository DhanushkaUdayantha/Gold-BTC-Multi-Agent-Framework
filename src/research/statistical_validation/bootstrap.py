"""
Bootstrap Statistical Resampling Module.

Implements 10,000-iteration non-parametric bootstrap resampling to produce empirical
confidence intervals for trading performance metrics (Expectancy, Win Rate, Total R).

CRITICAL REQUIREMENT:
Distinguishes real sample size (Real N) from simulated bootstrap resamples (Bootstrap Resamples = 10,000).
Never reports bootstrap sample count as real observations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MetricBootstrapCI:
    """Confidence interval and distribution statistics for a single metric."""
    metric_name: str
    real_n: int
    bootstrap_resamples: int
    point_estimate: float
    mean: float
    median: float
    std_error: float
    ci_lower_2_5: float
    ci_upper_97_5: float
    confidence_level: float = 0.95
    p_positive: float = 0.0  # Probability that metric > 0


@dataclass
class BootstrapResult:
    """Consolidated bootstrap validation output across all core trading metrics."""
    symbol: str
    real_n: int
    bootstrap_resamples: int
    seed: int
    expectancy_r: MetricBootstrapCI
    total_r: MetricBootstrapCI
    win_rate_pct: MetricBootstrapCI
    status: str  # "STABLE", "PROMISING", "INSUFFICIENT_SAMPLE", "INCONCLUSIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_bootstrap_validation(
    r_multiples: List[float],
    symbol: str = "BTC/USD",
    n_resamples: int = 10000,
    seed: int = 42,
    confidence: float = 0.95,
) -> BootstrapResult:
    """
    Run 10,000 bootstrap resamples on realized R outcomes.
    
    Args:
        r_multiples: List of realized R multiples (e.g. [+1.5, -1.0, +1.5, -1.0, ...])
        symbol: Asset identifier ("BTC/USD" or "XAU/USD")
        n_resamples: Number of bootstrap iterations (default: 10,000)
        seed: Random seed for deterministic reproducibility
        confidence: Confidence level (default: 0.95)
        
    Returns:
        BootstrapResult containing CIs for Expectancy, Total R, and Win Rate.
    """
    real_n = len(r_multiples)
    if real_n == 0:
        empty_ci = MetricBootstrapCI("EMPTY", 0, n_resamples, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, confidence, 0.0)
        return BootstrapResult(
            symbol=symbol,
            real_n=0,
            bootstrap_resamples=n_resamples,
            seed=seed,
            expectancy_r=empty_ci,
            total_r=empty_ci,
            win_rate_pct=empty_ci,
            status="INSUFFICIENT_SAMPLE",
        )

    arr = np.array(r_multiples, dtype=float)
    rng = np.random.default_rng(seed)

    # 1. Generate bootstrap resample indices of shape (n_resamples, real_n)
    sample_indices = rng.integers(0, real_n, size=(n_resamples, real_n))
    resampled_r = arr[sample_indices]  # Shape: (10000, real_n)

    # 2. Compute resampled metrics
    # Expectancy (mean R per trade)
    resampled_means = np.mean(resampled_r, axis=1)
    # Total R (sum R over real_n sample length)
    resampled_sums = np.sum(resampled_r, axis=1)
    # Win Rate (%)
    resampled_wins = np.mean(resampled_r > 0, axis=1) * 100.0

    # 3. Compute Percentiles (2.5% and 97.5% for 95% CI)
    alpha = (1.0 - confidence) / 2.0 * 100.0
    p_lower = alpha
    p_upper = 100.0 - alpha

    # Helper to build MetricBootstrapCI
    def build_ci(metric_name: str, point_est: float, samples: np.ndarray, is_pct: bool = False) -> MetricBootstrapCI:
        ci_low = float(np.percentile(samples, p_lower))
        ci_high = float(np.percentile(samples, p_upper))
        mean_val = float(np.mean(samples))
        med_val = float(np.median(samples))
        std_err = float(np.std(samples, ddof=1))
        p_pos = float(np.mean(samples > 0))

        decimals = 2 if is_pct else 4
        return MetricBootstrapCI(
            metric_name=metric_name,
            real_n=real_n,
            bootstrap_resamples=n_resamples,
            point_estimate=round(point_est, decimals),
            mean=round(mean_val, decimals),
            median=round(med_val, decimals),
            std_error=round(std_err, decimals),
            ci_lower_2_5=round(ci_low, decimals),
            ci_upper_97_5=round(ci_high, decimals),
            confidence_level=confidence,
            p_positive=round(p_pos, 4),
        )

    point_ev = float(np.mean(arr))
    point_tot_r = float(np.sum(arr))
    point_wr = float(np.mean(arr > 0) * 100.0)

    ev_ci = build_ci("Expectancy_R", point_ev, resampled_means, is_pct=False)
    tot_ci = build_ci("Total_R", point_tot_r, resampled_sums, is_pct=False)
    wr_ci = build_ci("Win_Rate_Pct", point_wr, resampled_wins, is_pct=True)

    # Determine status
    if real_n < 25:
        status = "INSUFFICIENT_SAMPLE"
    elif ev_ci.ci_lower_2_5 > 0:
        status = "STABLE"
    elif ev_ci.mean > 0 and ev_ci.p_positive >= 0.75:
        status = "PROMISING"
    else:
        status = "INCONCLUSIVE"

    return BootstrapResult(
        symbol=symbol,
        real_n=real_n,
        bootstrap_resamples=n_resamples,
        seed=seed,
        expectancy_r=ev_ci,
        total_r=tot_ci,
        win_rate_pct=wr_ci,
        status=status,
    )
