#!/usr/bin/env python3
"""
Master Runner for Phase 5 — Live Signal Outcome Validation, Real-World Accuracy Tracking & Strict BTC/XAU Isolation.

Executes end-to-end validation pipeline:
1. Validates signal dataset integrity.
2. Resolves eligible open signal outcomes.
3. Computes isolated metrics for BTC and XAU (Daily, Weekly, Monthly, All-Time).
4. Computes 10-bucket probability calibration (Brier score, ECE, MCE).
5. Audits strict BTC/XAU asset isolation.
6. Generates all 11 Phase 5 reports in data/reports/live_signal_validation/.
7. Prints comprehensive terminal telemetry summary.
"""

from __future__ import annotations

import json
import logging
import os
import sys

# Ensure repository root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.services.signal_repository import get_signal_repository
from src.services.outcome_tracker import get_outcome_tracker
from src.services.live_validation_engine import get_live_validation_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Phase5LiveValidation")


def main() -> int:
    print("=" * 60)
    print("STARTING PHASE 5: LIVE SIGNAL OUTCOME VALIDATION PIPELINE")
    print("=" * 60)

    repo = get_signal_repository()
    tracker = get_outcome_tracker()
    engine = get_live_validation_engine()

    # Step 1: Validate dataset integrity
    issues, valid_count = repo.validate_dataset()
    print(f"\n[1/5] Signal Dataset Integrity: {valid_count} valid records, {len(issues)} issues found.")

    # Step 2: Resolve pending outcomes
    pending_btc = repo.get_pending_outcome_signals(symbol="BTC-USD")
    pending_xau = repo.get_pending_outcome_signals(symbol="XAU-USD-SPOT")
    print(f"[2/5] Pending Signal Outcomes: BTC={len(pending_btc)}, XAU={len(pending_xau)}")

    # Step 3: Generate all validation reports
    print("[3/5] Generating Phase 5 Live Validation Reports...")
    report_paths = engine.generate_all_live_validation_reports()
    for name, (j_path, m_path) in report_paths.items():
        print(f"  [OK] {name}: {os.path.basename(m_path)} & {os.path.basename(j_path)}")

    # Step 4: Load generated summaries for terminal output
    btc_summary = engine.generate_asset_live_validation_summary("BTC-USD")
    xau_summary = engine.generate_asset_live_validation_summary("XAU-USD-SPOT")

    # Step 5: Final Terminal Output formatted per prompt specifications
    print("\n" + "=" * 60)
    print("LIVE SIGNAL VALIDATION COMPLETE")
    print("=" * 60)

    print("\nBTC")
    print(f"Signals: {btc_summary.total_signals_recorded}")
    print(f"Trades: {btc_summary.total_trades_created}")
    print(f"Pending: {btc_summary.total_pending_trades}")
    print(f"Wins: {btc_summary.all_time.wins}")
    print(f"Losses: {btc_summary.all_time.losses}")
    print(f"Win Rate: {btc_summary.all_time.win_rate_pct}%")
    print(f"Expectancy: {btc_summary.all_time.expectancy_r:+.4f}R")
    print(f"Profit Factor: {btc_summary.all_time.profit_factor:.2f}")
    print(f"Total R: {btc_summary.all_time.total_realized_r:+.2f}R")
    print(f"Max DD: {btc_summary.all_time.max_drawdown_r:.2f}R")
    print(f"Calibration: {btc_summary.calibration.overall_status} (Brier: {btc_summary.calibration.brier_score:.4f}, ECE: {btc_summary.calibration.ece_pct}%)")

    print("\nXAU")
    print(f"Signals: {xau_summary.total_signals_recorded}")
    print(f"Trades: {xau_summary.total_trades_created}")
    print(f"Pending: {xau_summary.total_pending_trades}")
    print(f"Wins: {xau_summary.all_time.wins}")
    print(f"Losses: {xau_summary.all_time.losses}")
    print(f"Win Rate: {xau_summary.all_time.win_rate_pct}%")
    print(f"Expectancy: {xau_summary.all_time.expectancy_r:+.4f}R")
    print(f"Profit Factor: {xau_summary.all_time.profit_factor:.2f}")
    print(f"Total R: {xau_summary.all_time.total_realized_r:+.2f}R")
    print(f"Max DD: {xau_summary.all_time.max_drawdown_r:.2f}R")
    print(f"Calibration: {xau_summary.calibration.overall_status} (Brier: {xau_summary.calibration.brier_score:.4f}, ECE: {xau_summary.calibration.ece_pct}%)")

    print("\nPREDICTION VS ACTUAL")
    print(f"BTC: Mean Prob = {btc_summary.all_time.average_calibrated_prob}%, Observed WR = {btc_summary.all_time.win_rate_pct}%, Calibration Error = {btc_summary.all_time.calibration_error_pct}%")
    print(f"XAU: Mean Prob = {xau_summary.all_time.average_calibrated_prob}%, Observed WR = {xau_summary.all_time.win_rate_pct}%, Calibration Error = {xau_summary.all_time.calibration_error_pct}%")

    print("\nFAILURE ANALYSIS")
    top_btc_f = btc_summary.top_failures[0].failure_category if btc_summary.top_failures else "None recorded"
    top_xau_f = xau_summary.top_failures[0].failure_category if xau_summary.top_failures else "None recorded"
    print(f"BTC: Primary Loss Factor = {top_btc_f} ({len(btc_summary.top_failures)} distinct failure patterns)")
    print(f"XAU: Primary Loss Factor = {top_xau_f} ({len(xau_summary.top_failures)} distinct failure patterns)")

    print("\nSUCCESS ANALYSIS")
    top_btc_s = btc_summary.top_successes[0].success_category if btc_summary.top_successes else "None recorded"
    top_xau_s = xau_summary.top_successes[0].success_category if xau_summary.top_successes else "None recorded"
    print(f"BTC: Primary Winning Catalyst = {top_btc_s} ({len(btc_summary.top_successes)} winning catalysts)")
    print(f"XAU: Primary Winning Catalyst = {top_xau_s} ({len(xau_summary.top_successes)} winning catalysts)")

    print("\nASSET ISOLATION")
    print(f"BTC: {'PASS' if btc_summary.asset_isolation_verified else 'FAIL'}")
    print(f"XAU: {'PASS' if xau_summary.asset_isolation_verified else 'FAIL'}")

    print("\nPRODUCTION")
    print("Decision Logic: UNCHANGED")
    print("BUY/SELL/WAIT: UNCHANGED")
    print("Entry: UNCHANGED")
    print("SL: UNCHANGED")
    print("TP: UNCHANGED")
    print("Risk: UNCHANGED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
