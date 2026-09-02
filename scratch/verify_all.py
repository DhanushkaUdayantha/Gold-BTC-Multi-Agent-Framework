import requests
import sqlite3
import json
import sys

def verify():
    print("=== 1. HEALTH CHECK ===")
    try:
        h = requests.get("http://127.0.0.1:8000/health", timeout=5).json()
        print("Health Status:", h.get("status"), "| App:", h.get("app"), "| Feed:", h.get("feed"))
    except Exception as e:
        print("Health error:", e)

    print("\n=== 2. PRODUCTION DECISION API ===")
    try:
        dec_xau = requests.get("http://127.0.0.1:8000/api/v1/decision?symbol=XAU-USD-SPOT", timeout=10).json()
        print("XAU Decision:", dec_xau.get("decision"), "| Confidence:", dec_xau.get("confidence"), "| Confluence:", dec_xau.get("confluence_pct"))
        dec_btc = requests.get("http://127.0.0.1:8000/api/v1/decision?symbol=BTC-USD", timeout=10).json()
        print("BTC Decision:", dec_btc.get("decision"), "| Confidence:", dec_btc.get("confidence"), "| Confluence:", dec_btc.get("confluence_pct"))
    except Exception as e:
        print("Decision error:", e)

    print("\n=== 3. ML SHADOW STATUS API ===")
    try:
        status = requests.get("http://127.0.0.1:8000/api/v1/ml/shadow/status", timeout=5).json()
        print("Shadow Mode:", status.get("mode"))
        print("Production Influence:", status.get("production_influence"))
        print("BTC Model:", status.get("models", {}).get("BTC/USD"))
        print("XAU Model:", status.get("models", {}).get("XAU/USD"))
    except Exception as e:
        print("Shadow status error:", e)

    print("\n=== 4. ML SHADOW METRICS API ===")
    try:
        m_btc = requests.get("http://127.0.0.1:8000/api/v1/ml/shadow/metrics?symbol=BTC/USD", timeout=5).json()
        print("BTC Metrics:", m_btc.get("symbol"), "| Total Obs:", m_btc.get("total_observations"), "| Milestone:", m_btc.get("milestone_reached"))
        m_xau = requests.get("http://127.0.0.1:8000/api/v1/ml/shadow/metrics?symbol=XAU/USD", timeout=5).json()
        print("XAU Metrics:", m_xau.get("symbol"), "| Total Obs:", m_xau.get("total_observations"), "| Milestone:", m_xau.get("milestone_reached"))
    except Exception as e:
        print("Shadow metrics error:", e)

    print("\n=== 5. ML SHADOW OBSERVATIONS API ===")
    try:
        obs = requests.get("http://127.0.0.1:8000/api/v1/ml/shadow/observations?limit=5", timeout=5).json()
        print("Recent Observations Returned:", len(obs))
        if obs:
            last = obs[-1]
            print(f"Latest Obs: id={last.get('observation_id')}, symbol={last.get('symbol')}, prob={last.get('ml_probability')}, pred={last.get('ml_predicted_class')}")
    except Exception as e:
        print("Shadow observations error:", e)

    print("\n=== 6. LIVE MARKET FEED CHECK ===")
    try:
        p_xau = requests.get("http://127.0.0.1:8000/api/v1/market/price?symbol=XAU-USD-SPOT", timeout=5).json()
        print("XAU Spot Price:", p_xau.get("price"), "| Provider:", p_xau.get("provider"), "| Time:", p_xau.get("timestamp"))
        p_btc = requests.get("http://127.0.0.1:8000/api/v1/market/price?symbol=BTC-USD", timeout=5).json()
        print("BTC Spot Price:", p_btc.get("price"), "| Provider:", p_btc.get("provider"), "| Time:", p_btc.get("timestamp"))

        c_xau = requests.get("http://127.0.0.1:8000/api/v1/market/candles?symbol=XAU-USD-SPOT&timeframe=5m&limit=5", timeout=5).json()
        print("XAU Candles Count:", len(c_xau.get("candles", [])), "| Provider:", c_xau.get("provider"))
        c_btc = requests.get("http://127.0.0.1:8000/api/v1/market/candles?symbol=BTC-USD&timeframe=5m&limit=5", timeout=5).json()
        print("BTC Candles Count:", len(c_btc.get("candles", [])), "| Provider:", c_btc.get("provider"))
    except Exception as e:
        print("Market feed error:", e)

    print("\n=== 7. HISTORICAL DATABASE & TABLES ===")
    try:
        conn = sqlite3.connect("data/historical/historical_market_data.db")
        cursor = conn.cursor()
        tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("SQLite Database Tables:", tables)
        for t in ["market_candles", "ml_shadow_observations", "strategy_backtest_runs"]:
            if t in tables:
                count = cursor.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                print(f" - Table '{t}': {count} rows")
        conn.close()
    except Exception as e:
        print("DB error:", e)

if __name__ == "__main__":
    verify()
