"""
Governance Analytics & Comprehensive Sub-Analysis Engine.

Generates deep sub-cohort breakdowns, asymmetry metrics, and research validation reports:
- Trade Removal & Asymmetry Analysis (Winner Retention % vs Loser Elimination %)
- Missed Winners & Removed Losers Analysis
- Coverage Analysis & Decision Agreement Matrix
- Asset Breakdowns (BTC vs XAU sub-cohorts)
- Regime & Session Robustness Analysis
- Threshold Sensitivity & Confirmation Ablation Studies
- Out-of-Sample (OOS) & Untouched Holdout Evaluation

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.research.outcome_engine import OutcomeEngine, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class TradeRemovalAnalysis:
    """Asymmetry between loser elimination and winner retention."""
    base_trades: int
    shadow_trades: int
    trades_removed: int
    trade_reduction_pct: float
    base_winners: int
    shadow_winners: int
    removed_winners_count: int
    winner_retention_pct: float
    base_losers: int
    shadow_losers: int
    removed_losers_count: int
    loser_reduction_pct: float
    removed_winner_r_loss: float
    removed_loser_r_gain: float
    net_r_saved: float
    benefit_cost_ratio: float


@dataclass
class MissedWinnerRecord:
    """A profitable trade eliminated by hypothetical gating."""
    signal_id: str
    symbol: str
    timestamp: str
    direction: str
    probability: float
    regime: str
    realized_r: float
    validation_status: str
    rejection_reason: str


@dataclass
class AssetBreakdownMetrics:
    """Sub-cohort performance for an asset class."""
    cohort_name: str
    signal_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    total_realized_r: float


class GovernanceMetricsEngine:
    """Calculates all governance sub-analyses and writes reports."""

    @classmethod
    def compute_trade_removal(
        cls,
        base_signals: List[Dict[str, Any]],
        shadow_signals: List[Dict[str, Any]],
    ) -> Tuple[TradeRemovalAnalysis, List[MissedWinnerRecord]]:
        """Calculate winner retention, loser elimination, and missed winners."""
        base_trades = [s for s in base_signals if s["direction"] in ("BUY", "SELL")]
        shadow_trades = [s for s in shadow_signals if s["direction"] in ("BUY", "SELL")]

        n_b = len(base_trades)
        n_s = len(shadow_trades)
        removed_count = n_b - n_s
        red_pct = round((removed_count / n_b * 100.0), 1) if n_b > 0 else 0.0

        b_wins = [s for s in base_trades if s["outcome"] == "WIN"]
        s_wins = [s for s in shadow_trades if s["outcome"] == "WIN"]
        rem_wins = len(b_wins) - len(s_wins)
        win_ret_pct = round((len(s_wins) / len(b_wins) * 100.0), 1) if b_wins else 0.0

        b_losers = [s for s in base_trades if s["outcome"] == "LOSS"]
        s_losers = [s for s in shadow_trades if s["outcome"] == "LOSS"]
        rem_losers = len(b_losers) - len(s_losers)
        lose_red_pct = round((rem_losers / len(b_losers) * 100.0), 1) if b_losers else 0.0

        # Identify individual missed winners
        shadow_kept_ids = {s["signal_id"] for s in shadow_trades}
        missed_winners: List[MissedWinnerRecord] = []
        rem_win_r = 0.0

        for s in b_wins:
            if s["signal_id"] not in shadow_kept_ids:
                rem_win_r += s.get("realized_r", 1.0)
                missed_winners.append(
                    MissedWinnerRecord(
                        signal_id=s.get("signal_id", ""),
                        symbol=s.get("symbol", ""),
                        timestamp=s.get("timestamp", ""),
                        direction=s.get("direction", ""),
                        probability=s.get("probability", 0.0),
                        regime=s.get("regime", ""),
                        realized_r=s.get("realized_r", 1.0),
                        validation_status=s.get("qualification_status", "NOT_QUALIFIED"),
                        rejection_reason=s.get("gating_reason", "Strategy criteria not met"),
                    )
                )

        rem_lose_r = 0.0
        for s in b_losers:
            if s["signal_id"] not in shadow_kept_ids:
                rem_lose_r += abs(s.get("realized_r", -1.0))

        net_saved = rem_lose_r - rem_win_r
        benefit_cost = round(rem_lose_r / rem_win_r, 2) if rem_win_r > 0 else 99.0

        removal_analysis = TradeRemovalAnalysis(
            base_trades=n_b,
            shadow_trades=n_s,
            trades_removed=removed_count,
            trade_reduction_pct=red_pct,
            base_winners=len(b_wins),
            shadow_winners=len(s_wins),
            removed_winners_count=rem_wins,
            winner_retention_pct=win_ret_pct,
            base_losers=len(b_losers),
            shadow_losers=len(s_losers),
            removed_losers_count=rem_losers,
            loser_reduction_pct=lose_red_pct,
            removed_winner_r_loss=round(rem_win_r, 2),
            removed_loser_r_gain=round(rem_lose_r, 2),
            net_r_saved=round(net_saved, 2),
            benefit_cost_ratio=benefit_cost,
        )

        return removal_analysis, missed_winners

    @classmethod
    def evaluate_asset_breakdowns(
        cls,
        signals: List[Dict[str, Any]],  # Rich signal dicts with 'symbol', 'direction', 'outcome', 'realized_r', 'is_qualified', 'is_conflict'
    ) -> Dict[str, AssetBreakdownMetrics]:
        """Compute exhaustive sub-cohort breakdowns for BTC and XAU."""
        cohort_filters: Dict[str, Any] = {
            "BTC All": lambda s: "BTC" in s["symbol"].upper(),
            "BTC BUY": lambda s: "BTC" in s["symbol"].upper() and s["direction"] == "BUY",
            "BTC SELL": lambda s: "BTC" in s["symbol"].upper() and s["direction"] == "SELL",
            "BTC Qualified SELL": lambda s: "BTC" in s["symbol"].upper() and s["direction"] == "SELL" and s.get("is_qualified", False),
            "BTC Non-Qualified": lambda s: "BTC" in s["symbol"].upper() and not s.get("is_qualified", False),
            "BTC Conflicts": lambda s: "BTC" in s["symbol"].upper() and s.get("is_conflict", False),
            "XAU All": lambda s: "XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper(),
            "XAU BUY": lambda s: ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s["direction"] == "BUY",
            "XAU SELL": lambda s: ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s["direction"] == "SELL",
            "XAU Qualified BUY": lambda s: ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s["direction"] == "BUY" and s.get("is_qualified", False),
            "XAU Non-Qualified": lambda s: ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and not s.get("is_qualified", False),
            "XAU Conflicts": lambda s: ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s.get("is_conflict", False),
        }

        results: Dict[str, AssetBreakdownMetrics] = {}
        for name, fn in cohort_filters.items():
            matched = [s for s in signals if fn(s)]
            r_vals = [s["realized_r"] for s in matched]
            perf = OutcomeEngine.calculate_performance_metrics(r_vals, total_signals_count=len(matched))
            results[name] = AssetBreakdownMetrics(
                cohort_name=name,
                signal_count=len(matched),
                win_rate_pct=perf.win_rate_pct,
                expectancy_r=perf.expectancy_r,
                profit_factor=perf.profit_factor,
                max_drawdown_r=perf.max_drawdown_r,
                total_realized_r=perf.total_realized_r,
            )
        return results

    @classmethod
    def evaluate_regimes_and_sessions(
        cls,
        signals: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Compute performance slices across market regimes and sessions."""
        regimes = ["LOW_VOLATILITY", "TRENDING", "RANGING", "HIGH_VOLATILITY"]
        sessions = ["LONDON", "NEW_YORK", "ASIA", "OVERLAP"]

        reg_results = {}
        for r in regimes:
            b_slice = [s for s in signals if s.get("regime") == r and s.get("base_dir") in ("BUY", "SELL")]
            s_slice = [s for s in signals if s.get("regime") == r and s.get("shadow_dir") in ("BUY", "SELL")]

            b_perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in b_slice])
            s_perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in s_slice])

            reg_results[r] = {
                "base_trades": len(b_slice),
                "shadow_trades": len(s_slice),
                "base_expectancy_r": b_perf.expectancy_r,
                "shadow_expectancy_r": s_perf.expectancy_r,
                "delta_expectancy_r": round(s_perf.expectancy_r - b_perf.expectancy_r, 3),
                "shadow_profit_factor": s_perf.profit_factor,
                "shadow_max_dd_r": s_perf.max_drawdown_r,
                "shadow_total_r": s_perf.total_realized_r,
                "classification": "STABLE" if s_perf.expectancy_r > 0.10 else ("UNSTABLE" if s_perf.expectancy_r < 0 else "INSUFFICIENT_SAMPLE"),
            }

        sess_results = {}
        for sess in sessions:
            b_slice = [s for s in signals if s.get("session") == sess and s.get("base_dir") in ("BUY", "SELL")]
            s_slice = [s for s in signals if s.get("session") == sess and s.get("shadow_dir") in ("BUY", "SELL")]

            b_perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in b_slice])
            s_perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in s_slice])

            sess_results[sess] = {
                "base_trades": len(b_slice),
                "shadow_trades": len(s_slice),
                "base_expectancy_r": b_perf.expectancy_r,
                "shadow_expectancy_r": s_perf.expectancy_r,
                "delta_expectancy_r": round(s_perf.expectancy_r - b_perf.expectancy_r, 3),
                "shadow_profit_factor": s_perf.profit_factor,
                "shadow_max_dd_r": s_perf.max_drawdown_r,
                "shadow_total_r": s_perf.total_realized_r,
            }

        return reg_results, sess_results

    @classmethod
    def evaluate_threshold_sensitivity(
        cls,
        signals: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Evaluate sensitivity over threshold plateaus."""
        btc_thresholds = [0.38, 0.39, 0.40, 0.41, 0.42, 0.45, 0.50]
        xau_thresholds = [0.40, 0.41, 0.42, 0.43, 0.45, 0.48, 0.50]

        btc_res = []
        for t in btc_thresholds:
            matched = [s for s in signals if "BTC" in s["symbol"].upper() and s["direction"] == "SELL" and s.get("probability", 0) >= t and s.get("regime") == "LOW_VOLATILITY"]
            perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in matched])
            btc_res.append({
                "threshold": t,
                "trades": len(matched),
                "win_rate_pct": perf.win_rate_pct,
                "expectancy_r": perf.expectancy_r,
                "profit_factor": perf.profit_factor,
                "max_drawdown_r": perf.max_drawdown_r,
                "total_r": perf.total_realized_r,
                "classification": "STABLE_PLATEAU" if perf.expectancy_r >= 0.30 else "DEGRADED",
            })

        xau_res = []
        for t in xau_thresholds:
            matched = [s for s in signals if ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s["direction"] == "BUY" and s.get("probability", 0) >= t and s.get("vwap_aligned", False)]
            perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in matched])
            xau_res.append({
                "threshold": t,
                "trades": len(matched),
                "win_rate_pct": perf.win_rate_pct,
                "expectancy_r": perf.expectancy_r,
                "profit_factor": perf.profit_factor,
                "max_drawdown_r": perf.max_drawdown_r,
                "total_r": perf.total_realized_r,
                "classification": "STABLE_PLATEAU" if perf.expectancy_r >= 0.15 else "DEGRADED",
            })

        return {"BTC": btc_res, "XAU": xau_res}

    @classmethod
    def evaluate_confirmation_ablation(
        cls,
        signals: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Ablation analysis of individual confirmation components."""
        # BTC Combinations
        btc_ablations = [
            ("Probability Only (P>=0.40)", lambda s: s.get("probability", 0) >= 0.40),
            ("Prob + Regime (P>=0.40 + LOW_VOL)", lambda s: s.get("probability", 0) >= 0.40 and s.get("regime") == "LOW_VOLATILITY"),
            ("Prob + HTF (P>=0.40 + HTF)", lambda s: s.get("probability", 0) >= 0.40 and s.get("htf_aligned", False)),
            ("Prob + S/R (P>=0.40 + SR)", lambda s: s.get("probability", 0) >= 0.40 and s.get("sr_aligned", False)),
            ("Prob + Regime + HTF", lambda s: s.get("probability", 0) >= 0.40 and s.get("regime") == "LOW_VOLATILITY" and s.get("htf_aligned", False)),
            ("Full Strategy (Prob + Regime + HTF + SR)", lambda s: s.get("probability", 0) >= 0.40 and s.get("regime") == "LOW_VOLATILITY" and s.get("htf_aligned", False) and s.get("sr_aligned", False)),
        ]

        btc_res = []
        btc_sells = [s for s in signals if "BTC" in s["symbol"].upper() and s["direction"] == "SELL"]
        for label, fn in btc_ablations:
            matched = [s for s in btc_sells if fn(s)]
            perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in matched])
            btc_res.append({
                "combination": label,
                "trades": len(matched),
                "win_rate_pct": perf.win_rate_pct,
                "expectancy_r": perf.expectancy_r,
                "profit_factor": perf.profit_factor,
                "max_drawdown_r": perf.max_drawdown_r,
                "total_r": perf.total_realized_r,
            })

        # XAU Combinations
        xau_ablations = [
            ("Probability Only (P>=0.42)", lambda s: s.get("probability", 0) >= 0.42),
            ("Prob + VWAP (P>=0.42 + VWAP)", lambda s: s.get("probability", 0) >= 0.42 and s.get("vwap_aligned", False)),
            ("Prob + EMA (P>=0.42 + EMA)", lambda s: s.get("probability", 0) >= 0.42 and s.get("ema_aligned", False)),
            ("Prob + HTF (P>=0.42 + HTF)", lambda s: s.get("probability", 0) >= 0.42 and s.get("htf_aligned", False)),
            ("Prob + VWAP + EMA", lambda s: s.get("probability", 0) >= 0.42 and s.get("vwap_aligned", False) and s.get("ema_aligned", False)),
            ("Full Strategy (Prob + VWAP + EMA + HTF)", lambda s: s.get("probability", 0) >= 0.42 and s.get("vwap_aligned", False) and s.get("ema_aligned", False) and s.get("htf_aligned", False)),
        ]

        xau_res = []
        xau_buys = [s for s in signals if ("XAU" in s["symbol"].upper() or "GOLD" in s["symbol"].upper()) and s["direction"] == "BUY"]
        for label, fn in xau_ablations:
            matched = [s for s in xau_buys if fn(s)]
            perf = OutcomeEngine.calculate_performance_metrics([s["realized_r"] for s in matched])
            xau_res.append({
                "combination": label,
                "trades": len(matched),
                "win_rate_pct": perf.win_rate_pct,
                "expectancy_r": perf.expectancy_r,
                "profit_factor": perf.profit_factor,
                "max_drawdown_r": perf.max_drawdown_r,
                "total_r": perf.total_realized_r,
            })

        return {"BTC": btc_res, "XAU": xau_res}
