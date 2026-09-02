"""
Unit and integration tests for the Historical Strength Backtesting & Calibration Module.
"""
import pytest
from src.services.strength_backtest_calibration import (
    HistoricalStrengthBacktestCalibrator,
    _wilson_interval,
    TradeOutcomeMetrics,
    StrengthBucketCalibration,
)


def test_wilson_interval_bounds():
    """Test that Wilson Score intervals are correctly bounded and calibrated."""
    low, high = _wilson_interval(50, 100)
    assert 40.0 <= low <= 41.0
    assert 59.0 <= high <= 60.0

    # Small sample (5/8 = 62.5%) -> wide interval
    low_small, high_small = _wilson_interval(5, 8)
    assert low_small <= 35.0
    assert high_small >= 80.0

    # Large sample (247/399 = 61.9%) -> narrow interval
    low_large, high_large = _wilson_interval(247, 399)
    assert 57.0 <= low_large <= 58.0
    assert 66.0 <= high_large <= 67.0


def test_compute_trade_metrics_empty():
    calibrator = HistoricalStrengthBacktestCalibrator()
    m = calibrator.compute_trade_metrics([])
    assert m.total_trades == 0
    assert m.win_rate_pct == 0.0
    assert m.profit_factor == 0.0


def test_compute_trade_metrics_synthetic():
    calibrator = HistoricalStrengthBacktestCalibrator()
    trades = [
        {"outcome": "WIN", "realized_r": 1.5, "mfe": 2.1, "mae": 0.4, "time_to_outcome_minutes": 45},
        {"outcome": "WIN", "realized_r": 1.5, "mfe": 1.8, "mae": 0.6, "time_to_outcome_minutes": 60},
        {"outcome": "LOSS", "realized_r": -1.0, "mfe": 0.3, "mae": 1.1, "time_to_outcome_minutes": 30},
        {"outcome": "WIN", "realized_r": 1.5, "mfe": 2.5, "mae": 0.2, "time_to_outcome_minutes": 90},
    ]
    m = calibrator.compute_trade_metrics(trades)
    assert m.total_trades == 4
    assert m.wins == 3
    assert m.losses == 1
    assert m.win_rate_pct == 75.0
    assert m.profit_factor == 4.5  # 4.5 gross wins / 1.0 gross loss
    assert m.expectancy_r == 0.875  # (0.75 * 1.5) - (0.25 * 1.0) = 1.125 - 0.25 = 0.875
    assert m.tp1_hits == 3
    assert m.tp2_hits == 2  # mfe >= 2.0 (2.1 and 2.5)
    assert m.sl_hits == 1


def test_evaluate_strength_buckets_monotonicity():
    calibrator = HistoricalStrengthBacktestCalibrator()
    trades = [
        {"confluence_score": 52, "outcome": "LOSS", "realized_r": -1.0},
        {"confluence_score": 55, "outcome": "WIN", "realized_r": 1.5},
        {"confluence_score": 65, "outcome": "WIN", "realized_r": 1.5},
        {"confluence_score": 68, "outcome": "WIN", "realized_r": 1.5},
        {"confluence_score": 75, "outcome": "WIN", "realized_r": 1.5},
        {"confluence_score": 85, "outcome": "WIN", "realized_r": 1.5},
    ]
    buckets = calibrator.evaluate_strength_buckets(trades)
    assert len(buckets) == 6
    b50 = next(b for b in buckets if b.bucket_name == "50% – 59%")
    b60 = next(b for b in buckets if b.bucket_name == "60% – 69%")
    assert b50.count == 2
    assert b50.observed_win_rate_pct == 50.0
    assert b60.count == 2
    assert b60.observed_win_rate_pct == 100.0


def test_full_calibration_run_and_export():
    """Verify that full calibration runs on the historical database and exports reports."""
    calibrator = HistoricalStrengthBacktestCalibrator()
    report = calibrator.run_full_calibration()

    assert report.btc_report.total_evaluated_trades > 0
    assert report.xau_report.total_evaluated_trades > 0
    assert report.btc_report.overall_metrics.win_rate_pct > 0
    assert report.xau_report.overall_metrics.win_rate_pct > 0

    # Test out-of-sample split metrics exist
    assert report.btc_report.out_of_sample_metrics.total_trades > 0
    assert report.xau_report.out_of_sample_metrics.total_trades > 0

    # Test walk-forward folds exist
    assert len(report.btc_report.walk_forward_folds) == 4
    assert len(report.xau_report.walk_forward_folds) == 4

    # Test export
    json_path, md_path = calibrator.export_reports(report)
    assert json_path.endswith(".json")
    assert md_path.endswith(".md")
