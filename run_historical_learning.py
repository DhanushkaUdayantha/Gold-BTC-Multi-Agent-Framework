"""
Automated Historical Learning & Empirical Discovery Runner.
Populates historical_signals with factual WIN/LOSS signals and reasons.
"""
import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.historical_data_service import HistoricalDataService
from src.services.historical_backtest_runner import HistoricalBacktestRunner
from src.models.historical_data import BacktestConfig, AmbiguousCandleRule
from src.services.historical_evidence_service import HistoricalEvidenceService

def main():
    print("=" * 70)
    print("HISTORICAL INTELLIGENCE LAYER: EMPIRICAL LEARNING PASS")
    print("=" * 70)

    db_path = "data/historical/historical_market_data.db"
    data_svc = HistoricalDataService(db_path=db_path)
    runner = HistoricalBacktestRunner(data_svc)

    # 1. Backtest Replay for BTC/USD
    print("\n[1/2] Running Empirical Learning for BTC/USD 15m (2024-2026)...")
    t0 = time.time()
    btc_cfg = BacktestConfig(
        symbol="BTC/USD",
        primary_timeframe="15m",
        start_date="2024-01-01",
        end_date="2026-08-30",
        min_confluence_score=40,
        ambiguous_candle_rule=AmbiguousCandleRule.WORST_CASE,
    )
    btc_run_rec, btc_result = runner.run_backtest_sync(btc_cfg)
    t_btc = time.time() - t0
    print(f"  BTC Replay Completed in {t_btc:.2f}s:")
    print(f"  Total Trades: {btc_result.total_trades} (Wins: {btc_result.wins}, Losses: {btc_result.losses})")
    print(f"  Win Rate: {btc_result.win_rate:.1f}% | Profit Factor: {btc_result.profit_factor:.2f} | Expectancy: {btc_result.expectancy_r:+.2f}R")

    # 2. Backtest Replay for XAU/USD
    print("\n[2/2] Running Empirical Learning for XAU/USD 15m (2024-2026)...")
    t0 = time.time()
    xau_cfg = BacktestConfig(
        symbol="XAU/USD",
        primary_timeframe="15m",
        start_date="2024-01-01",
        end_date="2026-08-30",
        min_confluence_score=40,
        ambiguous_candle_rule=AmbiguousCandleRule.WORST_CASE,
    )
    xau_run_rec, xau_result = runner.run_backtest_sync(xau_cfg)
    t_xau = time.time() - t0
    print(f"  XAU Replay Completed in {t_xau:.2f}s:")
    print(f"  Total Trades: {xau_result.total_trades} (Wins: {xau_result.wins}, Losses: {xau_result.losses})")
    print(f"  Win Rate: {xau_result.win_rate:.1f}% | Profit Factor: {xau_result.profit_factor:.2f} | Expectancy: {xau_result.expectancy_r:+.2f}R")

    # 3. Test Evidence Service
    print("\n[3/3] Testing Empirical Evidence Retrieval & Pattern Matching...")
    ev_svc = HistoricalEvidenceService(db_path=db_path, auto_start_learning=False)

    btc_ev = ev_svc.get_evidence_for_setup(
        symbol="BTC/USD",
        direction="BUY",
        confluence_score=78,
        market_regime="BULLISH_TREND",
        contributors=[{"name": "SMC Structure", "bias": "BULLISH", "points": 20}],
        force_refresh=True,
    )
    print("\n--- BTC/USD BUY Setup Evidence ---")
    print(f"Status: {btc_ev.status} (Quality: {btc_ev.evidence_quality})")
    print(f"Sample Size: {btc_ev.sample_size} (Similar Setups: {btc_ev.similar_count})")
    print(f"Win Rate: {btc_ev.win_rate}% (95% CI: {btc_ev.ci_lower}% - {btc_ev.ci_upper}%)")
    print(f"Calibrated Prob: {btc_ev.calibrated_probability}%")
    print(f"Expectancy: {btc_ev.expectancy}R | Profit Factor: {btc_ev.profit_factor}")
    print(f"Top Win Drivers: {btc_ev.top_success_reasons}")
    print(f"Top Risk Factors: {btc_ev.top_failure_reasons}")
    print(f"Confirmations: {btc_ev.historical_confirmations}")
    print(f"Conflicts: {btc_ev.historical_conflicts}")

    xau_ev = ev_svc.get_evidence_for_setup(
        symbol="XAU/USD",
        direction="BUY",
        confluence_score=75,
        market_regime="BULLISH_TREND",
        contributors=[{"name": "SMC Structure", "bias": "BULLISH", "points": 20}],
        force_refresh=True,
    )
    print("\n--- XAU/USD BUY Setup Evidence ---")
    print(f"Status: {xau_ev.status} (Quality: {xau_ev.evidence_quality})")
    print(f"Sample Size: {xau_ev.sample_size} (Similar Setups: {xau_ev.similar_count})")
    print(f"Win Rate: {xau_ev.win_rate}% (95% CI: {xau_ev.ci_lower}% - {xau_ev.ci_upper}%)")
    print(f"Calibrated Prob: {xau_ev.calibrated_probability}%")
    print(f"Expectancy: {xau_ev.expectancy}R | Profit Factor: {xau_ev.profit_factor}")
    print(f"Top Win Drivers: {xau_ev.top_success_reasons}")
    print(f"Top Risk Factors: {xau_ev.top_failure_reasons}")
    print(f"Confirmations: {xau_ev.historical_confirmations}")
    print(f"Conflicts: {xau_ev.historical_conflicts}")

    print("\n" + "=" * 70)
    print("HISTORICAL LEARNING PASS COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
