"""
Runner script for Strength-to-Probability Calibration and Independent Holdout Validation.

Executes:
1. True Point-in-Time Signal Replay for BTC-USD and XAU-USD
2. Strict Chronological 3-Way Split (60% Train, 20% Validation, 20% Untouched Holdout)
3. Fits and compares Raw Strength, Logistic (Platt), Isotonic, and Empirical Bucket Calibration
4. Lookahead Audit verification (0 violations)
5. Threshold sensitivity evaluation (50, 55, 60, 65, 70, 75, 80)
6. Independent BUY vs. SELL Directional Calibration
7. Exports JSON and Markdown reports to data/reports/
"""
from __future__ import annotations

import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.strength_probability_calibrator import StrengthProbabilityCalibrator


def main():
    print("=" * 80)
    print("STRENGTH-TO-PROBABILITY CALIBRATION & INDEPENDENT HOLDOUT ENGINE")
    print("=" * 80)
    print("Mode: Pure Research & Calibration. Zero Production Decision Logic Modified.\n")

    calibrator = StrengthProbabilityCalibrator()
    print("Generating comprehensive calibration reports for BTC-USD and XAU-USD...")
    
    json_path, md_path, audit_json_path, audit_md_path = calibrator.export_reports()

    print("\n[OK] Reports Exported Successfully:")
    print(f"  - Main JSON Report:          {json_path}")
    print(f"  - Main Markdown Report:      {md_path}")
    print(f"  - Lookahead Audit JSON:      {audit_json_path}")
    print(f"  - Lookahead Audit Markdown:  {audit_md_path}")

    # Load report and display summary
    report = calibrator.generate_full_research_report()
    
    print("\n" + "=" * 80)
    print("CALIBRATION MODEL PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"{'Model':<30} | {'BTC OOS Brier':<14} | {'BTC Holdout':<12} | {'XAU OOS Brier':<14} | {'XAU Holdout':<12} | {'Verdict'}")
    print("-" * 110)
    for m in report.global_model_comparison:
        print(
            f"{m['model']:<30} | {m['btc_oos_brier']:<14.4f} | {m['btc_holdout_brier']:<12.4f} | "
            f"{m['xau_oos_brier']:<14.4f} | {m['xau_holdout_brier']:<12.4f} | {m['verdict']}"
        )

    print("\n" + "=" * 80)
    print("BTC/USD STRENGTH -> PROBABILITY MAPPING TABLE")
    print("=" * 80)
    print(f"{'Range':<8} | {'Raw %':<6} | {'Logistic %':<10} | {'Isotonic %':<10} | {'Empirical %':<11} | {'Train N':<8} | {'Total N':<8} | {'Obs WR %':<9} | {'95% Wilson CI'}")
    print("-" * 95)
    for r in report.btc_report.strength_mapping_table:
        print(
            f"{r.strength_range:<8} | {r.raw_interpretation_pct:<6.1f} | {r.logistic_calibrated_pct:<10.1f} | "
            f"{r.isotonic_calibrated_pct:<10.1f} | {r.empirical_calibrated_pct:<11.1f} | {r.train_sample_n:<8} | "
            f"{r.total_sample_n:<8} | {r.observed_win_rate_pct:<9.1f} | [{r.wilson_ci_lower:.1f}%, {r.wilson_ci_upper:.1f}%]"
        )

    print("\n" + "=" * 80)
    print("XAU/USD STRENGTH -> PROBABILITY MAPPING TABLE")
    print("=" * 80)
    print(f"{'Range':<8} | {'Raw %':<6} | {'Logistic %':<10} | {'Isotonic %':<10} | {'Empirical %':<11} | {'Train N':<8} | {'Total N':<8} | {'Obs WR %':<9} | {'95% Wilson CI'}")
    print("-" * 95)
    for r in report.xau_report.strength_mapping_table:
        print(
            f"{r.strength_range:<8} | {r.raw_interpretation_pct:<6.1f} | {r.logistic_calibrated_pct:<10.1f} | "
            f"{r.isotonic_calibrated_pct:<10.1f} | {r.empirical_calibrated_pct:<11.1f} | {r.train_sample_n:<8} | "
            f"{r.total_sample_n:<8} | {r.observed_win_rate_pct:<9.1f} | [{r.wilson_ci_lower:.1f}%, {r.wilson_ci_upper:.1f}%]"
        )

    print("\n" + "=" * 80)
    print("DIRECTIONAL ASYMMETRY SUMMARY (BUY vs SELL)")
    print("=" * 80)
    print(f"BTC BUY (N={report.btc_report.directional_buy.sample_size:,}): Observed WR = {report.btc_report.directional_buy.observed_win_rate:.1f}%, Exp = {report.btc_report.directional_buy.mean_expectancy:+.2f}R -> {report.btc_report.directional_buy.statistical_edge_verdict}")
    print(f"BTC SELL (N={report.btc_report.directional_sell.sample_size:,}): Observed WR = {report.btc_report.directional_sell.observed_win_rate:.1f}%, Exp = {report.btc_report.directional_sell.mean_expectancy:+.2f}R -> {report.btc_report.directional_sell.statistical_edge_verdict}")
    print(f"XAU BUY (N={report.xau_report.directional_buy.sample_size:,}): Observed WR = {report.xau_report.directional_buy.observed_win_rate:.1f}%, Exp = {report.xau_report.directional_buy.mean_expectancy:+.2f}R -> {report.xau_report.directional_buy.statistical_edge_verdict}")
    print(f"XAU SELL (N={report.xau_report.directional_sell.sample_size:,}): Observed WR = {report.xau_report.directional_sell.observed_win_rate:.1f}%, Exp = {report.xau_report.directional_sell.mean_expectancy:+.2f}R -> {report.xau_report.directional_sell.statistical_edge_verdict}")

    print("\n" + "=" * 80)
    print("LOOKAHEAD AUDIT VERIFICATION")
    print("=" * 80)
    print(f"BTC Audit Violations: {report.btc_report.audit.violation_count} -> Status: {report.btc_report.audit.audit_status}")
    print(f"XAU Audit Violations: {report.xau_report.audit.violation_count} -> Status: {report.xau_report.audit.audit_status}")
    print("\nDone.")


if __name__ == "__main__":
    main()
