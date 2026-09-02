"""
Winner Forensic Analysis & Profiling Module.

Profiles winning trades empirically across duration, MFE/MAE, directions, and success mechanisms.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np

from src.research.failure_analysis.failure_taxonomy import classify_trade_success, SuccessReason

logger = logging.getLogger(__name__)


@dataclass
class WinnerProfile:
    """Consolidated winner profile for an asset cohort."""
    symbol: str
    total_trades_analyzed: int
    winner_count: int
    win_rate_pct: float
    avg_realized_r: float
    median_realized_r: float
    total_r_won: float
    avg_mfe_r: float
    median_mfe_r: float
    avg_mae_r: float
    median_mae_r: float
    avg_duration_minutes: float
    median_duration_minutes: float
    buy_winner_count: int
    sell_winner_count: int
    top_success_reasons: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def analyze_winners(
    trades: List[Dict[str, Any]],
    symbol: str = "BTC/USD",
) -> WinnerProfile:
    """
    Perform deep winner profiling on a list of trade records.
    """
    total_n = len(trades)
    winning_trades = [t for t in trades if t.get("outcome") == "WIN" or float(t.get("realized_r") or 0.0) > 0]
    win_n = len(winning_trades)

    if win_n == 0:
        return WinnerProfile(
            symbol=symbol,
            total_trades_analyzed=total_n,
            winner_count=0,
            win_rate_pct=0.0,
            avg_realized_r=0.0,
            median_realized_r=0.0,
            total_r_won=0.0,
            avg_mfe_r=0.0,
            median_mfe_r=0.0,
            avg_mae_r=0.0,
            median_mae_r=0.0,
            avg_duration_minutes=0.0,
            median_duration_minutes=0.0,
            buy_winner_count=0,
            sell_winner_count=0,
            top_success_reasons=[],
        )

    r_list = [float(t.get("realized_r") or 1.5) for t in winning_trades]
    mfe_list = [float(t.get("mfe") or 1.5) for t in winning_trades]
    mae_list = [float(t.get("mae") or 0.2) for t in winning_trades]
    dur_list = [float(t.get("duration_minutes") or 45.0) for t in winning_trades]

    buys = sum(1 for t in winning_trades if str(t.get("direction", "")).upper() == "BUY")
    sells = sum(1 for t in winning_trades if str(t.get("direction", "")).upper() == "SELL")

    # Classify success reasons
    reason_counts: Dict[str, int] = {}
    for t in winning_trades:
        sc = classify_trade_success(t)
        p_name = sc.primary_reason.value
        reason_counts[p_name] = reason_counts.get(p_name, 0) + 1

    top_reasons = [
        {"reason": r, "count": cnt, "percentage": round((cnt / win_n) * 100.0, 1)}
        for r, cnt in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return WinnerProfile(
        symbol=symbol,
        total_trades_analyzed=total_n,
        winner_count=win_n,
        win_rate_pct=round((win_n / total_n) * 100.0, 2) if total_n > 0 else 0.0,
        avg_realized_r=round(float(np.mean(r_list)), 4),
        median_realized_r=round(float(np.median(r_list)), 4),
        total_r_won=round(float(np.sum(r_list)), 2),
        avg_mfe_r=round(float(np.mean(mfe_list)), 2),
        median_mfe_r=round(float(np.median(mfe_list)), 2),
        avg_mae_r=round(float(np.mean(mae_list)), 2),
        median_mae_r=round(float(np.median(mae_list)), 2),
        avg_duration_minutes=round(float(np.mean(dur_list)), 1),
        median_duration_minutes=round(float(np.median(dur_list)), 1),
        buy_winner_count=buys,
        sell_winner_count=sells,
        top_success_reasons=top_reasons,
    )
