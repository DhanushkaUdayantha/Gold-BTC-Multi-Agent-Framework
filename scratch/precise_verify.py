"""
Precise verification script with correct source names.
"""
import sqlite3
import time
import requests
import json

DB_PATH = "data/historical/historical_market_data.db"
conn = sqlite3.connect(DB_PATH, timeout=30.0)
conn.row_factory = sqlite3.Row

print("=" * 80)
print("1. CANDLE COUNT BREAKDOWN BY SYMBOL, TIMEFRAME & SOURCE")
print("=" * 80)

# Query indexed combinations directly
queries = [
    ("BTC/USD", "5m", "binance"),
    ("BTC/USD", "5m", "binance_live"),
    ("BTC/USD", "15m", "binance"),
    ("XAU/USD", "5m", "yahoo"),
    ("XAU/USD", "5m", "yahoo_live"),
    ("XAU/USD", "15m", "yahoo"),
]

for sym, tf, src in queries:
    row = conn.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe=? AND source=?",
        (sym, tf, src)
    ).fetchone()
    print(f"{sym:<10} {tf:<5} {src:<15} : {row[0]:>10,} candles  [{row[1]}  -->  {row[2]}]")

print("\n" + "=" * 80)
print("2. TOTALS PER SYMBOL & TIMEFRAME")
print("=" * 80)
for sym in ["BTC/USD", "XAU/USD"]:
    for tf in ["5m", "15m"]:
        row = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe=?",
            (sym, tf)
        ).fetchone()
        print(f"{sym:<10} {tf:<5} TOTAL            : {row[0]:>10,} candles  [{row[1]}  -->  {row[2]}]")

print("\n" + "=" * 80)
print("3. LIVE INGESTION STATUS TABLE (IN DB)")
print("=" * 80)
cur = conn.execute("SELECT * FROM live_ingestion_status")
for row in cur.fetchall():
    print(json.dumps(dict(row), indent=2))

print("\n" + "=" * 80)
print("4. IMMUTABLE BASELINE AUDIT SAMPLES (Earliest & Latest Baseline Candles)")
print("=" * 80)
for sym, tf, src in [("BTC/USD", "5m", "binance"), ("XAU/USD", "5m", "yahoo")]:
    print(f"\n--- {sym} {tf} Baseline ({src}) ---")
    c1 = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol=? AND timeframe=? AND source=? ORDER BY epoch_ms ASC LIMIT 2", (sym, tf, src)).fetchall()
    for r in c1:
        print(f"  Earliest: {dict(r)}")
    c2 = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol=? AND timeframe=? AND source=? ORDER BY epoch_ms DESC LIMIT 2", (sym, tf, src)).fetchall()
    for r in c2:
        print(f"  Latest:   {dict(r)}")

# Also show first 2 and last 2 of live candles for BTC/USD
print("\n--- BTC/USD 5m Live Extended (binance_live) ---")
c_live_first = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol='BTC/USD' AND timeframe='5m' AND source='binance_live' ORDER BY epoch_ms ASC LIMIT 2").fetchall()
for r in c_live_first:
    print(f"  Live First: {dict(r)}")
c_live_last = conn.execute("SELECT epoch_ms, timestamp, open, high, low, close, volume, source FROM candles WHERE symbol='BTC/USD' AND timeframe='5m' AND source='binance_live' ORDER BY epoch_ms DESC LIMIT 2").fetchall()
for r in c_live_last:
    print(f"  Live Latest: {dict(r)}")

conn.close()

print("\n" + "=" * 80)
print("5. LIVE API ENDPOINT VERIFICATION")
print("=" * 80)
endpoints = [
    "http://127.0.0.1:8000/api/v1/backtest/ingestion/status",
    "http://127.0.0.1:8000/api/v1/backtest/datasets/status",
    "http://127.0.0.1:8000/api/v1/backtest/datasets/live-status",
]
for ep in endpoints:
    t0 = time.perf_counter()
    resp = requests.get(ep, timeout=10)
    lat = (time.perf_counter() - t0) * 1000
    print(f"\n---> {ep} ({resp.status_code} in {lat:.1f}ms):")
    print(json.dumps(resp.json(), indent=2))
