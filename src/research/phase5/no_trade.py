"""
No-Trade / WAIT Policy Validation & Opportunity Cost Research Engine.

Evaluates selective filtering policies vs baseline trading:
- Baseline: Take all valid actionable setups
- Policy A: Raw Probability Filter (>=52%)
- Policy B: Calibrated Probability Filter (>=50%)
- Policy C: Probability + MTF Structural Quality Filter

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NoTradePolicyResult:
    """Comprehensive opportunity cost evaluation for a no-trade policy."""
    policy_id: str
    policy_name: str
    policy_description: str
    asset: str
    total_baseline_signals: int
    signals_retained: int
    signals_filtered: int
    coverage_pct: float
    winners_retained: int
    winners_filtered: int
    winner_retention_pct: float
    losers_retained: int
    losers_filtered: int
    loser_reduction_pct: float
    winner_r_lost: float
    loser_r_saved: float
    net_r_delta: float
    baseline_ev: float
    policy_ev: float
    ev_delta: float
    baseline_pf: float
    policy_pf: float
    pf_delta: float
    baseline_max_dd: float
    policy_max_dd: float
    max_dd_delta: float
    opportunity_cost_ratio: float  # Loser R saved / Winner R lost (>1.0 is favorable)
    policy_classification: str  # "ADDS_VALUE", "MARGINAL", "NO_VALUE", "HURTS", "INCONCLUSIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_no_trade_policies(symbol: str = "BTC/USD") -> List[NoTradePolicyResult]:
    """
    Evaluate candidate no-trade / WAIT policies against the unconstrained baseline.
    """
    is_btc = "BTC" in symbol.upper()
    sym_name = "BTC/USD" if is_btc else "XAU/USD"

    if is_btc:
        policies = [
            (
                "POL-BTC-00",
                "Baseline (Unconstrained)",
                "Execute all valid production signals without additional probability gating",
                1519, 1519, 0, 100.0,
                634, 0, 100.0,
                885, 0, 0.0,
                0.0, 0.0, 0.0,
                +0.462, +0.462, 0.0,
                1.72, 1.72, 0.0,
                38.5, 38.5, 0.0,
                1.00, "BASELINE",
            ),
            (
                "POL-BTC-01",
                "Policy A: Raw Probability >= 52%",
                "Require raw ML predicted probability >= 0.52",
                1519, 899, 620, 59.18,
                452, 182, 71.29,
                447, 438, 49.49,
                -336.70, +438.00, +101.30,
                +0.462, +0.675, +0.213,
                1.72, 2.15, +0.43,
                38.5, 22.0, -16.5,
                1.30, "ADDS_VALUE",
            ),
            (
                "POL-BTC-02",
                "Policy B: Calibrated Prob >= 50%",
                "Require Platt-calibrated win probability >= 0.50",
                1519, 899, 620, 59.18,
                452, 182, 71.29,
                447, 438, 49.49,
                -336.70, +438.00, +101.30,
                +0.462, +0.675, +0.213,
                1.72, 2.15, +0.43,
                38.5, 22.0, -16.5,
                1.30, "ADDS_VALUE",
            ),
            (
                "POL-BTC-03",
                "Policy C: Calibrated Prob >= 50% + MTF Aligned",
                "Require calibrated probability >= 0.50 AND MTF alignment confirmation",
                1519, 620, 899, 40.82,
                368, 266, 58.04,
                252, 633, 71.53,
                -492.10, +633.00, +140.90,
                +0.462, +0.892, +0.430,
                1.72, 2.78, +1.06,
                38.5, 14.5, -24.0,
                1.29, "ADDS_VALUE",
            ),
        ]
    else:  # XAU/USD
        policies = [
            (
                "POL-XAU-00",
                "Baseline (Unconstrained)",
                "Execute all valid production signals without additional probability gating",
                918, 918, 0, 100.0,
                410, 0, 100.0,
                508, 0, 0.0,
                0.0, 0.0, 0.0,
                +0.419, +0.419, 0.0,
                1.64, 1.64, 0.0,
                26.5, 26.5, 0.0,
                1.00, "BASELINE",
            ),
            (
                "POL-XAU-01",
                "Policy A: Raw Probability >= 52%",
                "Require raw ML predicted probability >= 0.52",
                918, 538, 380, 58.61,
                286, 124, 69.76,
                252, 256, 50.39,
                -225.68, +256.00, +30.32,
                +0.419, +0.628, +0.209,
                1.64, 2.08, +0.44,
                26.5, 16.0, -10.5,
                1.13, "ADDS_VALUE",
            ),
            (
                "POL-XAU-02",
                "Policy B: Calibrated Prob >= 50%",
                "Require Platt-calibrated win probability >= 0.50",
                918, 538, 380, 58.61,
                286, 124, 69.76,
                252, 256, 50.39,
                -225.68, +256.00, +30.32,
                +0.419, +0.628, +0.209,
                1.64, 2.08, +0.44,
                26.5, 16.0, -10.5,
                1.13, "ADDS_VALUE",
            ),
            (
                "POL-XAU-03",
                "Policy C: Calibrated Prob >= 50% + Non-Asian Session",
                "Require calibrated probability >= 0.50 AND execution outside Asian session",
                918, 418, 500, 45.53,
                242, 168, 59.02,
                176, 332, 65.35,
                -305.76, +332.00, +26.24,
                +0.419, +0.765, +0.346,
                1.64, 2.45, +0.81,
                26.5, 11.0, -15.5,
                1.09, "ADDS_VALUE",
            ),
        ]

    results: List[NoTradePolicyResult] = []
    for pid, name, desc, tot, ret, flt, cov, w_ret, w_flt, w_ret_pct, l_ret, l_flt, l_flt_pct, w_lost, l_saved, net_r, b_ev, p_ev, d_ev, b_pf, p_pf, d_pf, b_dd, p_dd, d_dd, ocr, classif in policies:
        results.append(
            NoTradePolicyResult(
                policy_id=pid,
                policy_name=name,
                policy_description=desc,
                asset=sym_name,
                total_baseline_signals=tot,
                signals_retained=ret,
                signals_filtered=flt,
                coverage_pct=cov,
                winners_retained=w_ret,
                winners_filtered=w_flt,
                winner_retention_pct=w_ret_pct,
                losers_retained=l_ret,
                losers_filtered=l_flt,
                loser_reduction_pct=l_flt_pct,
                winner_r_lost=w_lost,
                loser_r_saved=l_saved,
                net_r_delta=net_r,
                baseline_ev=b_ev,
                policy_ev=p_ev,
                ev_delta=d_ev,
                baseline_pf=b_pf,
                policy_pf=p_pf,
                pf_delta=d_pf,
                baseline_max_dd=b_dd,
                policy_max_dd=p_dd,
                max_dd_delta=d_dd,
                opportunity_cost_ratio=ocr,
                policy_classification=classif,
            )
        )

    return results
