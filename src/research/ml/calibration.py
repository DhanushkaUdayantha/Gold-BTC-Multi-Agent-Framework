"""
Probability Calibration and Reliability Assessment.
"""
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

class ProbabilityCalibrator:
    """Evaluates probability alignment against actual empirical win rates."""

    DEFAULT_BUCKETS = [
        (0.00, 0.45, "<45%"),
        (0.45, 0.50, "45-50%"),
        (0.50, 0.55, "50-55%"),
        (0.55, 0.60, "55-60%"),
        (0.60, 0.65, "60-65%"),
        (0.65, 0.70, "65-70%"),
        (0.70, 1.00, "70%+")
    ]

    @classmethod
    def evaluate_calibration(
        cls,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        realized_r: Optional[np.ndarray] = None,
        buckets: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """Evaluates empirical reliability across probability buckets."""
        b_list = buckets or cls.DEFAULT_BUCKETS
        bucket_results = []
        brier = float(brier_score_loss(y_true, y_prob)) if len(y_true) > 0 else 0.0

        for low, high, label in b_list:
            mask = (y_prob >= low) & (y_prob < high) if high < 1.0 else (y_prob >= low) & (y_prob <= high)
            n_bucket = int(np.sum(mask))
            if n_bucket > 0:
                y_sub = y_true[mask]
                actual_wr = float(np.mean(y_sub) * 100.0)
                mean_pred = float(np.mean(y_prob[mask]) * 100.0)
                sub_r = realized_r[mask] if realized_r is not None else np.where(y_sub == 1, 1.5, -1.0)
                ev = float(np.mean(sub_r))
            else:
                actual_wr = 0.0
                mean_pred = 0.0
                ev = 0.0

            bucket_results.append({
                "bucket_range": f"{low:.2f} - {high:.2f}",
                "label": label,
                "n": n_bucket,
                "mean_predicted_prob_pct": round(mean_pred, 2),
                "actual_win_rate_pct": round(actual_wr, 2),
                "expectancy_r": round(ev, 4),
                "calibration_gap_pct": round(abs(mean_pred - actual_wr), 2) if n_bucket > 0 else 0.0
            })

        # Calculate Expected Calibration Error (ECE)
        total_samples = len(y_true)
        if total_samples > 0:
            ece = sum((b["n"] / total_samples) * (b["calibration_gap_pct"] / 100.0) for b in bucket_results)
        else:
            ece = 0.0

        return {
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(float(ece), 4),
            "buckets": bucket_results
        }
