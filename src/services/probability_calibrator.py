"""
Probability Calibrator — estimates empirical win probability from historical signals.

KEY DESIGN PRINCIPLES:
1. Confluence score (0–100) is NEVER presented as a probability.
   It remains a confluence score.
2. Calibrated probability is computed ONLY from historical outcomes via
   isotonic regression (preferred) or logistic regression (small samples).
3. Chronological train/validation split (NEVER random shuffle of time-series).
4. Walk-forward validation when sample ≥ 200.
5. Calibration status enforces minimum sample thresholds:
   INSUFFICIENT_DATA (<50), EXPLORATORY (50–199), VALID (200+), PREFERRED (500+)
6. If calibration quality is poor (Brier score ≥ 0.24), status = UNRELIABLE.
7. All outputs include sample size and disclaimers.

DISCLAIMER: Calibrated probabilities are ESTIMATES from limited historical data.
They are NOT guarantees. Past performance does not guarantee future results.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from src.models.signal_record import SignalRecord, CalibrationResult

logger = logging.getLogger(__name__)

# Calibration thresholds
_INSUFFICIENT_THRESHOLD = 50
_EXPLORATORY_THRESHOLD = 200
_VALID_THRESHOLD = 500

# Train/validation split ratio (chronological)
_TRAIN_RATIO = 0.70

# Brier score threshold above which calibration is flagged UNRELIABLE
# (0.25 = no-skill baseline for binary outcomes; we use 0.24 as threshold)
_BRIER_UNRELIABLE_THRESHOLD = 0.24

# Walk-forward: minimum folds
_WF_MIN_FOLDS = 3


def _get_outcome_str(r: Any) -> Optional[str]:
    if isinstance(r, dict):
        out = r.get("outcome")
        if isinstance(out, dict):
            return out.get("outcome")
        return str(out) if out else None
    if hasattr(r, "outcome"):
        out = getattr(r, "outcome", None)
        if hasattr(out, "outcome"):
            return getattr(out, "outcome", None)
        return str(out) if out else None
    return None


def _get_confluence_score(r: Any) -> float:
    if isinstance(r, dict):
        return float(r.get("confluence_score", 0))
    return float(getattr(r, "confluence_score", 0))


def _get_signal_time(r: Any) -> str:
    if isinstance(r, dict):
        return str(r.get("signal_timestamp") or r.get("timestamp") or "")
    return str(getattr(r, "signal_timestamp", "") or getattr(r, "timestamp", "") or "")


class ProbabilityCalibrator:
    """
    Empirical probability calibrator using isotonic regression
    on historical signal outcomes, grouped by confluence score.
    """

    def calibrate(
        self,
        completed_signals: List[Any],
        current_score: Optional[int] = None,
        train_ratio: float = _TRAIN_RATIO,
    ) -> CalibrationResult:
        """
        Compute calibration from completed WIN/LOSS signals.
        current_score: if provided, calibrated_probability is returned for it.
        """
        # Filter to WIN/LOSS only (exclude BREAKEVEN/EXPIRED/INVALID for R-based calibration)
        wl_signals = [
            r for r in completed_signals
            if _get_outcome_str(r) in ("WIN", "LOSS")
        ]
        n = len(wl_signals)

        # ---- Minimum data check ----
        if n < _INSUFFICIENT_THRESHOLD:
            return CalibrationResult(
                calibration_status="INSUFFICIENT_DATA",
                sample_size=n,
                reliability_note=(
                    f"Need ≥{_INSUFFICIENT_THRESHOLD} completed WIN/LOSS signals, have {n}. "
                    "Do NOT interpret confluence score as a probability."
                ),
            )

        # Sort chronologically (NEVER shuffle time-series data)
        try:
            sorted_signals = sorted(wl_signals, key=_get_signal_time)
        except Exception:
            sorted_signals = wl_signals

        # ---- Train/Validation split ----
        split_idx = int(len(sorted_signals) * train_ratio)
        split_idx = max(1, min(split_idx, len(sorted_signals) - 1))
        train = sorted_signals[:split_idx]
        val = sorted_signals[split_idx:]
        n_train = len(train)
        n_val = len(val)

        # ---- Determine calibration method ----
        method = "logistic" if n_train < 100 else "isotonic"

        # ---- Fit calibration model ----
        try:
            if method == "isotonic":
                calibrator_fn = self._fit_isotonic(train)
            else:
                calibrator_fn = self._fit_logistic(train)
        except Exception as exc:
            logger.error(f"ProbabilityCalibrator: fit error: {exc}")
            return CalibrationResult(
                calibration_status="UNRELIABLE",
                sample_size=n,
                training_size=n_train,
                validation_size=n_val,
                method_used=method,
                reliability_note=f"Calibration fit failed: {exc}",
            )

        # ---- In-sample accuracy ----
        in_sample_acc = self._compute_accuracy(train, calibrator_fn)

        # ---- Out-of-sample evaluation ----
        oos_acc = self._compute_accuracy(val, calibrator_fn)
        brier = self._compute_brier_score(val, calibrator_fn)
        cal_error = self._compute_calibration_error(val, calibrator_fn)

        # ---- Walk-forward validation ----
        wf_folds = 0
        if n >= 200:
            wf_folds = self._walk_forward_folds(sorted_signals)

        # ---- Determine status ----
        if brier is not None and brier >= _BRIER_UNRELIABLE_THRESHOLD:
            status = "UNRELIABLE"
            reliability_note = (
                f"Brier score {brier:.4f} ≥ {_BRIER_UNRELIABLE_THRESHOLD} threshold. "
                "Calibration is not reliable. Do NOT use as a probability."
            )
        elif n >= _VALID_THRESHOLD:
            status = "PREFERRED"
            reliability_note = f"Preferred calibration — {n} completed signals."
        elif n >= _EXPLORATORY_THRESHOLD:
            status = "VALID"
            reliability_note = f"Valid for exploratory use — {n} signals."
        else:
            status = "EXPLORATORY"
            reliability_note = (
                f"Exploratory — {n} signals (≥{_EXPLORATORY_THRESHOLD} needed for VALID). "
                "Treat with caution."
            )

        # ---- Calibrated probability for current score ----
        calib_prob = None
        if current_score is not None and status != "UNRELIABLE":
            try:
                raw = calibrator_fn(current_score)
                calib_prob = round(max(0.0, min(1.0, raw)), 4)
            except Exception:
                calib_prob = None

        return CalibrationResult(
            calibration_status=status,
            sample_size=n,
            training_size=n_train,
            validation_size=n_val,
            calibrated_probability=round(calib_prob * 100, 1) if calib_prob is not None else None,
            calibrated_for_score=current_score,
            brier_score=round(brier, 6) if brier is not None else None,
            oos_accuracy=round(oos_acc * 100, 2) if oos_acc is not None else None,
            calibration_error=round(cal_error, 4) if cal_error is not None else None,
            in_sample_accuracy=round(in_sample_acc * 100, 2) if in_sample_acc is not None else None,
            method_used=method,
            split_type="chronological_70_30",
            walk_forward_folds=wf_folds,
            reliability_note=reliability_note,
        )

    # ------------------------------------------------------------------
    # Calibration models
    # ------------------------------------------------------------------

    def _fit_isotonic(self, train: List[Any]):
        """
        Fit isotonic regression: score → P(WIN).
        Groups scores into bins and enforces monotonicity.
        Returns a callable f(score: int) → float.
        """
        try:
            from sklearn.isotonic import IsotonicRegression
            import numpy as np
        except ImportError:
            raise ImportError(
                "scikit-learn is required for probability calibration. "
                "Run: pip install scikit-learn>=1.4.0"
            )

        X = np.array([_get_confluence_score(r) for r in train], dtype=float)
        y = np.array(
            [1.0 if _get_outcome_str(r) == "WIN" else 0.0 for r in train],
            dtype=float,
        )

        ir = IsotonicRegression(out_of_bounds="clip", increasing=True)
        ir.fit(X, y)

        def predict(score: int) -> float:
            return float(ir.predict([[score]])[0])

        return predict

    def _fit_logistic(self, train: List[Any]):
        """
        Fit logistic regression for small samples.
        Returns a callable f(score: int) → float.
        """
        try:
            from sklearn.linear_model import LogisticRegression
            import numpy as np
        except ImportError:
            raise ImportError("scikit-learn is required for probability calibration.")

        X = np.array([[_get_confluence_score(r)] for r in train], dtype=float)
        y = np.array(
            [1.0 if _get_outcome_str(r) == "WIN" else 0.0 for r in train],
            dtype=float,
        )

        # Check if we have both classes
        if len(set(y)) < 2:
            # All WIN or all LOSS — degenerate case
            mean_y = float(y.mean())

            def predict_constant(score: int) -> float:
                return mean_y
            return predict_constant

        lr = LogisticRegression(max_iter=1000)
        lr.fit(X, y)

        def predict(score: int) -> float:
            prob = lr.predict_proba([[score]])[0]
            return float(prob[1])  # P(WIN)

        return predict

    # ------------------------------------------------------------------
    # Evaluation metrics
    # ------------------------------------------------------------------

    def _compute_accuracy(self, signals: List[Any], predict_fn) -> Optional[float]:
        if not signals:
            return None
        correct = 0
        for r in signals:
            try:
                score = _get_confluence_score(r)
                prob = predict_fn(score)
                predicted_win = prob >= 0.5
                actual_win = _get_outcome_str(r) == "WIN"
                if predicted_win == actual_win:
                    correct += 1
            except Exception:
                pass
        return correct / len(signals) if signals else None

    def _compute_brier_score(self, signals: List[Any], predict_fn) -> Optional[float]:
        """
        Brier score = mean((probability - actual_outcome)^2).
        Lower is better. 0.25 = no-skill baseline for 50/50 binary outcomes.
        """
        if not signals:
            return None
        squared_errors = []
        for r in signals:
            try:
                score = _get_confluence_score(r)
                prob = predict_fn(score)
                actual = 1.0 if (_get_outcome_str(r) == "WIN") else 0.0
                squared_errors.append((prob - actual) ** 2)
            except Exception:
                pass
        if not squared_errors:
            return None
        return sum(squared_errors) / len(squared_errors)

    def _compute_calibration_error(
        self, signals: List[Any], predict_fn, n_bins: int = 5
    ) -> Optional[float]:
        """
        Mean Absolute Calibration Error (MACE):
        Split predictions into bins, compare mean predicted prob vs actual fraction.
        """
        if len(signals) < n_bins * 2:
            return None

        pred_actual = []
        for r in signals:
            try:
                score = _get_confluence_score(r)
                prob = predict_fn(score)
                actual = 1.0 if (_get_outcome_str(r) == "WIN") else 0.0
                pred_actual.append((prob, actual))
            except Exception:
                pass

        if len(pred_actual) < n_bins:
            return None

        # Sort by predicted probability, split into bins
        pred_actual.sort(key=lambda x: x[0])
        bin_size = len(pred_actual) // n_bins
        errors = []
        for i in range(n_bins):
            bin_slice = pred_actual[i * bin_size: (i + 1) * bin_size]
            if not bin_slice:
                continue
            mean_pred = sum(p for p, _ in bin_slice) / len(bin_slice)
            mean_actual = sum(a for _, a in bin_slice) / len(bin_slice)
            errors.append(abs(mean_pred - mean_actual))

        return sum(errors) / len(errors) if errors else None

    # ------------------------------------------------------------------
    # Walk-forward validation
    # ------------------------------------------------------------------

    def _walk_forward_folds(self, sorted_signals: List[SignalRecord]) -> int:
        """
        Walk-forward validation: train on initial window, test on next chunk.
        Returns the number of valid folds completed.
        """
        n = len(sorted_signals)
        fold_size = n // (_WF_MIN_FOLDS + 1)
        if fold_size < 10:
            return 0

        folds_completed = 0
        for fold in range(_WF_MIN_FOLDS):
            train_end = (fold + 1) * fold_size
            val_end = min(train_end + fold_size, n)
            train = sorted_signals[:train_end]
            val = sorted_signals[train_end:val_end]

            if len(train) < 20 or len(val) < 5:
                break

            try:
                if len(train) >= 100:
                    fn = self._fit_isotonic(train)
                else:
                    fn = self._fit_logistic(train)
                brier = self._compute_brier_score(val, fn)
                if brier is not None:
                    folds_completed += 1
                    logger.debug(
                        f"WF fold {fold+1}: train={len(train)}, val={len(val)}, brier={brier:.4f}"
                    )
            except Exception as exc:
                logger.debug(f"WF fold {fold+1} failed: {exc}")
                break

        return folds_completed


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_calibrator_instance: Optional[ProbabilityCalibrator] = None


def get_probability_calibrator() -> ProbabilityCalibrator:
    global _calibrator_instance
    if _calibrator_instance is None:
        _calibrator_instance = ProbabilityCalibrator()
    return _calibrator_instance
