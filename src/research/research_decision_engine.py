"""
Phase 3 Research Decision Engine.

Aggregates all research findings and produces a statistically-grounded,
human-readable governance decision for each evaluated strategy change.

Decision outputs:
  REJECT               — Evidence is negative or insufficient
  KEEP_ADVISORY        — No change; current behavior is appropriate
  PROMISING            — Positive signals but insufficient evidence
  RESEARCH_APPROVED    — Strong evidence across all validation stages
  PRODUCTION_CANDIDATE — Exceptional evidence; requires explicit human approval
                         before ANY production deployment

⚠️  PRODUCTION_CANDIDATE NEVER auto-activates any filter.
⚠️  Only advisory; production changes require explicit human authorization.

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Decision taxonomy
# ---------------------------------------------------------------------------

class ResearchDecision(str):
    REJECT               = "REJECT"
    KEEP_ADVISORY        = "KEEP_ADVISORY"
    PROMISING            = "PROMISING"
    RESEARCH_APPROVED    = "RESEARCH_APPROVED"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"


# ---------------------------------------------------------------------------
# Evidence sources
# ---------------------------------------------------------------------------

@dataclass
class EvidenceInput:
    """Consolidated summary inputs from Phase 3 research modules."""
    # Core metrics
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    total_trades: int

    # OOS
    oos_expectancy_r: float
    oos_trades: int

    # Walk-forward
    wf_positive_ratio: float      # 0.0–1.0
    wf_median_expectancy: float

    # Holdout
    holdout_expectancy_r: float
    holdout_trades: int

    # Stress
    stress_passes_slippage: bool
    stress_passes_execution: bool
    mc_p5_drawdown_r: float       # 5th-percentile worst MC drawdown

    # Statistical
    p_value: Optional[float]
    expectancy_ci_lower: float
    expectancy_ci_upper: float

    # Overfitting / multiple testing
    overfitting_risk: str          # LOW / MODERATE / HIGH / CRITICAL

    # Robustness score
    robustness_score: float        # 0–100
    robustness_grade: str          # A / B / C / D / F

    # Asset-level
    btc_robustness: str            # ROBUST / PROMISING / WEAK / UNSTABLE / INSUFFICIENT_DATA
    xau_robustness: str

    # Calibration
    brier_score: float             # Lower = better; 0.25 = no-skill
    calibration_classification: str  # OVERCONFIDENT / UNDERCONFIDENT / WELL_CALIBRATED / MIXED

    # Missed winners
    winner_retention_pct: float
    loser_reduction_pct: float
    benefit_cost_ratio: float

    # Filter ablation summary
    filters_adds_value: List[str] = field(default_factory=list)
    filters_hurts: List[str] = field(default_factory=list)

    # Governance context
    strategy_label: str = "Phase3_Research"
    dataset_version: str = "v1.0"


@dataclass
class GovernanceGate:
    """One required gate for a target decision level."""
    gate_name: str
    description: str
    required: bool
    passed: Optional[bool]
    detail: str


@dataclass
class ResearchDecisionRecord:
    """Complete governance decision."""
    generated_at: str
    strategy_label: str
    dataset_version: str

    decision: str    # ResearchDecision value
    evidence_level: str    # STRONG / MODERATE / WEAK / INSUFFICIENT
    confidence: str        # HIGH / MEDIUM / LOW

    # Required gates per decision level
    gates: List[GovernanceGate]
    gates_passed: int
    gates_failed: int

    # Summary
    supporting_evidence: List[str]
    counter_evidence: List[str]
    conditions_to_promote: List[str]   # What would push to PRODUCTION_CANDIDATE
    action_items: List[str]

    # Source metrics snapshot
    evidence: EvidenceInput

    # CRITICAL disclaimer
    disclaimer: str = (
        "⚠️  RESEARCH ADVISORY ONLY.  This decision DOES NOT authorize any production change. "
        "PRODUCTION_CANDIDATE requires explicit written human approval before any deployment. "
        "Past performance does not guarantee future results."
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ResearchDecisionEngine:
    """
    Evaluates all Phase 3 evidence and produces a governance decision.
    """

    # Gate thresholds
    MINIMUM_TRADES       = 100
    MINIMUM_EXPECTANCY   = 0.05    # R
    MINIMUM_OOS_EXP      = 0.02
    MINIMUM_WF_RATIO     = 0.50    # 50% positive folds
    MINIMUM_PF           = 1.10
    MAX_MC_DRAWDOWN      = 35.0    # Max acceptable 5th-pct Monte Carlo DD
    MAX_BRIER_PASSMARK   = 0.23
    MIN_BCR              = 1.0     # Benefit-cost ratio for filter

    @classmethod
    def evaluate(cls, evidence: EvidenceInput) -> ResearchDecisionRecord:
        """Run all governance gates and return a ResearchDecisionRecord."""
        gates: List[GovernanceGate] = []

        # ---- Gate 1: Sample size ----
        gates.append(GovernanceGate(
            gate_name="SAMPLE_SIZE",
            description=f"≥{cls.MINIMUM_TRADES} resolved trades",
            required=True,
            passed=evidence.total_trades >= cls.MINIMUM_TRADES,
            detail=f"{evidence.total_trades} trades",
        ))

        # ---- Gate 2: Positive expectancy ----
        gates.append(GovernanceGate(
            gate_name="POSITIVE_EXPECTANCY",
            description=f"Expectancy ≥ +{cls.MINIMUM_EXPECTANCY}R",
            required=True,
            passed=evidence.expectancy_r >= cls.MINIMUM_EXPECTANCY,
            detail=f"{evidence.expectancy_r:+.4f}R",
        ))

        # ---- Gate 3: OOS positive ----
        gates.append(GovernanceGate(
            gate_name="OOS_POSITIVE",
            description=f"OOS expectancy ≥ +{cls.MINIMUM_OOS_EXP}R",
            required=True,
            passed=evidence.oos_expectancy_r >= cls.MINIMUM_OOS_EXP,
            detail=f"{evidence.oos_expectancy_r:+.4f}R (n={evidence.oos_trades})",
        ))

        # ---- Gate 4: Walk-forward ----
        gates.append(GovernanceGate(
            gate_name="WALK_FORWARD",
            description=f"≥{cls.MINIMUM_WF_RATIO:.0%} WF folds positive",
            required=True,
            passed=evidence.wf_positive_ratio >= cls.MINIMUM_WF_RATIO,
            detail=f"{evidence.wf_positive_ratio:.0%} positive folds",
        ))

        # ---- Gate 5: Profit factor ----
        gates.append(GovernanceGate(
            gate_name="PROFIT_FACTOR",
            description=f"Profit Factor ≥ {cls.MINIMUM_PF}",
            required=True,
            passed=evidence.profit_factor >= cls.MINIMUM_PF,
            detail=f"PF={evidence.profit_factor:.2f}",
        ))

        # ---- Gate 6: Monte Carlo max DD ----
        gates.append(GovernanceGate(
            gate_name="MONTE_CARLO_DD",
            description=f"MC 5th-pct drawdown ≤ {cls.MAX_MC_DRAWDOWN}R",
            required=True,
            passed=evidence.mc_p5_drawdown_r <= cls.MAX_MC_DRAWDOWN,
            detail=f"MC P5 DD = {evidence.mc_p5_drawdown_r:.1f}R",
        ))

        # ---- Gate 7: Overfitting risk ----
        gates.append(GovernanceGate(
            gate_name="OVERFITTING_RISK",
            description="Multiple-testing risk is LOW or MODERATE",
            required=True,
            passed=evidence.overfitting_risk in ("LOW", "MODERATE"),
            detail=f"Risk = {evidence.overfitting_risk}",
        ))

        # ---- Gate 8: Holdout positive ----
        gates.append(GovernanceGate(
            gate_name="HOLDOUT_POSITIVE",
            description="Untouched holdout expectancy ≥ 0",
            required=False,
            passed=evidence.holdout_expectancy_r >= 0 if evidence.holdout_trades >= 20 else None,
            detail=f"{evidence.holdout_expectancy_r:+.4f}R (n={evidence.holdout_trades})",
        ))

        # ---- Gate 9: Calibration ----
        gates.append(GovernanceGate(
            gate_name="AI_CALIBRATION",
            description=f"Brier score ≤ {cls.MAX_BRIER_PASSMARK}",
            required=False,
            passed=evidence.brier_score <= cls.MAX_BRIER_PASSMARK,
            detail=f"Brier={evidence.brier_score:.4f} ({evidence.calibration_classification})",
        ))

        # ---- Gate 10: Stress tests ----
        gates.append(GovernanceGate(
            gate_name="STRESS_TESTS",
            description="Passes slippage stress test",
            required=False,
            passed=evidence.stress_passes_slippage,
            detail="Slippage=OK" if evidence.stress_passes_slippage else "Slippage=FAIL",
        ))

        # ---- Gate 11: BCR ≥ 1.0 ----
        gates.append(GovernanceGate(
            gate_name="FILTER_BCR",
            description=f"Filter benefit-cost ratio ≥ {cls.MIN_BCR}",
            required=False,
            passed=evidence.benefit_cost_ratio >= cls.MIN_BCR,
            detail=f"BCR={evidence.benefit_cost_ratio:.2f}",
        ))

        # ---- Gate 12: Robustness grade ----
        gates.append(GovernanceGate(
            gate_name="ROBUSTNESS_GRADE",
            description="Robustness grade ≥ B (score ≥ 70)",
            required=False,
            passed=evidence.robustness_score >= 70,
            detail=f"Score={evidence.robustness_score:.0f}, Grade={evidence.robustness_grade}",
        ))

        required_gates  = [g for g in gates if g.required]
        optional_gates  = [g for g in gates if not g.required]
        required_pass   = [g for g in required_gates if g.passed is True]
        required_fail   = [g for g in required_gates if g.passed is False]
        optional_pass   = [g for g in optional_gates if g.passed is True]
        all_pass        = len(required_pass) + len(optional_pass)
        all_fail        = len(required_fail)

        # Decision logic
        decision, level, confidence = cls._decision_logic(
            required_pass=len(required_pass),
            required_fail=len(required_fail),
            required_total=len(required_gates),
            optional_pass=len(optional_pass),
            optional_total=len(optional_gates),
            evidence=evidence,
        )

        supporting, counter, promote, actions = cls._narrative(
            decision, gates, evidence
        )

        return ResearchDecisionRecord(
            generated_at=datetime.now(timezone.utc).isoformat(),
            strategy_label=evidence.strategy_label,
            dataset_version=evidence.dataset_version,
            decision=decision,
            evidence_level=level,
            confidence=confidence,
            gates=gates,
            gates_passed=all_pass,
            gates_failed=all_fail,
            supporting_evidence=supporting,
            counter_evidence=counter,
            conditions_to_promote=promote,
            action_items=actions,
            evidence=evidence,
        )

    @classmethod
    def _decision_logic(
        cls,
        required_pass: int,
        required_fail: int,
        required_total: int,
        optional_pass: int,
        optional_total: int,
        evidence: EvidenceInput,
    ) -> Tuple[str, str, str]:
        all_required_pass = required_fail == 0

        if not all_required_pass:
            if required_fail >= required_total // 2:
                return ResearchDecision.REJECT, "INSUFFICIENT", "HIGH"
            return ResearchDecision.REJECT, "WEAK", "MEDIUM"

        opt_ratio = optional_pass / max(optional_total, 1)

        if (opt_ratio >= 0.80
                and evidence.robustness_score >= 80
                and evidence.holdout_expectancy_r >= 0.05
                and evidence.holdout_trades >= 20
                and evidence.overfitting_risk == "LOW"):
            return ResearchDecision.PRODUCTION_CANDIDATE, "STRONG", "HIGH"

        if (opt_ratio >= 0.60
                and evidence.robustness_score >= 65
                and evidence.wf_positive_ratio >= 0.65):
            return ResearchDecision.RESEARCH_APPROVED, "STRONG", "HIGH"

        if opt_ratio >= 0.40 or evidence.robustness_score >= 55:
            return ResearchDecision.PROMISING, "MODERATE", "MEDIUM"

        return ResearchDecision.KEEP_ADVISORY, "MODERATE", "MEDIUM"

    @staticmethod
    def _narrative(
        decision: str,
        gates: List[GovernanceGate],
        evidence: EvidenceInput,
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        supporting, counter, promote, actions = [], [], [], []

        passed = [g for g in gates if g.passed is True]
        failed = [g for g in gates if g.passed is False]

        for g in passed:
            supporting.append(f"✅ {g.gate_name}: {g.detail}")
        for g in failed:
            counter.append(f"❌ {g.gate_name}: {g.detail} — REQUIRED" if g.required else f"⚠️  {g.gate_name}: {g.detail}")

        # Promotion conditions
        if evidence.holdout_trades < 20:
            promote.append("Collect more holdout data (≥20 trades in holdout period)")
        if evidence.robustness_score < 80:
            promote.append(f"Improve robustness score to ≥80 (current: {evidence.robustness_score:.0f})")
        if evidence.holdout_expectancy_r < 0.05:
            promote.append(f"Holdout expectancy must reach ≥+0.05R (current: {evidence.holdout_expectancy_r:+.4f}R)")
        if evidence.overfitting_risk not in ("LOW",):
            promote.append(f"Reduce overfitting risk to LOW (current: {evidence.overfitting_risk})")

        # Actions
        actions.append(f"Decision: {decision} — do NOT modify production until explicitly authorized")
        if decision in (ResearchDecision.PROMISING, ResearchDecision.RESEARCH_APPROVED):
            actions.append("Run extended OOS validation on a wider date range before re-evaluating")
        if decision == ResearchDecision.PRODUCTION_CANDIDATE:
            actions.append("⚠️  HUMAN AUTHORIZATION REQUIRED before any production deployment")
            actions.append("Present this report to the governance board for sign-off")
        if evidence.filters_hurts:
            actions.append(f"Investigate filters that HURT performance: {', '.join(evidence.filters_hurts)}")

        return supporting, counter, promote, actions


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_governance_report(record: ResearchDecisionRecord) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "FINAL_PHASE3_GOVERNANCE_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "FINAL_PHASE3_GOVERNANCE_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(record), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write governance JSON: %s", exc)

    decision_icon = {
        "REJECT": "🔴",
        "KEEP_ADVISORY": "🟡",
        "PROMISING": "🔵",
        "RESEARCH_APPROVED": "✅",
        "PRODUCTION_CANDIDATE": "🏆",
    }.get(record.decision, "?")

    lines = [
        "# Final Phase 3 Governance Report",
        f"\n**Generated:** {record.generated_at}",
        f"**Strategy:** {record.strategy_label}  |  **Dataset:** {record.dataset_version}",
        f"\n## Decision: {decision_icon} {record.decision}",
        f"**Evidence Level:** {record.evidence_level}  |  **Confidence:** {record.confidence}",
        f"**Gates Passed:** {record.gates_passed}  |  **Gates Failed:** {record.gates_failed}",
        "\n> " + record.disclaimer,
        "\n## Supporting Evidence",
    ]
    for s in record.supporting_evidence:
        lines.append(f"- {s}")
    lines += ["\n## Counter Evidence"]
    for c in record.counter_evidence:
        lines.append(f"- {c}")

    lines += ["\n## Gate Summary", "| Gate | Required | Passed | Detail |", "| --- | --- | --- | --- |"]
    for g in record.gates:
        passed_str = "✅" if g.passed else ("❌" if g.passed is False else "➖")
        req_str = "YES" if g.required else "no"
        lines.append(f"| {g.gate_name} | {req_str} | {passed_str} | {g.detail} |")

    lines += ["\n## Conditions to Promote"]
    for p in record.conditions_to_promote:
        lines.append(f"- {p}")
    lines += ["\n## Required Actions"]
    for a in record.action_items:
        lines.append(f"- {a}")

    # Key evidence snapshot
    e = record.evidence
    lines += [
        "\n## Evidence Snapshot",
        "| Metric | Value |", "| --- | --- |",
        f"| Trades | {e.total_trades} |",
        f"| Expectancy | {e.expectancy_r:+.4f}R [{e.expectancy_ci_lower:+.3f}–{e.expectancy_ci_upper:+.3f}] |",
        f"| Profit Factor | {e.profit_factor:.2f} |",
        f"| Max Drawdown | {e.max_drawdown_r:.1f}R |",
        f"| OOS Expectancy | {e.oos_expectancy_r:+.4f}R (n={e.oos_trades}) |",
        f"| WF Positive Ratio | {e.wf_positive_ratio:.0%} |",
        f"| MC P5 Drawdown | {e.mc_p5_drawdown_r:.1f}R |",
        f"| Robustness Score | {e.robustness_score:.0f}/100 (Grade {e.robustness_grade}) |",
        f"| Brier Score | {e.brier_score:.4f} |",
        f"| Overfitting Risk | {e.overfitting_risk} |",
        f"| BTC Robustness | {e.btc_robustness} |",
        f"| XAU Robustness | {e.xau_robustness} |",
    ]

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write governance MD: %s", exc)

    return json_path, md_path
