# 🌟 BTC & Gold (BTC/USD & XAU/USD) AI Trading Analysis Platform

A quantitative multi-timeframe market data analysis, technical indicators engine, and market structure advisory system for **Bitcoin (`BTC/USD`)** and **Gold (`XAU/USD`)**.

> [!IMPORTANT]
> **Safety Notice**: This system is designed **strictly for market analysis, quantitative technical calculations, historical backtesting, and AI market condition classification (BULLISH / BEARISH / NEUTRAL)**. It does not place real orders, execute live trades, connect to brokerage accounts, or promise guaranteed profits. All historical performance metrics reflect gross backtested results (frictionless) on the available dataset.

---

## 📌 Complete Architecture

```
                          ┌────────────────────────┐
                          │   FastAPI REST API     │
                          │   (src/api/main.py)    │
                          └──────────┬─────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
      ┌──────────▼─────────────┐     │       ┌───────────▼────────────┐
      │   MarketDataService    │     │       │TechnicalAnalysisService│
      │(src/services/market...)│     │       │(src/services/techni...)│
      └──────────┬─────────────┘     │       └───────────┬────────────┘
                 │                   │                   │
        ┌────────┴────────┐          │          ┌────────┴────────┐
        │                 │          │          │                 │
┌───────▼────────┐ ┌──────▼────────┐ │   ┌──────▼────────┐ ┌──────▼────────┐
│  Binance API   │ │ GoldPriceDev  │ │   │TechnicalEngine│ │  SMC / OTE    │
│  (BTC Feeds)   │ │& Yahoo (XAU)  │ │   │ (Indicators)  │ │  (Structure)  │
└────────────────┘ └───────────────┘ │   └───────┬───────┘ └──────┬────────┘
                                     │           │                │
                          ┌──────────▼───────────┴────────────────▼┐
                          │         ConfluenceEngine (100 Pts)     │
                          │ 16 Technical Factors (90 Pts Max)      │
                          │ + 1 Gemini AI Factor (10 Pts Max)      │
                          └───────────────────┬────────────────────┘
                                              │
                                   ┌──────────▼─────────────┐
                                   │     DecisionEngine     │
                                   │ Empirical Quality Gates│
                                   │ (BTC & XAU Separation) │
                                   └──────────┬─────────────┘
                                              │
                          ┌───────────────────┴───────────────────┐
                          │                                       │
               ┌──────────▼─────────────┐             ┌───────────▼────────────┐
               │    GeminiAIProvider    │             │   Historical Evidence  │
               │(Google Gemini 3.5 Flash│             │ & Backtest Database    │
               │  Structured Context)   │             │ (2,438 Resolved Setups)│
               └────────────────────────┘             └────────────────────────┘
```

---

## 📁 Project Structure

```
d:\Project\TRADE\
├── .env                          # Local environment settings & API keys
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore configuration
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Project dependencies
├── README.md                     # Complete project documentation
├── SCORE_AND_CLAIMS_AUDIT.md     # Forensic scoring & claims audit report
│
├── config/
│   ├── __init__.py
│   └── settings.py               # Pydantic-based configuration management
│
├── data/
│   └── historical/
│       └── historical_market_data.db # SQLite database (2,438 resolved signals)
│
├── src/
│   ├── __init__.py
│   ├── models/                   # Pydantic data schemas (Market, TA, Decision, Historical)
│   ├── services/                 # Core engines: Confluence, Decision, Technical, SMC, OTE, AI
│   └── api/                      # FastAPI routes (/decision, /technical, /market, /backtest)
│
├── frontend/                     # Next.js 14 Web Dashboard (App Router, Tailwind, Heroes)
└── tests/                        # 512 passing automated pytest tests
```

---

## ⚙️ Confluence Scoring System (100 Points Model)

The central scoring engine evaluates **17 contributors** with point-in-time synchronization:

* **16 Technical & Structural Contributors**: Maximum **90 Points**
  * HTF Trend (11), Market Structure (9), Momentum (8), MTF Alignment (8), S/R Price Action (8)
  * Breakout / Retest (6), Supply & Demand (5), Volume Confirmation (5), SMC / ICT (5)
  * ICT Concepts (4), Fibonacci OTE (4), Elliott Wave (4), VWAP (4), EMA Stack (4)
  * RSI Momentum (3), MACD Dynamics (2)
* **1 Gemini AI Contributor**: Maximum **10 Points**
  * Evaluates multi-timeframe context and historical setup evidence.
* **Total Maximum Confluence Score**: **100 Points** (`technical_score (90) + gemini_score (10) = 100`)

---

## 🚀 Running the Project

### 1. Run Automated Unit Tests (512 tests, 100% pass rate)
```bash
.venv\Scripts\pytest tests/ -v
```

### 2. Start the Backend API Server
```bash
uvicorn src.api.main:app --reload --port 8000
```
Interactive Swagger API documentation: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

### 3. Start the Next.js Frontend Dashboard
```bash
cd frontend
npm run dev
```
Access the dashboard at: **[http://localhost:3000](http://localhost:3000)**

---

## 📊 Empirical Signal Quality Gates

To eliminate low-expectancy trade setups and minimize drawdowns, production decisions are filtered by validated empirical quality gates:

1. **Bitcoin (BTC)**:
   * Confluence Score $\ge 58\%$
   * Multi-timeframe trend alignment required
   * Unconfirmed Asia session BUYs gated to `WAIT`
2. **Gold (XAU)**:
   * Confluence Score $\ge 58\%$
   * Multi-timeframe trend alignment required
   * VWAP directional alignment required

*Note: All quality gates act strictly as protective filters; they can allow an existing setup or gate it to `WAIT`, but will never invert trade direction.*
