"""
Phase 3 AI Probability Calibration Analysis.

Groups historical signals by AI probability bucket and computes:
- Predicted probability (bucket midpoint)
- Actual win rate (empirical)
- Calibration error per bucket
- Brier score
- Expected Calibration Error (ECE)
- Per-bucket classification: OVERCONFIDENT / UNDERCONFIDENT / WELL_CALIBRATED

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

import numpy as np

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class BucketCalibration(str):
    OVERCONFIDENT    = "OVERCONFIDENT"    # predicted >> actual
    UNDERCONFIDENT   = "UNDERCONFIDENT"   # predicted << actual
    WELL_CALIBRATED  = "WELL_CALIBRATED"  # |predicted - actual| < 5pp
    INSUFFICIENT_DATA= "INSUFFICIENT_DATA"


@dataclass
class ProbabilityBucket:
    """Performance for a single AI probability bucket."""
    bucket_label: str           # e.g. "40–50%"
    bucket_lower: float         # 0.0–1.0
    bucket_upper: float
    bucket_midpoint: float      # Predicted probability representative
    sample_size: int
    win_count: int
    actual_win_rate: float      # Empirical win rate 0.0–1.0
    calibration_error: float    # abs(predicted - actual) as fraction
    calibration_pct: float      # calibration_error * 100
    wilson_ci_lower: float
    wilson_ci_upper: float
    classification: str = BucketCalibration.INSUFFICIENT_DATA


@dataclass
class AICalibrationReport:
    """Full AI probability calibration analysis."""
    generated_at: str
    total_signals: int
    total_resolved: int   # WIN + LOSS + EXPIRED
    brier_score: float    # Overall: lower = better (0.25 = no-skill)
    ece: float            # Expected Calibration Error (weighted avg abs error)
    overall_classification: str  # OVERCONFIDENT / UNDERCONFIDENT / WELL_CALIBRATED / MIXED
    buckets: List[ProbabilityBucket] = field(default_factory=list)
    asset_breakdown: Dict[str, float] = field(default_factory=dict)  # asset → brier score
    regime_breakdown: Dict[str, float] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)
    disclaimer: str = (
        "AI calibration is computed from historical advisory signals only. "
        "Sample sizes per bucket may be small.  Results are not a guarantee of future performance."
    )


# ---------------------------------------------------------------------------
# Calibration Engine
# ---------------------------------------------------------------------------

class AICalibrationEngine:
    """Computes calibration metrics for AI probability outputs."""

    BUCKET_STEP = 0.10   # 10 buckets of 10% width
    MIN_BUCKET_SIZE = 10 # Minimum for calibration verdict
    WELL_CALIBRATED_TOLERANCE = 0.05  # ±5pp

    @classmethod
    def analyze(cls, records: List[Any]) -> AICalibrationReport:
        """
        Compute full AI probability calibration.

        ``records`` must have:
          - ai.ai_probability: float (0.0–1.0)
          - outcome: "WIN" / "LOSS" / "EXPIRED"
        """
        resolved = [
            r for r in records
            if getattr(r, "outcome", "OPEN") in ("WIN", "LOSS", "EXPIRED")
            and getattr(r, "decision", "WAIT") in ("BUY", "SELL")
        ]

        buckets = cls._build_buckets(resolved)
        brier   = cls._brier_score(resolved)
        ece     = cls._ece(buckets)
        overall = cls._classify_overall(buckets)

        asset_brier   = cls._brier_by_group(resolved, "asset")
        regime_brier  = cls._brier_by_group(resolved, "regime")

        findings = cls._findings(buckets, brier, ece, overall)

        return AICalibrationReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_signals=len(records),
            total_resolved=len(resolved),
            brier_score=brier,
            ece=ece,
            overall_classification=overall,
            buckets=buckets,
            asset_breakdown=asset_brier,
            regime_breakdown=regime_brier,
            findings=findings,
        )

    # ------------------------------------------------------------------ helpers

    @classmethod
    def _build_buckets(cls, resolved: List[Any]) -> List[ProbabilityBucket]:
        buckets: List[ProbabilityBucket] = []
        for i in range(10):
            lower = i * cls.BUCKET_STEP
            upper = lower + cls.BUCKET_STEP
            mid   = (lower + upper) / 2.0
            label = f"{int(lower*100)}–{int(upper*100)}%"

            subset = [r for r in resolved
                      if lower <= (getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0) < upper]
            # Include 100% in last bucket
            if i == 9:
                subset = [r for r in resolved
                          if (getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0) >= lower]

            n  = len(subset)
            wins = sum(1 for r in subset if getattr(r, "outcome", "") == "WIN")
            actual_wr = wins / n if n > 0 else 0.0
            cal_err   = abs(mid - actual_wr)
            cal_pct   = round(cal_err * 100, 1)

            # Wilson CI
            if n >= 2:
                from src.research.statistical_validation import compute_wilson_score_interval
                ci = compute_wilson_score_interval(wins, n)
                wilson_lo = ci.ci_lower / 100.0
                wilson_hi = ci.ci_upper / 100.0
            else:
                wilson_lo = 0.0
                wilson_hi = 1.0

            if n < cls.MIN_BUCKET_SIZE:
                classification = BucketCalibration.INSUFFICIENT_DATA
            elif cal_err <= cls.WELL_CALIBRATED_TOLERANCE:
                classification = BucketCalibration.WELL_CALIBRATED
            elif actual_wr < mid - cls.WELL_CALIBRATED_TOLERANCE:
                classification = BucketCalibration.OVERCONFIDENT
            else:
                classification = BucketCalibration.UNDERCONFIDENT

            buckets.append(ProbabilityBucket(
                bucket_label=label,
                bucket_lower=lower,
                bucket_upper=upper,
                bucket_midpoint=mid,
                sample_size=n,
                win_count=wins,
                actual_win_rate=round(actual_wr, 4),
                calibration_error=round(cal_err, 4),
                calibration_pct=cal_pct,
                wilson_ci_lower=round(wilson_lo, 4),
                wilson_ci_upper=round(wilson_hi, 4),
                classification=classification,
            ))
        return buckets

    @staticmethod
    def _brier_score(resolved: List[Any]) -> float:
        """Brier score = mean((predicted - actual)^2). Lower is better (0.25 = no-skill)."""
        if not resolved:
            return 0.25
        squared_errors = []
        for r in resolved:
            pred = float(getattr(getattr(r, "ai", None), "ai_probability", 0.5) or 0.5)
            actual = 1.0 if getattr(r, "outcome", "") == "WIN" else 0.0
            squared_errors.append((pred - actual) ** 2)
        return round(float(np.mean(squared_errors)), 4)

    @staticmethod
    def _ece(buckets: List[ProbabilityBucket]) -> float:
        """Expected Calibration Error — weighted average of per-bucket calibration errors."""
        total = sum(b.sample_size for b in buckets)
        if total == 0:
            return 0.0
        ece = sum(
            b.sample_size / total * b.calibration_error
            for b in buckets if b.sample_size > 0
        )
        return round(ece, 4)

    @staticmethod
    def _classify_overall(buckets: List[ProbabilityBucket]) -> str:
        calibrated = [b for b in buckets
                      if b.sample_size >= 10 and b.classification != BucketCalibration.INSUFFICIENT_DATA]
        if not calibrated:
            return BucketCalibration.INSUFFICIENT_DATA
        n_oc  = sum(1 for b in calibrated if b.classification == BucketCalibration.OVERCONFIDENT)
        n_uc  = sum(1 for b in calibrated if b.classification == BucketCalibration.UNDERCONFIDENT)
        n_wc  = sum(1 for b in calibrated if b.classification == BucketCalibration.WELL_CALIBRATED)
        if n_wc >= len(calibrated) * 0.6:
            return BucketCalibration.WELL_CALIBRATED
        if n_oc > n_uc and n_oc >= 2:
            return BucketCalibration.OVERCONFIDENT
        if n_uc > n_oc and n_uc >= 2:
            return BucketCalibration.UNDERCONFIDENT
        return "MIXED"

    @classmethod
    def _brier_by_group(cls, resolved: List[Any], attr: str) -> Dict[str, float]:
        from collections import defaultdict
        groups: Dict[str, List[Any]] = defaultdict(list)
        for r in resolved:
            key = str(getattr(r, attr, "UNKNOWN") or "UNKNOWN")
            groups[key].append(r)
        return {k: cls._brier_score(v) for k, v in sorted(groups.items())}

    @staticmethod
    def _findings(
        buckets: List[ProbabilityBucket],
        brier: float,
        ece: float,
        overall: str,
    ) -> List[str]:
        findings = [
            f"Overall calibration: {overall}",
            f"Brier score: {brier:.4f} (no-skill baseline = 0.25; lower = better)",
            f"Expected Calibration Error (ECE): {ece:.4f} ({ece*100:.1f}pp average error)",
        ]
        worst_bucket = max(
            [b for b in buckets if b.sample_size >= 10],
            key=lambda b: b.calibration_error,
            default=None,
        )
        if worst_bucket:
            findings.append(
                f"Worst-calibrated bucket: {worst_bucket.bucket_label} "
                f"(predicted {worst_bucket.bucket_midpoint:.0%}, "
                f"actual {worst_bucket.actual_win_rate:.1%}, "
                f"error {worst_bucket.calibration_pct:.1f}pp, n={worst_bucket.sample_size})"
            )
        # Specific directional insight
        high_buckets = [b for b in buckets if b.bucket_lower >= 0.7 and b.sample_size >= 10]
        for b in high_buckets:
            if b.classification == BucketCalibration.OVERCONFIDENT:
                findings.append(
                    f"High-probability bucket {b.bucket_label}: AI predicted {b.bucket_midpoint:.0%} "
                    f"but actual WR={b.actual_win_rate:.1%} — AI IS OVERCONFIDENT at high probabilities"
                )
        return findings


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_calibration_report(report: AICalibrationReport) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "AI_CALIBRATION_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "AI_CALIBRATION_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write calibration JSON: %s", exc)

    lines = [
        "# AI Probability Calibration Report",
        f"\n**Generated:** {report.generated_at}",
        f"**Overall Classification:** {report.overall_classification}",
        f"**Brier Score:** {report.brier_score:.4f}  |  **ECE:** {report.ece:.4f}  ({report.ece*100:.1f}pp)",
        f"**Resolved signals:** {report.total_resolved} / {report.total_signals}",
        "\n## Calibration Table",
        "| Bucket | N | Predicted | Actual WR | Error (pp) | Classification |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for b in report.buckets:
        lines.append(
            f"| {b.bucket_label} | {b.sample_size} | {b.bucket_midpoint:.0%} "
            f"| {b.actual_win_rate:.1%} | {b.calibration_pct:.1f} | {b.classification} |"
        )

    lines += ["\n## Findings"]
    for f_str in report.findings:
        lines.append(f"- {f_str}")

    lines += ["\n## Asset Brier Scores"]
    for asset, bs in report.asset_breakdown.items():
        lines.append(f"- {asset}: {bs:.4f}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write calibration MD: %s", exc)

    return json_path, md_path
