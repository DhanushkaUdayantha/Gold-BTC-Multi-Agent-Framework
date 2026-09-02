"""
Phase 3 Robustness Scoring Engine.

Computes a multi-dimensional, explainable robustness score (0–100) for a
research trading edge, with letter grade:
  A = ≥85  B = 70–84  C = 55–69  D = 40–54  F = <40

Each dimension is scored independently and contributes a transparent portion.
Weak areas are NOT hidden by strong areas.

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
# Score components (max points per dimension)
# ---------------------------------------------------------------------------

MAX_SCORES = {
    "expectancy_quality":   15,
    "oos_stability":        15,
    "wf_stability":         10,
    "profit_factor":        10,
    "drawdown_quality":     10,
    "calibration":          10,
    "regime_stability":     8,
    "asset_stability":      8,
    "session_stability":    5,
    "stress_robustness":    5,
    "statistical_evidence": 4,
}
TOTAL_MAX = sum(MAX_SCORES.values())   # 100


@dataclass
class DimensionScore:
    dimension: str
    max_points: int
    earned_points: float
    pct: float
    status: str    # STRONG / ADEQUATE / WEAK / CRITICAL / UNAVAILABLE
    detail: str


@dataclass
class RobustnessScore:
    """Multi-dimensional robustness score."""
    generated_at: str
    strategy_label: str
    total_score: float         # 0–100
    grade: str                 # A / B / C / D / F
    dimensions: List[DimensionScore] = field(default_factory=list)
    weak_areas: List[str]      = field(default_factory=list)
    strong_areas: List[str]    = field(default_factory=list)
    summary: str = ""
    disclaimer: str = "Research-only robustness score. Not a guarantee of future performance."


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class RobustnessScorer:
    """
    Computes an explainable robustness score from research metrics.
    """

    @classmethod
    def score(
        cls,
        strategy_label: str,
        expectancy_r: float,
        profit_factor: float,
        max_drawdown_r: float,
        oos_expectancy: float,
        wf_positive_ratio: float,           # 0.0–1.0 (e.g. 0.75 = 3/4)
        wf_median_expectancy: float,
        calibration_brier: float,           # 0.25 = no-skill
        calibration_ece: float,             # 0.0–1.0; lower = better
        regime_positive_pct: float,         # % regimes with positive expectancy
        asset_max_dd_ratio: float,          # max DD per asset / overall DD (1.0 = balanced)
        session_positive_pct: float,        # % sessions with positive expectancy
        stress_passes_slippage: bool,
        stress_passes_execution: bool,
        p_value: Optional[float],
        sample_size: int,
        overfitting_risk: str = "LOW",      # LOW / MODERATE / HIGH / CRITICAL
    ) -> RobustnessScore:
        dims: List[DimensionScore] = []

        # 1. Expectancy Quality (15 pts)
        pts, status, detail = cls._score_expectancy(expectancy_r, sample_size)
        dims.append(DimensionScore("expectancy_quality", MAX_SCORES["expectancy_quality"],
                                   pts, cls._pct(pts, MAX_SCORES["expectancy_quality"]), status, detail))

        # 2. OOS Stability (15 pts)
        pts, status, detail = cls._score_oos(oos_expectancy, sample_size)
        dims.append(DimensionScore("oos_stability", MAX_SCORES["oos_stability"],
                                   pts, cls._pct(pts, MAX_SCORES["oos_stability"]), status, detail))

        # 3. Walk-Forward Stability (10 pts)
        pts, status, detail = cls._score_wf(wf_positive_ratio, wf_median_expectancy)
        dims.append(DimensionScore("wf_stability", MAX_SCORES["wf_stability"],
                                   pts, cls._pct(pts, MAX_SCORES["wf_stability"]), status, detail))

        # 4. Profit Factor (10 pts)
        pts, status, detail = cls._score_pf(profit_factor)
        dims.append(DimensionScore("profit_factor", MAX_SCORES["profit_factor"],
                                   pts, cls._pct(pts, MAX_SCORES["profit_factor"]), status, detail))

        # 5. Drawdown Quality (10 pts)
        pts, status, detail = cls._score_dd(max_drawdown_r, expectancy_r)
        dims.append(DimensionScore("drawdown_quality", MAX_SCORES["drawdown_quality"],
                                   pts, cls._pct(pts, MAX_SCORES["drawdown_quality"]), status, detail))

        # 6. AI Calibration (10 pts)
        pts, status, detail = cls._score_calibration(calibration_brier, calibration_ece)
        dims.append(DimensionScore("calibration", MAX_SCORES["calibration"],
                                   pts, cls._pct(pts, MAX_SCORES["calibration"]), status, detail))

        # 7. Regime Stability (8 pts)
        pts, status, detail = cls._score_regime(regime_positive_pct)
        dims.append(DimensionScore("regime_stability", MAX_SCORES["regime_stability"],
                                   pts, cls._pct(pts, MAX_SCORES["regime_stability"]), status, detail))

        # 8. Asset Stability (8 pts)
        pts, status, detail = cls._score_asset(asset_max_dd_ratio)
        dims.append(DimensionScore("asset_stability", MAX_SCORES["asset_stability"],
                                   pts, cls._pct(pts, MAX_SCORES["asset_stability"]), status, detail))

        # 9. Session Stability (5 pts)
        pts, status, detail = cls._score_session(session_positive_pct)
        dims.append(DimensionScore("session_stability", MAX_SCORES["session_stability"],
                                   pts, cls._pct(pts, MAX_SCORES["session_stability"]), status, detail))

        # 10. Stress Robustness (5 pts)
        pts, status, detail = cls._score_stress(stress_passes_slippage, stress_passes_execution)
        dims.append(DimensionScore("stress_robustness", MAX_SCORES["stress_robustness"],
                                   pts, cls._pct(pts, MAX_SCORES["stress_robustness"]), status, detail))

        # 11. Statistical Evidence (4 pts)
        pts, status, detail = cls._score_statistics(p_value, sample_size)
        dims.append(DimensionScore("statistical_evidence", MAX_SCORES["statistical_evidence"],
                                   pts, cls._pct(pts, MAX_SCORES["statistical_evidence"]), status, detail))

        raw_total = sum(d.earned_points for d in dims)

        # Overfitting penalty
        penalty = {"LOW": 0.0, "MODERATE": 2.0, "HIGH": 5.0, "CRITICAL": 10.0}.get(overfitting_risk, 0.0)
        total = max(0.0, round(raw_total - penalty, 1))

        grade = cls._grade(total)

        weak   = [d.dimension for d in dims if d.status in ("WEAK", "CRITICAL")]
        strong = [d.dimension for d in dims if d.status == "STRONG"]

        summary = (
            f"Total: {total:.0f}/100 (Grade {grade}). "
            f"Strong: [{', '.join(strong)}]. "
            f"Weak: [{', '.join(weak)}]. "
            f"Overfitting risk: {overfitting_risk} ({penalty:.0f}pt penalty)."
        )

        return RobustnessScore(
            generated_at=datetime.now(timezone.utc).isoformat(),
            strategy_label=strategy_label,
            total_score=total,
            grade=grade,
            dimensions=dims,
            weak_areas=weak,
            strong_areas=strong,
            summary=summary,
        )

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _pct(pts: float, max_pts: int) -> float:
        return round(pts / max_pts * 100, 1)

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 85:  return "A"
        if score >= 70:  return "B"
        if score >= 55:  return "C"
        if score >= 40:  return "D"
        return "F"

    @staticmethod
    def _score_expectancy(exp: float, n: int) -> Tuple[float, str, str]:
        if n < 50:
            return 0.0, "UNAVAILABLE", f"Insufficient sample ({n} trades)"
        if exp >= 0.25:
            return 15.0, "STRONG", f"Expectancy {exp:+.4f}R ≥ 0.25R"
        if exp >= 0.15:
            return 11.0, "STRONG", f"Expectancy {exp:+.4f}R ≥ 0.15R"
        if exp >= 0.05:
            return 7.0, "ADEQUATE", f"Expectancy {exp:+.4f}R ≥ 0.05R"
        if exp >= 0.0:
            return 3.0, "WEAK", f"Expectancy {exp:+.4f}R marginally positive"
        return 0.0, "CRITICAL", f"Expectancy {exp:+.4f}R NEGATIVE"

    @staticmethod
    def _score_oos(oos_exp: float, n: int) -> Tuple[float, str, str]:
        if n < 20:
            return 0.0, "UNAVAILABLE", "Insufficient OOS sample"
        if oos_exp >= 0.15:
            return 15.0, "STRONG", f"OOS expectancy {oos_exp:+.4f}R ≥ 0.15R"
        if oos_exp >= 0.05:
            return 10.0, "ADEQUATE", f"OOS expectancy {oos_exp:+.4f}R ≥ 0.05R"
        if oos_exp >= 0.0:
            return 5.0, "WEAK", f"OOS expectancy {oos_exp:+.4f}R marginally positive"
        return 0.0, "CRITICAL", f"OOS expectancy {oos_exp:+.4f}R NEGATIVE"

    @staticmethod
    def _score_wf(wf_ratio: float, wf_med_exp: float) -> Tuple[float, str, str]:
        if wf_ratio >= 0.75 and wf_med_exp >= 0.10:
            return 10.0, "STRONG", f"WF: {wf_ratio:.0%} positive, median {wf_med_exp:+.4f}R"
        if wf_ratio >= 0.50 and wf_med_exp >= 0.0:
            return 6.0, "ADEQUATE", f"WF: {wf_ratio:.0%} positive, median {wf_med_exp:+.4f}R"
        if wf_ratio >= 0.50:
            return 3.0, "WEAK", f"WF: {wf_ratio:.0%} positive, median exp marginal"
        return 0.0, "CRITICAL", f"WF: <50% positive folds"

    @staticmethod
    def _score_pf(pf: float) -> Tuple[float, str, str]:
        if pf >= 1.5:
            return 10.0, "STRONG", f"PF {pf:.2f} ≥ 1.5"
        if pf >= 1.3:
            return 7.0, "ADEQUATE", f"PF {pf:.2f} ≥ 1.3"
        if pf >= 1.1:
            return 4.0, "WEAK", f"PF {pf:.2f} ≥ 1.1"
        return 0.0, "CRITICAL", f"PF {pf:.2f} < 1.1"

    @staticmethod
    def _score_dd(max_dd: float, exp: float) -> Tuple[float, str, str]:
        if max_dd <= 10:
            return 10.0, "STRONG", f"Max DD {max_dd:.1f}R ≤ 10R"
        if max_dd <= 20:
            return 6.0, "ADEQUATE", f"Max DD {max_dd:.1f}R ≤ 20R"
        if max_dd <= 35:
            return 3.0, "WEAK", f"Max DD {max_dd:.1f}R ≤ 35R"
        return 0.0, "CRITICAL", f"Max DD {max_dd:.1f}R > 35R — excessive"

    @staticmethod
    def _score_calibration(brier: float, ece: float) -> Tuple[float, str, str]:
        if brier <= 0.18 and ece <= 0.05:
            return 10.0, "STRONG", f"Brier={brier:.4f}, ECE={ece:.4f} — well calibrated"
        if brier <= 0.22 or ece <= 0.10:
            return 6.0, "ADEQUATE", f"Brier={brier:.4f}, ECE={ece:.4f}"
        if brier <= 0.25:
            return 3.0, "WEAK", f"Brier={brier:.4f} near no-skill baseline"
        return 0.0, "CRITICAL", f"Brier={brier:.4f} > 0.25 — worse than no-skill"

    @staticmethod
    def _score_regime(regime_pos_pct: float) -> Tuple[float, str, str]:
        if regime_pos_pct >= 0.75:
            return 8.0, "STRONG", f"{regime_pos_pct:.0%} regimes positive"
        if regime_pos_pct >= 0.50:
            return 5.0, "ADEQUATE", f"{regime_pos_pct:.0%} regimes positive"
        return 0.0, "WEAK", f"Only {regime_pos_pct:.0%} regimes positive — regime sensitive"

    @staticmethod
    def _score_asset(asset_dd_ratio: float) -> Tuple[float, str, str]:
        """Low ratio = one asset dominates DD; 1.0 = balanced; >1.0 = skewed."""
        if asset_dd_ratio <= 0.7:    # One asset dominates
            return 3.0, "WEAK", f"Asset DD ratio {asset_dd_ratio:.2f} — one asset dominates drawdown"
        return 8.0, "STRONG", f"Asset DD ratio {asset_dd_ratio:.2f} — balanced"

    @staticmethod
    def _score_session(session_pos_pct: float) -> Tuple[float, str, str]:
        if session_pos_pct >= 0.75:
            return 5.0, "STRONG", f"{session_pos_pct:.0%} sessions positive"
        if session_pos_pct >= 0.50:
            return 3.0, "ADEQUATE", f"{session_pos_pct:.0%} sessions positive"
        return 0.0, "WEAK", f"<50% sessions positive"

    @staticmethod
    def _score_stress(passes_slippage: bool, passes_execution: bool) -> Tuple[float, str, str]:
        if passes_slippage and passes_execution:
            return 5.0, "STRONG", "Passes slippage and execution stress tests"
        if passes_slippage or passes_execution:
            return 2.0, "ADEQUATE", "Passes one stress test"
        return 0.0, "WEAK", "Fails both slippage and execution stress tests"

    @staticmethod
    def _score_statistics(p_value: Optional[float], n: int) -> Tuple[float, str, str]:
        if p_value is None or n < 30:
            return 0.0, "UNAVAILABLE", "p-value not computed or sample too small"
        if p_value < 0.001 and n >= 200:
            return 4.0, "STRONG", f"p={p_value:.4f} < 0.001, n={n}"
        if p_value < 0.01 and n >= 100:
            return 3.0, "ADEQUATE", f"p={p_value:.4f} < 0.01, n={n}"
        if p_value < 0.05:
            return 1.0, "WEAK", f"p={p_value:.4f} < 0.05 (nominal)"
        return 0.0, "CRITICAL", f"p={p_value:.4f} ≥ 0.05 — not significant"


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_robustness_report(report: RobustnessScore) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "ROBUSTNESS_SCORE_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "ROBUSTNESS_SCORE_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write robustness JSON: %s", exc)

    grade_emoji = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "🔴", "F": "❌"}.get(report.grade, "?")
    lines = [
        "# Robustness Score Report",
        f"\n**Generated:** {report.generated_at}",
        f"**Strategy:** {report.strategy_label}",
        f"**Score:** {report.total_score:.0f}/100  —  Grade: {grade_emoji} {report.grade}",
        f"\n## Summary",
        report.summary,
        f"\n## Dimension Scores",
        "| Dimension | Max | Earned | % | Status | Detail |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for d in report.dimensions:
        status_icon = {"STRONG": "✅", "ADEQUATE": "🟡", "WEAK": "⚠️", "CRITICAL": "❌", "UNAVAILABLE": "➖"}.get(d.status, "?")
        lines.append(f"| {d.dimension} | {d.max_points} | {d.earned_points:.0f} | {d.pct:.0f}% | {status_icon} {d.status} | {d.detail} |")

    lines += [f"\n## Strong Areas"]
    for s in report.strong_areas:
        lines.append(f"- {s}")
    lines += ["\n## Weak Areas"]
    for w in report.weak_areas:
        lines.append(f"- {w}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write robustness MD: %s", exc)

    return json_path, md_path
