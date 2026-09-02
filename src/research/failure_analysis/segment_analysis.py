"""
Multi-Dimensional Forensic Segmentation Module.

Breaks down trading outcomes across:
- Market Regimes
- Trading Sessions
- Trade Directions (BUY vs SELL)
- Confluence Score Buckets
- AI / Calibrated Probability Buckets
- Multi-Timeframe Alignment States

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SegmentBreakdown:
    """Performance statistics for a single segment slice."""
    dimension: str
    slice_name: str
    sample_count: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    total_r: float
    max_drawdown_r: float
    ci_lower_win_rate_pct: float
    ci_upper_win_rate_pct: float
    sample_sufficiency: str  # "SUFFICIENT" (N>=30), "MODERATE" (N>=10), "INSUFFICIENT" (N<10)


@dataclass
class MultiDimensionalForensics:
    """Consolidated multi-dimensional forensic analysis."""
    symbol: str
    total_trades: int
    regimes: List[SegmentBreakdown]
    sessions: List[SegmentBreakdown]
    directions: List[SegmentBreakdown]
    confluence_buckets: List[SegmentBreakdown]
    probability_buckets: List[SegmentBreakdown]
    mtf_alignments: List[SegmentBreakdown]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_slice_stats(dimension: str, slice_name: str, trades_subset: List[Dict[str, Any]]) -> SegmentBreakdown:
    """Compute performance metrics for a specific slice."""
    n = len(trades_subset)
    if n == 0:
        return SegmentBreakdown(
            dimension=dimension,
            slice_name=slice_name,
            sample_count=0,
            win_count=0,
            loss_count=0,
            win_rate_pct=0.0,
            expectancy_r=0.0,
            profit_factor=0.0,
            total_r=0.0,
            max_drawdown_r=0.0,
            ci_lower_win_rate_pct=0.0,
            ci_upper_win_rate_pct=0.0,
            sample_sufficiency="INSUFFICIENT",
        )

    r_list = [float(t.get("realized_r") or 0.0) for t in trades_subset]
    wins = sum(1 for r in r_list if r > 0)
    losses = sum(1 for r in r_list if r < 0)
    wr = (wins / n) * 100.0
    ev = float(np.mean(r_list))
    tot = float(np.sum(r_list))

    pos_sum = float(np.sum([r for r in r_list if r > 0]))
    neg_sum = float(np.abs(np.sum([r for r in r_list if r < 0])))
    pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 0.0

    # Drawdown
    equity = np.cumsum(r_list)
    peak = np.maximum.accumulate(equity)
    dd = float(np.max(peak - equity)) if len(equity) > 0 else 0.0

    # Wilson CI for Win Rate
    z = 1.95996
    p = wins / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    spread = (z / denom) * math.sqrt((p * (1 - p) / n) + (z**2) / (4 * (n**2)))
    ci_low = max(0.0, round((center - spread) * 100.0, 2))
    ci_high = min(100.0, round((center + spread) * 100.0, 2))

    sufficiency = "SUFFICIENT" if n >= 30 else ("MODERATE" if n >= 10 else "INSUFFICIENT")

    return SegmentBreakdown(
        dimension=dimension,
        slice_name=slice_name,
        sample_count=n,
        win_count=wins,
        loss_count=losses,
        win_rate_pct=round(wr, 2),
        expectancy_r=round(ev, 4),
        profit_factor=pf,
        total_r=round(tot, 2),
        max_drawdown_r=round(dd, 2),
        ci_lower_win_rate_pct=ci_low,
        ci_upper_win_rate_pct=ci_high,
        sample_sufficiency=sufficiency,
    )


def run_segment_forensics(
    trades: List[Dict[str, Any]],
    symbol: str = "BTC/USD",
) -> MultiDimensionalForensics:
    """
    Perform multi-dimensional forensic segmentation across all canonical dimensions.
    """
    n = len(trades)

    # 1. Regimes
    regime_slices = ["TRENDING", "CHOP", "HIGH_VOLATILITY", "LOW_VOLATILITY", "UNKNOWN"]
    reg_breaks: List[SegmentBreakdown] = []
    for reg in regime_slices:
        sub = [t for t in trades if reg in str(t.get("market_regime") or t.get("regime") or "").upper()]
        reg_breaks.append(_compute_slice_stats("Regime", reg, sub))

    # 2. Sessions
    session_slices = ["ASIA", "LONDON", "NEW_YORK", "OVERLAP"]
    sess_breaks: List[SegmentBreakdown] = []
    for sess in session_slices:
        sub = [t for t in trades if sess in str(t.get("session") or "").upper()]
        sess_breaks.append(_compute_slice_stats("Session", sess, sub))

    # 3. Directions
    dir_breaks: List[SegmentBreakdown] = [
        _compute_slice_stats("Direction", "BUY", [t for t in trades if str(t.get("direction", "")).upper() == "BUY"]),
        _compute_slice_stats("Direction", "SELL", [t for t in trades if str(t.get("direction", "")).upper() == "SELL"]),
    ]

    # 4. Confluence Buckets
    conf_buckets = [
        ("<40", lambda c: c < 40),
        ("40-49", lambda c: 40 <= c < 50),
        ("50-57", lambda c: 50 <= c < 58),
        ("58-64", lambda c: 58 <= c < 65),
        ("65-74", lambda c: 65 <= c < 75),
        (">=75", lambda c: c >= 75),
    ]
    conf_breaks: List[SegmentBreakdown] = []
    for lbl, fn in conf_buckets:
        sub = [t for t in trades if fn(float(t.get("confluence_score") or t.get("signal_strength") or 50))]
        conf_breaks.append(_compute_slice_stats("Confluence", lbl, sub))

    # 5. Probability Buckets
    prob_buckets = [
        ("<45%", lambda p: p < 0.45),
        ("45-50%", lambda p: 0.45 <= p < 0.50),
        ("50-55%", lambda p: 0.50 <= p < 0.55),
        ("55-60%", lambda p: 0.55 <= p < 0.60),
        ("60-65%", lambda p: 0.60 <= p < 0.65),
        (">=65%", lambda p: p >= 0.65),
    ]
    prob_breaks: List[SegmentBreakdown] = []
    for lbl, fn in prob_buckets:
        sub = [t for t in trades if fn(float(t.get("calibrated_probability") or t.get("ai_probability") or 0.5))]
        prob_breaks.append(_compute_slice_stats("Probability", lbl, sub))

    # 6. MTF Alignment
    mtf_slices = [
        ("ALIGNED", lambda t: t.get("mtf_aligned") is True or t.get("htf_aligned") is True),
        ("PARTIALLY_ALIGNED", lambda t: t.get("mtf_aligned") is None),
        ("CONFLICTED", lambda t: t.get("mtf_aligned") is False or t.get("htf_aligned") is False),
    ]
    mtf_breaks: List[SegmentBreakdown] = []
    for lbl, fn in mtf_slices:
        sub = [t for t in trades if fn(t)]
        mtf_breaks.append(_compute_slice_stats("MTF_Alignment", lbl, sub))

    return MultiDimensionalForensics(
        symbol=symbol,
        total_trades=n,
        regimes=reg_breaks,
        sessions=sess_breaks,
        directions=dir_breaks,
        confluence_buckets=conf_breaks,
        probability_buckets=prob_breaks,
        mtf_alignments=mtf_breaks,
    )
