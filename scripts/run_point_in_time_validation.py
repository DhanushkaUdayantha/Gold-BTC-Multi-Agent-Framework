"""
Standalone runner for True Point-in-Time Strength Validation & Lookahead Bias Audit.

Usage:
    python scripts/run_point_in_time_validation.py
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.point_in_time_validator import PointInTimeStrengthValidator


def main():
    print("=" * 85)
    print(" TRUE POINT-IN-TIME HISTORICAL STRENGTH VALIDATION & LOOKAHEAD AUDIT")
    print("=" * 85)
    print("Replaying historical market trades with strict zero-lookahead information sets...")
    print("Auditing against temporal leakage, future outcomes, and sample contamination...\n")

    validator = PointInTimeStrengthValidator()
    report = validator.run_full_point_in_time_validation()
    paths = validator.export_all_reports(report)

    btc = report.btc_report
    xau = report.xau_report

    print("=" * 85)
    print(f" LOOKAHEAD BIAS AUDIT VERDICT")
    print("=" * 85)
    print(f"  BTC-USD: {btc.audit_summary.audit_verdict} ({btc.audit_summary.total_signals_audited:,} signals audited | {btc.audit_summary.lookahead_violations_count} violations)")
    print(f"  XAU-USD: {xau.audit_summary.audit_verdict} ({xau.audit_summary.total_signals_audited:,} signals audited | {xau.audit_summary.lookahead_violations_count} violations)")
    print("=" * 85)

    print("\n" + "=" * 85)
    print(f" BTC-USD POINT-IN-TIME DIRECTIONAL PERFORMANCE")
    print("=" * 85)
    print(f"  BUY  (N={btc.directional_buy.count:<4}): WR {btc.directional_buy.win_rate_pct:.1f}% [95% CI: {btc.directional_buy.wilson_ci_lower:.1f}%-{btc.directional_buy.wilson_ci_upper:.1f}%] | Expectancy: {btc.directional_buy.expectancy_r:+.2f}R | PF: {btc.directional_buy.profit_factor:.2f} | Verdict: {btc.directional_buy.statistical_verdict}")
    print(f"  SELL (N={btc.directional_sell.count:<4}): WR {btc.directional_sell.win_rate_pct:.1f}% [95% CI: {btc.directional_sell.wilson_ci_lower:.1f}%-{btc.directional_sell.wilson_ci_upper:.1f}%] | Expectancy: {btc.directional_sell.expectancy_r:+.2f}R | PF: {btc.directional_sell.profit_factor:.2f} | Verdict: {btc.directional_sell.statistical_verdict}")
    print(f"  Directional Asymmetry: SELL outperforms BUY by {btc.directional_asymmetry['buy_minus_sell_expectancy']:+.2f}R expectancy ({btc.directional_asymmetry['buy_minus_sell_win_rate']:+.1f}% WR)")

    print("\n" + "=" * 85)
    print(f" XAU-USD POINT-IN-TIME DIRECTIONAL PERFORMANCE")
    print("=" * 85)
    print(f"  BUY  (N={xau.directional_buy.count:<4}): WR {xau.directional_buy.win_rate_pct:.1f}% [95% CI: {xau.directional_buy.wilson_ci_lower:.1f}%-{xau.directional_buy.wilson_ci_upper:.1f}%] | Expectancy: {xau.directional_buy.expectancy_r:+.2f}R | PF: {xau.directional_buy.profit_factor:.2f} | Verdict: {xau.directional_buy.statistical_verdict}")
    print(f"  SELL (N={xau.directional_sell.count:<4}): WR {xau.directional_sell.win_rate_pct:.1f}% [95% CI: {xau.directional_sell.wilson_ci_lower:.1f}%-{xau.directional_sell.wilson_ci_upper:.1f}%] | Expectancy: {xau.directional_sell.expectancy_r:+.2f}R | PF: {xau.directional_sell.profit_factor:.2f} | Verdict: {xau.directional_sell.statistical_verdict}")
    print(f"  Directional Asymmetry: BUY outperforms SELL by {xau.directional_asymmetry['buy_minus_sell_expectancy']:+.2f}R expectancy ({xau.directional_asymmetry['buy_minus_sell_win_rate']:+.1f}% WR)")

    print("\n" + "=" * 85)
    print(" HYPOTHETICAL STRENGTH THRESHOLD SENSITIVITY (BTC-USD)")
    print("=" * 85)
    print(f" {'Threshold':<10} | {'Signals':<8} | {'Win Rate %':<11} | {'Expectancy':<11} | {'PF':<6} | {'Max DD':<8} | {'WF Cons %':<10} | {'Verdict'}")
    print("-" * 85)
    for t in btc.threshold_evaluations:
        print(f" >= {t.threshold}%{'':<5} | {t.num_signals:<8} | {t.win_rate_pct:<11.1f} | {t.expectancy_r:<+11.2f} | {t.profit_factor:<6.2f} | {t.max_drawdown_r:<8.1f} | {t.walk_forward_consistency_pct:<10.0f} | {t.statistical_verdict}")

    print("\n" + "=" * 85)
    print(" HYPOTHETICAL STRENGTH THRESHOLD SENSITIVITY (XAU-USD)")
    print("=" * 85)
    print(f" {'Threshold':<10} | {'Signals':<8} | {'Win Rate %':<11} | {'Expectancy':<11} | {'PF':<6} | {'Max DD':<8} | {'WF Cons %':<10} | {'Verdict'}")
    print("-" * 85)
    for t in xau.threshold_evaluations:
        print(f" >= {t.threshold}%{'':<5} | {t.num_signals:<8} | {t.win_rate_pct:<11.1f} | {t.expectancy_r:<+11.2f} | {t.profit_factor:<6.2f} | {t.max_drawdown_r:<8.1f} | {t.walk_forward_consistency_pct:<10.0f} | {t.statistical_verdict}")

    print("\n" + "=" * 85)
    print(" REPORTS EXPORTED")
    print("=" * 85)
    for k, v in paths.items():
        print(f"  {k:<16}: {v}")
    print("=" * 85)


if __name__ == "__main__":
    main()
