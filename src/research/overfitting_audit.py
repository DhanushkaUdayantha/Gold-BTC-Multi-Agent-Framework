"""
Phase 3 Overfitting Audit Module.

Tracks every experiment, filter test, and policy comparison run during research
and computes Bonferroni-corrected significance thresholds to flag
MULTIPLE_TESTING_RISK.

Does NOT hide negative experiments.  All runs are recorded and included
in the final report.

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)

# Family-wide alpha for multiple testing correction
FAMILY_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ExperimentEntry:
    """Single experiment or comparison registered for overfitting tracking."""
    experiment_id: str
    experiment_type: str       # FILTER_ABLATION / POLICY_COMPARISON / ASSET_RESEARCH / CALIBRATION / OTHER
    description: str
    n_comparisons: int = 1     # How many hypotheses this experiment tests
    p_value: Optional[float] = None
    is_significant: Optional[bool] = None
    bonferroni_threshold: Optional[float] = None
    registered_at: str = ""

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()


@dataclass
class OverfittingReport:
    """Full multiple-testing audit."""
    generated_at: str
    total_experiments: int
    total_comparisons: int
    total_filters_tested: int
    total_policies_tested: int
    total_candidates_tested: int

    # Bonferroni correction
    family_alpha: float
    bonferroni_threshold: float   # alpha / total_comparisons
    adjusted_threshold_note: str

    # Risk assessment
    multiple_testing_risk: str    # LOW / MODERATE / HIGH / CRITICAL
    significant_at_bonferroni: int  # # experiments passing corrected threshold
    significant_at_nominal: int    # # experiments passing 0.05

    # All experiments
    experiments: List[ExperimentEntry] = field(default_factory=list)

    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class OverfittingAuditor:
    """
    Tracks experiments and computes multiple-testing risk.
    """

    def __init__(self):
        self._experiments: List[ExperimentEntry] = []

    def register(
        self,
        experiment_id: str,
        experiment_type: str,
        description: str,
        n_comparisons: int = 1,
        p_value: Optional[float] = None,
    ) -> None:
        """Register a research experiment or comparison."""
        entry = ExperimentEntry(
            experiment_id=experiment_id,
            experiment_type=experiment_type,
            description=description,
            n_comparisons=n_comparisons,
            p_value=p_value,
        )
        self._experiments.append(entry)

    def compute_report(self) -> OverfittingReport:
        """Compute the full overfitting / multiple-testing audit."""
        total_exp  = len(self._experiments)
        total_comp = max(sum(e.n_comparisons for e in self._experiments), 1)
        n_filters  = sum(1 for e in self._experiments if e.experiment_type == "FILTER_ABLATION")
        n_policies = sum(1 for e in self._experiments if e.experiment_type == "POLICY_COMPARISON")
        n_cands    = sum(1 for e in self._experiments if e.experiment_type == "ASSET_RESEARCH")

        bonf_threshold = FAMILY_ALPHA / total_comp

        # Update entries with their Bonferroni threshold
        sig_bonf = 0
        sig_nom  = 0
        for e in self._experiments:
            e.bonferroni_threshold = bonf_threshold
            if e.p_value is not None:
                e.is_significant = e.p_value < bonf_threshold
                if e.p_value < bonf_threshold:
                    sig_bonf += 1
                if e.p_value < FAMILY_ALPHA:
                    sig_nom += 1

        # Risk level
        if total_comp >= 100:
            risk = "CRITICAL"
        elif total_comp >= 50:
            risk = "HIGH"
        elif total_comp >= 20:
            risk = "MODERATE"
        else:
            risk = "LOW"

        adjusted_note = (
            f"With {total_comp} total comparisons, Bonferroni-corrected α = "
            f"{bonf_threshold:.4f}. "
            f"A result is significant only if p < {bonf_threshold:.4f}."
        )

        findings = [
            f"Total comparisons made: {total_comp} across {total_exp} experiments",
            f"Multiple-testing risk: {risk}",
            f"Nominal α=0.05 threshold: {sig_nom} experiment(s) would pass",
            f"Bonferroni α={bonf_threshold:.4f} threshold: {sig_bonf} experiment(s) pass",
        ]
        if risk in ("HIGH", "CRITICAL"):
            findings.append(
                "WARNING: High multiple-testing risk. Any 'statistically significant' "
                "result may be a false positive. All findings require independent OOS confirmation."
            )

        recommendations = []
        if n_filters > 5:
            recommendations.append(
                "Filter ablation tested many filters in parallel. "
                "Only promote filters with ADDS_VALUE verdict AND positive OOS delta."
            )
        if n_policies > 3:
            recommendations.append(
                "Multiple gating policies compared. "
                "Final policy must be evaluated on the UNTOUCHED holdout only."
            )
        if sig_nom > sig_bonf:
            recommendations.append(
                f"{sig_nom - sig_bonf} result(s) appear significant at α=0.05 "
                "but FAIL the Bonferroni threshold. "
                "Treat as exploratory / INSUFFICIENT_EVIDENCE."
            )

        return OverfittingReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_experiments=total_exp,
            total_comparisons=total_comp,
            total_filters_tested=n_filters,
            total_policies_tested=n_policies,
            total_candidates_tested=n_cands,
            family_alpha=FAMILY_ALPHA,
            bonferroni_threshold=round(bonf_threshold, 6),
            adjusted_threshold_note=adjusted_note,
            multiple_testing_risk=risk,
            significant_at_bonferroni=sig_bonf,
            significant_at_nominal=sig_nom,
            experiments=list(self._experiments),
            findings=findings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Singleton (shared across Phase 3 pipeline)
# ---------------------------------------------------------------------------

_global_auditor = OverfittingAuditor()


def get_global_auditor() -> OverfittingAuditor:
    """Return the singleton overfitting auditor used across Phase 3."""
    return _global_auditor


def reset_global_auditor() -> None:
    """Reset the global auditor (useful for testing)."""
    global _global_auditor
    _global_auditor = OverfittingAuditor()


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_overfitting_report(report: OverfittingReport) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "OVERFITTING_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "OVERFITTING_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write overfitting JSON: %s", exc)

    risk_emoji = {"LOW": "✅", "MODERATE": "⚠️", "HIGH": "🔴", "CRITICAL": "🚨"}.get(report.multiple_testing_risk, "?")
    lines = [
        "# Overfitting / Multiple-Testing Audit Report",
        f"\n**Generated:** {report.generated_at}",
        f"**Risk Level:** {risk_emoji} {report.multiple_testing_risk}",
        f"**Total Comparisons:** {report.total_comparisons}  |  "
        f"**Bonferroni α:** {report.bonferroni_threshold:.4f}",
        f"\n## Threshold Note",
        report.adjusted_threshold_note,
        f"\n## Summary",
        f"| Metric | Value |",
        "| --- | --- |",
        f"| Total Experiments | {report.total_experiments} |",
        f"| Filters Tested | {report.total_filters_tested} |",
        f"| Policies Tested | {report.total_policies_tested} |",
        f"| Sig @ α=0.05 | {report.significant_at_nominal} |",
        f"| Sig @ Bonferroni | {report.significant_at_bonferroni} |",
        "\n## Findings",
    ]
    for f_str in report.findings:
        lines.append(f"- {f_str}")
    lines += ["\n## Recommendations"]
    for r_str in report.recommendations:
        lines.append(f"- {r_str}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write overfitting MD: %s", exc)

    return json_path, md_path
