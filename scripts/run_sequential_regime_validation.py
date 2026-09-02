"""
Runner script for Regime-Aware Sequential Validation Research.

Executes:
1. Sequential Event Simulation (Chronological replay, equity curves, drawdowns, streaks)
2. Regime Transition Testing (Static regimes, sessions, sequential state shifts)
3. Rolling Performance Analysis (25, 50, 100, 200 trade windows)
4. Probability Calibration Drift & Expected Calibration Error (ECE) Tracking
5. Real-Time Strategy Degradation Detection
6. 10,000-Path Monte Carlo Random-Walk Trade-Sequence Stress Testing
7. Synchronized Multi-Asset Portfolio Simulation (BTC SELL + XAU BUY)
8. Export of 6 JSON & Markdown reports to data/reports/
"""
from __future__ import annotations

import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.sequential_regime_validator import SequentialRegimeValidator


def main():
    print("=" * 90)
    print("REGIME-AWARE SEQUENTIAL VALIDATION & PORTFOLIO ENGINE")
    print("=" * 90)
    print("Mode: Pure Empirical Research. Zero Production Decision Logic Modified.\n")

    validator = SequentialRegimeValidator()
    print("Running sequential event simulation, regime transitions, rolling windows, and 10k Monte Carlo...")

    report_paths = validator.export_all_reports()

    print("\n[OK] Reports Exported Successfully:")
    for k, p in report_paths.items():
        print(f"  - {k:<25}: {p}")

    report = validator.run_full_validation_suite()

    print("\n" + "=" * 120)
    print("MASTER QUALIFICATION & SEQUENTIAL STABILITY SUMMARY")
    print("=" * 120)
    print(
        f"{'Strategy ID':<30} | {'Asset':<7} | {'Dir':<4} | {'N':<5} | {'WR %':<6} | {'Exp (R)':<8} | {'PF':<5} | "
        f"{'Total R':<8} | {'Max DD':<7} | {'Rolling-50':<12} | {'MC 5% R':<9} | {'Score':<5} | {'Qualification Verdict'}"
    )
    print("-" * 155)

    for p in report.candidate_profiles:
        s = p.sequential_simulation
        r50 = next((r for r in p.rolling_windows if r.window_size == 50), None)
        r50_str = f"{r50.mean_rolling_expectancy:+.2f}R" if r50 else "N/A"
        mc = p.monte_carlo_stress
        print(
            f"{p.strategy_id:<30} | {p.asset:<7} | {p.direction:<4} | {s.total_trades:<5} | {s.win_rate_pct:<6.1f} | {s.expectancy_r:<+8.2f} | {s.profit_factor:<5.2f} | "
            f"{s.total_cumulative_r:<+8.1f} | {s.max_drawdown_r:<7.1f} | {r50_str:<12} | +{mc.percentile_5th_r:<8.1f} | {p.final_qualification_score:<5.1f} | {p.qualification_classification}"
        )

    print("\n" + "=" * 90)
    print("MULTI-ASSET COMBINED PORTFOLIO PERFORMANCE")
    print("=" * 90)
    p1 = report.primary_portfolio
    print(f"Portfolio ID:            {p1.portfolio_id}")
    print(f"Total Portfolio Trades:  {p1.total_trades_count:,}")
    print(f"Combined Expectancy:     {p1.combined_expectancy_r:+.2f}R (Win Rate: {p1.combined_win_rate_pct:.1f}%, PF: {p1.combined_profit_factor:.2f})")
    print(f"Combined Total Return:   {p1.combined_total_r:+.1f}R")
    print(f"Portfolio Max Drawdown:  {p1.combined_max_drawdown_r:.1f}R (Standalone Sum: {p1.sum_standalone_dd_r:.1f}R)")
    print(f"Diversification Benefit: {p1.diversification_benefit_pct:.1f}% reduction in max DD")
    print(f"Correlation (rho):       {p1.trade_correlation_rho:+.3f}")
    print(f"Concentration Risk:      {p1.concentration_risk_grade}")

    print("\nDone.")


if __name__ == "__main__":
    main()
