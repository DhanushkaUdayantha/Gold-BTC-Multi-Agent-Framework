"""
Inspect database schema, columns, and available signal features in historical_market_data.db.
"""
import sqlite3
import json

def inspect():
    conn = sqlite3.connect("data/historical/historical_market_data.db")
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables:", [t[0] for t in tables])

    for t in tables:
        t_name = t[0]
        cur.execute(f"PRAGMA table_info({t_name})")
        cols = cur.fetchall()
        print(f"\nColumns for table '{t_name}':")
        for c in cols:
            print(f"  {c[1]} ({c[2]})")

    # Sample rows from historical_signals
    cur.execute("SELECT * FROM historical_signals LIMIT 3")
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print("\nSample historical_signals records:")
    for i, row in enumerate(rows):
        print(f"\n--- Record {i+1} ---")
        for k, v in zip(col_names, row):
            print(f"  {k}: {v}")

    # Check distinct values of market_regime, direction, outcome, etc.
    cur.execute("SELECT DISTINCT market_regime FROM historical_signals")
    print("\nDistinct market_regime values:", [r[0] for r in cur.fetchall()])

    cur.execute("SELECT DISTINCT direction FROM historical_signals")
    print("Distinct direction values:", [r[0] for r in cur.fetchall()])

    cur.execute("SELECT DISTINCT outcome FROM historical_signals")
    print("Distinct outcome values:", [r[0] for r in cur.fetchall()])

    # Check if there are other signal tables or breakdown tables
    cur.execute("SELECT COUNT(*) FROM historical_signals WHERE symbol LIKE '%BTC%'")
    print("BTC signals count:", cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM historical_signals WHERE symbol LIKE '%XAU%'")
    print("XAU signals count:", cur.fetchone()[0])

    conn.close()

if __name__ == "__main__":
    inspect()
