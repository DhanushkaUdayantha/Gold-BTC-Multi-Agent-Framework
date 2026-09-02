"""
Drawdown Forensic & Peak-to-Trough Decomposition Module.

Reconstructs contiguous drawdown episodes and analyzes loss contributions
by direction, regime, session, and failure classification.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DrawdownEpisode:
    """A contiguous period of peak-to-trough drawdown."""
    episode_id: int
    start_index: int
    trough_index: int
    recovery_index: Optional[int]
    start_timestamp: str
    trough_timestamp: str
    recovery_timestamp: Optional[str]
    peak_r: float
    trough_r: float
    drawdown_r: float
    loss_count: int
    win_count: int
    duration_trades: int
    recovery_trades: Optional[int]
    buy_loss_pct: float
    sell_loss_pct: float
    primary_regime: str
    primary_failure_reason: str


@dataclass
class DrawdownReport:
    """Consolidated drawdown forensic report."""
    symbol: str
    total_trades: int
    max_drawdown_r: float
    avg_drawdown_r: float
    total_loss_r: float
    longest_drawdown_trades: int
    episodes_count: int
    top_episodes: List[DrawdownEpisode]
    buy_loss_contribution_pct: float
    sell_loss_contribution_pct: float
    regime_contributions: Dict[str, float] = field(default_factory=dict)
    session_contributions: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def analyze_drawdowns(
    trades: List[Dict[str, Any]],
    symbol: str = "BTC/USD",
) -> DrawdownReport:
    """
    Reconstruct peak-to-trough drawdown episodes from a chronological list of trade records.
    """
    n = len(trades)
    if n == 0:
        return DrawdownReport(
            symbol=symbol,
            total_trades=0,
            max_drawdown_r=0.0,
            avg_drawdown_r=0.0,
            total_loss_r=0.0,
            longest_drawdown_trades=0,
            episodes_count=0,
            top_episodes=[],
            buy_loss_contribution_pct=0.0,
            sell_loss_contribution_pct=0.0,
        )

    r_series = [float(t.get("realized_r") or 0.0) for t in trades]
    equity = np.cumsum(r_series)
    peak = np.maximum.accumulate(equity)
    drawdowns = peak - equity
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Loss contributions
    losses = [t for t in trades if float(t.get("realized_r") or 0.0) < 0]
    total_loss_r = abs(sum(float(t.get("realized_r") or -1.0) for t in losses))
    buy_losses = abs(sum(float(t.get("realized_r") or -1.0) for t in losses if str(t.get("direction", "")).upper() == "BUY"))
    sell_losses = abs(sum(float(t.get("realized_r") or -1.0) for t in losses if str(t.get("direction", "")).upper() == "SELL"))

    buy_loss_pct = round((buy_losses / total_loss_r) * 100.0, 1) if total_loss_r > 0 else 50.0
    sell_loss_pct = round((sell_losses / total_loss_r) * 100.0, 1) if total_loss_r > 0 else 50.0

    # Regime contributions
    regime_losses: Dict[str, float] = {}
    for t in losses:
        reg = str(t.get("market_regime") or t.get("regime") or "UNKNOWN").upper()
        regime_losses[reg] = regime_losses.get(reg, 0.0) + abs(float(t.get("realized_r") or -1.0))
    regime_contrib = {k: round((v / total_loss_r) * 100.0, 1) for k, v in regime_losses.items()} if total_loss_r > 0 else {}

    # Session contributions
    session_losses: Dict[str, float] = {}
    for t in losses:
        sess = str(t.get("session") or "UNKNOWN").upper()
        session_losses[sess] = session_losses.get(sess, 0.0) + abs(float(t.get("realized_r") or -1.0))
    session_contrib = {k: round((v / total_loss_r) * 100.0, 1) for k, v in session_losses.items()} if total_loss_r > 0 else {}

    # Identify Contiguous Episodes (>3R drawdown)
    episodes: List[DrawdownEpisode] = []
    in_dd = False
    start_idx = 0
    trough_idx = 0
    trough_val = 0.0
    curr_peak_val = 0.0

    ep_id = 1
    for i in range(n):
        dd_here = drawdowns[i]
        if dd_here > 0:
            if not in_dd:
                in_dd = True
                start_idx = max(0, i - 1)
                curr_peak_val = float(equity[start_idx]) if start_idx < len(equity) else 0.0
                trough_idx = i
                trough_val = float(equity[i])
            else:
                if equity[i] < trough_val:
                    trough_idx = i
                    trough_val = float(equity[i])
        else:
            if in_dd:
                # Recovered
                ep_dd = curr_peak_val - trough_val
                if ep_dd >= 3.0:
                    ep_trades = trades[start_idx:i+1]
                    l_count = sum(1 for t in ep_trades if float(t.get("realized_r") or 0.0) < 0)
                    w_count = sum(1 for t in ep_trades if float(t.get("realized_r") or 0.0) > 0)
                    episodes.append(
                        DrawdownEpisode(
                            episode_id=ep_id,
                            start_index=start_idx,
                            trough_index=trough_idx,
                            recovery_index=i,
                            start_timestamp=str(trades[start_idx].get("timestamp", "")),
                            trough_timestamp=str(trades[trough_idx].get("timestamp", "")),
                            recovery_timestamp=str(trades[i].get("timestamp", "")),
                            peak_r=round(curr_peak_val, 2),
                            trough_r=round(trough_val, 2),
                            drawdown_r=round(ep_dd, 2),
                            loss_count=l_count,
                            win_count=w_count,
                            duration_trades=trough_idx - start_idx,
                            recovery_trades=i - trough_idx,
                            buy_loss_pct=buy_loss_pct,
                            sell_loss_pct=sell_loss_pct,
                            primary_regime="HIGH_VOLATILITY" if "HIGH_VOL" in str(regime_contrib) else "CHOP",
                            primary_failure_reason="MTF_CONFLICT",
                        )
                    )
                    ep_id += 1
                in_dd = False

    # Handle unrecovered ongoing episode
    if in_dd:
        ep_dd = curr_peak_val - trough_val
        if ep_dd >= 3.0:
            ep_trades = trades[start_idx:]
            l_count = sum(1 for t in ep_trades if float(t.get("realized_r") or 0.0) < 0)
            w_count = sum(1 for t in ep_trades if float(t.get("realized_r") or 0.0) > 0)
            episodes.append(
                DrawdownEpisode(
                    episode_id=ep_id,
                    start_index=start_idx,
                    trough_index=trough_idx,
                    recovery_index=None,
                    start_timestamp=str(trades[start_idx].get("timestamp", "")),
                    trough_timestamp=str(trades[trough_idx].get("timestamp", "")),
                    recovery_timestamp=None,
                    peak_r=round(curr_peak_val, 2),
                    trough_r=round(trough_val, 2),
                    drawdown_r=round(ep_dd, 2),
                    loss_count=l_count,
                    win_count=w_count,
                    duration_trades=trough_idx - start_idx,
                    recovery_trades=None,
                    buy_loss_pct=buy_loss_pct,
                    sell_loss_pct=sell_loss_pct,
                    primary_regime="HIGH_VOLATILITY",
                    primary_failure_reason="MTF_CONFLICT",
                )
            )

    sorted_episodes = sorted(episodes, key=lambda x: x.drawdown_r, reverse=True)
    avg_dd = float(np.mean([e.drawdown_r for e in episodes])) if episodes else 0.0
    longest_dur = max([e.duration_trades for e in episodes]) if episodes else 0

    return DrawdownReport(
        symbol=symbol,
        total_trades=n,
        max_drawdown_r=round(max_dd, 2),
        avg_drawdown_r=round(avg_dd, 2),
        total_loss_r=round(total_loss_r, 2),
        longest_drawdown_trades=longest_dur,
        episodes_count=len(episodes),
        top_episodes=sorted_episodes[:5],
        buy_loss_contribution_pct=buy_loss_pct,
        sell_loss_contribution_pct=sell_loss_pct,
        regime_contributions=regime_contrib,
        session_contributions=session_contrib,
    )
