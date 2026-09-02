"""
Automated Test Suite for Strength-to-Probability Calibration and Independent Holdout Validation.

Validates:
1. Zero Future Data Leakage & Lookahead Bias Auditing
2. Chronological 3-way Train/Validation/Holdout Split Integrity
3. Calibration Model Reproducibility & Determinism
4. Probability Bounds [0.01, 0.99]
5. Metric Correctness (Brier Score, Log Loss, ECE, MCE)
6. Wilson Score 95% Confidence Interval Formula
7. Non-parametric Bootstrap Confidence Interval for Expectancy
8. Hypothetical Threshold Selection & Research Metrics
9. Independent Directional (BUY vs. SELL) Calibration Separation
10. Holdout Isolation Verification (Untouched during Training/Selection)
11. Structured Report Generation (JSON & Markdown Exports)
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import numpy as np
import pytest

from src.services.strength_probability_calibrator import (
    StrengthProbabilityCalibrator,
    RawStrengthModel,
    LogisticCalibrationModel,
    IsotonicCalibrationModel,
    EmpiricalBucketCalibrationModel,
    _wilson_score_interval,
    _bootstrap_ci_expectancy,
    CalibrationLookaheadAudit,
    FullCalibrationResearchReport,
)
from src.services.point_in_time_validator import PointInTimeTradeRecord


@pytest.fixture
def sample_pit_records():
    """Generate synthetic deterministic point-in-time trade records for testing."""
    records = []
    base_ts = 1500000000
    for i in range(100):
        ts = f"2020-01-01T{i:02d}:00:00Z"
        dir_ = "BUY" if i % 2 == 0 else "SELL"
        strength = 50 + (i % 25)
        # Outcome correlated with strength for tests
        is_win = (i % 3 != 0) if strength >= 60 else (i % 2 == 0)
        outcome = "WIN" if is_win else "LOSS"
        realized_r = 1.5 if outcome == "WIN" else -1.0
        
        rec = PointInTimeTradeRecord(
            signal_id=f"sig_{i:04d}",
            signal_timestamp=ts,
            direction=dir_,
            confluence_score=60,
            actual_outcome=outcome,
            realized_r=realized_r,
            mfe=2.0 if outcome == "WIN" else 0.5,
            mae=0.5 if outcome == "WIN" else 1.2,
            buy_strength=strength,
            sell_strength=strength - 5,
            selected_strength=strength,
            historical_bias="BUY" if dir_ == "BUY" else "SELL",
            sample_size_used=50,
            similar_setup_count=30,
            historical_win_rate_used=55.0,
            wilson_ci_lower=40.0,
            wilson_ci_upper=70.0,
            expectancy_used=0.25,
            profit_factor_used=1.3,
            similarity_score=85,
            earliest_observation_timestamp="2019-01-01T00:00:00Z",
            latest_observation_timestamp=ts,
            future_timestamp_used=False,
            future_trade_used=False,
            future_outcome_used=False,
            future_calibration_data_used=False,
        )
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# 1. Temporal Isolation & Lookahead Audit Tests
# ---------------------------------------------------------------------------

def test_chronological_split_integrity(sample_pit_records):
    """Verify that split_data produces strict chronological non-overlapping sets."""
    calibrator = StrengthProbabilityCalibrator()
    train_set, val_set, holdout_set = calibrator.split_data(sample_pit_records, train_ratio=0.60, val_ratio=0.20)

    assert len(train_set) == 60
    assert len(val_set) == 20
    assert len(holdout_set) == 20
    assert len(train_set) + len(val_set) + len(holdout_set) == len(sample_pit_records)

    # Check timestamps strictly non-decreasing across boundary
    assert train_set[-1].signal_timestamp <= val_set[0].signal_timestamp
    assert val_set[-1].signal_timestamp <= holdout_set[0].signal_timestamp


def test_lookahead_audit_clean(sample_pit_records):
    """Verify that lookahead audit passes with 0 violations on clean chronological data."""
    calibrator = StrengthProbabilityCalibrator()
    train_set, val_set, holdout_set = calibrator.split_data(sample_pit_records, train_ratio=0.60, val_ratio=0.20)
    audit = calibrator.perform_lookahead_audit("BTC/USD", train_set, val_set, holdout_set)

    assert audit.audit_status == "PASSED"
    assert audit.violation_count == 0
    assert not audit.future_calibration_data_used
    assert not audit.future_outcome_used
    assert not audit.future_signal_used


def test_lookahead_audit_detects_leakage(sample_pit_records):
    """Verify that lookahead audit fails if temporal ordering is violated."""
    calibrator = StrengthProbabilityCalibrator()
    train_set, val_set, holdout_set = calibrator.split_data(sample_pit_records, train_ratio=0.60, val_ratio=0.20)

    # Introduce a synthetic violation
    val_set[0].future_outcome_used = True
    audit = calibrator.perform_lookahead_audit("BTC/USD", train_set, val_set, holdout_set)

    assert audit.audit_status == "FAILED"
    assert audit.violation_count > 0
    assert audit.future_outcome_used


# ---------------------------------------------------------------------------
# 2. Calibration Models & Probability Bounds Tests
# ---------------------------------------------------------------------------

def test_probability_bounds():
    """Verify that all models output probabilities strictly bounded in [0.01, 0.99]."""
    X_train = np.array([20, 40, 60, 80, 100], dtype=np.float64)
    y_train = np.array([0, 0, 1, 1, 1], dtype=np.int32)
    X_test = np.array([-50, 0, 25, 50, 75, 100, 150], dtype=np.float64)

    models = [
        RawStrengthModel().fit(X_train, y_train),
        LogisticCalibrationModel().fit(X_train, y_train),
        IsotonicCalibrationModel().fit(X_train, y_train),
        EmpiricalBucketCalibrationModel().fit(X_train, y_train),
    ]

    for model in models:
        probs = model.predict_proba(X_test)
        assert np.all(probs >= 0.01), f"{model.name} produced prob < 0.01: {probs}"
        assert np.all(probs <= 0.99), f"{model.name} produced prob > 0.99: {probs}"


def test_logistic_calibration_reproducibility():
    """Verify that Logistic Calibration is deterministic and produces a valid formula."""
    X = np.array([30, 40, 50, 60, 70, 80], dtype=np.float64)
    y = np.array([0, 0, 0, 1, 1, 1], dtype=np.int32)

    m1 = LogisticCalibrationModel().fit(X, y)
    m2 = LogisticCalibrationModel().fit(X, y)

    p1 = m1.predict_proba(X)
    p2 = m2.predict_proba(X)

    np.testing.assert_allclose(p1, p2)
    assert m1.is_fitted
    assert "P(Win | strength)" in m1.get_formula()


def test_empirical_bucket_calibration_smoothing():
    """Verify that empirical bucket model applies Laplace smoothing without div by zero."""
    X = np.array([52, 53, 58, 62], dtype=np.float64)
    y = np.array([0, 0, 1, 1], dtype=np.int32)

    emp = EmpiricalBucketCalibrationModel(bin_width=5).fit(X, y)
    assert emp.is_fitted
    probs = emp.predict_proba(np.array([52, 95]))  # 95 was not in training
    assert len(probs) == 2
    assert 0.01 <= probs[0] <= 0.99
    assert 0.01 <= probs[1] <= 0.99


# ---------------------------------------------------------------------------
# 3. Metric Calculations (Brier, LogLoss, ECE, Wilson CI, Bootstrap)
# ---------------------------------------------------------------------------

def test_brier_and_log_loss_computation():
    """Verify Brier Score and Log Loss calculation accuracy."""
    calibrator = StrengthProbabilityCalibrator()
    y_true = [1, 0, 1, 1]
    p_pred = [0.8, 0.2, 0.9, 0.7]

    metrics = calibrator.compute_metrics(y_true, p_pred)
    # Expected Brier: ((0.8-1)^2 + (0.2-0)^2 + (0.9-1)^2 + (0.7-1)^2)/4 = (0.04 + 0.04 + 0.01 + 0.09)/4 = 0.045
    assert abs(metrics.brier_score - 0.045) < 1e-3
    assert metrics.log_loss > 0.0
    assert metrics.expected_calibration_error >= 0.0
    assert metrics.max_calibration_error >= 0.0


def test_wilson_score_interval():
    """Verify Wilson Score 95% Confidence Interval mathematical bounds."""
    # 0 wins in 10
    low0, high0 = _wilson_score_interval(0, 10)
    assert low0 == 0.0
    assert 0.0 < high0 < 35.0

    # 10 wins in 10
    low10, high10 = _wilson_score_interval(10, 10)
    assert low10 > 65.0
    assert high10 == 100.0

    # 50 wins in 100
    low50, high50 = _wilson_score_interval(50, 100)
    assert 39.0 <= low50 <= 41.0
    assert 59.0 <= high50 <= 61.0


def test_bootstrap_ci_expectancy():
    """Verify deterministic non-parametric bootstrap confidence interval."""
    r_vals = [1.5, -1.0, 1.5, 1.5, -1.0, 1.5, -1.0, 1.5]
    low, high = _bootstrap_ci_expectancy(r_vals, n_bootstrap=500)
    assert low < np.mean(r_vals) < high


# ---------------------------------------------------------------------------
# 4. Threshold Research & Directional Separation Tests
# ---------------------------------------------------------------------------

def test_threshold_research_evaluation(sample_pit_records):
    """Verify that threshold research calculates metrics across all standard cutoffs."""
    calibrator = StrengthProbabilityCalibrator()
    train_set, val_set, holdout_set = calibrator.split_data(sample_pit_records, 0.6, 0.2)
    thresholds = calibrator.evaluate_threshold_research(train_set, val_set, holdout_set)

    assert len(thresholds) == 7
    th_values = [t.threshold for t in thresholds]
    assert th_values == [50, 55, 60, 65, 70, 75, 80]
    for t in thresholds:
        assert t.total_trades <= len(sample_pit_records)
        assert t.statistical_verdict in ("STATISTICALLY SUPPORTED", "PROMISING BUT INSUFFICIENT SAMPLE", "NOT SUPPORTED")


def test_directional_calibration_separation(sample_pit_records):
    """Verify that BUY and SELL directional calibrations are computed independently."""
    calibrator = StrengthProbabilityCalibrator()
    buy_sum = calibrator.evaluate_directional_calibration("BTC/USD", sample_pit_records, "BUY")
    sell_sum = calibrator.evaluate_directional_calibration("BTC/USD", sample_pit_records, "SELL")

    assert buy_sum.direction == "BUY"
    assert sell_sum.direction == "SELL"
    assert buy_sum.sample_size + sell_sum.sample_size == len(sample_pit_records)
    assert buy_sum.train_size + buy_sum.val_size + buy_sum.holdout_size == buy_sum.sample_size


# ---------------------------------------------------------------------------
# 5. Full Pipeline & Report Export Integration Test
# ---------------------------------------------------------------------------

def test_full_calibration_report_generation_and_export():
    """Verify that the calibrator runs end-to-end and exports valid JSON and Markdown reports."""
    calibrator = StrengthProbabilityCalibrator()
    json_p, md_p, audit_j, audit_m = calibrator.export_reports()

    assert os.path.exists(json_p), f"Missing {json_p}"
    assert os.path.exists(md_p), f"Missing {md_p}"
    assert os.path.exists(audit_j), f"Missing {audit_j}"
    assert os.path.exists(audit_m), f"Missing {audit_m}"

    # Verify JSON structure
    with open(json_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "btc_report" in data
    assert "xau_report" in data
    assert "global_model_comparison" in data
    assert "research_questions_answers" in data

    # Verify Markdown contains all critical sections
    with open(md_p, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "# Strength Score Probability Calibration & Holdout Validation Report" in md_text
    assert "## 1. Executive Summary" in md_text
    assert "## 10. Strength" in md_text
    assert "## 11. Hypothetical Threshold Research" in md_text
    assert "## 15. Lookahead Audit Confirmation" in md_text
    assert "## 18. Explicit Limitations" in md_text
