"""
Execution Stress & Slippage/Delay Degradation Module.

Evaluates strategy resilience under realistic execution friction:
1. Slippage Degradation (0.00R, 0.05R, 0.10R, 0.15R, 0.20R)
2. Latency / Bar-Delay (0-bar, 1-bar, 2-bar delay)

Classifies strategies strictly into ROBUST, SENSITIVE, or FRAGILE.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SlippageScenario:
    """Stress test outcome under a specific slippage penalty."""
    slippage_r: float
    effective_expectancy_r: float
    effective_profit_factor: float
    effective_total_r: float
    effective_win_rate_pct: float
    effective_max_drawdown_r: float
    trades_count: int


@dataclass
class LatencyScenario:
    """Stress test outcome under execution delay."""
    delay_bars: int
    expectancy_r: float
    profit_factor: float
    total_r: float
    trades_count: int


@dataclass
class ExecutionStressReport:
    """Full execution stress testing analysis across slippage and latency."""
    symbol: str
    real_n: int
    baseline_expectancy_r: float
    baseline_profit_factor: float
    baseline_total_r: float
    baseline_win_rate_pct: float
    baseline_max_drawdown_r: float
    slippage_scenarios: List[SlippageScenario]
    latency_scenarios: List[LatencyScenario]
    classification: str  # "ROBUST", "SENSITIVE", "FRAGILE"
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_max_drawdown(r_series: List[float]) -> float:
    """Calculate maximum peak-to-trough drawdown in R units."""
    if not r_series:
        return 0.0
    equity = np.cumsum(r_series)
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    return round(float(np.max(drawdown)), 2)


def run_execution_stress_analysis(
    r_multiples: List[float],
    symbol: str = "BTC/USD",
    forward_delay_r_map: Optional[Dict[int, List[float]]] = None,
) -> ExecutionStressReport:
    """
    Evaluate strategy under slippage degradation (0.00R to 0.20R) and latency.
    
    Args:
        r_multiples: Baseline realized R multiples
        symbol: Asset identifier
        forward_delay_r_map: Optional dictionary of delayed R-multiples for 1-bar, 2-bar latency
    """
    real_n = len(r_multiples)
    if real_n == 0:
        return ExecutionStressReport(
            symbol=symbol,
            real_n=0,
            baseline_expectancy_r=0.0,
            baseline_profit_factor=0.0,
            baseline_total_r=0.0,
            baseline_win_rate_pct=0.0,
            baseline_max_drawdown_r=0.0,
            slippage_scenarios=[],
            latency_scenarios=[],
            classification="FRAGILE",
            rationale="No trades available for stress testing",
        )

    arr = np.array(r_multiples, dtype=float)
    base_ev = float(np.mean(arr))
    base_tot = float(np.sum(arr))
    base_wr = float(np.mean(arr > 0) * 100.0)
    base_dd = calculate_max_drawdown(r_multiples)

    wins_sum = float(np.sum(arr[arr > 0])) if np.any(arr > 0) else 0.0
    losses_sum = float(np.abs(np.sum(arr[arr < 0]))) if np.any(arr < 0) else 1.0
    base_pf = round(wins_sum / losses_sum, 2) if losses_sum > 0 else 0.0

    # 1. Slippage Stress Scenarios: 0.00R, 0.05R, 0.10R, 0.15R, 0.20R
    slippage_levels = [0.00, 0.05, 0.10, 0.15, 0.20]
    slip_scenarios: List[SlippageScenario] = []

    for slip in slippage_levels:
        # Each trade suffers a slippage friction of slip R units
        degraded_r = arr - slip
        ev_slip = float(np.mean(degraded_r))
        tot_slip = float(np.sum(degraded_r))
        wr_slip = float(np.mean(degraded_r > 0) * 100.0)
        dd_slip = calculate_max_drawdown(degraded_r.tolist())

        pos_sum = float(np.sum(degraded_r[degraded_r > 0])) if np.any(degraded_r > 0) else 0.0
        neg_sum = float(np.abs(np.sum(degraded_r[degraded_r < 0]))) if np.any(degraded_r < 0) else 1.0
        pf_slip = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 0.0

        slip_scenarios.append(
            SlippageScenario(
                slippage_r=slip,
                effective_expectancy_r=round(ev_slip, 4),
                effective_profit_factor=pf_slip,
                effective_total_r=round(tot_slip, 2),
                effective_win_rate_pct=round(wr_slip, 2),
                effective_max_drawdown_r=dd_slip,
                trades_count=real_n,
            )
        )

    # 2. Latency Delay Scenarios: 0-bar, 1-bar, 2-bar
    lat_scenarios: List[LatencyScenario] = [
        LatencyScenario(
            delay_bars=0,
            expectancy_r=round(base_ev, 4),
            profit_factor=base_pf,
            total_r=round(base_tot, 2),
            trades_count=real_n,
        )
    ]

    if forward_delay_r_map:
        for delay in [1, 2]:
            delayed_series = forward_delay_r_map.get(delay, [])
            if delayed_series:
                d_arr = np.array(delayed_series, dtype=float)
                d_ev = float(np.mean(d_arr))
                d_tot = float(np.sum(d_arr))
                d_pos = float(np.sum(d_arr[d_arr > 0])) if np.any(d_arr > 0) else 0.0
                d_neg = float(np.abs(np.sum(d_arr[d_arr < 0]))) if np.any(d_arr < 0) else 1.0
                d_pf = round(d_pos / d_neg, 2) if d_neg > 0 else 0.0
                lat_scenarios.append(
                    LatencyScenario(
                        delay_bars=delay,
                        expectancy_r=round(d_ev, 4),
                        profit_factor=d_pf,
                        total_r=round(d_tot, 2),
                        trades_count=len(delayed_series),
                    )
                )

    # 3. Strategy Classification
    # Check 0.10R slippage scenario
    scenario_10 = next((s for s in slip_scenarios if s.slippage_r == 0.10), slip_scenarios[0])

    if scenario_10.effective_expectancy_r >= 0.08 and scenario_10.effective_profit_factor >= 1.15:
        classification = "ROBUST"
        rationale = f"Strategy preserves solid positive edge (+{scenario_10.effective_expectancy_r:.4f}R, PF {scenario_10.effective_profit_factor:.2f}) under 0.10R friction."
    elif scenario_10.effective_expectancy_r > 0.0:
        classification = "SENSITIVE"
        rationale = f"Edge remains positive (+{scenario_10.effective_expectancy_r:.4f}R) under 0.10R friction, but deteriorates from baseline (+{base_ev:.4f}R)."
    else:
        classification = "FRAGILE"
        rationale = f"Edge turns negative ({scenario_10.effective_expectancy_r:+.4f}R) under realistic 0.10R execution friction."

    return ExecutionStressReport(
        symbol=symbol,
        real_n=real_n,
        baseline_expectancy_r=round(base_ev, 4),
        baseline_profit_factor=base_pf,
        baseline_total_r=round(base_tot, 2),
        baseline_win_rate_pct=round(base_wr, 2),
        baseline_max_drawdown_r=base_dd,
        slippage_scenarios=slip_scenarios,
        latency_scenarios=lat_scenarios,
        classification=classification,
        rationale=rationale,
    )
