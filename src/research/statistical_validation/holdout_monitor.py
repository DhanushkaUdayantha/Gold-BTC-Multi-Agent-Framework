"""
Holdout Sample Sufficiency & Milestone Monitor Module.

Tracks progressive forward sample accumulation for small-sample assets (specifically XAU/USD N=42 holdout).
Defines immutable milestones (N >= 50, 75, 100, 150, 200) and prevents premature claims of statistical proof.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MilestoneThreshold:
    """Evaluation criteria and status for a specific sample size tier."""
    target_n: int
    current_n: int
    is_reached: bool
    status_label: str
    required_expectancy_r: float
    required_win_rate_pct: float
    required_profit_factor: float


@dataclass
class HoldoutMilestoneReport:
    """Progressive holdout monitoring report for XAU/USD and BTC/USD."""
    symbol: str
    current_holdout_n: int
    forward_shadow_resolved_n: int
    total_evaluable_n: int
    active_milestone_target: int
    milestone_progress_pct: float
    sample_sufficiency_status: str  # "INSUFFICIENT_SAMPLE", "PRELIMINARY", "PROMISING", "STABLE"
    milestones: List[MilestoneThreshold]
    next_action_recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_holdout_milestones(
    symbol: str = "XAU/USD",
    current_holdout_n: int = 42,
    forward_shadow_resolved_n: int = 0,
) -> HoldoutMilestoneReport:
    """
    Evaluate sample sufficiency against predefined fixed research milestones.
    
    Milestones:
    - Tier 1: N >= 50  (Preliminary signal)
    - Tier 2: N >= 75  (Initial statistical power)
    - Tier 3: N >= 100 (Minimum acceptable holdout threshold)
    - Tier 4: N >= 150 (Robust evaluation)
    - Tier 5: N >= 200 (Institutional grade evidence)
    """
    total_n = current_holdout_n + forward_shadow_resolved_n
    milestone_targets = [50, 75, 100, 150, 200]
    milestone_objects: List[MilestoneThreshold] = []

    active_target = 200
    for t in milestone_targets:
        reached = total_n >= t
        if not reached and active_target == 200:
            active_target = t

        label = "REACHED" if reached else "PENDING"
        milestone_objects.append(
            MilestoneThreshold(
                target_n=t,
                current_n=total_n,
                is_reached=reached,
                status_label=label,
                required_expectancy_r=0.10,
                required_win_rate_pct=45.0,
                required_profit_factor=1.20,
            )
        )

    # Determine Overall Sample Sufficiency Status
    if total_n < 50:
        sufficiency = "INSUFFICIENT_SAMPLE"
        action = f"Current sample N={total_n} is too small. Continue collecting live forward shadow observations until N>=50."
    elif total_n < 100:
        sufficiency = "PRELIMINARY"
        action = f"Sample N={total_n} reached Tier 1. Continue accumulating forward shadow observations toward N>=100."
    elif total_n < 150:
        sufficiency = "PROMISING"
        action = f"Sample N={total_n} reached Tier 3 threshold. Safe for initial statistical significance testing."
    else:
        sufficiency = "STABLE"
        action = f"Sample N={total_n} provides robust statistical sample support."

    progress_pct = min(100.0, round((total_n / active_target) * 100.0, 1))

    return HoldoutMilestoneReport(
        symbol=symbol,
        current_holdout_n=current_holdout_n,
        forward_shadow_resolved_n=forward_shadow_resolved_n,
        total_evaluable_n=total_n,
        active_milestone_target=active_target,
        milestone_progress_pct=progress_pct,
        sample_sufficiency_status=sufficiency,
        milestones=milestone_objects,
        next_action_recommendation=action,
    )
