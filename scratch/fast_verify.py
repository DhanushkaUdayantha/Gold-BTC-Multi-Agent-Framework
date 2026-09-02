"""
Fast targeted verification script utilizing indexed lookups.
"""
import sqlite3
import time
import requests
import json
from datetime import datetime, timezone

DB_PATH = "data/historical/historical_market_data.db"

conn = sqlite3.connect(DB_PATH, timeout=30.0)
conn.row_factory = sqlite3.Row

print("=" * 75)
print("1. BTC/USD 5m CANDLE AUDIT")
print("=" * 75)

# Baseline count
r_btc_base = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='BTC/USD' AND timeframe='5m' AND source='kaggle'").fetchone()
print(f"BTC/USD Baseline (kaggle):     {r_btc_base[0]:,} candles | Range: {r_btc_base[1]} -> {r_btc_base[2]}")

# Live count
r_btc_live = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='BTC/USD' AND timeframe='5m' AND source='binance_live'").fetchone()
print(f"BTC/USD Live (binance_live):   {r_btc_live[0]:,} candles | Range: {r_btc_live[1]} -> {r_btc_live[2]}")

# Total BTC 5m
r_btc_tot = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='BTC/USD' AND timeframe='5m'").fetchone()
print(f"BTC/USD Total 5m:              {r_btc_tot[0]:,} candles | Range: {r_btc_tot[1]} -> {r_btc_tot[2]}")

print("\n" + "=" * 75)
print("2. XAU/USD 5m CANDLE AUDIT")
print("=" * 75)

# Baseline count
r_xau_base = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='XAU/USD' AND timeframe='5m' AND source='kaggle'").fetchone()
print(f"XAU/USD Baseline (kaggle):     {r_xau_base[0]:,} candles | Range: {r_xau_base[1]} -> {r_xau_base[2]}")

# Live count
r_xau_live = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='XAU/USD' AND timeframe='5m' AND source='yahoo_live'").fetchone()
print(f"XAU/USD Live (yahoo_live):     {r_xau_live[0]:,} candles | Range: {r_xau_live[1]} -> {r_xau_live[2]}")

# Total XAU 5m
r_xau_tot = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='XAU/USD' AND timeframe='5m'").fetchone()
print(f"XAU/USD Total 5m:              {r_xau_tot[0]:,} candles | Range: {r_xau_tot[1]} -> {r_xau_tot[2]}")

print("\n" + "=" * 75)
print("3. PRIMARY KEY DUPLICATE INTEGRITY CHECK")
print("=" * 75)
# Count distinct vs total
for sym in ["BTC/USD", "XAU/USD"]:
    tot = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", (sym,)).fetchone()[0]
    distinct = conn.execute("SELECT COUNT(DISTINCT epoch_ms || '_' || timeframe) FROM candles WHERE symbol=?", (sym,)).fetchone()[0]
    print(f"{sym}: Total rows = {tot:,} | Distinct (epoch_ms + timeframe) = {distinct:,} | Duplicates = {tot - distinct}")

print("\n" + "=" * 75)
print("4. LIVE INGESTION STATUS TABLE (IN DB)")
print("=" * 75)
cur = conn.execute("SELECT * FROM live_ingestion_status")
for row in cur.fetchall():
    print(json.dumps(dict(row), indent=2))

print("\n" + "=" * 75)
print("5. BASELINE IMMUTABILITY SAMPLE AUDIT")
print("=" * 75)
for sym in ["BTC/USD", "XAU/USD"]:
    print(f"\n--- {sym} 5m Baseline First 2 & Last 2 (Immutable kaggle rows) ---")
    cur = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol=? AND timeframe='5m' AND source='kaggle' ORDER BY epoch_ms ASC LIMIT 2", (sym,))
    for r in cur.fetchall():
        print(f"  First: {dict(r)}")
    cur = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol=? AND timeframe='5m' AND source='kaggle' ORDER BY epoch_ms DESC LIMIT 2", (sym,))
    for r in cur.fetchall():
        print(f"  Last:  {dict(r)}")

conn.close()

print("\n" + "=" * 75)
print("6. LIVE API ENDPOINT RESPONSES & TIMING")
print("=" * 75)
endpoints = [
    "http://127.0.0.1:8000/api/v1/backtest/ingestion/status",
    "http://127.0.0.1:8000/api/v1/backtest/datasets/status",
    "http://127.0.0.1:8000/api/v1/backtest/datasets/live-status",
]
for ep in endpoints:
    t0 = time.perf_counter()
    try:
        resp = requests.get(ep, timeout=10)
        ms = (time.perf_counter() - t0) * 1000
        print(f"\n---> {ep} ({resp.status_code} in {ms:.2f} ms):")
        print(json.dumps(resp.json(), indent=2))
    except Exception as exc:
        print(f"Error fetching {ep}: {exc}")
