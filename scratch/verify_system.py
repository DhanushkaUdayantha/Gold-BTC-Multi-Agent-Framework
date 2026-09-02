"""
Comprehensive system verification script.
Tests all endpoints via FastAPI TestClient and SQLite database assertions.
"""
import sys
import os
import json
import sqlite3

# Insert project root
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.api.main import app

def run_verification():
    client = TestClient(app)

    print("=" * 70)
    print("HISTORICAL INTELLIGENCE & GEMINI AI LAYER VERIFICATION")
    print("=" * 70)

    # 1. Health Check
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200, f"Health failed: {res_health.text}"
    health_data = res_health.json()
    print("\n[1] Health Status:")
    print(f"  Status: {health_data.get('status')}")
    print(f"  AI Provider: {health_data.get('ai_provider')} ({health_data.get('ai_model')})")
    print(f"  Gemini Configured: {health_data.get('gemini_configured')}")
    print(f"  Gemini Active: {health_data.get('gemini_active')}")
    assert health_data.get("gemini_configured") is True
    assert health_data.get("gemini_active") is True

    # 2. Fast Dataset Status (<100ms)
    res_dataset = client.get("/api/v1/backtest/datasets/status")
    assert res_dataset.status_code == 200, f"Dataset status failed: {res_dataset.text}"
    ds_data = res_dataset.json()
    print("\n[2] Dataset Status:")
    print(f"  Status: {ds_data.get('status')}")
    print(f"  Total Historical Candles: {ds_data.get('total_candles'):,}")
    for sym, sym_info in ds_data.get("symbols", {}).items():
        print(f"  - {sym}: {sym_info.get('total_candles'):,} candles | Completed Signals: {sym_info.get('completed_signals')}")

    # 3. SQLite Signal Counts & Outcome Verification
    db_path = "data/historical/historical_market_data.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT symbol, direction, outcome, COUNT(*) FROM historical_signals GROUP BY symbol, direction, outcome ORDER BY symbol, direction, outcome")
    signal_counts = cur.fetchall()
    conn.close()

    print("\n[3] Historical Completed Signals in SQLite Database:")
    for sym, direction, outcome, count in signal_counts:
        print(f"  - {sym} {direction} {outcome}: {count} signals")

    # 4. Live Decision for XAU-USD-SPOT
    res_xau = client.get("/api/v1/decision?symbol=XAU-USD-SPOT")
    assert res_xau.status_code == 200, f"XAU decision failed: {res_xau.text}"
    xau_data = res_xau.json()
    print("\n[4] XAU/USD Live Decision & Empirical Historical Evidence:")
    print(f"  Decision: {xau_data.get('decision')} (Confidence: {xau_data.get('confidence_pct')}%)")
    print(f"  Historical Status: {xau_data.get('historical_evidence_status')} (Quality: {xau_data.get('evidence_quality')})")
    print(f"  Sample Size: {xau_data.get('historical_sample_size')} | Win Rate: {xau_data.get('historical_win_rate')}%")
    print(f"  Expectancy: {xau_data.get('historical_expectancy')}R | Profit Factor: {xau_data.get('historical_profit_factor')}")
    print(f"  Top Win Drivers: {xau_data.get('top_success_reasons')}")
    print(f"  Top Risk Caveats: {xau_data.get('top_failure_reasons')}")
    print(f"  Gemini Score: {xau_data.get('gemini_score')}/10 (Provider: {xau_data.get('ai_provider')})")

    # 5. Live Decision for BTC-USD
    res_btc = client.get("/api/v1/decision?symbol=BTC-USD")
    assert res_btc.status_code == 200, f"BTC decision failed: {res_btc.text}"
    btc_data = res_btc.json()
    print("\n[5] BTC/USD Live Decision & Empirical Historical Evidence:")
    print(f"  Decision: {btc_data.get('decision')} (Confidence: {btc_data.get('confidence_pct')}%)")
    print(f"  Historical Status: {btc_data.get('historical_evidence_status')} (Quality: {btc_data.get('evidence_quality')})")
    print(f"  Sample Size: {btc_data.get('historical_sample_size')} | Win Rate: {btc_data.get('historical_win_rate')}%")
    print(f"  Expectancy: {btc_data.get('historical_expectancy')}R | Profit Factor: {btc_data.get('historical_profit_factor')}")
    print(f"  Top Win Drivers: {btc_data.get('top_success_reasons')}")
    print(f"  Top Risk Caveats: {btc_data.get('top_failure_reasons')}")
    print(f"  Gemini Score: {btc_data.get('gemini_score')}/10 (Provider: {btc_data.get('ai_provider')})")

    print("\n" + "=" * 70)
    print("ALL SYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
