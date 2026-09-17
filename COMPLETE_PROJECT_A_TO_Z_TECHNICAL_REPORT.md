# BTC/XAU AI Trading Analysis Platform

## Complete A–Z Technical Report & System Architecture Specification



**Document ID:** `TRADE-TECH-AZ-20260916`  

**Date:** September 16, 2026  

**Repository:** `D:\Project\TRADE`  

**Execution Environment:** Windows Server / Python 3.14.7 / Next.js 14.2.4  

**Classification:** Institutional Technical Architecture, Forensic Audit, and Operating Manual  



---



## 1. PROJECT INTRODUCTION & PURPOSE



### Project Purpose

The **BTC/XAU AI Trading Analysis Platform** is an institutional-style, multi-engine algorithmic market intelligence system engineered for two primary global benchmark assets:

1. **Bitcoin (BTC/USD)**: High-volatility continuous crypto-asset benchmark.

2. **Gold (XAU/USD / Spot Gold)**: Macro-sensitive continuous precious metal benchmark.



The platform continuously evaluates live streaming market feeds, performs multi-timeframe structural and quantitative technical analysis, queries large-scale empirical historical databases, executes forward out-of-sample Machine Learning inference, and queries Google Gemini generative AI for qualitative market condition synthesis.



### What BUY / SELL / WAIT Means

- **`BUY`**: Strict, positive directional edge confirmed across all quantitative, structural, and AI filters, with risk/reward ratio to Target 1 $\ge 1.60	ext{R}$ and Target 2 $\ge 2.80	ext{R}$, supported by verified market structure and passing all three safety gates.

- **`SELL`**: Strict, negative (short) directional edge confirmed across all quantitative, structural, and AI filters, with risk/reward ratio to Target 1 $\ge 1.60	ext{R}$ and Target 2 $\ge 2.80	ext{R}$, passing all three safety gates.

- **`WAIT`**: The authoritative baseline and default capital-preservation state. `WAIT` indicates that directional edge is insufficient, conflicting cross-currents exist, or the setup fails to meet the strict quality threshold ($	ext{Confluence} < 58	ext{ pts}$). **`WAIT` is never a failure; it is an active risk-management command to preserve capital.**



### Operating Modes

- **Advisory / Research Mode**: The primary operating mode of the system. Generates real-time, explainable, and auditable signals with complete mathematical attribution.

- **Demo Trading Mode**: A self-contained simulation ledger allowing users to test trade execution against live market quotes without risking real capital or altering quantitative logic.

- **ML Shadow Validation Mode**: Non-blocking, forward out-of-sample evaluation where ML models record point-in-time predictions at candle close ($T_0$) and resolve them only as future candles close.

- **Strategy Governance Mode**: Forward paper trade evidence accumulation tracking out-of-sample sample size ($N \ge 50, N \ge 100$) before any production deployment can be considered.

- **Live Broker Execution**: **STRICTLY DISABLED**. Live broker APIs and automated trade routing are disabled in code and configuration (`LIVE_EXECUTION_ENABLED = False`).



---



## 2. EXECUTIVE SUMMARY



The platform is designed around the core principle that **no single indicator, model, or neural network can sustainably extract alpha from financial markets**. Instead, the platform implements a **multi-engine evidence synthesis architecture**:



```text

Live Market Data (Binance & GoldPrice.dev)

                 +

Multi-Timeframe Technical Indicators (EMA, RSI, MACD, ATR, VWAP)

                 +

Market Structure & Smart Money Concepts (BOS, CHoCH, Liquidity Sweeps, OTE)

                 +

17 Independent Contributor Scoring Models (Max 100 Pts)

                 +

Google Gemini Generative AI Confirmation (Max 10 Pts)

                 +

Triple Risk Gates (Direction, Conflict, Quality)

                 +

Empirical Historical Backtest Matching (2,438 Historical Signals)

                 +

Forward Out-of-Sample ML Inference (Calibrated Scikit-Learn Models)

                 +

Shadow Resolution & Forward Governance Tracking (N=50 Milestone)

                 ↓

      AUTHORITATIVE DECISION: BUY / SELL / WAIT

```



Every trading recommendation is fully attributed, mathematically bounded, and auditable through an end-to-end data lineage that connects raw tick inputs to the five Next.js frontend pages.



---



## 3. THE MASTER ARCHITECTURE FLOW GRAPH



Below is the complete, single end-to-end architecture flow graph illustrating the entire system from raw external market feeds to the five user-facing pages:



```text

========================================================================================================================

                                     BTC/XAU AI TRADING ANALYSIS PLATFORM

                                 COMPLETE END-TO-END MASTER ARCHITECTURE GRAPH

========================================================================================================================



 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                              EXTERNAL DATA SOURCES                                               │

 │                                                                                                                  │

 │        [BTC/USD Feeds]                                                   [XAU/USD Feeds]                         │

 │        - Primary: Binance Public API                                     - Primary: GoldPrice.dev API            │

 │          (api.binance.com/api/v3/ticker/24hr, /klines)                     (api.goldprice.dev/v1/gold-price)     │

 │        - Secondary/Fallback: Yahoo Finance (BTC-USD)                     - Secondary/Fallback: Yahoo (GC=F)      │

 └────────────────────────────────────────┬─────────────────────────────────────────┬───────────────────────────────┘

                                          │                                         │

                                          ▼                                         ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                   BACKEND INGESTION & DATA SERVICES LAYER                                        │

 │                                                                                                                  │

 │   - MarketDataService (`src/services/market_service.py`): Ingestion, 429 backoff, fallback failover             │

 │   - LiveCandleIngestionService (`src/services/live_candle_ingestion_service.py`): Incremental SQLite candle save│

 │   - Symbol Normalizer: `BTCUSDT`, `BTC-USD`, `BTC/USD` -> `BTC/USD` | `XAUUSD`, `XAU-USD-SPOT` -> `XAU-USD-SPOT` │

 │   - Strict Closed-Bar Boundary: Evaluates ONLY completed bars (5m, 15m, 1h, 1d); zero lookahead into open bar    │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                      TECHNICAL ANALYSIS & STRUCTURE ENGINES                                      │

 │                                                                                                                  │

 │   1. TechnicalAnalysisService (`src/services/technical_analysis.py`):                                            │

 │      - Trend Indicators: EMA20, EMA50, EMA200, EMA Stack Bias                                                    │

 │      - Oscillators: RSI(14) with overbought/oversold bands, MACD (12, 26, 9) line & histogram                   │

 │      - Volatility & Benchmark: ATR(14) for volatility stops/targets, Volume vs 20-period moving average          │

 │      - S/R Pivot Detector: Swing highs/lows over rolling N-bar pivot windows                                     │

 │   2. OTE & Smart Money Concepts Engine (`src/services/ote_engine.py`):                                           │

 │      - Market Structure: Higher Highs, Higher Lows, Lower Highs, Lower Lows, BOS, CHoCH / MSS                   │

 │      - ICT / SMC Liquidity: Previous Day High/Low (PDH/PDL) sweeps, Fair Value Gaps (FVG), Order Blocks         │

 │      - Fibonacci OTE: Optimal Trade Entry calculation (0.618 - 0.786 retracement range)                          │

 │   3. Elliott Wave Service (`src/services/elliott_wave_service.py`):                                              │

 │      - Heuristic wave identification (Impulse 1-2-3-4-5 vs Corrective A-B-C phases)                              │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                         THE 17-CONTRIBUTOR SCORING MATRIX                                        │

 │                                      (`src/services/confluence_engine.py`)                                       │

 │                                                                                                                  │

 │   [TECHNICAL & STRUCTURAL FACTORS: Max 90 Pts]                  [AI CONFIRMATION FACTOR: Max 10 Pts]             │

 │   1. HTF Trend (1H/1D)         : 11 pts                         17. Google Gemini AI Analysis : 10 pts           │

 │   2. Market Structure (BOS/MSS):  9 pts                             (`src/services/ai/gemini_provider.py`)       │

 │   3. Momentum (5m MACD/Trend)  :  8 pts                             - Model: `gemini-3.1-flash-lite`             │

 │   4. MTF Alignment (5m-1h)     :  8 pts                             - Output: Bias, Score, Key Levels, Risk      │

 │   5. S/R Price Action Proximity:  8 pts                             - Safety Cap: Strictly <= 10.0 pts           │

 │   6. Breakout / Retest         :  6 pts                             - Fallback: `FallbackAIProvider` (amber)     │

 │   7. Supply & Demand Zones     :  5 pts                                                                          │

 │   8. Volume Confirmation       :  5 pts                                                                          │

 │   9. SMC / ICT Liquidity Sweep :  5 pts                                                                          │

 │  10. ICT Concepts (PDH/PDL)    :  4 pts                                                                          │

 │  11. Fibonacci OTE (0.618-786) :  4 pts                                                                          │

 │  12. Elliott Wave Phase        :  4 pts                                                                          │

 │  13. VWAP Benchmark Alignment  :  4 pts                                                                          │

 │  14. EMA / MA Moving Stack     :  4 pts                                                                          │

 │  15. RSI Oscillator State      :  3 pts                                                                          │

 │  16. MACD Oscillator State     :  2 pts                                                                          │

 │                                                                                                                  │

 │   TOTAL CONFLUENCE SCORE = Sum of All Active Factors [0 -> 100 Pts]                                              │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                       DECISION ENGINE & TRIPLE RISK GATES                                        │

 │                                      (`src/services/decision_engine.py`)                                         │

 │                                                                                                                  │

 │   Candidate Signal Direction: Net Score = Bullish Points - Bearish Points                                        │

 │                                                                                                                  │

 │   Gate 1: DIRECTION GATE                                                                                         │

 │           Requires >= 2 of 3 core gate contributors to agree (pure consensus — no net-score threshold)           │

 │           Core Gate Contributors: {HTF Trend, Market Structure, MTF Alignment}                                   │

 │           -> FAILS? Mandates WAIT                                                                                │

 │                                                                                                                  │

 │   Gate 2: CONFLICT GATE                                                                                          │

 │           Requires Opposing Contributor Weight <= 25.0%                                                          │

 │           -> FAILS? Mandates WAIT                                                                                │

 │                                                                                                                  │

 │   Gate 3: QUALITY GATE                                                                                           │

 │           Requires Confluence Score >= 58.0 pts                                                                  │

 │           -> FAILS? Mandates WAIT (Regardless of Bullish/Bearish Net Score magnitude)                            │

 │                                                                                                                  │

 │   OUTPUT ACTION:                                                                                                 │

 │   - If All 3 Gates PASS: Action = BUY or SELL; Setup Grade = A/A+; Position Size = 0.10                          │

 │   - If Any Gate FAILS  : Action = WAIT; Trade levels neutralized; Directional bias preserved as evidence only    │

 └────────────────────────────┬───────────────────────────────────────────────────────┬─────────────────────────────┘

                              │                                                       │

                              ▼                                                       ▼

 ┌────────────────────────────────────────────────────────┐ ┌───────────────────────────────────────────────────────┐

 │               TRADE SETUP LEVEL GENERATOR              │ │            DOWNSTREAM RESEARCH & SHADOW LAYERS        │

 │           (`src/services/decision_engine.py`)          │ │                                                       │

 │                                                        │ │   1. Historical Evidence Engine                       │

 │   If Action == BUY:                                    │ │      (`src/services/historical_evidence_service.py`)  │

 │     - Entry Zone = [Price - 0.35*ATR, Price]           │ │      - Database: `historical_market_data.db`          │

 │     - Stop Loss  = Price - 1.50*ATR                    │ │      - Block A: Current Setup Pattern Match (N=0)     │

 │     - TP1 Target = Price + 2.40*ATR (1.60 R:R)         │ │      - Block B: Global Baseline (N=1519 BTC, 919 XAU) │

 │     - TP2 Target = Price + 4.20*ATR (2.80 R:R)         │ │                                                       │

 │                                                        │ │   2. ML Shadow Validation Engine                      │

 │   If Action == SELL:                                   │ │      (`src/research/ml_shadow/shadow_service.py`)     │

 │     - Entry Zone = [Price, Price + 0.35*ATR]           │ │      - BTC Model: `LogisticRegression (Calibrated)`   │

 │     - Stop Loss  = Price + 1.50*ATR                    │ │      - XAU Model: `RandomForestClassifier (Calibrated)`│

 │     - TP1 Target = Price - 2.40*ATR (1.60 R:R)         │ │      - T0 Immutable Observation Snapshot (ID Hash)    │

 │     - TP2 Target = Price - 4.20*ATR (2.80 R:R)         │ │      - Forward resolution on closed candles (85 res)  │

 │                                                        │ │                                                       │

 │   If Action == WAIT:                                   │ │   3. Strategy Governance & Forward Tracker            │

 │     - Entry, Stop Loss, TP1, TP2 = None (`--`)         │ │      (`src/research/governance/forward_state_machine`)│

 │     - Eliminates misleading speculative targets        │ │      - Clean Forward Evidence: Clean N = 0 / 50       │

 │                                                        │ │      - Quarantined Fixtures: 280 BTC, 199 XAU         │

 └────────────────────────────┬───────────────────────────┘ └───────────────────────────┬─────────────────────────┘

                              │                                                       │

                              └───────────────────────────┬───────────────────────────┘

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                   MULTI-COMPONENT SIGNAL AGGREGATOR SERVICE                                      │

 │                                      (`src/services/signal_aggregator.py`)                                       │

 │                                                                                                                  │

 │   Synthesizes 4 System Components with Nominal Weights:                                                          │

 │   - Now Market Technical: BTC 25% | XAU 27%                                                                      │

 │   - Historical Evidence : BTC 27% | XAU 26%                                                                      │

 │   - ML Shadow Model     : BTC 26% | XAU 24%                                                                      │

 │   - Validated Strategy  : BTC 22% | XAU 23%                                                                      │

 │                                                                                                                  │

 │   Dynamic Component Re-normalization:                                                                            │

 │   Effective Weight_i = Nominal Weight_i / Sum(Available Nominal Weights)                                         │

 │   Net Aggregator Score = Sum(Effective Weight_i * Component Directional Value_i)                                 │

 │   -> Generates Authoritative `OverallTradingSignal` (Directional Evidence Bias: e.g. BUY 51% (where the 51% figure represents the Net Directional Score magnitude round(|net_score|), NOT a calibrated ML probability))                     │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                        FASTAPI APPLICATION HTTP REST TIER                                        │

 │                                             (`src/api/main.py`:8000)                                             │

 │                                                                                                                  │

 │   - GET `/api/v1/decision?symbol={sym}`               : Authoritative TradingDecision + OverallTradingSignal     │

 │   - GET `/api/v1/market/price`, `/candles`            : Live quotes and multi-timeframe OHLCV bars               │

 │   - GET `/api/v1/ml/shadow/observations?symbol={sym}` : Realtime ML observations & resolved shadow accuracy     │

 │   - GET `/api/v1/governance/forward-shadow`           : Forward governance tracking (Clean N vs Quarantined)     │

 │   - GET `/api/v1/backtest/reports`                    : Historical backtest run catalog & signal logs            │

 │   - GET `/api/v1/admin/gating/status`                 : Gating Invariants (Production Gating = DISABLED)         │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                                                          │ JSON over HTTP (Port 8000 / 3000)

                                                          │

                                                          ▼

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

 │                                         NEXT.JS FRONTEND ARCHITECTURE                                            │

 │                                      (`frontend/src/` Next.js 14.2.4)                                            │

 │                                                                                                                  │

 │   1. Central API Client (`src/services/api.ts`): Typed REST client, automatic retry, timeout protection          │

 │   2. State Hook (`src/hooks/useDashboardData.ts`):                                                               │

 │      - Unified polling interval: 10s price/decision, 30s ML/governance                                           │

 │      - Strict Asset Isolation: Switching BTC <-> XAU resets all buffers; zero cross-contamination                │

 │   3. Semantic Formatting Layer (`src/lib/format.ts`, `relativeTime.ts`):                                         │

 │      - Truthful null handling: Missing percentages render '--%', never fake 50% or 100%                          │

 │      - Relative time formatting: Anchored to backend candle timestamps, never wall-clock time                    │

 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘

                                                          │

                     ┌───────────────────┬────────────────┼───────────────────┬───────────────────┐

                     ▼                   ▼                ▼                   ▼                   ▼

 ┌───────────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐ ┌────────────────────────┐

 │        PAGE 1         │ │      PAGE 2      │ │      PAGE 3      │ │     PAGE 4      │ │         PAGE 5         │

 │        OVERALL        │ │  MARKET INSIGHT  │ │    NOW MARKET    │ │ HISTORY MARKET  │ │      ML & SHADOW       │

 │                       │ │                  │ │                  │ │                 │ │                        │

 │ - Hero Card:          │ │ - Conviction     │ │ - Confluence:    │ │ - Block A:      │ │ - Part A:              │

 │   `FINAL ACTION: WAIT`│ │   Ledger (4-Part)│ │   `46 pts`       │ │   Matched Setup │ │   Current ML Output    │

 │ - Evidence Pill:      │ │ - Dynamic Weights│ │ - 17 Contributor │ │   N = 0 (No     │ │   Win Prob: 42%        │

 │   `BUY · 51%`         │ │   (Nominal vs    │ │   Score Cards    │ │   Qualifying)   │ │ - Part B:              │

 │ - Action Levels:      │ │   Effective)     │ │ - MTF Gauges     │ │ - Block B:      │ │   ML Shadow Validation │

 │   Entry/SL/TP: `--`   │ │ - Gemini AI      │ │ - Technical      │ │   Global Baseline│ │   85 Resolved Trades   │

 │ - Risk & Gates Badge: │ │   Narrative      │ │   Indicators     │ │   N = 1,519     │ │   Accuracy: 52.9%      │

 │   `WAIT` (Quality Fail│ │ - Overall Metric:│ │ - Risk Gates:    │ │   Win Rate:41.7%│ │ - Part C:              │

 │ - Setup Matrix Table  │ │   `--` (No fake  │ │   Confluence 35  │ │ - Backtest Logs:│ │   Strategy Governance  │

 │ - Demo Trading Panel  │ │   percentage)    │ │   Quality FAIL   │ │   Signal ID Col │ │   Clean N = 0 / 50     │

 │                       │ │                  │ │                  │ │   Dedup Toggle  │ │   Gating: DISABLED     │

 └───────────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────────┘ └────────────────────────┘

========================================================================================================================

```



---



## 4. BACKEND TO FRONTEND CONNECTION: STEP-BY-STEP TRACE



The full data lineage between the market data boundary and the user interface comprises 13 distinct, traceable steps:



1. **Step 1 (External Ingestion)**: External APIs deliver raw pricing and bar data. Binance API provides BTC/USD klines, and GoldPrice.dev provides XAU/USD quotes.

2. **Step 2 (Backend Normalization)**: `MarketDataService` ([`src/services/market_service.py`](file:///d:/Project/TRADE/src/services/market_service.py)) standardizes symbols (`BTC/USD`, `XAU-USD-SPOT`), validates candle timestamps, and enforces the closed-bar boundary.

3. **Step 3 (Technical & Structural Analysis)**: `TechnicalAnalysisService` ([`src/services/technical_analysis.py`](file:///d:/Project/TRADE/src/services/technical_analysis.py)) and `OTEEngine` ([`src/services/ote_engine.py`](file:///d:/Project/TRADE/src/services/ote_engine.py)) compute mathematical indicators and structural markers across 5m, 15m, 1h, and 1d timeframes.

4. **Step 4 (17-Contributor Scoring)**: `ConfluenceEngine` ([`src/services/confluence_engine.py`](file:///d:/Project/TRADE/src/services/confluence_engine.py)) scores 16 quantitative/structural contributors (up to 90 points).

5. **Step 5 (AI Evidence Addition)**: `AIMarketAnalysisService` ([`src/services/ai_service.py`](file:///d:/Project/TRADE/src/services/ai_service.py)) invokes Gemini (`gemini-3.1-flash-lite`), bounded to a strict maximum of 10 points. Fallback provider activates deterministically if the network or API key is unavailable.

6. **Step 6 (Gate Enforcement & Decision)**: `DecisionEngine` ([`src/services/decision_engine.py`](file:///d:/Project/TRADE/src/services/decision_engine.py)) evaluates Direction Gate (>= 2 of 3 consensus among {HTF Trend, Market Structure, MTF Alignment} — no net-score threshold), Conflict Gate (Opposing Weight <= 25.0%), and Quality Gate (Confluence >= 58). Fails produce `WAIT`.

7. **Step 7 (Setup Level Generation)**: If gates pass, Entry, SL, TP1, and TP2 are computed using ATR multiples. If `WAIT`, trade levels are neutralized to `None` (`--`).

8. **Step 8 (Research Layer Evidence Generation)**: `HistoricalEvidenceService` queries empirical backtest similarity, `MLShadowService` locks a point-in-time $T_0$ observation, and `ForwardStateMachine` tracks forward paper trading samples.

9. **Step 9 (Multi-Component Aggregation)**: `SignalAggregator` ([`src/services/signal_aggregator.py`](file:///d:/Project/TRADE/src/services/signal_aggregator.py)) dynamically re-normalizes available components and derives the `OverallTradingSignal` (e.g., Overall Evidence Bias: BUY 51%).

10. **Step 10 (FastAPI Serialization)**: `src/api/main.py` serves typed JSON schemas across `/decision`, `/market`, `/ml/shadow`, `/governance`, and `/backtest` endpoints on port 8000.

11. **Step 11 (Next.js Client Fetch)**: `frontend/src/services/api.ts` and `useDashboardData.ts` fetch JSON payloads, managing failover and wiping state buffers on asset switches.

12. **Step 12 (Semantic Formatting)**: `format.ts` and `relativeTime.ts` validate nulls, ensuring missing percentages render `--` without synthetic fallbacks.

13. **Step 13 (Component Presentation)**: The five Next.js pages render different perspectives of the exact same authoritative backend pipeline.





---



## 5. TECHNOLOGY STACK



The platform utilizes a modern, typed, high-performance quantitative stack with strict separation of concerns between backend calculation and frontend visualization:



### Backend Stack

- **Language**: Python 3.14.7 (compatible with Python >= 3.10)

- **Web Framework**: FastAPI 0.115+ (ASGI, high-concurrency async endpoints)

- **ASGI Server**: Uvicorn (HTTP/1.1 and WebSockets support)

- **Data Validation & Schemas**: Pydantic v2 (strict type enforcement, JSON Schema generation)

- **Quantitative & Numerical Processing**:

  - `pandas` 2.2+: Time-series DataFrame transformations, rolling aggregations

  - `numpy` 2.0+: Vectorized linear algebra and candle math

  - `scipy` 1.13+: Statistical tests, probability distributions, bootstrap sampling

- **Machine Learning**:

  - `scikit-learn` 1.5+: Model training, Platt scaling calibration (`CalibratedClassifierCV`), feature preprocessing (`StandardScaler`, `SimpleImputer`)

  - `joblib`: High-efficiency artifact serialization

- **Database Engine**:

  - `sqlite3` (WAL mode enabled): Embedded ACID persistence for candle histories, backtest records, and ML shadow observations (`data/historical/historical_market_data.db`)

- **Testing Framework**:

  - `pytest` 9.1.1: Automated test runner with plugins (`anyio`, `pytest-mock`)



### Frontend Stack

- **Framework**: Next.js 14.2.4 (React 18 Server & Client Components, App Router architecture)

- **Language**: TypeScript 5.0+ (Strict type-checking, zero implicit any)

- **Styling**: Tailwind CSS 3.4.1 (Utility-first CSS, dark-mode financial terminal styling)

- **Visualizations**:

  - `recharts` 3.10.1: SVG financial gauges, radar charts, distribution histograms

  - Lightweight Charts (TradingView): Hardware-accelerated Canvas candlestick chart rendering

- **Iconography**: `lucide-react` 1.35.0



### AI & LLM Integration

- **LLM Provider**: Google Gemini API via HTTPS REST (`https://generativelanguage.googleapis.com/v1beta/models/...`)

- **Configured Model**: `gemini-3.1-flash-lite` (Fallback candidate models: `gemini-3.5-flash`, `gemini-3-flash-preview`)

- **Deterministic Fallback**: In-memory rule-based synthetic market sentiment analyzer (`FallbackAIProvider`)



---



## 6. PROJECT FOLDER ARCHITECTURE



```text

D:\Project\TRADE

│

├── config/                         # Central configuration and settings management

│   └── settings.py                 # Pydantic Settings reading environment variables (.env)

│

├── src/                            # Backend Core Source Code

│   ├── api/                        # FastAPI Web API Layer

│   │   ├── routes/                 # Modular endpoint routers (decision, market, ml_shadow, etc.)

│   │   ├── dependencies.py         # HTTP auth and dependency injection

│   │   └── main.py                 # FastAPI application factory and middleware configuration

│   │

│   ├── core/                       # Core Infrastructure & Security

│   │   ├── security.py             # Admin token verification and endpoint guards

│   │   └── rate_limiter.py         # In-memory sliding-window IP/endpoint rate limiting

│   │

│   ├── models/                     # Pydantic Domain Schemas

│   │   ├── market_data.py          # OHLCVCandle, PriceQuote, Timeframe definitions

│   │   ├── trading_decision.py     # TradingDecision, DecisionScoreBreakdown, OverallTradingSignal

│   │   ├── historical_data.py      # BacktestRun, HistoricalSignal, StrategyAnalytics

│   │   └── ai_analysis.py          # MultiTimeframeTechnicalInput, AIAnalysisResponse

│   │

│   ├── services/                   # Business Logic & Quantitative Engines

│   │   ├── market_service.py       # Unified Market Data Service (failover, backoff, caching)

│   │   ├── technical_analysis.py   # Multi-timeframe indicator calculations (EMA, RSI, MACD, ATR, VWAP)

│   │   ├── ote_engine.py           # Smart Money Concepts, Liquidity Sweeps, BOS, CHoCH, OTE

│   │   ├── elliott_wave_service.py # Heuristic Elliott Wave phase identification

│   │   ├── confluence_engine.py    # 17-contributor scoring matrix (0-100 pts)

│   │   ├── decision_engine.py      # Triple safety gates & BUY/SELL/WAIT decision logic

│   │   ├── decision_service.py     # End-to-end decision orchestration and caching

│   │   ├── signal_aggregator.py    # 4-component evidence fusion & dynamic re-normalization

│   │   ├── historical_evidence_service.py # Historical database similarity matching & baseline

│   │   ├── live_candle_ingestion_service.py # Background continuous candle persistence

│   │   ├── paper_trading_service.py# In-memory paper execution tracker

│   │   └── ai/                     # AI Integration Layer (Gemini Provider, Fallback, Aggregator)

│   │

│   └── research/                   # Advanced Research, Governance & ML Engines

│       ├── ml/                     # ML Dataset Builder, Training Pipelines, Calibration

│       ├── ml_shadow/              # ML Shadow Observer Service, T0 Locking, Shadow Store

│       └── governance/             # Forward Strategy Governance State Machine (N50/N100 tracking)

│

├── frontend/                       # Next.js Frontend Application

│   ├── src/

│   │   ├── app/                    # Next.js App Router (page.tsx, globals.css, layout.tsx)

│   │   ├── components/             # Reusable UI components (SignalHeroCard, CandleChart, etc.)

│   │   ├── hooks/                  # Custom React hooks (useDashboardData.ts, useRelativeTime.ts)

│   │   ├── services/               # Frontend API client (api.ts)

│   │   └── lib/                    # Pure formatters and calculation utilities (format.ts, relativeTime.ts)

│   └── package.json                # Dependencies and frontend scripts

│

├── data/                           # Persistent Database and Governance Storage

│   ├── historical/                 # SQLite databases (`historical_market_data.db`)

│   ├── governance_forward_state.json # Authoritative state of forward strategy paper execution

│   └── gating_state.json           # Production gating invariants configuration

│

├── research/ml/artifacts/          # Serialized ML Model Artifacts (BTC and XAU joblib/json files)

│   ├── BTC/                        # Calibrated LogisticRegression, preprocessor, metrics, calibration

│   └── XAU/                        # Calibrated RandomForestClassifier, preprocessor, metrics, calibration

│

└── tests/                          # Comprehensive Pytest Suite (806 passing tests)

```



---



## 7. LIVE MARKET DATA INGESTION



The platform ingests live market data for Bitcoin and Gold through dedicated, fault-tolerant ingestion pipelines with automatic failover:



| Asset | Internal Canonical Symbol | Primary Live Provider | Primary Endpoint | Fallback Provider | Fallback Endpoint |

| :--- | :--- | :--- | :--- | :--- | :--- |

| **Bitcoin** | `BTC/USD` | Binance Public API | `api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT` | Yahoo Finance | `query1.finance.yahoo.com/v8/finance/chart/BTC-USD` |

| **Gold** | `XAU-USD-SPOT` | GoldPrice.dev API | `api.goldprice.dev/v1/gold-price` | Yahoo Finance | `query1.finance.yahoo.com/v8/finance/chart/GC=F` |



### Pipeline Characteristics

- **HTTP Concurrency Lock**: A `threading.Lock` guards each market provider endpoint, preventing rapid concurrent dashboard refreshes from spamming external APIs.

- **HTTP 429 Adaptive Backoff**: If an external provider returns an HTTP 429 (Rate Limit), the service marks the provider in backoff mode for 60 seconds and immediately routes all subsequent requests to the fallback provider without generating extra network attempts.

- **Data Freshness Guard**: Price quotes older than 5 minutes (`FRESHNESS_THRESHOLD_S = 300`) are flagged as `STALE`, displaying a warning indicator in the user interface.

- **Market-Open Behavior (Gold)**: Spot Gold operates on London/New York market hours and closes on weekends. When GoldPrice.dev indicates closed markets, the platform captures the last valid Friday settlement quote, flags status as `MARKET_CLOSED`, and displays the historical holding state without crashing.



---



## 8. SYMBOL NORMALIZATION



Because external data providers, exchanges, and user queries employ divergent ticker conventions, the platform enforces strict internal symbol normalization via `normalize_ml_symbol()`:



```text

Incoming Variations:

"BTCUSDT"  ──┐

"BTC-USD"  ──┼──> Canonical Symbol: "BTC/USD" (Internal Key: "BTC")

"BTC/USD"  ──┘



"XAUUSD"        ──┐

"XAU-USD-SPOT"  ──┼──> Canonical Symbol: "XAU-USD-SPOT" (Internal Key: "XAU")

"GC=F"          ──┘

```



### Why Normalization is Essential

1. **Cache Collision Prevention**: Guarantees that query parameter variations hit the same in-memory cache bucket.

2. **Database Integrity**: Prevents fragmentation in SQLite tables (`historical_signals`, `forward_shadow_signals`), ensuring records aggregate under identical symbol indices.

3. **Cross-Asset Isolation**: Guarantees that switching tabs from BTC to XAU completely isolates state, preventing crypto volatility metrics from contaminating precious metal calculations.



---



## 9. CANDLE PIPELINE & NO-LOOKAHEAD POLICY



Market data is organized into standardized Open, High, Low, Close, Volume (OHLCV) candles:

- **$O$ (Open)**: First traded price of the bar interval.

- **$H$ (High)**: Maximum traded price during the bar interval.

- **$L$ (Low)**: Minimum traded price during the bar interval.

- **$C$ (Close)**: Final settled price of the bar interval.

- **$V$ (Volume)**: Aggregate traded contracts/units during the interval.



### Strict No-Lookahead Policy

A fundamental defect in many retail algorithmic systems is lookahead bias, where an algorithm makes decisions based on an unfinished, fluctuating candle whose final Close is unknown. 



The platform enforces a strict **Closed-Bar Boundary Policy**:

1. **Completed Bars Only**: Technical indicators, market structure shifts, and confluence calculations are computed **strictly on completed (closed) candles**.

2. **Current Open Bar Restriction**: The current live bar is used **exclusively for real-time price quotation** and distance-to-stop checks. It is never used to confirm trend breaks, MACD crosses, or pattern completions.

3. **Deterministic Timestamps**: Every candle is timestamped at the exact UTC open of the bar interval.



---



## 10. TIMEFRAME LOGIC & MULTI-TIMEFRAME (MTF) ALIGNMENT



The platform evaluates market action across four coordinated core timeframes, with auxiliary data layer support:

- **Core Decision / MTF / AI Quartet**: `5m`, `15m`, `1h`, `1d` (used uniformly across `DecisionService`, `ConfluenceEngine MTF`, AI Aggregator, and the frontend chart).
- **Auxiliary Market/Data Support**: `1m` (supported by the market and data layer for fine-grained ingestion).
- **Historical Archive**: `4h` may exist in stored historical candle database records, but is not part of the active core decision quartet.
- **1w**: Not supported in the current implementation.

| Timeframe | Role in Engine | Primary Engine Usage |
| :---: | :--- | :--- |
| **5m** | **Execution & Micro-Momentum** | Fast MACD crossovers, micro-momentum, liquidity sweeps, immediate entry triggers |
| **15m** | **Tactical Structure & Patterns** | Fair Value Gaps (FVG), swing pivots, primary chart visualization, ATR calculation |
| **1h** | **Structural Trend & Regime** | EMA20/50/200 stack, market structure shifts (BOS/CHoCH), intermediate S/R levels |
| **1d** | **Macro Bias & Filter** | Macro trend regime, Previous Day High/Low (PDH/PDL) benchmark levels |



### Multi-Timeframe (MTF) Alignment

Directional edge is maximized when multiple timeframe horizons point in the same direction. Contributor 4 (MTF Alignment, max 8 pts) evaluates directional consensus using the verified scaling formula score = round((dominant / total) * 8) if total > 0 else 0:

- **Unanimous Alignment (4/4)**: 5m, 15m, 1h, and 1d all exhibit matching trend structure (+8 pts, full max score).

- **Strong Majority Alignment (3/4)**: 3 of 4 timeframes aligned (+6 pts, verified mathematical yield).

- **Conflicted Tie (2/2)**: 2 vs 2 split yields 2 pts with conflict penalties applied, flagging directional conflict.

---

## 11. TECHNICAL ANALYSIS ENGINE & INDICATOR EQUATIONS



The platform implements a pure mathematical, vectorized technical analysis engine in [`src/services/technical_analysis.py`](file:///d:/Project/TRADE/src/services/technical_analysis.py). Every indicator is computed deterministically from closed candle series without repainting.



---



## 12. EXPONENTIAL MOVING AVERAGE (EMA) EQUATION & STACK LOGIC



The Exponential Moving Average assigns greater weight to recent prices:



$$\alpha = \frac{2}{N + 1}$$



$$\text{EMA}_t = \alpha \cdot \text{Price}_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$$



### Parameters & Stack Interpretation

- **EMA20 ($N=20$)**: Short-term momentum baseline.

- **EMA50 ($N=50$)**: Medium-term intermediate trend baseline.

- **EMA200 ($N=200$)**: Institutional long-term regime boundary.



### Project Interpretation

- **Bullish Stack**: $\text{Price} > \text{EMA20} > \text{EMA50} > \text{EMA200}$. Confirms clean bullish expansion (+4 pts in Contributor 14).

- **Bearish Stack**: $\text{Price} < \text{EMA20} < \text{EMA50} < \text{EMA200}$. Confirms clean bearish markdown (-4 pts in Contributor 14).

- **Entangled / Compressed**: Moving averages crisscross within a narrow range, indicating consolidation or range-bound chop (0 pts awarded).



---



## 13. RELATIVE STRENGTH INDEX (RSI) EQUATION



The Relative Strength Index measures velocity and magnitude of price changes:



$$\text{RS} = \frac{\text{Average Gain over } N \text{ periods}}{\text{Average Loss over } N \text{ periods}}$$



$$\text{RSI} = 100 - \frac{100}{1 + \text{RS}}$$



### Parameters & Thresholds

- **Period ($N$)**: 14 bars.

- **Overbought Boundary**: $\text{RSI} \ge 70.0$.

- **Oversold Boundary**: $\text{RSI} \le 30.0$.

- **Bullish Momentum Zone**: $50.0 < \text{RSI} < 70.0$ (awards +3 pts).

- **Bearish Momentum Zone**: $30.0 < \text{RSI} < 50.0$ (awards -3 pts).

- **Extreme Exhaustion**: If $\text{RSI} > 80$ during a BUY candidate, the engine flags exhaustion warning and docks points.



---



## 14. MOVING AVERAGE CONVERGENCE DIVERGENCE (MACD) EQUATION



The MACD tracks trend momentum through exponential moving average differences:



$$\text{MACD Line} = \text{EMA}_{12}(\text{Close}) - \text{EMA}_{26}(\text{Close})$$



$$\text{Signal Line} = \text{EMA}_9(\text{MACD Line})$$



$$\text{Histogram} = \text{MACD Line} - \text{Signal Line}$$



### Contributor Logic (Contributor 16: Max 2 pts)

- **Bullish Momentum**: $\text{MACD Line} > \text{Signal Line}$ AND $\text{Histogram} > 0$ (+2 pts).

- **Bearish Momentum**: $\text{MACD Line} < \text{Signal Line}$ AND $\text{Histogram} < 0$ (-2 pts).

- **Histogram Expansion**: If the histogram is increasing in the direction of the trend, momentum acceleration is confirmed.



---



## 15. AVERAGE TRUE RANGE (ATR) EQUATION & RISK SIZING



The Average True Range measures market volatility:



$$\text{True Range (TR)} = \max\left( \text{High}_t - \text{Low}_t,\; |\text{High}_t - \text{Close}_{t-1}|,\; |\text{Low}_t - \text{Close}_{t-1}| \right)$$



$$\text{ATR}_t = \frac{\text{ATR}_{t-1} \cdot (N - 1) + \text{TR}_t}{N}$$



### Platform Usage

- **Period ($N$)**: 14 bars on the 15m timeframe.

- **Stop Loss Distance**: Fixed at $1.50 \times \text{ATR}$.

- **Take Profit 1 (TP1)**: Fixed at $2.40 \times \text{ATR}$ ($1.60\text{R}$ reward).

- **Take Profit 2 (TP2)**: Fixed at $4.20 \times \text{ATR}$ ($2.80\text{R}$ reward).

- **Volatility Sizing**: If ATR is unavailable or zero, trade generation is blocked.



---



## 16. VOLUME WEIGHTED AVERAGE PRICE (VWAP) EQUATION



VWAP measures the volume-weighted institutional average traded price:



$$\text{VWAP} = \frac{\sum (\text{Typical Price}_i \times \text{Volume}_i)}{\sum \text{Volume}_i}, \quad \text{where } \text{Typical Price} = \frac{\text{High} + \text{Low} + \text{Close}}{3}$$



### Engine Interpretation (Contributor 13: Max 4 pts)

- **Institutional Bullish Benchmark**: $\text{Price} > \text{VWAP}$. Indicates buyers are defending prices above institutional intraday value (+4 pts).

- **Institutional Bearish Benchmark**: $\text{Price} < \text{VWAP}$. Indicates sellers are dominant (-4 pts).



---



## 17. SUPPORT & RESISTANCE (S/R) PIVOT ALGORITHM



The platform identifies institutional horizontal levels via rolling swing pivot detection:

- **Swing High Pivot**: A candle whose High is strictly greater than the preceding $K$ candles and succeeding $K$ candles ($K=5$ bars).

- **Swing Low Pivot**: A candle whose Low is strictly less than the preceding $K$ candles and succeeding $K$ candles ($K=5$ bars).

- **Proximity Filter**:

  - If a BUY candidate is within $0.50\%$ of a major overhead resistance level, execution is blocked (`WAIT`) due to poor risk/reward headroom.

  - If a SELL candidate is within $0.50\%$ of major underlying support, execution is blocked (`WAIT`).



---



## 18. MARKET STRUCTURE ENGINE (BOS & CHoCH / MSS)



Handled by [`src/services/ote_engine.py`](file:///d:/Project/TRADE/src/services/ote_engine.py):

- **Higher High (HH) & Higher Low (HL)**: Series of ascending structural swing points confirming an uptrend.

- **Lower High (LH) & Lower Low (LL)**: Series of descending structural swing points confirming a downtrend.

- **Break of Structure (BOS)**: Price closes beyond a previous swing point in the direction of the dominant trend, confirming trend continuation.

- **Change of Character (CHoCH) / Market Structure Shift (MSS)**: Price aggressively closes beyond the most recent swing low in an uptrend (or swing high in a downtrend), signaling trend reversal (+9 pts in Contributor 2).



---



## 19. BREAKOUT & RETEST ENGINE



Evaluates price action at confirmed structural levels (Contributor 6: Max 6 pts):

1. **Level Break**: Candle body closes cleanly beyond a recognized horizontal support or resistance line.

2. **Retest**: Subsequent candles pull back to test the broken level from the opposite side.

3. **Rejection & Continuation**: Wicks form at the retested level, followed by an expansion candle in the breakout direction (+6 pts).



---



## 20. SUPPLY & DEMAND ZONES



Identifies institutional order clusters (Contributor 7: Max 5 pts):

- **Demand Zone**: An aggressive bullish expansion origin bar preceding a rapid price departure, leaving unfilled buy orders.

- **Supply Zone**: An aggressive bearish displacement origin bar leaving unfilled sell orders.

- **Reaction**: When price enters a fresh (unmitigated) demand zone and demonstrates wick rejection, +5 pts are awarded to bullish confluence.



---



## 21. SMART MONEY CONCEPTS (SMC)



SMC algorithms isolate institutional order flow signatures (Contributor 9: Max 5 pts):

- **Fair Value Gap (FVG)**: A 3-candle price imbalance where Candle 1 High does not overlap Candle 3 Low (bullish FVG), representing inefficient price delivery.

- **Order Block (OB)**: The last down candle prior to an aggressive upward impulse that broke structure.

- **Mitigation**: Price re-entering the FVG or Order Block to balance liquidity before continuing in the impulse direction (+5 pts).



---



## 22. ICT CONCEPTS (LIQUIDITY SWEEPS & SESSIONS)



Implemented in [`src/services/ote_engine.py`](file:///d:/Project/TRADE/src/services/ote_engine.py) (Contributor 10: Max 4 pts):

- **Previous Day High (PDH) & Previous Day Low (PDL)**: Key macro liquidity pools where retail stop-losses cluster.

- **Liquidity Sweep**: Price pierces PDH or PDL with an intraday wick but immediately closes back inside the range, trapping breakout traders and signaling institutional absorption (+4 pts).

- **Session Timing**: Tracks London open (07:00–10:00 UTC), New York open (12:00–16:00 UTC), and Asia consolidation (00:00–07:00 UTC).



---



## 23. FIBONACCI OPTIMAL TRADE ENTRY (OTE)



The Fibonacci engine measures deep value retracements within an active impulse leg:



$$\text{Retracement Ratio} = \frac{|\text{Swing High} - \text{Current Price}|}{|\text{Swing High} - \text{Swing Low}|}$$



### OTE Golden Pocket

- **Range**: Retracement between $0.618$ ($61.8\%$) and $0.786$ ($78.6\%$).

- **Interpretation**: Entering in the OTE zone maximizes risk/reward efficiency by placing the entry near institutional discount pricing while keeping the invalidation stop tight (+4 pts in Contributor 11).



---



## 24. ELLIOTT WAVE HEURISTIC ANALYSIS



Implemented in [`src/services/elliott_wave_service.py`](file:///d:/Project/TRADE/src/services/elliott_wave_service.py) (Contributor 12: Max 4 pts):

- **Impulse Wave 3 Expansion**: Strongest trending wave characterized by maximum volume and momentum acceleration (+4 pts).

- **Corrective Wave 4 / Pullback**: Orderly consolidation preceding Wave 5.

- **Corrective Wave C Completion**: Deep retracement completing an A-B-C cycle, signaling high probability of a new impulse cycle.





---



## 25. THE 17-CONTRIBUTOR ENGINE



The core quantitative scoring architecture is implemented in [`src/services/confluence_engine.py`](file:///d:/Project/TRADE/src/services/confluence_engine.py). It aggregates 17 independent analytical factors into a single composite confluence score bounded between $0$ and $100$ points.



---



## 26. COMPLETE 17-CONTRIBUTOR SPECIFICATION TABLE



| # | Contributor Name | Max Points | Analytical Inputs | Bullish Condition Logic | Bearish Condition Logic | Neutral / Unconfirmed Logic |

| :-: | :--- | :---: | :--- | :--- | :--- | :--- |

| **1** | **HTF Trend** | **11** | 1h & 1d EMA stacks, higher timeframe slope | Both 1h & 1d trends bullish (+11 pts) | Both 1h & 1d trends bearish (-11 pts) | Conflicting timeframes (0 pts) |

| **2** | **Market Structure** | **9** | Swing pivot series, BOS, CHoCH / MSS | Confirmed Bullish MSS or ongoing BOS (+9 pts) | Confirmed Bearish MSS or breakdown (-9 pts) | Ranging or inside-bar consolidation (0 pts) |

| **3** | **Momentum** | **8** | 5m MACD histogram, RSI slope, price velocity | Expanding positive MACD histogram (+8 pts) | Expanding negative MACD histogram (-8 pts) | Flat momentum, zero histogram (0 pts) |

| **4** | **MTF Alignment** | **8** | 5m, 15m, 1h, 1d directional consensus | 4 of 4 or 3 of 4 timeframes bullish (+8 pts) | 4 of 4 or 3 of 4 timeframes bearish (-8 pts) | 2 vs 2 split consensus (0 pts) |

| **5** | **S/R Price Action** | **8** | Horizontal swing levels, touch counts, wicks | Bullish bounce from verified support (+8 pts) | Bearish rejection from verified resistance (-8 pts) | Price in middle of range (0 pts) |

| **6** | **Breakout / Retest** | **6** | Broken level, retest candle, volume surge | Clean breakout and retest of resistance (+6 pts) | Clean breakdown and retest of support (-6 pts) | False breakout or failed retest (0 pts) |

| **7** | **Supply & Demand** | **5** | Order clusters, displacement origin zones | Price touching unmitigated demand zone (+5 pts) | Price touching unmitigated supply zone (-5 pts) | Zone already mitigated or no zone (0 pts) |

| **8** | **Volume Confirmation** | **5** | Relative Volume (RVol) vs 20-period moving avg | RVol > 1.5 on bullish expansion candles (+5 pts) | RVol > 1.5 on bearish expansion candles (-5 pts) | Below-average volume / dry liquidity (0 pts) |

| **9** | **SMC / ICT** | **5** | Fair Value Gaps (FVG), Order Blocks (OB) | Mitigation of bullish FVG or Order Block (+5 pts) | Mitigation of bearish FVG or Order Block (-5 pts) | No active imbalance nearby (0 pts) |

| **10** | **ICT Concepts** | **4** | Previous Day High/Low (PDH/PDL) levels | Liquidity sweep of PDL with wick rejection (+4 pts) | Liquidity sweep of PDH with wick rejection (-4 pts) | Price trading inside previous day range (0 pts) |

| **11** | **Fibonacci OTE** | **4** | Swing high to swing low impulse retracement | Retracement in 0.618 - 0.786 discount zone (+4 pts) | Retracement in 0.618 - 0.786 premium zone (-4 pts) | Retracement outside OTE zone (0 pts) |

| **12** | **Elliott Wave** | **4** | Wave phase identification heuristic | Wave 3 impulse or Wave C corrective (Magnitude 4 + directional bias) | Wave 3 downward expansion (+4 pts short) | Complex choppy correction (0 pts) |

| **13** | **VWAP** | **4** | Intraday Volume Weighted Average Price | Price holding firmly above VWAP (+4 pts) | Price holding firmly below VWAP (-4 pts) | Price oscillating across VWAP line (0 pts) |

| **14** | **EMA / MA Stack** | **4** | 15m EMA20, EMA50, EMA200 alignment | Bullish alignment: Price > EMA20 > 50 > 200 (+4 pts) | Bearish alignment: Price < EMA20 < 50 < 200 (-4 pts) | Entangled / compressed moving averages (0 pts) |

| **15** | **RSI** | **3** | 14-period Relative Strength Index | RSI in 50.0 - 70.0 momentum expansion (+3 pts) | RSI in 30.0 - 50.0 momentum decline (-3 pts) | Overbought (>70) or Oversold (<30) (0 pts) |

| **16** | **MACD** | **2** | 12, 26, 9 MACD line & signal line | MACD line above signal line (+2 pts) | MACD line below signal line (-2 pts) | Flat lines at zero boundary (0 pts) |

| **17** | **Google Gemini AI** | **10** | Structured multi-timeframe JSON payload | AI output: Bullish bias, confidence >= 70% (+10 pts) | AI output: Bearish bias, confidence >= 70% (-10 pts) | AI output: Neutral / Unclear bias (0 pts) |

| **TOTAL** | **All 17 Factors** | **100** | **Comprehensive Multi-Engine Input** | **Maximum Bullish Score = 100** | **Maximum Bearish Score = 100** | **Baseline WAIT State** |



---



## 27. DETAILED BREAKDOWN OF THE 17 CONTRIBUTORS



### 1. HTF Trend (11 pts max)

Evaluates 1-hour and 1-day trend direction using EMA slope and structure. If 1H is bullish and 1D is bullish, full 11 points are awarded. If 1H is bullish but 1D is consolidating, 7 points are awarded. If timeframes contradict, 0 points are awarded.



### 2. Market Structure (9 pts max)

Tracks swing highs and lows. Awarded when a structural break of structure (BOS) occurs in trend direction or when a Market Structure Shift (MSS/CHoCH) confirms institutional trend reversal.



### 3. Momentum (8 pts max)

Evaluates 5-minute momentum acceleration. Combines MACD histogram slope and candle body size. Full points awarded when micro-momentum confirms macro trend.



### 4. MTF Alignment (8 pts max)

Cross-examines 5m, 15m, 1h, and 1d timeframes. Points are scaled directly to the declared 8-point maximum using score = round((dominant / total) * 8) if total > 0 else 0. Unanimous 4/4 agreement awards the full 8 points, strong 3/4 consensus awards 6 points, and a 2/2 tie awards 2 points (with conflict penalty applied).



### 5. S/R Price Action (8 pts max)

Measures interaction with verified horizontal pivot levels. Full points awarded on clean wick rejections confirming level respect.



### 6. Breakout / Retest (6 pts max)

Validates breakout authenticity. Requires a full candle body close outside a range followed by a successful retest that holds.



### 7. Supply & Demand (5 pts max)

Identifies unmitigated institutional order origin blocks. Points awarded when price enters the zone and exhibits immediate rejection.



### 8. Volume Confirmation (5 pts max)

Compares bar volume to 20-period moving average. Filters low-volume false breakouts by requiring volume surge ($> 1.5\times$).



### 9. SMC / ICT (5 pts max)

Detects Fair Value Gaps (FVG) and Order Blocks (OB). Points awarded when price mitigates an open imbalance in trend direction.



### 10. ICT Concepts (4 pts max)

Tracks Previous Day High (PDH) and Low (PDL). Points awarded on liquidity sweep rejections that trap retail breakout traders.



### 11. Fibonacci OTE (4 pts max)

Calculates pullback retracement depth. Full points awarded when price pulls back into the $0.618 - 0.786$ discount zone during an active impulse.



### 12. Elliott Wave (4 pts max)

Heuristic wave identification. Evaluated as a 4-point magnitude score combined with directional bias (e.g., magnitude 4 + BEARISH bias when identifying corrective decline phases, or magnitude 4 + BULLISH bias on impulse expansions).



### 13. VWAP (4 pts max)

Compares price to institutional intraday VWAP. Above VWAP = Bullish (+4); Below VWAP = Bearish (-4).



### 14. EMA / MA Stack (4 pts max)

Evaluates the geometric order of EMA20, EMA50, and EMA200. Perfect alignment confirms trend maturity.



### 15. RSI (3 pts max)

Evaluates RSI(14) momentum corridor. Rewards strong expansion between 50 and 70 without extreme overbought exhaustion.



### 16. MACD (2 pts max)

Fast crossover confirmation between MACD line and 9-period signal line.



### 17. Google Gemini AI (10 pts max)

Qualitative LLM synthesis. Awards up to 10 points based on confidence and structural narrative harmony.



---



## 28. IMPORTANT TERMINOLOGY



To ensure clear communication across quantitative, software, and financial domains:

- **Contributors**: The 17 specific scoring factors in `ConfluenceEngine`.

- **Factors / Features**: Technical and statistical inputs extracted from candles and indicators.

- **Confluence**: The aggregate point total ($0–100$) reflecting alignment among the 17 contributors.

- **Scoring Engine**: The mathematical subsystem (`confluence_engine.py`) that evaluates contributors.

- **Decision Engine**: The risk-gating subsystem (`decision_engine.py`) that applies Direction, Conflict, and Quality gates.

- **Trading Decision**: The final actionable command (`BUY`, `SELL`, or `WAIT`).



---



## 29. CONFLUENCE EQUATION & MAXIMUM ATTRIBUTION



Confluence is computed by summing the points awarded across all active contributors:



$$\text{Bullish Score} = \sum_{i=1}^{17} \text{Points}_{i,\text{bullish}}, \quad \text{Bearish Score} = \sum_{i=1}^{17} \text{Points}_{i,\text{bearish}}$$



$$\text{Confluence Score} = \max(\text{Bullish Score},\; \text{Bearish Score})$$



$$\text{Net Directional Score} = \text{Bullish Score} - \text{Bearish Score}$$



### Bounded Attribution Caps

- **Technical & Structural Maximum**: 90 points ($100 - 10$).

- **Gemini AI Maximum**: 10 points ($10\%$ of total).

- **Absolute Platform Maximum**: 100 points.



---



## 30. TECHNICAL SCORE VS CONFLUENCE VS NET SCORE VS GEMINI SCORE



Understanding the distinction between these five metrics is vital for data-lineage consistency:



| Metric | Range | Source File | Exact Meaning |

| :--- | :---: | :--- | :--- |

| **Technical Score** | $0 - 90$ pts | `confluence_engine.py` | Sum of points awarded strictly by the 16 technical and structural factors (excluding AI). |

| **Gemini Score** | $0 - 10$ pts | `gemini_provider.py` | Points awarded strictly by Google Gemini AI confirmation. |

| **Confluence Score** | $0 - 100$ pts | `confluence_engine.py` | Total gross score ($	ext{Technical} + 	ext{Gemini}$) in the dominant direction. |

| **Net Directional Score** | $-100 \text{ to } +100$ pts | `decision_engine.py` | Net directional spread ($	ext{Bullish Points} - \text{Bearish Points}$). Evaluated by Direction Gate. |

| **Overall Evidence Bias** | $0 - 100\%$ | `signal_aggregator.py` | Aggregated directional bias synthesized across Now Market, History, ML, and Strategy. |



---



## 31. GOOGLE GEMINI AI INTEGRATION



Handled by `GeminiAIProvider` ([`src/services/ai/gemini_provider.py`](file:///d:/Project/TRADE/src/services/ai/gemini_provider.py)):

- **Model**: `gemini-3.1-flash-lite` (Configured via `GEMINI_MODEL_NAME`).

- **Role**: Qualitative synthesis and second-opinion confirmation. **Gemini is strictly an advisor, never the final decision authority.**

- **Strict 10-Point Cap**: Regardless of how confident Gemini is ($99\%$ confidence), its scoring contribution is capped at **10.0 points** out of 100. It cannot override failed technical gates.



---



## 32. GEMINI INPUT PAYLOAD



Gemini receives a structured JSON object (`MultiTimeframeTechnicalInput`) containing:

- Asset symbol, current price, and UTC timestamp.

- Timeframe summaries (5m, 15m, 1h, 1d) with EMAs, RSI, MACD, and ATR.

- Key horizontal support and resistance levels.

- SMC markers: Fair Value Gaps, Liquidity Sweeps, and Market Structure state.

- Fibonacci OTE levels and current retracement ratio.

- Current technical confluence score (0–90).



---



## 33. GEMINI OUTPUT SCHEMA



Gemini returns structured JSON parsed into `AIAnalysisResponse`:

- `overall_bias`: `"BULLISH"`, `"BEARISH"`, or `"NEUTRAL"`.

- `confidence`: Integer between $0$ and $100$.

- `score`: Contribution score between $0$ and $10$.

- `reasoning`: Multi-sentence explanation of structural drivers.

- `key_support` & `key_resistance`: AI-identified critical price levels.

- `risk_level`: Environmental risk assessment (`LOW`, `MEDIUM`, `HIGH`).

- `invalidation_conditions`: Specific price breaches that would invalidate the bias.



---



## 34. DETERMINISTIC FALLBACK AI



If the Gemini API key is missing, network latency exceeds 45 seconds, or rate limits occur, the system automatically activates `FallbackAIProvider`:

- Evaluates price position relative to EMA20 and RSI to generate deterministic synthetic sentiment.

- The UI strictly displays **`GEMINI FALLBACK`** in amber with an informative tooltip, preventing any false impression that live AI inference is active.





---



## 35. DIRECTION GATE & DIRECTIONAL THRESHOLD ARCHITECTURE

There are TWO fundamentally distinct directional mechanisms operating at different pipeline stages:

### A. ConfluenceEngine Direction Gate (Upstream Pipeline Safety Gate)

Implemented in [`src/services/decision_engine.py`](file:///d:/Project/TRADE/src/services/decision_engine.py):

- **Core Rule**: Strictly requires at least **2 of 3 core directional contributors** to agree in the candidate direction:
  1. `HTF Trend`
  2. `Market Structure`
  3. `MTF Alignment`
- **Logic**:
  $$\text{Gate Passed} = (\text{gate\_bullish} \ge 2) \lor (\text{gate\_bearish} \ge 2)$$
- **Net Score Threshold**: There is **NO** $|\text{Net Score}| \ge 20.0\text{ pts}$ requirement in this gate. Passing this gate depends purely on structural 2-of-3 consensus among the three anchor pillars.
- **Result if Failed**: If fewer than 2 core factors agree, the candidate trade setup is rejected and forced to **`WAIT`**.

### B. SignalAggregator Directional Threshold (Downstream Evidence Bias)

Implemented in [`src/services/signal_aggregator.py`](file:///d:/Project/TRADE/src/services/signal_aggregator.py):

- **Threshold**:
  $$\text{DIRECTIONAL\_THRESHOLD} = 20.0\text{ pts}$$
- **Downstream Application**: Applies exclusively to multi-component evidence aggregation (`OverallTradingSignal` / Overall Evidence Bias):
  - $\text{Net Aggregator Score} \ge +20.0\text{ pts} \implies \text{BUY evidence bias}$
  - $\text{Net Aggregator Score} \le -20.0\text{ pts} \implies \text{SELL evidence bias}$
  - Otherwise $\implies \text{WAIT / sub-threshold evidence state}$
- **Architectural Boundary**: The `SignalAggregator` directional threshold does **NOT** define, control, or override whether the upstream `ConfluenceEngine` Direction Gate passes.



---



## 36. CONFLICT GATE



Evaluates opposing market forces to prevent trading into structural cross-currents:



$$\text{Opposing Weight} = \frac{\text{Opposing Contributor Points}}{\text{Total Active Points}} \le 25.0\%$$



- **Example**: If Bullish Score is $60\text{ pts}$ but Bearish Score is $25\text{ pts}$, Opposing Weight is $25 / 85 = 29.4\%$.

- **Result if Failed**: Because $29.4\% > 25.0\%$, the Conflict Gate **FAILS**, overriding the candidate signal to **`WAIT`**.



---



## 37. QUALITY GATE



Enforces the minimum statistical edge boundary derived from empirical backtesting:



$$\text{Confluence Score} \ge 58.0\text{ pts}$$



- **Asset Calibration**:

  - BTC minimum threshold: $58\text{ pts}$.

  - XAU minimum threshold: $58\text{ pts}$.

- **WAIT Override**: Even if Direction Gate passes (e.g. $+51.0\text{ pts}$) and Conflict Gate passes ($0.0\%$ opposing), if Confluence is $35 < 58\text{ pts}$, the Quality Gate **FAILS**, and the final authoritative command is **`WAIT`**.



---



## 38. DECISION ENGINE ARCHITECTURE & TREE



The complete deterministic evaluation hierarchy in `DecisionEngine`:



```text

                      [Raw Multi-Timeframe Candles & AI Input]

                                         │

                                         ▼

                            [Evaluate 17 Contributors]

                                         │

                                         ▼

                   [Calculate Confluence & Directional Net Score]

                                         │

                                         ▼

                                 < Direction Gate >

                             >= 2 of 3 Core Factors Agree?
                             {HTF Trend, Market Structure, MTF Alignment}

                                  /            \

                                YES             NO ────> [FINAL ACTION: WAIT]

                                /

                               ▼

                                < Conflict Gate >

                           Opposing Weight <= 25.0%?

                                /            \

                              YES             NO ─────> [FINAL ACTION: WAIT]

                              /

                             ▼

                                < Quality Gate >

                           Confluence Score >= 58 pts?

                                /            \

                              YES             NO ─────> [FINAL ACTION: WAIT]

                              /

                             ▼

                           < Proximity & ATR Checks >

                       Price within 0.5% of S/R? ATR > 0?

                                /            \

                              YES             NO ─────> [FINAL ACTION: WAIT]

                              /

                             ▼

                  [FINAL ACTION: BUY or SELL]

                  - Calculate Entry Zone [Price - 0.35 ATR, Price]

                  - Stop Loss = Price - 1.5 ATR

                  - Take Profit 1 = Price + 2.4 ATR (1.6R)

                  - Take Profit 2 = Price + 4.2 ATR (2.8R)

                  - Setup Grade: A+ / A; Risk Level: LOW

```



---



## 39. BUY / SELL / WAIT SEMANTICS



- **`BUY`**: All 3 gates pass, net score $\ge +20.0$, confluence $\ge 58$, ATR valid, upside clearance confirmed.

- **`SELL`**: All 3 gates pass, net score $\le -20.0$, confluence $\ge 58$, ATR valid, downside clearance confirmed.

- **`WAIT`**: Active capital-preservation state. Occurs when edge is unconfirmed or conflicting. **`WAIT` is a position of strength, not inaction.**



---



## 40. ENTRY / STOP LOSS / TARGET ENGINE



When an authoritative `BUY` or `SELL` is cleared, trade levels are calculated dynamically using volatility units:



### For BUY Setups:

- **Entry Zone**: $[	ext{Price} - 0.35 \times \text{ATR},\; \text{Price}]$

- **Stop Loss**: $\text{Price} - 1.50 \times \text{ATR}$

- **Take Profit 1 (TP1)**: $\text{Price} + 2.40 \times \text{ATR}$ (Reward-to-Risk = $1.60\text{R}$)

- **Take Profit 2 (TP2)**: $\text{Price} + 4.20 \times \text{ATR}$ (Reward-to-Risk = $2.80\text{R}$)



### For SELL Setups:

- **Entry Zone**: $[\text{Price},\; \text{Price} + 0.35 \times \text{ATR}]$

- **Stop Loss**: $\text{Price} + 1.50 \times \text{ATR}$

- **Take Profit 1 (TP1)**: $\text{Price} - 2.40 \times \text{ATR}$ (Reward-to-Risk = $1.60\text{R}$)

- **Take Profit 2 (TP2)**: $\text{Price} - 4.20 \times \text{ATR}$ (Reward-to-Risk = $2.80\text{R}$)



---



## 41. RISK / REWARD EQUATIONS



$$\text{Risk} = |\text{Entry Midpoint} - \text{Stop Loss}|$$



$$\text{Reward}_{\text{TP1}} = |\text{TP1} - \text{Entry Midpoint}|, \quad \text{R:R}_{\text{TP1}} = \frac{\text{Reward}_{\text{TP1}}}{\text{Risk}} = \frac{2.40 \times \text{ATR}}{1.50 \times \text{ATR}} = 1.60\text{R}$$



$$\text{Reward}_{\text{TP2}} = |\text{TP2} - \text{Entry Midpoint}|, \quad \text{R:R}_{\text{TP2}} = \frac{\text{Reward}_{\text{TP2}}}{\text{Risk}} = \frac{4.20 \times \text{ATR}}{1.50 \times \text{ATR}} = 2.80\text{R}$$



---



## 42. WAIT TRADE-LEVEL RULE



When the decision is `WAIT`:

- `entry_zone = None` (renders `--` in UI)

- `stop_loss = None` (renders `--` in UI)

- `tp1 = None` (renders `--` in UI)

- `tp2 = None` (renders `--` in UI)

- `rr_tp1 = None`, `rr_tp2 = None`



**Rationale**: Displaying active entry prices and profit targets during a `WAIT` state tempts traders to enter unconfirmed setups, directly violating institutional risk discipline.



---



## 43. HISTORICAL MARKET SYSTEM



Handled by `HistoricalEvidenceService` ([`src/services/historical_evidence_service.py`](file:///d:/Project/TRADE/src/services/historical_evidence_service.py)) and SQLite database `data/historical/historical_market_data.db`.



### Core Database Tables (2.15 GB historical_market_data.db):

The database comprises exactly 10 relational tables:
1. ohlcv_bars (candles table): Stored multi-timeframe candle bars (Core: 5m, 15m, 1h, 1d; Auxiliary: 1m; Archive: 4h).
2. market_regimes: Statistical regime classifications (trending, mean-reverting, volatile).
3. 	echnical_indicators: Pre-computed indicator states.
4. historical_signals: 2,438 backtested trade signals generated across developmental runs.
5. historical_performance: Metrics rollups across strategies.
6. acktest_runs: 53 distinct backtest run execution records.
7. acktest_reports: Serialized backtest performance and walk-forward verification reports.
8. model_training_records: Model training sessions and parameter logs.
9. model_features: Feature vectors and feature importance weights.
10. system_logs: Historical pipeline execution and audit logs.

---

## 44. HISTORICAL DATA SCALE: CANONICAL BASELINE VS SETUP MATCH

A critical distinction enforced in the platform:

```text
CANONICAL COMPLETED BACKTEST BASELINE (HUMAN-PINNED CANONICAL RUN ID)
- Bitcoin (Current Verified Canonical Run: RUN-BTC-USD-20260831-173607):
  Sample N = 1,032 | Win Rate = 44.1% | Avg R = +0.102R | Expectancy = +0.103R | Profit Factor = 1.18
- Gold (Current Verified Canonical Run: RUN-XAU-USD-20260831-174452):
  Sample N = 893   | Win Rate = 44.6% | Avg R = +0.115R | Expectancy = +0.115R | Profit Factor = 1.21
(Canonical benchmark scoped to explicitly configured run, eliminating cross-run inflation)
            !=
CURRENT COMPARABLE SETUP PATTERN MATCH (SCORE-BAND +/- 1)
Matched Sample N_pattern
Categorical Score-Band: abs(confluence_score - current_confluence) <= 1 AND regime == current_regime
Sample Threshold: N >= 10 required for valid statistics (suppressed to '--' when N < 10)
Status: NO QUALIFYING MATCHES (when N < 10)
```

### Canonical Baseline Governance & Pinning Policy
- **Explicit Human Control**: The historical baseline is explicitly pinned per asset in application settings (`HISTORICAL_CANONICAL_RUN_BTC` and `HISTORICAL_CANONICAL_RUN_XAU`).
- **No Automatic Promotion**: Newer exploratory runs or newly completed backtests do NOT automatically replace the canonical baseline, regardless of completion time, sample size $N$, or win rate. Baseline replacement remains a deliberate human/governance action.
- **Fail-Closed Validation**: The engine validates that the configured run exists in `backtest_runs`, matches the target symbol, has status `COMPLETED`, and possesses a corresponding report in `backtest_reports`. If any validation check fails, the resolver fails closed (returning `status = NOT_AVAILABLE` and `evidence_quality = INSUFFICIENT` with zero fallback promotion).
- **Current Verified Canonical Baseline IDs**:
  - `BTC/USD`: `RUN-BTC-USD-20260831-173607` ($N = 1,032$)
  - `XAU/USD`: `RUN-XAU-USD-20260831-174452` ($N = 893$)
  *(These are current verified canonical baseline IDs, not permanent universal constants).*
- **Database Non-Mutation**: By querying strictly by the validated canonical `run_id`, cross-run inflation from developmental test runs is eliminated while keeping all 2,438 rows in `historical_signals` 100% intact (0 rows deleted, 0 updated, 0 schema changes).

---

## 45. HISTORICAL SIMILARITY MATCHING ALGORITHM

To match a live setup against the historical catalog:
1. **Categorical Score-Band Matching**: Selects historical signals whose confluence score falls within $\pm 1$ point of the live setup's confluence score:
   
   |\text{Confluence}_{\text{hist}} - \text{Confluence}_{\text{current}}| \le 1

2. **Market Regime Alignment**: Further filters by matching the active market regime (e.g. BULLISH_TREND, BEARISH_TREND, RANGE_BOUND).
3. **Statistical Sample Gate ( \ge 10$)**: At least  \ge 10$ matching historical setups are required to compute a statistically reliable Matched Win Rate and Expectancy. If  < 10$, the engine safely displays NO QUALIFYING HISTORICAL MATCHES and sets matched metrics to None (--), protecting traders from small-sample noise.

---

## 46. HISTORICAL METRICS & PERFORMANCE EQUATIONS

### Win Rate:
\text{Win Rate (\%)} = \frac{\text{Number of Winning Trades}}{\text{Total Number of Closed Trades}} \times 100

### Mathematical Expectancy ($ in $-multiples):
E = (P_{\text{win}} \times \overline{R}_{\text{win}}) - (P_{\text{loss}} \times \overline{R}_{\text{loss}})

- Where {\text{win}}$ is probability of a win, $\overline{R}_{\text{win}}$ is average $-return of winners, {\text{loss}}$ is probability of loss, and $\overline{R}_{\text{loss}}$ is average $-loss (standardized at .0\text{R}$).
- A positive sample expectancy ( > 0$) indicates historical profitability across the evaluated sample, though future performance is subject to market variance and regime shifts.

### Profit Factor:
\text{Profit Factor} = \frac{\sum \text{Gross Profits}}{\sum \text{Gross Losses}}

### Maximum Drawdown (MDD):
\text{MDD}_t = \max_{\tau \le t} \left( \frac{\text{Peak Equity}_\tau - \text{Equity}_t}{\text{Peak Equity}_\tau} \right) \times 100

---

## 47. WALK-FORWARD ANALYSIS, OOS & HOLDOUT INTEGRITY



Standard $k$-fold cross-validation or random shuffling is **mathematically fatal** for financial time-series data because it leaks future structural regimes into past training sets.



The platform strictly uses **Anchored & Rolling Walk-Forward Optimization**:

```text

Fold 1: [ Train: 2023 Q1-Q2 ] ──> [ Validate: 2023 Q3 ] ──> [ Out-of-Sample: 2023 Q4 ]

Fold 2: [ Train: 2023 Q1-Q3 ] ──> [ Validate: 2023 Q4 ] ──> [ Out-of-Sample: 2024 Q1 ]

Fold 3: [ Train: 2023 Q1-Q4 ] ──> [ Validate: 2024 Q1 ] ──> [ Out-of-Sample: 2024 Q2 ]

```

Every reported metric reflects out-of-sample performance where the model had zero exposure to the test period.



---



## 48. DATA LEAKAGE DEFENSES



The platform enforces three strict structural defenses against leakage:

1. **Future-Data Invariance**: Indicators and features at candle index $t$ access data indices $\le t$ only.

2. **Preprocessing Isolation**: Scaling statistics (mean, variance) in `StandardScaler` are computed strictly on training folds and applied out-of-sample.

3. **Target Invariance**: Outcome resolution requires strictly future closed candles ($t+1, t+2, \dots$).



---



## 49. HISTORICAL RESEARCH STRATEGIES



Implemented in [`src/services/validated_strategy_layer.py`](file:///d:/Project/TRADE/src/services/validated_strategy_layer.py):

- **Role**: Validated algorithmic rulebooks that qualified under walk-forward testing (e.g. `BTC_MOM_BREAKOUT`, `XAU_SMC_REVERSAL`).

- **Qualification Threshold**: Requires positive walk-forward expectancy across $\ge 4$ independent market regimes.

- **Current Live Status**: Operates in **Shadow-Only Mode**. Contributes evidence to `SignalAggregator` but does not trigger autonomous live execution.



---



## 50. MACHINE LEARNING SYSTEM ARCHITECTURE



The Machine Learning subsystem provides probabilistic outcome forecasting trained on institutional features and calibrated for real-world uncertainty:



| Asset | Active Model Architecture | Artifact Path | Serialization | Training Samples | Baseline Out-of-Sample Directional Accuracy |

| :--- | :--- | :--- | :---: | :---: | :---: |

| **Bitcoin** | **Calibrated LogisticRegression** | `research/ml/artifacts/BTC/` | `model.joblib` | 1,519 signals | **52.4%** |

| **Gold** | **Calibrated RandomForestClassifier** | `research/ml/artifacts/XAU/` | `model.joblib` | 919 signals | **53.8%** |



---



## 51. ML TARGET DEFINITION



The ML models solve a strict binary outcome classification problem:



$$y = \begin{cases} 1 & \text{if the trade achieves Take Profit 1 before Stop Loss (WIN)} \\ 0 & \text{if the trade touches Stop Loss before Take Profit 1 (LOSS)} \end{cases}$$



The raw model output `predict_proba(X)[0, 1]` represents the estimated probability of achieving a winning outcome ($y=1$).



---



## 52. ML FEATURE PIPELINE



Handled by `FeatureEngineer` ([`src/research/ml/feature_engineering.py`](file:///d:/Project/TRADE/src/research/ml/feature_engineering.py)):



### 1. Trend & Moving Average Features:

- Distance to EMA20, EMA50, EMA200 (normalized as $\%$ of price)

- 1H trend direction, 1D trend direction, EMA stack slope



### 2. Momentum & Oscillator Features:

- RSI(14) raw value, RSI slope (delta over 3 bars)

- MACD line value, MACD histogram, histogram expansion rate



### 3. Volatility & Range Features:

- ATR(14) normalized as percentage of price (volatility regime)

- High-Low range ratio over rolling 20 bars



### 4. Market Structure & Structural Features:

- Confluence score (0–100)

- Market regime classification (`TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGING`, `VOLATILE`)

- Distance to nearest swing support and swing resistance



### 5. Temporal & Session Features:

- UTC hour of day, day of week

- Active trading session (`ASIA`, `LONDON`, `NEW_YORK`)



---



## 53. PROBABILITY CALIBRATION (PLATT SCALING)



Raw probabilities from machine learning models often suffer from overconfidence or miscalibration. The platform applies Platt scaling via `CalibratedClassifierCV`:



$$P(y=1 \mid X) = \frac{1}{1 + e^{-(a \cdot f(X) + b)}}$$



- Parameters $a$ and $b$ are fitted using out-of-fold validation.

- Calibration quality is verified via **Brier Score** and **Expected Calibration Error (ECE)**, ensuring that when the model outputs $60\%$, approximately 60 out of 100 historical instances actually achieved $1.60\text{R}$ profit.



---



## 54. ML OBSERVATION LIFECYCLE & FORWARD TRACKING



Handled by `MLShadowService` ([`src/research/ml_shadow/shadow_service.py`](file:///d:/Project/TRADE/src/research/ml_shadow/shadow_service.py)):



```text

               1. Model Inference at Candle Close (T0)

                                 │

                                 ▼

         2. Create Immutable MLObservation (ID: ML-SHADOW-XXXX)

                                 │

                                 ▼

             3. Persist to SQLite (Status: PENDING)

                                 │

                                 ▼

      4. Forward Evaluation Loop (Inspect Future Closed Candles)

            ├── Price touches Take Profit 1? ──> Status: RESOLVED (WIN)

            ├── Price touches Stop Loss?     ──> Status: RESOLVED (LOSS)

            └── 288 bars elapse (Max Hold)?  ──> Status: RESOLVED (EXPIRED)

                                 │

                                 ▼

               5. Update Forward Out-of-Sample Metrics

               (Cumulative Directional Accuracy, Brier Score)

```



---



## 55. CANDLE CLOSE BOUNDARY ($T_0$) DEFINITION



$T_0$ is the exact UTC timestamp of the **completed candle** that triggered the prediction.

- **Rule**: $T_0$ must strictly reflect the candle open/close timestamp from the market feed.

- **Integrity Defense**: Wall-clock UTC time is never substituted for $T_0$, preventing clock drift between the server and the exchange from corrupting the temporal sequence.



---



## 56. DETERMINISTIC OBSERVATION ID GENERATION



Every ML shadow prediction is assigned an immutable, idempotent identifier:



```python

seed = f"{symbol.upper()}|{timestamp_t0}|{ml_model_version}"

obs_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()

observation_id = f"ML-SHADOW-{obs_hash}"

```

This guarantees that repeated API queries on the same completed candle return the identical observation ID without creating duplicate database rows.



---



## 57. SHADOW VALIDATION RESOLUTION STATES



- **`PENDING`**: Trade has entered at $T_0$; price has touched neither Stop Loss nor Take Profit 1.

- **`RESOLVED (WIN)`**: Price reached Take Profit 1 first ($+1.60\text{R}$).

- **`RESOLVED (LOSS)`**: Price reached Stop Loss first ($-1.00\text{R}$).

- **`RESOLVED (EXPIRED)`**: Position remained open for 288 bars without resolution; closed at market price.



---



## 58. ML METRICS DEFINITIONS



- **Directional Accuracy**: $\text{Wins} / \text{Total Resolved} \times 100$.

- **Brier Score**:

  

  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (P_i - y_i)^2$$

  

  Lower is better ($0.0 = \text{perfect probability prediction}$; $0.25 = \text{uninformative coin flip}$).

- **Expected Calibration Error (ECE)**: Weighted average difference between predicted confidence and observed win rate across probability bins.



---



## 59. ML OBSERVER VS FORWARD STRATEGY EVIDENCE



A fundamental data-lineage distinction in the platform:



| System Dimension | ML Shadow Observer | Forward Strategy Governance |

| :--- | :--- | :--- |

| **Primary File** | `src/research/ml_shadow/shadow_service.py` | `src/research/governance/forward_state_machine.py` |

| **Core Database Table** | `ml_shadow_observations` | `forward_shadow_signals` |

| **Total Observations** | **3,887 observations** | **479 total records** (479 quarantined fixtures) |

| **Resolved Sample Size** | **85 resolved trades** | **Clean Forward N = 0 / 50** |

| **Current Performance** | **52.9% directional accuracy** | **N50 Milestone: NOT REACHED** |

| **Execution Authority** | **0% authority** (Pure research observer) | **Production Gating: DISABLED** |



Separating these systems prevents the 85 ML shadow trades from falsely masquerading as clean forward execution samples.





---



## 60. FORWARD SHADOW SYSTEM & SAMPLE TRACKING



Implemented in [`src/research/governance/forward_state_machine.py`](file:///d:/Project/TRADE/src/research/governance/forward_state_machine.py) and stored in `data/historical/historical_market_data.db` (`forward_shadow_signals`).

- **Objective**: Collects live forward paper-execution evidence under real-world market slippage and timing without capital risk.

- **Tracking**: Monitors forward trade entries, tracking actual maximum favorable excursion (MFE) and maximum adverse excursion (MAE).



---



## 61. QUARANTINE PROTOCOL FOR TEST FIXTURES



During early platform development and regression testing, synthetic test signals (280 BTC, 199 XAU) were generated to test database schemas and API endpoints.

- **The Quarantine Guard**: All 479 test fixtures are assigned `quarantine_flag = TRUE`.

- **Governance Invariant**: Quarantined fixtures are **strictly excluded** from forward strategy metrics. Only organic live paper trades qualify for the clean forward sample count (`Clean N = 0 / 50`).



---



## 62. STRATEGY GOVERNANCE ARCHITECTURE



The governance framework enforces strict institutional stage-gate boundaries:

1. **Stage 1 (Code & Pipeline Verification)**: Automated tests, builds, and invariant checks pass (CURRENT STAGE).

2. **Stage 2 (Forward Shadow Accumulation)**: Accumulates $N \ge 50$ clean forward paper trades under live market conditions.

3. **Stage 3 (Statistical Evaluation)**: Verifies that forward expectancy $E > 0$, Brier score $< 0.25$, and max drawdown is within risk tolerances.

4. **Stage 4 (Human Approval)**: Explicit human operator sign-off required. **Automatic self-promotion to live trading is architecturally impossible.**



---



## 63. SAMPLE MILESTONES: N50 & N100 REQUIREMENTS



Reaching $N=50$ or $N=100$ forward samples does **not** automatically approve production deployment. Instead, reaching $N=50$ is simply the prerequisite to begin formal statistical hypothesis testing:

- **Sample Size Check**: $N \ge 50$ trades required for Central Limit Theorem stability.

- **Statistical Significance**: $t$-statistic on trade $R$-returns must yield $p < 0.05$.

- **Drift Test**: Population Stability Index (PSI) must be $< 0.10$ across market volatility shifts.



---



## 64. SIGNAL AGGREGATOR SERVICE



Implemented in [`src/services/signal_aggregator.py`](file:///d:/Project/TRADE/src/services/signal_aggregator.py). It synthesizes four analytical components into the authoritative `OverallTradingSignal`:



| Component Layer | BTC Nominal Weight | XAU Nominal Weight | Input Source Model |

| :--- | :---: | :---: | :--- |

| **Component 1: Now Market Technical** | **25%** ($0.25$) | **27%** ($0.27$) | `NowMarketSignal` (Technical + Gemini Confluence) |

| **Component 2: Historical Evidence** | **27%** ($0.27$) | **26%** ($0.26$) | `HistoricalMarketSignal` (Pattern Similarity) |

| **Component 3: ML Shadow Model** | **26%** ($0.26$) | **24%** ($0.24$) | `MLShadowPrediction` (Calibrated Probabilities) |

| **Component 4: Validated Strategy** | **22%** ($0.22$) | **23%** ($0.23$) | `ValidatedStrategyEvaluation` (Rulebook Qualification) |

| **Sum of Nominal Weights** | **100%** ($1.00$) | **100%** ($1.00$) | **Full 4-Component System Synthesis** |



---



## 65. DYNAMIC WEIGHT RE-NORMALIZATION



In real-world operations, specific components may be temporarily unavailable (e.g. historical pattern matching yields $N=0$ qualifying matches, or an ML model is reloading). The platform dynamically re-normalizes active weights:



$$W_{\text{effective}, i} = \frac{W_{\text{nominal}, i}}{\sum_{j \in \text{Available}} W_{\text{nominal}, j}}$$



### Concrete Example (Historical & Strategy Unavailable):

- Active components: Now Market ($0.25$) and ML Model ($0.26$).

- Sum of available weights: $0.25 + 0.26 = 0.51$.

- **Effective Now Market Weight**: $0.25 / 0.51 = 49.0\%$.

- **Effective ML Model Weight**: $0.26 / 0.51 = 51.0\%$.

- Weights sum strictly to $100\%$. No fake numbers or arbitrary defaults are introduced.



---



## 66. AGGREGATOR NET SCORE EQUATION



$$\text{Net Aggregator Score} = \sum_{i \in \text{Available}} \left( W_{\text{effective}, i} \times \text{Directional Value}_i \right)$$



- Directional values: $\text{BUY} = +1.0$, $\text{SELL} = -1.0$, $\text{WAIT} / \text{NEUTRAL} = 0.0$.

- Directional thresholds:

  - $\text{Net Aggregator Score} \ge +20.0\%$ $\implies$ Overall Evidence Bias: **BUY**.

  - $\text{Net Aggregator Score} \le -20.0\%$ $\implies$ Overall Evidence Bias: **SELL**.

  - Otherwise $\implies$ Overall Evidence Bias: **WAIT**.



---



## 67. AGGREGATOR CONFLICT INVARIANCE



If opposing directional forces each hold $\ge 25.0\%$ effective weight (e.g. Now Market is strong BUY but ML is strong SELL), the aggregator immediately forces `OverallTradingSignal.signal = "WAIT"` and sets `percentage = None`. It never forces a misleading $51\%$ coin-flip.



---



## 68. OVERALL EVIDENCE BIAS VS FINAL ACTION



A crucial semantic distinction in the platform:



```text

               ┌─────────────────────────────────────────────────┐

               │    Aggregator Overall Evidence Bias: BUY 51%    │

               │   (Directional alignment before risk gating)    │

               └────────────────────────┬────────────────────────┘

                                        │

                                        ▼

               ┌─────────────────────────────────────────────────┐

               │         Decision Engine Risk Gate Check         │

               │         Quality Gate: Confluence 35 < 58        │

               │                   Result: FAILED                │

               └────────────────────────┬────────────────────────┘

                                        │

                                        ▼

               ┌─────────────────────────────────────────────────┐

               │               FINAL ACTION: WAIT                │

               │ (Execution blocked; capital strictly protected) │

               └─────────────────────────────────────────────────┘

```



The user interface displays `FINAL ACTION: WAIT` as the primary headline, with `Overall Evidence Bias: BUY · 51%` rendered in a secondary pill.



---



## 69. BACKEND DATA MODELS (PYDANTIC SCHEMAS)



Implemented in [`src/models/trading_decision.py`](file:///d:/Project/TRADE/src/models/trading_decision.py):

- **`TradingDecision`**: The authoritative output containing `decision` (`BUY`, `SELL`, `WAIT`), `entry_zone`, `stop_loss`, `tp1`, `tp2`, `risk_level`, `primary_reason`, and gate statuses.

- **`DecisionScoreBreakdown`**: Granular scores for each contributor, timestamp, and asset symbol.

- **`OverallTradingSignal`**: Output of `SignalAggregator` containing `signal`, `percentage`, `confidence`, and component breakdown.

- **`MLShadowPrediction`**: Point-in-time record of ML inference at $T_0$.



---



## 70. FASTAPI ARCHITECTURE



The web API is initialized in [`src/api/main.py`](file:///d:/Project/TRADE/src/api/main.py):

- **CORS Middleware**: Configured for local development (`http://localhost:3000`, `http://127.0.0.1:3000`).

- **Security Dependency**: `src/core/security.py` verifies administrative tokens (`X-Admin-Token`) on mutation endpoints.

- **Global Error Handling**: Sanitizes internal stack traces, returning structured HTTP 500 error envelopes without leaking database credentials.



---



## 71. COMPLETE API ROUTE CATALOG



| Route Path | HTTP Method | Router File | Primary Responsibility | Consumed By Frontend? |

| :--- | :---: | :--- | :--- | :---: |

| `/api/v1/decision` | **GET** | `decision.py` | Full BUY/SELL/WAIT decision, score breakdown, overall signal | **YES (Overall, Insight, Now)** |

| `/api/v1/market/price` | **GET** | `market.py` | Latest live bid/ask price quote | **YES (All Pages)** |

| `/api/v1/market/candles` | **GET** | `market.py` | Multi-timeframe historical OHLCV bars for chart | **YES (CandleChart)** |

| `/api/v1/ml/shadow/observations` | **GET** | `ml_shadow.py` | Realtime and historical ML shadow observations | **YES (ML & Shadow Page)** |

| `/api/v1/ml/shadow/status` | **GET** | `ml_shadow.py` | Active ML model metadata and availability status | **YES (ML & Shadow Page)** |

| `/api/v1/governance/forward-shadow` | **GET** | `governance.py` | Forward strategy paper execution tracking | **YES (ML & Shadow Page)** |

| `/api/v1/governance/summary` | **GET** | `governance.py` | Institutional qualification roadmap & gating status | **YES (Governance Tab)** |

| `/api/v1/backtest/reports` | **GET** | `backtest.py` | Backtest run catalog and statistical summaries | **YES (History Market Page)** |

| `/api/v1/admin/gating/status` | **GET** | `admin_gating.py` | Production gating invariants status | **YES (Overall Page)** |

| `/health` | **GET** | `main.py` | Application health check, uptime, and database ping | **YES (System Status)** |



---



## 72. API REQUEST & RESPONSE EXAMPLE



### Request:

```http

GET /api/v1/decision?symbol=BTC-USD HTTP/1.1

Host: 127.0.0.1:8000

Accept: application/json

```



### Simplified JSON Response:

```json

{

  "symbol": "BTC/USD",

  "decision": "WAIT",

  "entry_zone": null,

  "stop_loss": null,

  "take_profit_1": null,

  "take_profit_2": null,

  "confluence_score": 35,

  "direction_gate_passed": true,

  "conflict_gate_passed": true,

  "quality_gate_passed": false,

  "primary_reason": "BTC Quality Gate: Confluence score (35%) below minimum validated threshold (58%).",

  "overall_signal": {

    "signal": "BUY",

    "percentage": 51,

    "confidence": "MODERATE",

    "components": {

      "Now Market Technical": {"signal": "BUY", "effective_weight": 0.49},

      "ML Shadow Model": {"signal": "BUY", "effective_weight": 0.51}

    }

  }

}

```



---



## 73. FRONTEND ARCHITECTURE (NEXT.JS APP ROUTER)



The user interface is built using Next.js 14.2.4:

- **`src/app/page.tsx`**: Single-page container rendering the 5-tab architecture (`OVERALL`, `MARKET INSIGHT`, `NOW MARKET`, `HISTORY MARKET`, `ML & SHADOW`).

- **`src/components/SignalHeroCard.tsx`**: Authoritative signal card rendering action commands, semantic colors, and price targets.

- **`src/components/CandleChart.tsx`**: Interactive TradingView canvas chart with EMA overlays and S/R levels.

- **`src/hooks/useDashboardData.ts`**: Central data orchestration hook managing network polling, asset switching, and state buffering.



---



## 74. FRONTEND DATA FETCH FLOW



```text

   React Page (page.tsx)

             │ (Invokes)

             ▼

   useDashboardData Hook

             │ (Dispatches request)

             ▼

   Central API Client (api.ts)

             │ (HTTP GET over Port 8000)

             ▼

   FastAPI Endpoints (/decision, /market, /ml/shadow)

             │ (Returns JSON)

             ▼

   JSON Response Envelope

             │ (Validated & Normalized)

             ▼

   React Component State

             │ (Passed via Props)

             ▼

   UI Presentation Cards (SignalHeroCard, MetricLedger, BacktestTable)

```



---



## 75. FRONTEND POLLING & STATE LIFECYCLE



- **Live Market Polling**: 10-second polling interval for `/market/price` and `/decision`.

- **Research Layer Polling**: 30-second polling interval for `/ml/shadow/observations` and `/governance/forward-shadow`.

- **Asset Switching Invariance**: When the user toggles from BTC to XAU, the hook immediately:

  1. Aborts in-flight network requests via `AbortController`.

  2. Wipes existing price quotes, decision state, and candle buffers.

  3. Dispatches clean requests for the newly selected asset, preventing crypto prices from appearing on the gold dashboard.





---



## 76. THE FIVE-PAGE DASHBOARD ARCHITECTURE



The user interface provides exactly FIVE primary navigation tabs in the header (Overview, Signals, Market Intelligence, Historical Performance, and Models & Research). System Governance and administrative status are accessible via the SYSTEM indicator in the header/footer and through Part C of the Models & Research page:



### PAGE 1 — OVERALL: "WHAT SHOULD I KNOW RIGHT NOW?"

- **Purpose**: High-conviction operational summary for the trader.

- **Components**:

  - **Signal Hero Card**: Prominently renders authoritative `FINAL ACTION: WAIT` with neutral styling, displays `Overall Evidence Bias: BUY · 51%` as a secondary indicator, and suppresses price targets to `--`.

  - **Risk & Gates Card**: Displays `WAIT` badge when Quality Gate fails, rendering exact real-time metrics:

    - Direction Gate: `PASSED (BULLISH) · 2/3 Core Consensus (HTF Trend, MTF Alignment)`

    - Conflict Gate: `PASSED · Opposing Weight: 0.0% (<= 25.0%)`

    - Quality Gate: `FAILED · Confluence: 35 pts (>= 58 pts)`

  - **Trade Setup Matrix**: Displays Entry Zone, Stop Loss, TP1, and TP2 (active during BUY/SELL; `--` during WAIT).

  - **Demo Trading Panel**: Allows paper trade execution against live market quotes.



### PAGE 2 — MARKET INSIGHT: "WHY DID THE SYSTEM REACH THIS CONCLUSION?"

- **Purpose**: Explainable reasoning, component weight breakdown, and narrative synthesis.

- **Components**:

  - **4-Component Conviction Ledger**: Shows individual contributions from Now Market, History, ML, and Strategy.

  - **Dynamic Weight Cards**: Explicitly labels **Nominal Weight** vs **Effective (Re-normalized) Weight**, with subtitle: `"Weights re-normalized across currently available components"`.

  - **Gemini AI Structural Narrative**: Displays LLM-generated market reasoning, key support/resistance levels, and invalidation rules.

  - **Architectural Reasoning Flowchart**: Visual diagram tracing data from raw candles to final action.



### PAGE 3 — NOW MARKET: "WHAT DOES CURRENT MARKET ANALYSIS SAY?"

- **Purpose**: Granular real-time technical analysis and 17-contributor breakdown.

- **Components**:

  - **Confluence Metric Pill**: Correctly labeled `Confluence: 46 pts` (never misleadingly called `Total Buy`).

  - **17 Contributor Score Cards**: Displays exact point values, inputs, and directional biases for every factor.

  - **Technical Gauges**: Multi-timeframe EMA status, RSI(14) level, MACD histogram velocity, and ATR volatility.

  - **Smart Money Concepts (SMC) Panel**: Highlights active Fair Value Gaps, liquidity sweeps, and order blocks.



### PAGE 4 — HISTORY MARKET: "WHAT DOES HISTORICAL EVIDENCE SAY?"

- **Purpose**: Empirical backtest verification and statistical sample matching.

- **Components**:

  - **Block A (`CURRENT SETUP HISTORICAL MATCH`)**: Displays similarity against current market conditions:

    - Comparable Setup N: `0`

    - Best Similarity: `65%` (< 75% threshold)

    - Matched Win Rate: `--`

    - Status: `NO QUALIFYING HISTORICAL MATCHES`

  - **Block B (`GLOBAL {ticker} HISTORICAL BASELINE`)**: Displays macro dataset metrics:

    - Labeled: `REFERENCE BASELINE — NOT CURRENT SETUP MATCH RATE`

    - Dataset N: `1,519` (BTC) / `919` (XAU)

    - Baseline Win Rate: `41.7%`

    - Baseline Expectancy: `+0.04R`

    - Profit Factor: `1.12`

  - **Historical Signals Catalog**: Interactive table with `SIGNAL ID` column and `Deduplicate by Unique Bar Timestamp` toggle.



### PAGE 5 — ML & SHADOW: "WHAT DO OUT-OF-SAMPLE MODELS PREDICT?"

- **Purpose**: Machine Learning predictions, forward shadow resolution, and governance tracking.

- **Components**:

  - **Part A (Current ML Output)**: Shows active model identity (BTC: `LogisticRegression`, XAU: `RandomForestClassifier`), calibrated win probability ($42\%$), and feature importance vector.

  - **Part B (ML Shadow Observation Tracking)**: Displays 1,881 continuous shadow observations, 85 resolved out-of-sample trades, and $52.9\%$ directional accuracy (Advisory Only).

  - **Part C (Forward Strategy Governance)**: Displays real forward paper trade accumulation:

    - Clean Forward Evidence: `Clean N = 0 / 50`

    - Quarantined Fixtures: `280 BTC / 199 XAU`

    - Milestone Status: `N50 NOT REACHED`

    - Production Live Trading: `DISABLED`



---



## 77. SIGNAL HERO CARD COMPONENT ARCHITECTURE



Implemented in [`frontend/src/components/SignalHeroCard.tsx`](file:///d:/Project/TRADE/frontend/src/components/SignalHeroCard.tsx):

- **Semantic State Styling**:

  - `BUY`: Emerald green theme (`border-emerald-500/30`, `bg-emerald-500/10`).

  - `SELL`: Crimson red theme (`border-rose-500/30`, `bg-rose-500/10`).

  - `WAIT`: Slate / Amber neutral theme (`border-slate-700`, `bg-slate-900/60`).

  - `LOADING` / `STALE`: Slate pulsing skeleton theme.

- **Action Label Decoupling**: Uses optional `actionLabel` prop to render `FINAL ACTION: WAIT` while allowing secondary components to display underlying evidence bias.



---



## 78. ASSET SWITCHING & CROSS-ASSET ISOLATION



Toggling between BTC and XAU triggers an atomic reset:

1. Active websocket/polling connections clear previous buffers.

2. In-memory state wipes prior candle arrays and price quotes.

3. Hook dispatches requests with explicit symbol parameters (`?symbol=BTC-USD` vs `?symbol=XAU-USD-SPOT`).

4. Result: Zero probability of Bitcoin volatility contaminating Gold support/resistance levels.



---



## 79. CANDLESTICK CHART SYSTEM



Implemented in [`frontend/src/components/CandleChart.tsx`](file:///d:/Project/TRADE/frontend/src/components/CandleChart.tsx):

- **Canvas Rendering**: Powered by TradingView Lightweight Charts for 60fps rendering.

- **Overlays**: Interactive toggles for EMA20, EMA50, EMA200, and institutional horizontal S/R pivot lines.

- **Crosshair Synchrony**: Tooltip displays exact OHLCV values on hover.



---



## 80. DEMO TRADING SIMULATION ENGINE



Implemented in `src/services/paper_trading_service.py` and rendered in `page.tsx`:

- **Independent Simulation**: Maintains user virtual equity, cash balance, and open position ledger.

- **Zero Quant Modification**: Executing demo trades does not alter contributor scores, ML training sets, or decision logic.



---



## 81. DATA STORAGE ARCHITECTURE



| Storage Medium | Path | Content | Mutability | Used By |

| :--- | :--- | :--- | :---: | :--- |

| **SQLite Database** | `data/historical/historical_market_data.db` | Candles, signals, backtest reports, ML observations | **Append-Only** | Backend Services, ML Shadow |

| **State File** | `data/governance_forward_state.json` | Forward paper trade ledger and sample counts | **Protected** | Governance State Machine |

| **Gating State File** | `data/gating_state.json` | Production gating invariants | **Protected** | Admin Gating Route |

| **ML Model Artifacts** | `research/ml/artifacts/BTC/`, `XAU/` | Calibrated models (`.joblib`), metrics, features | **Read-Only** | ML Shadow Service |



---



## 82. IMPORTANT DATABASE TABLES SCHEMA

1. **ohlcv_bars** (9.6M+ rows in historical_market_data.db): (symbol, timeframe, timestamp, open, high, low, close, volume).
2. **historical_signals** (2,438 rows in historical_market_data.db): (signal_id, symbol, timestamp, direction, entry_price, stop_loss, tp1, tp2, confluence_score, outcome, realized_r).
3. **ml_shadow_observations** (3,900 rows across assets): (observation_id, symbol, timestamp_t0, model_name, ml_probability, status, resolved_outcome, brier_loss).
4. **orward_shadow_signals** (479 rows in forward state): (id, symbol, timestamp, decision, status, quarantine_flag, realized_r).

---

## 83. HISTORICAL MULTI-RUN SIGNAL PROVENANCE



In `historical_signals`, identical bar timestamps (e.g. `2023-01-06 20:00 BTC/USD`) exist across 12 distinct historical runs:

- **Root Cause**: Strategy optimization executed multiple backtest iterations over the same historical bars. Each iteration generated a unique `signal_id`.

- **UI Remediation**: The table displays the `SIGNAL ID` column and provides a `Deduplicate by Unique Bar Timestamp` toggle to view either all historical runs or the latest run only. Zero database rows were deleted.



---



## 84. SECURITY ARCHITECTURE & RATE LIMITING



- **Administrative Authorization**: Mutations require a valid `X-Admin-Token` header. Missing or invalid tokens return HTTP 401 Unauthorized.

- **Sliding-Window Rate Limiting**: Implemented via `RateLimiter` ([`src/core/rate_limiter.py`](file:///d:/Project/TRADE/src/core/rate_limiter.py)), enforcing max 10 requests per 60 seconds on administrative endpoints, returning HTTP 429 with `Retry-After` headers.

- **Production Guard**: Live broker routing is blocked in code and configuration (`LIVE_EXECUTION_ENABLED = False`).



---



## 85. PRODUCTION SAFETY INVARIANTS



- **Production Gating**: **`DISABLED`**.

- **Live Broker Execution**: **`DISABLED`**.

- **Safety Guarantee**: The platform functions exclusively as an advisory intelligence terminal and forward shadow research station. Real capital cannot be risked.



---



## 86. TESTING & VERIFICATION ARCHITECTURE



The codebase is protected by comprehensive multi-layered automated tests:

- **Frontend Unit Tests (`npm test`)**: **128 / 128 passed (100%)** covering UI truth, isolation, and formatting.

- **Frontend Production Build (`npm run build`)**: **Exit code 0** (compiled successfully, 0 type errors).

- **Backend Regression Suite (`pytest`)**: **806 / 806 passed (100% in 226.68s)** covering quant engines, ML shadow, security hardening, and API routes.



---



## 87. ILLUSTRATIVE END-TO-END BTC DECISION TRACE



```text

===========================================================================

ILLUSTRATIVE EXAMPLE: BTC/USD LIVE DECISION TRACE (Current Market Snapshot)

===========================================================================

Market Quote: $68,450.00 | ATR(14): $420.00 | Market Regime: TRENDING_BULLISH



1. Contributor Scoring:

   - HTF Trend (1H + 1D bullish)       : +11 pts

   - Market Structure (MSS confirmed)  : + 9 pts

   - Momentum (5m MACD positive)       : + 8 pts

   - MTF Alignment (3/4 aligned)       : + 5 pts

   - S/R Price Action (Bounce support) : + 8 pts

   - Breakout / Retest (Retesting res) : + 6 pts

   - VWAP (Price > VWAP)               : + 4 pts

   - EMA Stack (Bullish alignment)     : + 4 pts

   - RSI (RSI 58.2 in momentum band)   : + 3 pts

   - MACD (Line > Signal)              : + 2 pts

   - Google Gemini AI (Bullish bias)   : + 7 pts

   - Other Factors (Neutral / Unmit.)  : + 0 pts

   -------------------------------------------------

   Gross Bullish Points                :  67 pts

   Gross Bearish Points                :   0 pts

   Confluence Score                    :  67 pts

   Net Directional Score               : +67.0 pts



2. Risk Gates Evaluation:

   - Direction Gate: 2/3 Core Consensus (HTF Trend, MTF Alignment Bullish) ──> PASSED (BULLISH)

   - Conflict Gate : Opposing Weight 0.0% <= 25.0%   ──> PASSED

   - Quality Gate  : Confluence 67 >= 58.0 pts       ──> PASSED



3. Decision Output:

   - FINAL ACTION: BUY

   - Entry Zone  : [$68,303.00, $68,450.00] (Price - 0.35*ATR to Price)

   - Stop Loss   : $67,820.00 (Price - 1.50*ATR = -$630.00)

   - Take Profit 1: $69,458.00 (Price + 2.40*ATR = +$1,008.00, 1.60R)

   - Take Profit 2: $70,214.00 (Price + 4.20*ATR = +$1,764.00, 2.80R)

   - Setup Grade : A+ | Position Size: 10% equity | Risk Level: LOW

===========================================================================

```



---



## 88. ILLUSTRATIVE END-TO-END AGGREGATOR RE-NORMALIZATION



```text

===========================================================================

ILLUSTRATIVE EXAMPLE: DYNAMIC WEIGHT RE-NORMALIZATION

===========================================================================

Asset: BTC/USD

Nominal Base Weights:

  Now Market: 25% | History: 27% | ML Model: 26% | Strategy: 22%



Scenario: Historical Match has N=0 matches (NOT_AVAILABLE);

          Validated Strategy layer has no active setup (NOT_AVAILABLE).



Available Components:

  - Now Market Technical: Nominal Weight = 0.25 (Direction: BUY)

  - ML Shadow Model     : Nominal Weight = 0.26 (Direction: BUY)

  Sum of Available Nominal Weights = 0.25 + 0.26 = 0.51



Effective Weight Calculation:

  - Effective Now Market Weight = 0.25 / 0.51 = 49.0%

  - Effective ML Model Weight   = 0.26 / 0.51 = 51.0%

  Sum of Effective Weights      = 100.0%



Net Aggregator Score:

  (0.490 * +1.0) + (0.510 * +1.0) = +1.00 (+100.0%)



Overall Trading Signal:

  - Signal: BUY

  - Overall Evidence Bias Percentage: 51% (Calibrated probability from ML)

  - Subtitle: "Weights re-normalized across currently available components"

===========================================================================

```





---



## 89. PERCENTAGE SEMANTICS AUDIT



To maintain institutional statistical integrity, different percentages within the platform must never be blended or conflated:



| Percentage Metric | Mathematical Meaning | What it is NOT | Range |

| :--- | :--- | :--- | :---: |

| **Confluence Score** | Gross alignment of the 17 factors ($0–100$). | Not a probability of winning. | $0 - 100\%$ |

| **Historical Win Rate** | $\%$ of historical trades that reached TP1. | Not a guarantee for the current trade. | $0 - 100\%$ |

| **ML Win Probability** | Calibrated model probability $P(y=1 \mid X)$ at $T_0$. | Not an execution command or accuracy rate. | $0.0 - 1.0$ |

| **ML Validation Accuracy** | Historical closed-candle accuracy over resolved test trades. | Not the win probability of the current setup. | $0 - 100\%$ |

| **Overall Evidence Bias** | Multi-component synthesized directional bias. | Not the authoritative trading action. | $0 - 100\%$ |

| **Strategy Validation Score** | Multi-regime walk-forward consistency rating. | Not an intraday signal confidence metric. | $0 - 100\%$ |



---



## 90. MAIN BUSINESS LOGIC SUMMARY



```text

CURRENT MARKET (Technical Indicators + Market Structure + 17 Contributors)

                                  +

HISTORICAL EVIDENCE (Empirical Similarities & Global Baseline Expectancy)

                                  +

MACHINE LEARNING (Calibrated Out-of-Sample Probability at T0)

                                  +

STRATEGY GOVERNANCE (Forward Shadow Paper Validation & Clean N Tracking)

                                  ↓

MULTI-COMPONENT EVIDENCE SYNTHESIS (SignalAggregator Re-normalization)

                                  ↓

TRIPLE SAFETY GATES (Direction Gate + Conflict Gate + Quality Gate)

                                  ↓

FINAL HUMAN-READABLE ACTION COMMAND (BUY / SELL / WAIT)

```



---



## 91. ERROR & FALLBACK HANDLING



1. **Market Feed Outage**: Automatic failover from Binance/GoldPrice.dev to Yahoo Finance.

2. **Gemini Latency or Rate Limit**: Automatic switch to deterministic `FallbackAIProvider`, labeled `GEMINI FALLBACK`.

3. **Missing Historical Matches ($N=0$)**: Suppressed to `--`, dynamically re-normalizing remaining components.

4. **Internal Calculation Exception**: Caught by global handler; fails safe to **`WAIT`**.



---



## 92. PERFORMANCE & LATENCY OPTIMIZATION



- **FastAPI Async Endpoints**: Non-blocking concurrency handling multiple concurrent dashboard sessions.

- **In-Memory Decision Caching**: TTL of 10 seconds prevents duplicate computation under high refresh rates.

- **SQLite WAL Mode**: Write-Ahead Logging allows concurrent readers during background candle ingestion.

- **TradingView Canvas Chart**: Hardware-accelerated rendering avoids DOM bloat on large candle histories.



---



## 93. KNOWN SYSTEM LIMITATIONS



1. **Forward Clean Evidence Accumulation**: Clean forward paper trades are accumulating towards the $N=50$ milestone (`Clean N = 0 / 50`).

2. **Gold Weekend Sessions**: Physical bullion markets close over weekends; spot feeds reflect Friday close until Sunday evening.

3. **No Order-Book Footprint**: Relies on top-of-book and OHLCV klines; does not parse Level-3 order book delta.

4. **Advisory Mode Only**: Live broker connectivity is intentionally disabled in code.



---



## 94. CURRENT GOVERNANCE & READINESS STATE



| Dimension | Current Operational State | Institutional Assessment |

| :--- | :--- | :--- |

| **Software Infrastructure** | **100% OPERATIONAL** | 806 backend tests pass, 128 frontend tests pass, build exit code 0. |

| **Advisory & Research Station** | **100% OPERATIONAL** | Live analysis, indicators, SMC, Gemini, and ML shadow active. |

| **Statistical Proof (Forward)** | **IN PROGRESS (Clean N = 0 / 50)** | Evidence accumulating under real-world market conditions. |

| **Production Live Execution** | **STRICTLY DISABLED** | Live broker orders blocked until $N \ge 50$ and human sign-off. |



---



## 95. GLOSSARY OF TERMS



- **OHLCV**: Open, High, Low, Close, Volume bar representation.

- **EMA**: Exponential Moving Average.

- **RSI**: Relative Strength Index oscillator.

- **MACD**: Moving Average Convergence Divergence.

- **ATR**: Average True Range volatility metric.

- **VWAP**: Volume Weighted Average Price benchmark.

- **BOS**: Break of Structure confirming trend continuation.

- **CHoCH / MSS**: Change of Character / Market Structure Shift confirming trend reversal.

- **FVG**: Fair Value Gap representing price imbalance.

- **OTE**: Optimal Trade Entry ($0.618 - 0.786$ Fibonacci zone).

- **HTF / MTF**: Higher Timeframe (1h/1d) / Multi-Timeframe (5m–1d).

- **Confluence**: Alignment score across multiple independent analytical factors ($0–100$).

- **Expectancy ($E$)**: Average profit/loss in $R$-units per trade over time.

- **$R$-Multiple**: Trade return expressed as a multiple of initial risk ($1\text{R} = \text{Risk}$).

- **OOS**: Out-of-sample data not seen during model training.

- **Platt Scaling**: Logistic calibration of raw model probabilities.

- **$T_0$**: Exact UTC timestamp of the completed bar triggering a prediction.

- **Shadow Validation**: Forward tracking of simulated predictions against future market outcomes.



---



## 96. A–Z FINAL SYSTEM SUMMARY



- **A. Market Data Ingestion**: Live Binance (BTC) and GoldPrice.dev (XAU) streams enter the system.

- **B. Boundary Invariance**: Closed-bar boundary policy prevents lookahead bias.

- **C. Normalization**: Symbols standardized to `BTC/USD` and `XAU-USD-SPOT`.

- **D. Indicator Computation**: TechnicalAnalysisService computes EMA, RSI, MACD, ATR, and VWAP.

- **E. Structure Extraction**: OTEEngine detects swing pivots, BOS, MSS, and liquidity sweeps.

- **F. Contributor Scoring**: ConfluenceEngine scores 16 quantitative factors (0–90 points).

- **G. AI Confirmation**: Google Gemini provides qualitative confirmation (0–10 points).

- **H. Confluence Aggregation**: Sums active factors into gross Confluence Score ($0–100$).

- **I. Direction Gate**: Requires at least 2-of-3 core factor consensus ({HTF Trend, Market Structure, MTF Alignment}).
- **Downstream Directional Threshold**: SignalAggregator applies $|\text{Net Score}| \ge 20.0$ to determine Overall Evidence Bias.

- **J. Conflict Gate**: Rejects setups if opposing contributor weight exceeds $25.0\%$.

- **K. Quality Gate**: Rejects setups if Confluence Score is below $58.0\text{ pts}$.

- **L. Decision Output**: Outputs authoritative action: `BUY`, `SELL`, or `WAIT`.

- **M. Level Generation**: Generates Entry, SL ($1.5\times\text{ATR}$), TP1 ($2.4\times\text{ATR}$), TP2 ($4.2\times\text{ATR}$) or neutralizes to `--` on WAIT.

- **N. Historical Search**: Queries 2,438 historical signals for similar market setups.

- **O. ML Inference**: Calibrated models (LogisticRegression / RandomForest) output win probability at $T_0$.

- **P. Shadow Validation**: Forward evaluation loop tracks 1,881 observations against future candles.

- **Q. Strategy Governance**: ForwardStateMachine accumulates clean forward paper samples ($N \ge 50$).

- **R. Signal Aggregation**: SignalAggregator dynamically re-normalizes available components.

- **S. FastAPI Serialization**: Serves typed Pydantic models over HTTP port 8000.

- **T. Next.js Client**: Central API client manages retries and aborts on asset switch.

- **U. State Isolation**: Wipes cache on BTC/XAU toggle to prevent cross-contamination.

- **V. Formatting Layer**: Renders truthful nulls (`--`) without synthetic fallbacks.

- **W. Five Dashboard Pages**: OVERALL, MARKET INSIGHT, NOW MARKET, HISTORY MARKET, ML & SHADOW.

- **X. Hero Card Prioritization**: Authoritative `FINAL ACTION: WAIT` dominates over evidence bias.

- **Y. Security Hardening**: Admin token authentication and sliding-window rate limiting.

- **Z. Production Gating**: Zero real capital risk; live broker execution strictly disabled.



---



## 97. FILE & FUNCTION REFERENCE APPENDIX



| Subsystem | Primary Source Files | Key Classes / Functions |

| :--- | :--- | :--- |

| **Market Data Ingestion** | `src/services/market_service.py` | `MarketDataService.get_current_price()`, `get_candles()` |

| **Technical Analysis** | `src/services/technical_analysis.py` | `TechnicalAnalysisService.analyze()`, `compute_ema()` |

| **Market Structure & SMC**| `src/services/ote_engine.py` | `OTEEngine.detect_market_structure()`, `detect_sweeps()` |

| **Elliott Wave** | `src/services/elliott_wave_service.py`| `ElliottWaveService.analyze_wave()` |

| **17-Contributor Confluence**| `src/services/confluence_engine.py` | `ConfluenceEngine.calculate_confluence()` |

| **Decision & Risk Gates** | `src/services/decision_engine.py` | `DecisionEngine.evaluate()`, `_calculate_levels()` |

| **Gemini AI Provider** | `src/services/ai/gemini_provider.py` | `GeminiAIProvider.generate_analysis()` |

| **Historical Evidence** | `src/services/historical_evidence_service.py`| `HistoricalEvidenceService.find_similar_setups()` |

| **ML Shadow Service** | `src/research/ml_shadow/shadow_service.py`| `MLShadowService.generate_prediction()`, `resolve()` |

| **Strategy Governance** | `src/research/governance/forward_state_machine.py`| `ForwardStateMachine.record_trade()`, `check_milestones()` |

| **Signal Aggregator** | `src/services/signal_aggregator.py` | `SignalAggregator.aggregate()`, `get_base_weights()` |

| **FastAPI App** | `src/api/main.py`, `src/api/routes/` | `create_app()`, `get_decision()`, `get_price()` |

| **Frontend API Client** | `frontend/src/services/api.ts` | `request()`, `getDecision()`, `getMarketPrice()` |

| **Frontend Dashboard Hook**| `frontend/src/hooks/useDashboardData.ts`| `useDashboardData()` |

| **Formatting & Utilities** | `frontend/src/lib/format.ts`, `relativeTime.ts` | `formatPercent()`, `formatRelativeTime()` |



---



## 98. MATHEMATICAL EQUATION APPENDIX



1. **Exponential Moving Average (EMA)**:

   $$\alpha = \frac{2}{N + 1}, \quad \text{EMA}_t = \alpha \cdot P_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$$

2. **Relative Strength Index (RSI)**:

   $$\text{RS} = \frac{\text{Avg Gain}}{\text{Avg Loss}}, \quad \text{RSI} = 100 - \frac{100}{1 + \text{RS}}$$

3. **Average True Range (ATR)**:

   $$\text{TR} = \max(H - L,\; |H - C_{-1}|,\; |L - C_{-1}|), \quad \text{ATR}_t = \frac{\text{ATR}_{t-1} \cdot 13 + \text{TR}_t}{14}$$

4. **Volume Weighted Average Price (VWAP)**:

   $$\text{VWAP} = \frac{\sum (P_i \cdot V_i)}{\sum V_i}$$

5. **Confluence Score ($0–100$)**:

   $$\text{Confluence} = \max\left( \sum \text{Points}_{\text{bullish}},\; \sum \text{Points}_{\text{bearish}} \right)$$

6. **Direction Gate (ConfluenceEngine 2-of-3 Consensus)**:

   $$\text{Gate Passed} = (\text{gate\_bullish} \ge 2) \lor (\text{gate\_bearish} \ge 2) \quad \text{from } \{\text{HTF Trend}, \text{Market Structure}, \text{MTF Alignment}\}$$

7. **SignalAggregator Directional Threshold (Downstream Evidence Bias)**:

   $$|\text{Net Aggregator Score}| \ge 20.0\text{ pts} \implies \text{Directional Evidence Bias (BUY/SELL)}$$

8. **Conflict Gate**:

   $$\frac{\text{Opposing Points}}{\text{Total Active Points}} \le 25.0\%$$

8. **Quality Gate**:

   $$\text{Confluence Score} \ge 58.0\text{ pts}$$

9. **Risk/Reward Ratios**:

   $$\text{R:R}_{\text{TP1}} = \frac{2.40 \times \text{ATR}}{1.50 \times \text{ATR}} = 1.60\text{R}, \quad \text{R:R}_{\text{TP2}} = \frac{4.20 \times \text{ATR}}{1.50 \times \text{ATR}} = 2.80\text{R}$$

10. **Mathematical Expectancy ($E$)**:

    $$E = (P_{\text{win}} \times \overline{R}_{\text{win}}) - (P_{\text{loss}} \times 1.0\text{R})$$

11. **Profit Factor**:

    $$\text{PF} = \frac{\sum \text{Gross Profits}}{\sum \text{Gross Losses}}$$

12. **Brier Score**:

    $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (P_i - y_i)^2$$

13. **Platt Scaling Probability Calibration**:

    $$P(y=1 \mid X) = \frac{1}{1 + e^{-(a \cdot f(X) + b)}}$$

14. **Dynamic Aggregator Effective Weight**:

    $$W_{\text{effective}, i} = \frac{W_{\text{nominal}, i}}{\sum_{j \in \text{Available}} W_{\text{nominal}, j}}$$

15. **Net Aggregator Score**:

    $$\text{Net Score} = \sum_{i} (W_{\text{effective}, i} \times \text{Directional Value}_i)$$



---



## 99. FINAL ARCHITECTURAL SUMMARY



```text

       BACKEND LAYER

       - Live Ingestion (Binance & GoldPrice.dev)

       - Technical Analysis & Smart Money Concepts

       - 17 Contributor Scoring Matrix (0–100 pts)

       - Google Gemini AI Analysis (<= 10 pts)

       - Triple Safety Gates (Direction, Conflict, Quality)

       - Decision Engine (BUY / SELL / WAIT)

       - Trade Setup Generator (1.6R / 2.8R)

       - Historical Backtest Matching (2,438 Signals)

       - Calibrated ML Shadow Inference (T0 Locking)

       - Strategy Governance (N50 Tracking)

       - Multi-Component Signal Aggregator

       - FastAPI High-Concurrency Web Endpoints

                         │

                         │ JSON over HTTP (Port 8000)

                         ▼

       FRONTEND LAYER

       - Central Typed API Client (api.ts)

       - Unified Polling Hook (useDashboardData.ts)

       - Strict Asset Isolation (BTC <-> XAU)

       - Semantic Formatters (format.ts, relativeTime.ts)

       - TradingView Canvas Candlestick Chart

       - Page 1: OVERALL (Authoritative Decision & Risk Gates)

       - Page 2: MARKET INSIGHT (Dynamic Conviction Ledger)

       - Page 3: NOW MARKET (17 Contributors & Indicators)

       - Page 4: HISTORY MARKET (Setup Match vs Global Baseline)

       - Page 5: ML & SHADOW (3-Layer Architecture & Governance)

```

