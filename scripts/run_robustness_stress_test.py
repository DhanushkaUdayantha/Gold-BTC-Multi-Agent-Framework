"""
Runner script for Robustness & Stress-Test Validation Research.

Executes:
1. Threshold Sensitivity & Performance Plateau Analysis (35%–50%)
2. Condition Ablation & Factor Sensitivity Testing
3. Time Stability across Historical Eras
4. 4-Fold Walk-Forward Cross-Validation Stress Testing
5. High-Precision 10,000-Resample Bootstrap Stability Analysis
6. Execution Friction & Slippage Stress Testing (0.00R to 0.20R)
7. Regime Breakdown & Multiple-Testing Selection-Bias Audit
8. Export of 4 JSON & Markdown reports to data/reports/
"""
from __future__ import annotations

import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.robustness_stress_tester import RobustnessStressTester


def main():
    print("=" * 80)
    print("ROBUSTNESS & STRESS-TEST VALIDATION ENGINE")
    print("=" * 80)
    print("Mode: Pure Empirical Stress Testing. Zero Production Decision Logic Modified.\n")

    tester = RobustnessStressTester()
    print("Executing full stress-testing suite (Thresholds, Ablation, 10k Bootstrap, Costs, Eras)...")

    report_paths = tester.export_all_reports()

    print("\n[OK] Reports Exported Successfully:")
    for k, p in report_paths.items():
        print(f"  - {k:<12}: {p}")

    report = tester.run_full_stress_test_suite()

    print("\n" + "=" * 110)
    print("CANDIDATE ROBUSTNESS PROFILES SUMMARY")
    print("=" * 110)
    print(
        f"{'Strategy ID':<30} | {'Asset':<7} | {'Dir':<4} | {'N':<5} | {'Exp (R)':<8} | {'PF':<5} | "
        f"{'OOS Exp':<8} | {'Holdout':<8} | {'WF':<5} | {'10k Boot 95% CI':<18} | {'Cost Tol':<8} | {'Score':<5} | {'Verdict'}"
    )
    print("-" * 145)

    for p in report.candidate_profiles:
        print(
            f"{p.strategy_id:<30} | {p.asset:<7} | {p.direction:<4} | {p.baseline_n:<5} | {p.baseline_expectancy_r:<+8.2f} | {p.baseline_profit_factor:<5.2f} | "
            f"{p.baseline_oos_expectancy_r:<+8.2f} | {p.baseline_holdout_expectancy_r:<+8.2f} | {p.walk_forward_metrics['positive_fold_ratio']:<5} | "
            f"[{p.bootstrap_10k.ci_lower_2_5:+.2f}, {p.bootstrap_10k.ci_upper_97_5:+.2f}] | {p.break_even_cost_r:<8.2f} | {p.robustness_score:<5.1f} | {p.robustness_classification}"
        )

    print("\n" + "=" * 80)
    print("HIGH-PRECISION 10,000-RESAMPLE BOOTSTRAP SUMMARY")
    print("=" * 80)
    for p in report.candidate_profiles[:4]:
        print(
            f"{p.strategy_id:<30} | Mean: {p.bootstrap_10k.mean_expectancy_r:+.3f}R | "
            f"95% CI: [{p.bootstrap_10k.ci_lower_2_5:+.3f}R, {p.bootstrap_10k.ci_upper_97_5:+.3f}R] | "
            f"P(Exp > 0): {p.bootstrap_10k.prob_positive_expectancy_pct:.1f}% | "
            f"P(Exp > 0.20R): {p.bootstrap_10k.prob_expectancy_above_20_pct:.1f}%"
        )

    print("\n" + "=" * 80)
    print("LOOKAHEAD AUDIT & TIME ISOLATION")
    print("=" * 80)
    print(f"Total Audited Signals: {report.audited_observations_count:,}")
    print(f"Selection Bias Risk:   {report.multiple_testing_audit.selection_bias_risk_grade}")
    print(f"Robust Candidates:     {len(report.strongest_robust_candidates)}")
    print(f"Fragile Candidates:    {len(report.fragile_candidates)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
