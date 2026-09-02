"""
Probability Calibration & Reliability Assessment Module.

Computes point-in-time and forward probability calibration metrics:
- Raw & Calibrated Brier Scores (Mean Squared Probability Error)
- Expected Calibration Error (ECE)
- Maximum Calibration Error (MCE)
- Reliability Buckets with Sample Counts & Wilson Confidence Intervals

Guarantees sample sufficiency checks before claiming well-calibrated status.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CalibrationBucket:
    """Statistics for an individual predicted probability range."""
    bucket_range: str
    label: str
    sample_count: int
    mean_predicted_prob_pct: float
    observed_win_rate_pct: float
    calibration_gap_pct: float
    ci_lower_pct: float
    ci_upper_pct: float
    sample_sufficiency: str  # "SUFFICIENT" (N>=25), "MODERATE" (N>=10), "INSUFFICIENT" (N<10)


@dataclass
class CalibrationReport:
    """Consolidated probability calibration evaluation."""
    symbol: str
    sample_size: int
    raw_brier_score: float
    calibrated_brier_score: float
    raw_ece_pct: float
    calibrated_ece_pct: float
    max_calibration_error_pct: float
    buckets: List[CalibrationBucket]
    calibration_status: str  # "WELL_CALIBRATED", "MODERATELY_CALIBRATED", "POORLY_CALIBRATED", "INSUFFICIENT_DATA"
    assessment_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_wilson_ci(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval for binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    z = 1.95996
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denom
    spread = (z / denom) * math.sqrt((p * (1 - p) / total) + (z**2) / (4 * (total**2)))
    lower = max(0.0, (center - spread) * 100.0)
    upper = min(100.0, (center + spread) * 100.0)
    return round(lower, 2), round(upper, 2)


def evaluate_probability_calibration(
    predicted_probs: List[float],
    binary_outcomes: List[int],  # 1 for WIN, 0 for LOSS
    symbol: str = "BTC/USD",
    raw_probs: Optional[List[float]] = None,
) -> CalibrationReport:
    """
    Perform probability calibration analysis on predicted probabilities vs realized outcomes.
    
    Args:
        predicted_probs: Model predicted probabilities in range [0.0, 1.0]
        binary_outcomes: Binary actual outcomes (1 for Win, 0 for Loss)
        symbol: Asset symbol
        raw_probs: Optional raw uncalibrated probabilities for comparison
    """
    n = len(predicted_probs)
    if n == 0 or len(binary_outcomes) != n:
        return CalibrationReport(
            symbol=symbol,
            sample_size=0,
            raw_brier_score=0.25,
            calibrated_brier_score=0.25,
            raw_ece_pct=0.0,
            calibrated_ece_pct=0.0,
            max_calibration_error_pct=0.0,
            buckets=[],
            calibration_status="INSUFFICIENT_DATA",
            assessment_notes="No observations available for probability calibration analysis",
        )

    preds = np.array(predicted_probs, dtype=float)
    actuals = np.array(binary_outcomes, dtype=float)

    # 1. Brier Score: Mean Squared Error between probability and binary outcome
    cal_brier = float(np.mean((preds - actuals) ** 2))

    if raw_probs and len(raw_probs) == n:
        raw_arr = np.array(raw_probs, dtype=float)
        raw_brier = float(np.mean((raw_arr - actuals) ** 2))
    else:
        raw_brier = cal_brier

    # 2. Binning into Reliability Buckets
    bucket_definitions = [
        (0.00, 0.45, "<45%"),
        (0.45, 0.50, "45-50%"),
        (0.50, 0.55, "50-55%"),
        (0.55, 0.60, "55-60%"),
        (0.60, 0.65, "60-65%"),
        (0.65, 0.70, "65-70%"),
        (0.70, 1.00, ">=70%"),
    ]

    buckets_out: List[CalibrationBucket] = []
    weighted_ece = 0.0
    raw_weighted_ece = 0.0
    max_gap = 0.0
    sufficient_buckets_count = 0

    for low, high, lbl in bucket_definitions:
        # Filter indices belonging to bucket
        if high == 1.00:
            mask = (preds >= low) & (preds <= high)
        else:
            mask = (preds >= low) & (preds < high)

        count = int(np.sum(mask))
        if count > 0:
            bucket_preds = preds[mask]
            bucket_actuals = actuals[mask]
            mean_pred = float(np.mean(bucket_preds)) * 100.0
            wins_count = int(np.sum(bucket_actuals == 1))
            observed_wr = (wins_count / count) * 100.0
            gap = abs(mean_pred - observed_wr)

            ci_low, ci_high = _compute_wilson_ci(wins_count, count)
            weighted_ece += (count / n) * gap
            max_gap = max(max_gap, gap)

            if count >= 25:
                sufficiency = "SUFFICIENT"
                sufficient_buckets_count += 1
            elif count >= 10:
                sufficiency = "MODERATE"
            else:
                sufficiency = "INSUFFICIENT"

            buckets_out.append(
                CalibrationBucket(
                    bucket_range=f"{low:.2f} - {high:.2f}",
                    label=lbl,
                    sample_count=count,
                    mean_predicted_prob_pct=round(mean_pred, 2),
                    observed_win_rate_pct=round(observed_wr, 2),
                    calibration_gap_pct=round(gap, 2),
                    ci_lower_pct=ci_low,
                    ci_upper_pct=ci_high,
                    sample_sufficiency=sufficiency,
                )
            )

    cal_ece = round(weighted_ece, 2)
    raw_ece = cal_ece  # Default to cal_ece if raw not binned separately

    # 3. Assess Calibration Quality
    if n < 50 or sufficient_buckets_count < 2:
        status = "INSUFFICIENT_DATA"
        notes = f"Sample size (N={n}) is too preliminary for definitive calibration confidence."
    elif cal_ece <= 7.0 and max_gap <= 15.0 and cal_brier < 0.25:
        status = "WELL_CALIBRATED"
        notes = f"Model probabilities closely track empirical win rates (ECE: {cal_ece}%, Brier: {cal_brier:.4f})."
    elif cal_ece <= 12.0:
        status = "MODERATELY_CALIBRATED"
        notes = f"Model shows directional calibration with modest bucket deviations (ECE: {cal_ece}%)."
    else:
        status = "POORLY_CALIBRATED"
        notes = f"Substantial gap between predicted probability and observed win rate (ECE: {cal_ece}%)."

    return CalibrationReport(
        symbol=symbol,
        sample_size=n,
        raw_brier_score=round(raw_brier, 4),
        calibrated_brier_score=round(cal_brier, 4),
        raw_ece_pct=round(raw_ece, 2),
        calibrated_ece_pct=round(cal_ece, 2),
        max_calibration_error_pct=round(max_gap, 2),
        buckets=buckets_out,
        calibration_status=status,
        assessment_notes=notes,
    )
