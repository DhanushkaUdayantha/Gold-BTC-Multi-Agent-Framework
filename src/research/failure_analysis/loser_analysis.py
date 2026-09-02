"""
Loser Forensic Analysis & Profiling Module.

Profiles losing trades empirically across duration, MFE/MAE, directions, and failure mechanisms.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np

from src.research.failure_analysis.failure_taxonomy import classify_trade_failure, FailureReason

logger = logging.getLogger(__name__)


@dataclass
class LoserProfile:
    """Consolidated loser profile for an asset cohort."""
    symbol: str
    total_trades_analyzed: int
    loser_count: int
    loss_rate_pct: float
    avg_loss_r: float
    median_loss_r: float
    total_r_lost: float
    avg_mfe_r: float
    median_mfe_r: float
    avg_mae_r: float
    median_mae_r: float
    avg_duration_minutes: float
    median_duration_minutes: float
    buy_loser_count: int
    sell_loser_count: int
    top_failure_reasons: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def analyze_losers(
    trades: List[Dict[str, Any]],
    symbol: str = "BTC/USD",
) -> LoserProfile:
    """
    Perform deep loser profiling on a list of trade records.
    """
    total_n = len(trades)
    losing_trades = [t for t in trades if t.get("outcome") == "LOSS" or float(t.get("realized_r") or 0.0) < 0]
    loss_n = len(losing_trades)

    if loss_n == 0:
        return LoserProfile(
            symbol=symbol,
            total_trades_analyzed=total_n,
            loser_count=0,
            loss_rate_pct=0.0,
            avg_loss_r=0.0,
            median_loss_r=0.0,
            total_r_lost=0.0,
            avg_mfe_r=0.0,
            median_mfe_r=0.0,
            avg_mae_r=0.0,
            median_mae_r=0.0,
            avg_duration_minutes=0.0,
            median_duration_minutes=0.0,
            buy_loser_count=0,
            sell_loser_count=0,
            top_failure_reasons=[],
        )

    r_list = [float(t.get("realized_r") or -1.0) for t in losing_trades]
    mfe_list = [float(t.get("mfe") or 0.3) for t in losing_trades]
    mae_list = [float(t.get("mae") or 1.0) for t in losing_trades]
    dur_list = [float(t.get("duration_minutes") or 30.0) for t in losing_trades]

    buys = sum(1 for t in losing_trades if str(t.get("direction", "")).upper() == "BUY")
    sells = sum(1 for t in losing_trades if str(t.get("direction", "")).upper() == "SELL")

    # Classify failure reasons
    reason_counts: Dict[str, int] = {}
    for t in losing_trades:
        fc = classify_trade_failure(t)
        p_name = fc.primary_reason.value
        reason_counts[p_name] = reason_counts.get(p_name, 0) + 1

    top_reasons = [
        {"reason": r, "count": cnt, "percentage": round((cnt / loss_n) * 100.0, 1)}
        for r, cnt in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return LoserProfile(
        symbol=symbol,
        total_trades_analyzed=total_n,
        loser_count=loss_n,
        loss_rate_pct=round((loss_n / total_n) * 100.0, 2) if total_n > 0 else 0.0,
        avg_loss_r=round(float(np.mean(r_list)), 4),
        median_loss_r=round(float(np.median(r_list)), 4),
        total_r_lost=round(float(np.abs(np.sum(r_list))), 2),
        avg_mfe_r=round(float(np.mean(mfe_list)), 2),
        median_mfe_r=round(float(np.median(mfe_list)), 2),
        avg_mae_r=round(float(np.mean(mae_list)), 2),
        median_mae_r=round(float(np.median(mae_list)), 2),
        avg_duration_minutes=round(float(np.mean(dur_list)), 1),
        median_duration_minutes=round(float(np.median(dur_list)), 1),
        buy_loser_count=buys,
        sell_loser_count=sells,
        top_failure_reasons=top_reasons,
    )
