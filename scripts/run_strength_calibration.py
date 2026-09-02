"""
Standalone execution script for Historical Strength Backtesting & Calibration Module.

Usage:
    python scripts/run_strength_calibration.py
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.strength_backtest_calibration import HistoricalStrengthBacktestCalibrator


def main():
    print("=" * 80)
    print(" HISTORICAL STRENGTH BACKTESTING & EMPIRICAL CALIBRATION MODULE")
    print("=" * 80)
    print("Evaluating BUY/SELL strength scores against actual future outcomes on BTC-USD and XAU-USD...")
    print("Using 70/30 out-of-sample split and 4-fold walk-forward validation...\n")

    calibrator = HistoricalStrengthBacktestCalibrator()
    report = calibrator.run_full_calibration()

    json_path, md_path = calibrator.export_reports(report)

    # Console Summary
    btc = report.btc_report
    xau = report.xau_report

    print("=" * 80)
    print(f" BTC/USD BACKTEST RESULTS ({btc.total_evaluated_trades:,} trades | {btc.dataset_period})")
    print("=" * 80)
    print(f"  Overall Win Rate:        {btc.overall_metrics.win_rate_pct}%  [95% CI: {btc.overall_metrics.ci_95_lower}% - {btc.overall_metrics.ci_95_upper}%]")
    print(f"  Overall Expectancy:      {btc.overall_metrics.expectancy_r:+.2f} R")
    print(f"  Overall Profit Factor:   {btc.overall_metrics.profit_factor}")
    print(f"  Max Drawdown:            {btc.overall_metrics.max_drawdown_r} R  ({btc.overall_metrics.max_drawdown_pct}%)")
    print(f"  Out-of-Sample (30%) WR:  {btc.out_of_sample_metrics.win_rate_pct}%  (Expectancy: {btc.out_of_sample_metrics.expectancy_r:+.2f}R | PF: {btc.out_of_sample_metrics.profit_factor})")
    print(f"  BUY vs SELL:             BUY WR: {btc.directional_comparison.buy_metrics.win_rate_pct}% (PF {btc.directional_comparison.buy_metrics.profit_factor}) vs SELL WR: {btc.directional_comparison.sell_metrics.win_rate_pct}% (PF {btc.directional_comparison.sell_metrics.profit_factor})")
    print(f"  TP1 / TP2 / SL Hit:      TP1: {btc.overall_metrics.tp1_hit_rate_pct}% | TP2: {btc.overall_metrics.tp2_hit_rate_pct}% | SL: {btc.overall_metrics.sl_hit_rate_pct}%")
    print(f"  Calibration Brier Score: {btc.brier_score:.4f}  (ECE: {btc.expected_calibration_error}% | Status: {btc.calibration_grade})")

    print("\n" + "=" * 80)
    print(f" XAU/USD BACKTEST RESULTS ({xau.total_evaluated_trades:,} trades | {xau.dataset_period})")
    print("=" * 80)
    print(f"  Overall Win Rate:        {xau.overall_metrics.win_rate_pct}%  [95% CI: {xau.overall_metrics.ci_95_lower}% - {xau.overall_metrics.ci_95_upper}%]")
    print(f"  Overall Expectancy:      {xau.overall_metrics.expectancy_r:+.2f} R")
    print(f"  Overall Profit Factor:   {xau.overall_metrics.profit_factor}")
    print(f"  Max Drawdown:            {xau.overall_metrics.max_drawdown_r} R  ({xau.overall_metrics.max_drawdown_pct}%)")
    print(f"  Out-of-Sample (30%) WR:  {xau.out_of_sample_metrics.win_rate_pct}%  (Expectancy: {xau.out_of_sample_metrics.expectancy_r:+.2f}R | PF: {xau.out_of_sample_metrics.profit_factor})")
    print(f"  BUY vs SELL:             BUY WR: {xau.directional_comparison.buy_metrics.win_rate_pct}% (PF {xau.directional_comparison.buy_metrics.profit_factor}) vs SELL WR: {xau.directional_comparison.sell_metrics.win_rate_pct}% (PF {xau.directional_comparison.sell_metrics.profit_factor})")
    print(f"  TP1 / TP2 / SL Hit:      TP1: {xau.overall_metrics.tp1_hit_rate_pct}% | TP2: {xau.overall_metrics.tp2_hit_rate_pct}% | SL: {xau.overall_metrics.sl_hit_rate_pct}%")
    print(f"  Calibration Brier Score: {xau.brier_score:.4f}  (ECE: {xau.expected_calibration_error}% | Status: {xau.calibration_grade})")

    print("\n" + "=" * 80)
    print(" CALIBRATION BY STRENGTH SCORE BUCKETS (BTC/USD)")
    print("=" * 80)
    print(f" {'Bucket':<12} | {'Trades':<8} | {'Pred Str %':<10} | {'Obs Win %':<10} | {'Expectancy':<10} | {'PF':<6} | {'Gap %':<6}")
    print("-" * 75)
    for b in btc.strength_buckets:
        print(f" {b.bucket_name:<12} | {b.count:<8} | {b.mean_predicted_strength:<10.1f} | {b.observed_win_rate_pct:<10.1f} | {b.expectancy_r:<+10.2f} | {b.profit_factor:<6.2f} | {b.calibration_gap_pct:<6.1f}")

    print("\n" + "=" * 80)
    print(" CALIBRATION BY STRENGTH SCORE BUCKETS (XAU/USD)")
    print("=" * 80)
    print(f" {'Bucket':<12} | {'Trades':<8} | {'Pred Str %':<10} | {'Obs Win %':<10} | {'Expectancy':<10} | {'PF':<6} | {'Gap %':<6}")
    print("-" * 75)
    for b in xau.strength_buckets:
        print(f" {b.bucket_name:<12} | {b.count:<8} | {b.mean_predicted_strength:<10.1f} | {b.observed_win_rate_pct:<10.1f} | {b.expectancy_r:<+10.2f} | {b.profit_factor:<6.2f} | {b.calibration_gap_pct:<6.1f}")

    print("\n" + "=" * 80)
    print(" REPORTS EXPORTED")
    print("=" * 80)
    print(f"  JSON Report:     {json_path}")
    print(f"  Markdown Report: {md_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
