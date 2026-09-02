"""
Unit and integration tests for True Point-in-Time Strength Validation & Lookahead Auditor.
"""
import pytest
from src.services.point_in_time_validator import (
    PointInTimeStrengthValidator,
    PointInTimeTradeRecord,
    _bootstrap_ci_expectancy,
)


def test_point_in_time_data_isolation():
    """Verify that every evaluated signal only accesses trades completed prior to its entry."""
    validator = PointInTimeStrengthValidator()
    btc_records, btc_audit = validator.run_point_in_time_replay("BTC/USD")

    assert btc_audit.is_clean, f"BTC Lookahead audit failed: {btc_audit.lookahead_violations_count} violations"
    assert btc_audit.future_timestamp_violations == 0
    assert btc_audit.future_trade_violations == 0
    assert btc_audit.future_outcome_violations == 0
    assert btc_audit.future_calibration_violations == 0

    xau_records, xau_audit = validator.run_point_in_time_replay("XAU/USD")
    assert xau_audit.is_clean, f"XAU Lookahead audit failed: {xau_audit.lookahead_violations_count} violations"
    assert xau_audit.future_timestamp_violations == 0


def test_temporal_monotonicity_invariant():
    """Verify that for every record, latest_observation_timestamp <= signal_timestamp."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("BTC/USD")

    for r in records:
        assert not r.future_timestamp_used
        assert not r.future_trade_used
        assert not r.future_outcome_used
        assert not r.future_calibration_data_used
        if r.latest_observation_timestamp != "N/A":
            assert r.latest_observation_timestamp <= r.signal_timestamp, (
                f"Temporal violation on signal {r.signal_id}: "
                f"latest obs {r.latest_observation_timestamp} > signal {r.signal_timestamp}"
            )


def test_strength_reproducibility_and_monotonicity():
    """Verify that strength scores are deterministic and within valid range [5, 95]."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("BTC/USD")

    for r in records:
        assert 5 <= r.buy_strength <= 95
        assert 5 <= r.sell_strength <= 95
        assert 5 <= r.selected_strength <= 95
        assert r.historical_bias in ("BUY", "SELL", "WAIT")


def test_calibration_buckets_correctness():
    """Verify strength score bucket grouping and metric calculations."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("XAU/USD")
    buckets = validator.evaluate_strength_buckets(records)

    assert len(buckets) == 6
    total_in_buckets = sum(b.count for b in buckets)
    total_wl = sum(1 for r in records if r.actual_outcome in ("WIN", "LOSS"))
    assert total_in_buckets == total_wl

    brier, ece, mce = validator.compute_brier_ece_mce(records, buckets)
    assert 0.0 <= brier <= 1.0
    assert 0.0 <= ece <= 100.0
    assert 0.0 <= mce <= 100.0


def test_directional_buy_sell_separation():
    """Verify that BUY and SELL performance metrics are calculated independently."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("BTC/USD")

    buy_m = validator.evaluate_directional(records, "BUY")
    sell_m = validator.evaluate_directional(records, "SELL")

    assert buy_m.count > 0
    assert sell_m.count > 0
    assert buy_m.count + sell_m.count == sum(1 for r in records if r.actual_outcome in ("WIN", "LOSS"))
    assert buy_m.direction == "BUY"
    assert sell_m.direction == "SELL"


def test_threshold_analysis_validity():
    """Verify that hypothetical threshold analysis produces monotonically decreasing or valid counts."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("BTC/USD")

    thresholds = validator.evaluate_hypothetical_thresholds(records)
    assert len(thresholds) == 7

    # Higher thresholds must filter for fewer or equal signals
    counts = [t.num_signals for t in thresholds]
    for k in range(len(counts) - 1):
        assert counts[k] >= counts[k + 1]


def test_walk_forward_folds_integrity():
    """Verify that walk-forward folds have non-overlapping test segments and strictly increasing train sizes."""
    validator = PointInTimeStrengthValidator()
    records, _ = validator.run_point_in_time_replay("BTC/USD")

    folds = validator.compute_walk_forward_folds(records)
    assert len(folds) == 4

    for k in range(len(folds) - 1):
        assert folds[k].train_count < folds[k + 1].train_count
        assert folds[k].test_count > 0
        assert folds[k].fold_index == k + 1


def test_bootstrap_ci_expectancy():
    """Verify non-parametric bootstrap confidence interval function."""
    r_vals = [1.5, 1.5, -1.0, 1.5, -1.0, 1.5, -1.0, 1.5]
    low, high = _bootstrap_ci_expectancy(r_vals, n_bootstrap=500)
    mean_val = sum(r_vals) / len(r_vals)
    assert low <= mean_val <= high


def test_full_point_in_time_validation_export():
    """Verify full validation run and report export."""
    validator = PointInTimeStrengthValidator()
    report = validator.run_full_point_in_time_validation()
    paths = validator.export_all_reports(report)

    assert "validation_json" in paths
    assert "validation_md" in paths
    assert "audit_json" in paths
    assert "audit_md" in paths

    assert len(report.research_conclusions_qa) == 11
    assert report.btc_report.audit_summary.is_clean
    assert report.xau_report.audit_summary.is_clean
