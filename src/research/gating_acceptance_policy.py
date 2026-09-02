"""
Fixed Gating Acceptance Policy.

Defines unambiguous, non-negotiable acceptance thresholds BEFORE experiment evaluation.
Thresholds are fixed to prevent post-hoc curve fitting or narrative-driven promotion.

Policy Version: 1.0

DISCLAIMER: Research governance layer only. Zero production decision logic modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

GATING_RESEARCH_POLICY_VERSION = "1.0"


class GovernanceClassification(str, Enum):
    PROMOTE_TO_GATING_RESEARCH = "PROMOTE_TO_GATING_RESEARCH"
    KEEP_ADVISORY = "KEEP_ADVISORY"
    REJECT = "REJECT"


class ThresholdStatus(str, Enum):
    PASSED = "PASSED"
    PREFERRED_PASSED = "PREFERRED_PASSED"
    BORDERLINE = "BORDERLINE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PolicyThresholds:
    """Fixed acceptance criteria for Gating Research Governance Policy v1.0."""
    # Sample Size
    min_sample_size: int = 500
    preferred_sample_size: int = 750

    # Expectancy
    min_expectancy_r: float = 0.15
    preferred_expectancy_r: float = 0.20

    # Profit Factor
    min_profit_factor: float = 1.20
    preferred_profit_factor: float = 1.30

    # Total Realized R
    min_total_realized_r: float = 0.0

    # Drawdown Benchmark (Validated Historical Benchmark = 10.5R)
    historical_benchmark_dd_r: float = 10.5
    max_dd_ratio_multiplier: float = 1.25  # Max allowable DD = 13.125R

    # Stability & Rolling Performance
    max_rolling_50_negative_ratio: float = 0.10  # <= 10% negative rolling-50 windows
    min_median_rolling_expectancy: float = 0.0

    # Walk-Forward & OOS
    min_walk_forward_positive_ratio: float = 0.75  # >= 75% positive folds
    require_positive_holdout: bool = True

    # Trade Elimination & Retention
    min_winner_retention_ratio: float = 0.30  # At least 30% of winners retained
    min_loser_reduction_ratio: float = 0.50   # At least 50% of losers eliminated

    # Slippage Stress Robustness
    min_slippage_robust_r: float = 0.10  # Must maintain positive expectancy under 0.10R slippage


@dataclass
class PolicyEvaluationResult:
    """Detailed result of policy threshold evaluation."""
    policy_version: str
    overall_status: GovernanceClassification
    checks: Dict[str, Dict[str, Any]]
    passed_count: int
    failed_count: int
    critical_failures: List[str]
    summary_reason: str


def evaluate_acceptance_policy(
    sample_size: int,
    expectancy_r: float,
    profit_factor: float,
    total_realized_r: float,
    max_drawdown_r: float,
    rolling_50_negative_ratio: float,
    median_rolling_exp: float,
    walk_forward_pos_ratio: float,
    holdout_expectancy_r: float,
    winner_retention_ratio: float,
    loser_reduction_ratio: float,
    expectancy_at_010_slippage: float,
    thresholds: Optional[PolicyThresholds] = None,
) -> PolicyEvaluationResult:
    """
    Evaluate experimental performance strictly against Policy Thresholds v1.0.
    """
    t = thresholds or PolicyThresholds()
    checks: Dict[str, Dict[str, Any]] = {}
    critical_failures: List[str] = []

    # 1. Sample Size Check
    sample_pass = sample_size >= t.min_sample_size
    sample_pref = sample_size >= t.preferred_sample_size
    checks["sample_size"] = {
        "value": sample_size,
        "required": t.min_sample_size,
        "preferred": t.preferred_sample_size,
        "status": ThresholdStatus.PREFERRED_PASSED if sample_pref else (ThresholdStatus.PASSED if sample_pass else ThresholdStatus.FAILED),
    }
    if not sample_pass:
        critical_failures.append(f"Insufficient sample size: {sample_size} < {t.min_sample_size}")

    # 2. Expectancy Check
    exp_pass = expectancy_r >= t.min_expectancy_r
    exp_pref = expectancy_r >= t.preferred_expectancy_r
    checks["expectancy"] = {
        "value": expectancy_r,
        "required": t.min_expectancy_r,
        "preferred": t.preferred_expectancy_r,
        "status": ThresholdStatus.PREFERRED_PASSED if exp_pref else (ThresholdStatus.PASSED if exp_pass else ThresholdStatus.FAILED),
    }
    if not exp_pass:
        critical_failures.append(f"Expectancy sub-threshold: {expectancy_r:.3f}R < {t.min_expectancy_r:.2f}R")

    # 3. Profit Factor Check
    pf_pass = profit_factor >= t.min_profit_factor
    pf_pref = profit_factor >= t.preferred_profit_factor
    checks["profit_factor"] = {
        "value": profit_factor,
        "required": t.min_profit_factor,
        "preferred": t.preferred_profit_factor,
        "status": ThresholdStatus.PREFERRED_PASSED if pf_pref else (ThresholdStatus.PASSED if pf_pass else ThresholdStatus.FAILED),
    }
    if not pf_pass:
        critical_failures.append(f"Profit Factor sub-threshold: {profit_factor:.2f} < {t.min_profit_factor:.2f}")

    # 4. Total Realized R Check
    tot_pass = total_realized_r > t.min_total_realized_r
    checks["total_realized_r"] = {
        "value": total_realized_r,
        "required": t.min_total_realized_r,
        "status": ThresholdStatus.PASSED if tot_pass else ThresholdStatus.FAILED,
    }
    if not tot_pass:
        critical_failures.append(f"Total Realized R non-positive: {total_realized_r:.2f}R <= 0")

    # 5. Drawdown Check
    max_allowable_dd = t.historical_benchmark_dd_r * t.max_dd_ratio_multiplier
    dd_pass = max_drawdown_r <= max_allowable_dd
    checks["max_drawdown"] = {
        "value": max_drawdown_r,
        "benchmark": t.historical_benchmark_dd_r,
        "max_allowable": max_allowable_dd,
        "status": ThresholdStatus.PASSED if dd_pass else ThresholdStatus.FAILED,
    }
    if not dd_pass:
        critical_failures.append(f"Max Drawdown exceeded allowable limit: {max_drawdown_r:.2f}R > {max_allowable_dd:.2f}R")

    # 6. Rolling-50 Stability Check
    roll_pass = rolling_50_negative_ratio <= t.max_rolling_50_negative_ratio
    checks["rolling_stability"] = {
        "negative_window_ratio": rolling_50_negative_ratio,
        "max_allowable": t.max_rolling_50_negative_ratio,
        "median_rolling_exp": median_rolling_exp,
        "status": ThresholdStatus.PASSED if (roll_pass and median_rolling_exp > 0) else ThresholdStatus.FAILED,
    }
    if not (roll_pass and median_rolling_exp > 0):
        critical_failures.append(f"Rolling-50 stability failed: {rolling_50_negative_ratio*100:.1f}% negative windows or non-positive median")

    # 7. Walk-Forward Check
    wf_pass = walk_forward_pos_ratio >= t.min_walk_forward_positive_ratio
    checks["walk_forward"] = {
        "positive_window_ratio": walk_forward_pos_ratio,
        "required": t.min_walk_forward_positive_ratio,
        "status": ThresholdStatus.PASSED if wf_pass else ThresholdStatus.FAILED,
    }
    if not wf_pass:
        critical_failures.append(f"Walk-forward positive window ratio failed: {walk_forward_pos_ratio*100:.1f}% < {t.min_walk_forward_positive_ratio*100:.1f}%")

    # 8. Holdout / OOS Check
    holdout_pass = holdout_expectancy_r > 0.0 if t.require_positive_holdout else True
    checks["untouched_holdout"] = {
        "holdout_expectancy_r": holdout_expectancy_r,
        "required_positive": t.require_positive_holdout,
        "status": ThresholdStatus.PASSED if holdout_pass else ThresholdStatus.FAILED,
    }
    if not holdout_pass:
        critical_failures.append(f"Untouched holdout expectancy non-positive: {holdout_expectancy_r:.3f}R <= 0")

    # 9. Winner Retention & Loser Elimination Check
    win_ret_pass = winner_retention_ratio >= t.min_winner_retention_ratio
    lose_red_pass = loser_reduction_ratio >= t.min_loser_reduction_ratio
    checks["trade_elimination"] = {
        "winner_retention_ratio": winner_retention_ratio,
        "loser_reduction_ratio": loser_reduction_ratio,
        "min_winner_retention": t.min_winner_retention_ratio,
        "min_loser_reduction": t.min_loser_reduction_ratio,
        "status": ThresholdStatus.PASSED if (win_ret_pass and lose_red_pass) else ThresholdStatus.FAILED,
    }
    if not (win_ret_pass and lose_red_pass):
        critical_failures.append(f"Trade elimination asymmetry failed (Win Ret: {winner_retention_ratio*100:.1f}%, Loser Red: {loser_reduction_ratio*100:.1f}%)")

    # 10. Slippage Stress Check
    slip_pass = expectancy_at_010_slippage > 0.0
    checks["slippage_stress"] = {
        "expectancy_at_010_slippage": expectancy_at_010_slippage,
        "status": ThresholdStatus.PASSED if slip_pass else ThresholdStatus.FAILED,
    }
    if not slip_pass:
        critical_failures.append(f"Failed slippage stress test: Expectancy at 0.10R slippage is {expectancy_at_010_slippage:.3f}R <= 0")

    passed_count = sum(1 for c in checks.values() if c["status"] in (ThresholdStatus.PASSED, ThresholdStatus.PREFERRED_PASSED))
    failed_count = len(checks) - passed_count

    # Determine Governance Classification
    if len(critical_failures) == 0 and passed_count == len(checks):
        classification = GovernanceClassification.PROMOTE_TO_GATING_RESEARCH
        summary = "All mandatory and stability thresholds satisfied under strict point-in-time validation. Qualified for future controlled gating research."
    elif len(critical_failures) <= 2 and expectancy_r > 0.05 and profit_factor > 1.05:
        classification = GovernanceClassification.KEEP_ADVISORY
        summary = f"Performance positive but failed {len(critical_failures)} stability/gating thresholds. Retain as advisory layer only."
    else:
        classification = GovernanceClassification.REJECT
        summary = f"Severe governance threshold failures ({len(critical_failures)} critical failures). Gating rejected."

    return PolicyEvaluationResult(
        policy_version=GATING_RESEARCH_POLICY_VERSION,
        overall_status=classification,
        checks=checks,
        passed_count=passed_count,
        failed_count=failed_count,
        critical_failures=critical_failures,
        summary_reason=summary,
    )
