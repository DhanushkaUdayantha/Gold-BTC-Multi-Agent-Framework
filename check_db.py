"""Quick DB inspection script."""
import sqlite3

conn = sqlite3.connect('data/historical/historical_market_data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("TABLES:", tables)

# Candles data
for sym in ['BTC/USD', 'XAU/USD']:
    for tf in ['15m', '1h', '5m', '4h', '1d']:
        cur.execute('SELECT COUNT(*) as cnt FROM candles WHERE symbol=? AND timeframe=?', (sym, tf))
        cnt = cur.fetchone()['cnt']
        if cnt > 0:
            cur.execute('SELECT MIN(timestamp) as mn, MAX(timestamp) as mx FROM candles WHERE symbol=? AND timeframe=?', (sym, tf))
            row = cur.fetchone()
            print(f'{sym} {tf}: {cnt} candles [{row["mn"][:10]} -> {row["mx"][:10]}]')

# Historical signals
cur.execute('SELECT symbol, direction, outcome, COUNT(*) as cnt FROM historical_signals GROUP BY symbol, direction, outcome')
rows = cur.fetchall()
print('SIGNALS BY OUTCOME:')
for r in rows:
    print(f'  {r["symbol"]} {r["direction"]} {r["outcome"]}: {r["cnt"]}')

# Datasets
cur.execute('SELECT dataset_id, symbol, row_count, valid_rows FROM datasets')
rows = cur.fetchall()
print('DATASETS:')
for r in rows:
    print(f'  {r["dataset_id"]}: {r["symbol"]} rows={r["row_count"]} valid={r["valid_rows"]}')

# Backtest runs
cur.execute('SELECT run_id, symbol, status, total_trades_generated FROM backtest_runs ORDER BY created_at DESC LIMIT 10')
rows = cur.fetchall()
print('BACKTEST RUNS:')
for r in rows:
    print(f'  {r["run_id"]}: {r["symbol"]} {r["status"]} trades={r["total_trades_generated"]}')

conn.close()
print("DONE")
