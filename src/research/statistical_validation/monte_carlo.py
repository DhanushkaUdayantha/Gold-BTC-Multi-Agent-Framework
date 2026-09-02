"""
Monte Carlo Simulation & Downside Risk Modeling Module.

Simulates 10,000 equity paths through non-parametric trade sequence resampling
to measure downside risk boundaries, drawdown percentiles, and loss probabilities.

Zero production trading logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloReport:
    """Consolidated Monte Carlo simulation results over 10,000 paths."""
    symbol: str
    real_n: int
    simulated_paths: int
    horizon_trades: int
    seed: int
    median_final_r: float
    percentile_5th_final_r: float
    percentile_1st_final_r: float
    median_max_drawdown_r: float
    percentile_95th_drawdown_r: float
    percentile_99th_drawdown_r: float
    p_final_r_negative: float
    p_loss_month: float  # Estimated probability of negative return over a 20-trade window
    median_max_losing_streak: int
    percentile_99th_losing_streak: int
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_max_streak(r_path: np.ndarray) -> int:
    """Compute longest contiguous streak of losing trades (R < 0)."""
    max_streak = 0
    curr_streak = 0
    for r in r_path:
        if r < 0:
            curr_streak += 1
            if curr_streak > max_streak:
                max_streak = curr_streak
        else:
            curr_streak = 0
    return max_streak


def run_monte_carlo_simulation(
    r_multiples: List[float],
    symbol: str = "BTC/USD",
    n_paths: int = 10000,
    horizon_trades: Optional[int] = None,
    seed: int = 42,
) -> MonteCarloReport:
    """
    Run 10,000 Monte Carlo path simulations.
    
    Args:
        r_multiples: List of realized R multiples
        symbol: Asset symbol
        n_paths: Number of simulated paths (default: 10,000)
        horizon_trades: Trade count per simulated path (defaults to len(r_multiples))
        seed: Random seed for reproducibility
    """
    real_n = len(r_multiples)
    if real_n == 0:
        return MonteCarloReport(
            symbol=symbol,
            real_n=0,
            simulated_paths=n_paths,
            horizon_trades=0,
            seed=seed,
            median_final_r=0.0,
            percentile_5th_final_r=0.0,
            percentile_1st_final_r=0.0,
            median_max_drawdown_r=0.0,
            percentile_95th_drawdown_r=0.0,
            percentile_99th_drawdown_r=0.0,
            p_final_r_negative=1.0,
            p_loss_month=1.0,
            median_max_losing_streak=0,
            percentile_99th_losing_streak=0,
            status="INSUFFICIENT_SAMPLE",
        )

    horizon = horizon_trades if horizon_trades and horizon_trades > 0 else real_n
    arr = np.array(r_multiples, dtype=float)
    rng = np.random.default_rng(seed)

    # Generate matrix of shape (n_paths, horizon)
    sampled_indices = rng.integers(0, real_n, size=(n_paths, horizon))
    paths_r = arr[sampled_indices]  # Shape: (10000, horizon)

    # 1. Final Realized R per path
    final_r_arr = np.sum(paths_r, axis=1)

    # 2. Maximum Drawdown per path
    cumulative_curves = np.cumsum(paths_r, axis=1)
    # Prefix with 0 at start
    padded_curves = np.pad(cumulative_curves, ((0, 0), (1, 0)), mode="constant", constant_values=0.0)
    running_max = np.maximum.accumulate(padded_curves, axis=1)
    drawdowns = running_max - padded_curves
    max_drawdowns_per_path = np.max(drawdowns, axis=1)

    # 3. Monthly Window Loss Probability (window of 20 trades)
    if horizon >= 20:
        window_20_sums = paths_r[:, :20].sum(axis=1)
        p_loss_m = float(np.mean(window_20_sums < 0))
    else:
        p_loss_m = float(np.mean(final_r_arr < 0))

    # 4. Losing Streaks
    streaks = np.array([_compute_max_streak(paths_r[i]) for i in range(min(n_paths, 2000))])

    # 5. Percentiles
    med_final = float(np.median(final_r_arr))
    p5_final = float(np.percentile(final_r_arr, 5.0))
    p1_final = float(np.percentile(final_r_arr, 1.0))

    med_dd = float(np.median(max_drawdowns_per_path))
    p95_dd = float(np.percentile(max_drawdowns_per_path, 95.0))
    p99_dd = float(np.percentile(max_drawdowns_per_path, 99.0))

    p_neg = float(np.mean(final_r_arr < 0))

    med_streak = int(np.median(streaks))
    p99_streak = int(np.percentile(streaks, 99.0))

    status = "STABLE" if p5_final > 0 and p_neg < 0.05 else ("PROMISING" if med_final > 0 else "FRAGILE")

    return MonteCarloReport(
        symbol=symbol,
        real_n=real_n,
        simulated_paths=n_paths,
        horizon_trades=horizon,
        seed=seed,
        median_final_r=round(med_final, 2),
        percentile_5th_final_r=round(p5_final, 2),
        percentile_1st_final_r=round(p1_final, 2),
        median_max_drawdown_r=round(med_dd, 2),
        percentile_95th_drawdown_r=round(p95_dd, 2),
        percentile_99th_drawdown_r=round(p99_dd, 2),
        p_final_r_negative=round(p_neg, 4),
        p_loss_month=round(p_loss_m, 4),
        median_max_losing_streak=med_streak,
        percentile_99th_losing_streak=p99_streak,
        status=status,
    )
