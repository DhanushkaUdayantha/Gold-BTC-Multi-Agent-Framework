"""
Streak & Loss/Winner Clustering Forensic Module.

Measures serial correlation, consecutive loss/win streaks, and rolling performance decay.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClusteringReport:
    """Consolidated loss and winner clustering statistics."""
    symbol: str
    total_trades: int
    autocorrelation_lag1: float
    is_clustered: bool  # True if |lag1| > 0.10
    longest_losing_streak: int
    median_losing_streak: int
    percentile_95th_losing_streak: int
    longest_winning_streak: int
    median_winning_streak: int
    percentile_95th_winning_streak: int
    worst_rolling_50_win_rate_pct: Optional[float]
    worst_rolling_50_expectancy_r: Optional[float]
    worst_rolling_100_win_rate_pct: Optional[float]
    worst_rolling_100_expectancy_r: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_streaks(r_series: List[float], positive: bool = False) -> List[int]:
    """Compute contiguous streak lengths."""
    streaks: List[int] = []
    curr = 0
    for r in r_series:
        match = (r > 0) if positive else (r < 0)
        if match:
            curr += 1
        else:
            if curr > 0:
                streaks.append(curr)
                curr = 0
    if curr > 0:
        streaks.append(curr)
    return streaks if streaks else [0]


def analyze_clustering(
    trades: List[Dict[str, Any]],
    symbol: str = "BTC/USD",
) -> ClusteringReport:
    """
    Perform streak clustering and serial autocorrelation analysis.
    """
    n = len(trades)
    if n == 0:
        return ClusteringReport(
            symbol=symbol,
            total_trades=0,
            autocorrelation_lag1=0.0,
            is_clustered=False,
            longest_losing_streak=0,
            median_losing_streak=0,
            percentile_95th_losing_streak=0,
            longest_winning_streak=0,
            median_winning_streak=0,
            percentile_95th_winning_streak=0,
            worst_rolling_50_win_rate_pct=None,
            worst_rolling_50_expectancy_r=None,
            worst_rolling_100_win_rate_pct=None,
            worst_rolling_100_expectancy_r=None,
        )

    r_series = [float(t.get("realized_r") or 0.0) for t in trades]
    arr = np.array(r_series, dtype=float)

    # 1. Autocorrelation Lag-1
    if len(arr) > 2:
        lag1 = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
        if np.isnan(lag1):
            lag1 = 0.0
    else:
        lag1 = 0.0

    # 2. Losing and Winning Streaks
    loss_streaks = _compute_streaks(r_series, positive=False)
    win_streaks = _compute_streaks(r_series, positive=True)

    max_loss_streak = max(loss_streaks)
    med_loss_streak = int(np.median(loss_streaks))
    p95_loss_streak = int(np.percentile(loss_streaks, 95.0))

    max_win_streak = max(win_streaks)
    med_win_streak = int(np.median(win_streaks))
    p95_win_streak = int(np.percentile(win_streaks, 95.0))

    # 3. Rolling-50 and Rolling-100 Performance
    worst_50_wr = None
    worst_50_ev = None
    if n >= 50:
        roll_50_wr = []
        roll_50_ev = []
        for i in range(n - 50 + 1):
            window = arr[i:i+50]
            roll_50_wr.append(float(np.mean(window > 0) * 100.0))
            roll_50_ev.append(float(np.mean(window)))
        worst_50_wr = round(float(np.min(roll_50_wr)), 2)
        worst_50_ev = round(float(np.min(roll_50_ev)), 4)

    worst_100_wr = None
    worst_100_ev = None
    if n >= 100:
        roll_100_wr = []
        roll_100_ev = []
        for i in range(n - 100 + 1):
            window = arr[i:i+100]
            roll_100_wr.append(float(np.mean(window > 0) * 100.0))
            roll_100_ev.append(float(np.mean(window)))
        worst_100_wr = round(float(np.min(roll_100_wr)), 2)
        worst_100_ev = round(float(np.min(roll_100_ev)), 4)

    return ClusteringReport(
        symbol=symbol,
        total_trades=n,
        autocorrelation_lag1=round(lag1, 4),
        is_clustered=bool(abs(lag1) > 0.10),
        longest_losing_streak=max_loss_streak,
        median_losing_streak=med_loss_streak,
        percentile_95th_losing_streak=p95_loss_streak,
        longest_winning_streak=max_win_streak,
        median_winning_streak=med_win_streak,
        percentile_95th_winning_streak=p95_win_streak,
        worst_rolling_50_win_rate_pct=worst_50_wr,
        worst_rolling_50_expectancy_r=worst_50_ev,
        worst_rolling_100_win_rate_pct=worst_100_wr,
        worst_rolling_100_expectancy_r=worst_100_ev,
    )
