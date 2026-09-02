"""
Analyze features and market condition distributions in historical_signals.
"""
import sqlite3
import json
import collections

conn = sqlite3.connect("data/historical/historical_market_data.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

for sym in ["BTC/USD", "XAU/USD"]:
    print(f"\n=================== {sym} ===================")
    cur.execute("SELECT * FROM historical_signals WHERE symbol = ? ORDER BY signal_timestamp ASC", (sym,))
    rows = cur.fetchall()
    print(f"Total rows: {len(rows)}")

    regimes = collections.Counter(r["market_regime"] for r in rows)
    sessions = collections.Counter(r["session"] for r in rows)
    directions = collections.Counter(r["direction"] for r in rows)
    outcomes = collections.Counter(r["outcome"] for r in rows)

    print("Regimes:", regimes)
    print("Sessions:", sessions)
    print("Directions:", directions)
    print("Outcomes:", outcomes)

    # Inspect contributor directions
    htf_dirs = collections.Counter()
    ms_dirs = collections.Counter()
    mom_dirs = collections.Counter()
    sr_dirs = collections.Counter()
    smc_dirs = collections.Counter()
    ote_dirs = collections.Counter()
    vwap_dirs = collections.Counter()
    ema_dirs = collections.Counter()

    for r in rows:
        c_dirs = json.loads(r["contributor_directions_json"]) if r["contributor_directions_json"] else {}
        htf_dirs[c_dirs.get("HTF Trend", "NONE")] += 1
        ms_dirs[c_dirs.get("Market Structure", "NONE")] += 1
        mom_dirs[c_dirs.get("Momentum", "NONE")] += 1
        sr_dirs[c_dirs.get("S/R Price Action", "NONE")] += 1
        smc_dirs[c_dirs.get("SMC / ICT", "NONE")] += 1
        ote_dirs[c_dirs.get("Fibonacci OTE", "NONE")] += 1
        vwap_dirs[c_dirs.get("VWAP", "NONE")] += 1
        ema_dirs[c_dirs.get("EMA / MA Stack", "NONE")] += 1

    print("HTF Trend Directions:", htf_dirs)
    print("Market Structure Directions:", ms_dirs)
    print("Momentum Directions:", mom_dirs)
    print("S/R Price Action Directions:", sr_dirs)
    print("SMC/ICT Directions:", smc_dirs)
    print("Fibonacci OTE Directions:", ote_dirs)
    print("VWAP Directions:", vwap_dirs)
    print("EMA Stack Directions:", ema_dirs)

conn.close()
