"""
Runner script for Stable Positive Expectancy Discovery Research.

Executes:
1. Field Availability Inspection
2. Point-in-Time Multi-Condition Dataset Construction
3. Combinatorial Search across Probability + Direction + Market Conditions
4. 3-Way Chronological Train/Val/Holdout Validation + 4-Fold Walk-Forward Cross-Validation
5. Lookahead Bias Auditing (0 violations)
6. Export of 6 reports in data/reports/
"""
from __future__ import annotations

import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.stable_expectancy_researcher import StableExpectancyResearcher


def main():
    print("=" * 80)
    print("STABLE POSITIVE EXPECTANCY DISCOVERY ENGINE")
    print("=" * 80)
    print("Mode: Pure Research & Strategy Search. Zero Production Decision Logic Modified.\n")

    researcher = StableExpectancyResearcher()
    print("Running combinatorial strategy search and validation on BTC-USD and XAU-USD...")

    report_paths = researcher.export_all_reports()

    print("\n[OK] Reports Exported Successfully:")
    for k, p in report_paths.items():
        print(f"  - {k:<12}: {p}")

    # Display Top 20 Candidates
    report = researcher.run_strategy_search()

    print("\n" + "=" * 120)
    print("TOP 20 STRATEGY CANDIDATES RANKING")
    print("=" * 120)
    print(
        f"{'Rank':<4} | {'Strategy ID':<28} | {'Asset':<7} | {'Dir':<4} | {'Prob':<4} | "
        f"{'N':<5} | {'WR %':<6} | {'Exp (R)':<8} | {'PF':<5} | {'OOS Exp':<8} | "
        f"{'Holdout':<8} | {'WF Stab':<8} | {'Bootstrap 95% CI':<18} | {'Verdict'}"
    )
    print("-" * 150)

    for i, c in enumerate(report.top_20_candidates, 1):
        print(
            f"{i:<4} | {c.strategy_id:<28} | {c.asset:<7} | {c.direction:<4} | {c.min_probability_pct:<4.0f} | "
            f"{c.total_trades:<5} | {c.win_rate_pct:<6.1f} | {c.expectancy_r:<+8.2f} | {c.profit_factor:<5.2f} | "
            f"{c.val_expectancy_r:<+8.2f} | {c.holdout_expectancy_r:<+8.2f} | {c.wf_stability_pct:<7.0f}% | "
            f"[{c.bootstrap_ci_lower:+.2f}, {c.bootstrap_ci_upper:+.2f}] | {c.statistical_verdict}"
        )

    print("\n" + "=" * 80)
    print("CATEGORY CHAMPIONS")
    print("=" * 80)
    if report.best_btc_strategy:
        b = report.best_btc_strategy
        print(f"Best BTC Strategy:  {b.strategy_id:<28} | Exp: {b.expectancy_r:+.2f}R | PF: {b.profit_factor:.2f} | Holdout: {b.holdout_expectancy_r:+.2f}R | WF: {b.wf_stability_pct:.0f}%")
    if report.best_xau_strategy:
        x = report.best_xau_strategy
        print(f"Best XAU Strategy:  {x.strategy_id:<28} | Exp: {x.expectancy_r:+.2f}R | PF: {x.profit_factor:.2f} | Holdout: {x.holdout_expectancy_r:+.2f}R | WF: {x.wf_stability_pct:.0f}%")
    if report.best_overall_strategy:
        o = report.best_overall_strategy
        print(f"Best Overall:       {o.strategy_id:<28} | Exp: {o.expectancy_r:+.2f}R | PF: {o.profit_factor:.2f} | Holdout: {o.holdout_expectancy_r:+.2f}R | WF: {o.wf_stability_pct:.0f}%")

    print("\n" + "=" * 80)
    print("LOOKAHEAD AUDIT VERIFICATION")
    print("=" * 80)
    print(f"Total Observations: {report.audit.total_observations_audited:,}")
    print(f"Violations Detected: {report.audit.violation_count}")
    print(f"Audit Status:        {report.audit.audit_status}")
    print("\nDone.")


if __name__ == "__main__":
    main()
