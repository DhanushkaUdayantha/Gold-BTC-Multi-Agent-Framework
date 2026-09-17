# PROJECT BACKEND <-> FRONTEND MASTER FLOW

**Document ID:** TRADE-DOC-MASTER-FLOW-20260916  
**Date:** September 16, 2026 (Updated Post-Repair: September 17, 2026)  
**Repository:** D:\Project\TRADE  
**System:** BTC/XAU AI Trading Analysis Platform  
**Purpose:** Single authoritative end-to-end flow diagram and step-by-step trace from external raw market feeds through backend quantitative, ML, AI, and historical pipelines to the five Next.js frontend pages.

---

## 1. THE MASTER ARCHITECTURE FLOW GRAPH

`	ext
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
 │   - MarketDataService (src/services/market_service.py): Ingestion, 429 backoff, fallback failover             │
 │   - LiveCandleIngestionService (src/services/live_candle_ingestion_service.py): Incremental SQLite candle save│
 │   - Symbol Normalizer: BTCUSDT, BTC-USD, BTC/USD -> BTC/USD | XAUUSD, XAU-USD-SPOT -> XAU-USD-SPOT │
 │   - Strict Closed-Bar Boundary: Evaluates ONLY completed bars (5m, 15m, 1h, 1d); zero lookahead into open bar    │
 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                      TECHNICAL ANALYSIS & STRUCTURE ENGINES                                      │
 │                                                                                                                  │
 │   1. TechnicalAnalysisService (src/services/technical_analysis.py):                                            │
 │      - Trend Indicators: EMA20, EMA50, EMA200, EMA Stack Bias                                                    │
 │      - Oscillators: RSI(14) with overbought/oversold bands, MACD (12, 26, 9) line & histogram                   │
 │      - Volatility & Benchmark: ATR(14) for volatility stops/targets, Volume vs 20-period moving average          │
 │      - S/R Pivot Detector: Swing highs/lows over rolling N-bar pivot windows                                     │
 │   2. OTE & Smart Money Concepts Engine (src/services/ote_engine.py):                                           │
 │      - Market Structure: Higher Highs, Higher Lows, Lower Highs, Lower Lows, BOS, CHoCH / MSS                   │
 │      - ICT / SMC Liquidity: Previous Day High/Low (PDH/PDL) sweeps, Fair Value Gaps (FVG), Order Blocks         │
 │      - Fibonacci OTE: Optimal Trade Entry calculation (0.618 - 0.786 retracement range)                          │
 │   3. Elliott Wave Service (src/services/elliott_wave_service.py):                                              │
 │      - Heuristic wave identification (Impulse 1-2-3-4-5 vs Corrective A-B-C phases; Mag 4 + Bias)                │
 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                         THE 17-CONTRIBUTOR SCORING MATRIX                                        │
 │                                      (src/services/confluence_engine.py)                                       │
 │                                                                                                                  │
 │   [TECHNICAL & STRUCTURAL FACTORS: Max 90 Pts]                  [AI CONFIRMATION FACTOR: Max 10 Pts]             │
 │   1. HTF Trend (1H/1D)         : 11 pts                         17. Google Gemini AI Analysis : 10 pts           │
 │   2. Market Structure (BOS/MSS):  9 pts                             (src/services/ai/gemini_provider.py)       │
 │   3. Momentum (5m MACD/Trend)  :  8 pts                             - Model: gemini-3.1-flash-lite             │
 │   4. MTF Alignment (5m-1h)     :  8 pts (4/4=8, 3/4=6)              - Output: Bias, Score, Key Levels, Risk      │
 │   5. S/R Price Action Proximity:  8 pts                             - Safety Cap: Strictly <= 10.0 pts           │
 │   6. Breakout / Retest         :  6 pts                             - Fallback: FallbackAIProvider (amber)     │
 │   7. Supply & Demand Zones     :  5 pts                                                                          │
 │   8. Volume Confirmation       :  5 pts                                                                          │
 │   9. SMC / ICT Liquidity Sweep :  5 pts                                                                          │
 │  10. ICT Concepts (PDH/PDL)    :  4 pts                                                                          │
 │  11. Fibonacci OTE (0.618-786) :  4 pts                                                                          │
 │  12. Elliott Wave Phase        :  4 pts (Score Mag 4 + Bias)                                                     │
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
 │                                      (src/services/decision_engine.py)                                         │
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
 │           (src/services/decision_engine.py)          │ │                                                       │
 │                                                        │ │   1. Historical Evidence Engine                       │
 │   If Action == BUY:                                    │ │      (src/services/historical_evidence_service.py)  │
 │     - Entry Zone = [Price - 0.35*ATR, Price]           │ │      - Database: historical_market_data.db          │
 │     - Stop Loss  = Price - 1.50*ATR                    │ │      - Block A: Pattern Match (Score-Band +/- 1)      │
 │     - TP1 Target = Price + 2.40*ATR (1.60 R:R)         │ │      - Block B: Canonical Baseline (BTC 1032, XAU 893)│
 │     - TP2 Target = Price + 4.20*ATR (2.80 R:R)         │ │                                                       │
 │                                                        │ │   2. ML Shadow Validation Engine                      │
 │   If Action == SELL:                                   │ │      (src/research/ml_shadow/shadow_service.py)     │
 │     - Entry Zone = [Price, Price + 0.35*ATR]           │ │      - BTC: LogisticRegression | XAU: RandomForest    │
 │     - Stop Loss  = Price + 1.50*ATR                    │ │      - Target: Binary Trade Setup WIN / LOSS Outcome  │
 │     - TP1 Target = Price - 2.40*ATR (1.60 R:R)         │ │      - T0 Immutable Observation Snapshot (ID Hash)    │
 │     - TP2 Target = Price - 4.20*ATR (2.80 R:R)         │ │      - Forward resolution on closed candles           │
 │                                                        │ │                                                       │
 │   If Action == WAIT:                                   │ │   3. Strategy Governance & Forward Tracker            │
 │     - Entry, Stop Loss, TP1, TP2 = None (--)         │ │      (src/research/governance/forward_state_machine)│
 │     - Eliminates misleading speculative targets        │ │      - Clean Forward Evidence: Clean N / 50 Target    │
 │                                                        │ │      - Quarantined Fixtures (Developmental Benchmark) │
 └────────────────────────────┬───────────────────────────┘ └───────────────────────────┬─────────────────────────┘
                              │                                                       │
                              └───────────────────────────┬───────────────────────────┘
                                                          │
                                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   MULTI-COMPONENT SIGNAL AGGREGATOR SERVICE                                      │
 │                                      (src/services/signal_aggregator.py)                                       │
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
 │   -> Generates Authoritative OverallTradingSignal (Directional Evidence Bias + Magnitude %)                    │
 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                        FASTAPI APPLICATION HTTP REST TIER                                        │
 │                                             (src/api/main.py:8000)                                             │
 │                                                                                                                  │
 │   - GET /api/v1/decision?symbol={sym}               : Authoritative TradingDecision + OverallTradingSignal     │
 │   - GET /api/v1/market/price, /candles            : Live quotes and multi-timeframe OHLCV bars               │
 │   - GET /api/v1/ml/shadow/observations?symbol={sym} : Realtime ML observations & resolved shadow accuracy     │
 │   - GET /api/v1/governance/forward-shadow           : Forward governance tracking (Clean N vs Quarantined)     │
 │   - GET /api/v1/backtest/reports                    : Historical backtest run catalog & signal logs            │
 │   - GET /api/v1/admin/gating/status                 : Gating Invariants (Production Gating = DISABLED)         │
 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                          │
                                                          │ JSON over HTTP (Port 8000 / 3000)
                                                          │
                                                          ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                         NEXT.JS FRONTEND ARCHITECTURE                                            │
 │                                      (rontend/src/ Next.js 14.2.4)                                            │
 │                                                                                                                  │
 │   1. Central API Client (src/services/api.ts): Typed REST client, automatic retry, timeout protection          │
 │   2. State Hook (src/hooks/useDashboardData.ts):                                                               │
 │      - Unified polling interval: 10s price/decision, 30s ML/governance                                           │
 │      - Strict Asset Isolation: Switching BTC <-> XAU resets all buffers; zero cross-contamination                │
 │   3. Semantic Formatting Layer (src/lib/format.ts, 
elativeTime.ts):                                         │
 │      - Truthful null handling: Missing percentages render '--%', never fake 50% or 100%                          │
 │      - Relative time formatting: Anchored to backend candle timestamps, never wall-clock time                    │
 └────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                          │
                     ┌───────────────────┬────────────────┼───────────────────┬───────────────────┐
                     ▼                   ▼                ▼                   ▼                   ▼
 ┌───────────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐ ┌────────────────────────┐
 │        PAGE 1         │ │      PAGE 2      │ │      PAGE 3      │ │     PAGE 4      │ │         PAGE 5         │
 │        OVERALL        │ │MARKETINTELLIGENCE│ │    NOW MARKET    │ │HISTORICAL PERF  │ │   MODELS & RESEARCH    │
 │                       │ │                  │ │                  │ │                 │ │                        │
 │ - Hero Card:          │ │ - Conviction     │ │ - Confluence:    │ │ - Block A:      │ │ - Part A:              │
 │   FINAL ACTION        │ │   Ledger (4-Part)│ │   Confluence Pts │ │   Matched Setups│ │   Current ML Output    │
 │   (BUY / SELL / WAIT) │ │ - Dynamic Weights│ │ - 17 Contributor │ │   Score-Band +/-1 │   Win Prob % (Calib)   │
 │ - Evidence Pill:      │ │   (Nominal vs    │ │   Score Cards    │ │   N_pattern     │ - Part B:              │
 │   Direction * Mag %   │ │   Effective)     │ │ - MTF Gauges     │ │ - Block B:      │ │   ML Shadow Validation │
 │ - Action Levels:      │ │ - Gemini AI      │ │   (4/4=8, 3/4=6) │ │   Canonical Run │ │   Observation Log      │
 │   Entry/SL/TP (or --)││   Narrative /    │ │ - Technical      │ │   Baseline      │ │   Resolved Trades Acc  │
 │ - Risk & Gates Badge: │ │   Fallback       │ │   Indicators &   │ │   (BTC/XAU N)   │ - Part C:              │
 │   Direction, Conflict,│ │ - Overall Metric:│ │   S/R Pivots     │ │ - Backtest Logs:│ │   Strategy Governance  │
 │   Quality Gate Status │ │   Evidence Bias  │ │ - Risk Gates:    │ │   Signal ID Col │ │   Clean N / 50 Target  │
 │ - Setup Matrix Table  │ │                  │ │   Pass / Fail    │ │   Canonical Run │ │   Gating: DISABLED     │
 │ - Demo Trading Panel  │ │                  │ │   Breakdown      │ │   Isolation     │ │                        │
 └───────────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────────┘ └────────────────────────┘
========================================================================================================================
`

---

## 2. STEP-BY-STEP TRACE: EXTERNAL MARKET FEED TO FIVE UI PAGES

The journey of market data through the platform follows 13 explicit, sequential operations:

### Step 1: External Provider Delivers Raw Market Feeds
- **BTC/USD**: Polled from Binance Public REST API (https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT for spot price; https://api.binance.com/api/v3/klines for historical candles). Fallback provider: Yahoo Finance (BTC-USD).
- **XAU/USD**: Polled from GoldPrice.dev API (https://api.goldprice.dev/v1/gold-price for live bid/ask). Fallback provider: Yahoo Finance (GC=F continuous gold futures).

### Step 2: Backend Normalization & Candle Boundary Invariance
- Handled by MarketDataService ([src/services/market_service.py](file:///d:/Project/TRADE/src/services/market_service.py)).
- **Symbol Normalization**: Canonical asset names BTC/USD and XAU-USD-SPOT map all incoming query variations (BTCUSDT, BTC-USD, XAUUSD).
- **Closed-Bar Boundary Policy**: The decision engine strictly evaluates **closed, completed candles** across the **Core Decision Quartet** (`5m`, `15m`, `1h`, `1d`). Auxiliary market/data support includes `1m`. Historical archive candles (`4h`) exist in stored database records but are not part of the active decision quartet. Timeframe `1w` is not supported in the current implementation. The currently forming (open) bar is never used to confirm breakout, RSI, or MACD signals, eliminating lookahead bias.

### Step 3: Multi-Timeframe Technical & Structural Calculation
- Handled by TechnicalAnalysisService ([src/services/technical_analysis.py](file:///d:/Project/TRADE/src/services/technical_analysis.py)) and OTEEngine ([src/services/ote_engine.py](file:///d:/Project/TRADE/src/services/ote_engine.py)).
- Produces mathematical values for EMA (20, 50, 200), RSI(14), MACD (12, 26, 9), ATR(14), VWAP, swing pivot support/resistance levels, Fair Value Gaps (FVG), Previous Day High/Low sweeps (PDH/PDL), and Market Structure Shifts (BOS/MSS).
- ElliottWaveService provides wave phase identification heuristics (Impulse Waves 1-5 vs Corrective Waves A-C), represented as a 4-point magnitude score coupled with directional bias (e.g., magnitude 4 + BEARISH bias).

### Step 4: 17-Contributor Scoring & Confluence Math
- Handled by ConfluenceEngine ([src/services/confluence_engine.py](file:///d:/Project/TRADE/src/services/confluence_engine.py)).
- Evaluates the 16 quantitative/structural contributors (up to 90 points total). Each contributor inspects multi-timeframe state and awards points with a directional bias (BULLISH, BEARISH, NEUTRAL).
- **Contributor 4 (MTF Alignment)**: Accurately scales to its declared maximum of 8 points using the formula score = round((dominant / total) * 8) if total > 0 else 0. Under 4 timeframes, 4/4 agreement awards 8 points, 3/4 awards 6 points, while conflicting splits (2/2) receive 2 points with conflict penalties applied.

### Step 5: Bounded Gemini AI Market Analysis
- Handled by AIMarketAnalysisService ([src/services/ai_service.py](file:///d:/Project/TRADE/src/services/ai_service.py)) and GeminiAIProvider ([src/services/ai/gemini_provider.py](file:///d:/Project/TRADE/src/services/ai/gemini_provider.py)).
- Google Gemini (gemini-3.1-flash-lite) receives structured multi-timeframe JSON and provides qualitative confirmation, awarded up to a strict maximum of **10.0 points** (Contributor 17).
- If API key is missing, network fails, or rate limits apply, FallbackAIProvider cleanly produces rule-based synthetic sentiment marked as GEMINI FALLBACK.

### Step 6: Decision Engine & Triple Safety Gate Enforcement
- Handled by DecisionEngine ([src/services/decision_engine.py](file:///d:/Project/TRADE/src/services/decision_engine.py)).
- Evaluates candidate signal direction via Net Score = Bullish Points - Bearish Points.
- **Direction Gate (ConfluenceEngine)**: Requires at least 2 of 3 core directional contributors to agree ({HTF Trend, Market Structure, MTF Alignment}), conceptually `gate_passed = gate_bullish >= 2 or gate_bearish >= 2`. There is NO `|Net Score| >= 20` requirement in this upstream gate.
- **Conflict Gate**: Requires Opposing Contributor Weight <= 25.0%.
- **Quality Gate**: Requires Confluence Score >= 58.0 pts.
- **SignalAggregator Directional Threshold**: Separately, the downstream `SignalAggregator` enforces `DIRECTIONAL_THRESHOLD = 20.0` to determine Overall Trading Signal / Evidence Bias (Net Score >= +20 → BUY bias, <= -20 → SELL bias, else WAIT / sub-threshold evidence state). The `SignalAggregator` threshold does NOT control the upstream `ConfluenceEngine` Direction Gate.
- If any safety gate fails, authoritative action becomes **WAIT**.

### Step 7: Trade Setup Generation & Neutralization
- If all gates pass, calculates Entry Zone, Stop Loss (1.5 x ATR), TP1 (2.4 x ATR / 1.6R), and TP2 (4.2 x ATR / 2.8R).
- If action is **WAIT**, all trade levels are suppressed to None (--), preventing traders from acting on unconfirmed setups.

### Step 8: Downstream Evidence Generation (Historical, ML, Governance)
- **Historical Evidence**: HistoricalEvidenceService queries data/historical/historical_market_data.db to check for matching patterns using categorical score-band (±1 pt) and market regime matching (with $N \ge 10$ significance rule). The historical baseline is explicitly pinned per asset in configuration to a human-reviewed canonical run (`HISTORICAL_CANONICAL_RUN_BTC: RUN-BTC-USD-20260831-173607`, $N = 1,032$; `HISTORICAL_CANONICAL_RUN_XAU: RUN-XAU-USD-20260831-174452`, $N = 893$). These are current verified canonical baseline IDs (not permanent universal constants). New exploratory or completed backtests do NOT automatically replace the canonical baseline. If a pinned run is missing or invalid, resolution fails closed (returning UNAVAILABLE/INSUFFICIENT with zero fallback promotion), eliminating cross-run inflation while keeping all 2,438 SQLite rows 100% intact (0 rows deleted, 0 updated).
- **ML Shadow Prediction**: MLShadowService computes out-of-sample probability using calibrated scikit-learn models (BTC: LogisticRegression, XAU: RandomForestClassifier) targeting binary trade setup outcome (WIN/LOSS). It locks an immutable T0 observation snapshot into SQLite.
- **Forward Strategy Governance**: ForwardStateMachine tracks forward paper trades, maintaining isolation between clean forward samples (Clean N / 50) and quarantined developmental fixtures.

### Step 9: Multi-Component Signal Aggregation
- Handled by SignalAggregator ([src/services/signal_aggregator.py](file:///d:/Project/TRADE/src/services/signal_aggregator.py)).
- Dynamically re-normalizes base component weights across active components (Now Market Technical, Historical Evidence, ML Shadow, Strategy Evidence) to produce OverallTradingSignal (Overall Evidence Bias, e.g. BUY 51%).
- **Semantic Clarification**: The 51% figure represents the Net Directional Score magnitude $\\text{round}(|\\text{net\_score}|)$ across available components, NOT a calibrated ML probability.

### Step 10: FastAPI Serialization & HTTP REST Endpoints
- Handled by src/api/main.py and routers in src/api/routes/ (93 registered REST endpoints).
- Serializes Pydantic domain models into clean JSON schemas and serves them on http://127.0.0.1:8000.

### Step 11: Next.js API Client Fetch & Asset Isolation
- Handled by rontend/src/services/api.ts and useDashboardData.ts.
- Executes parallel asynchronous requests with timeout protection and automatic failover. When the user switches between BTC and XAU, state buffers are wiped to prevent cross-contamination.

### Step 12: Formatting & Semantic Validation Layer
- Handled by src/lib/format.ts and src/lib/relativeTime.ts.
- Formats currency, R-multiples, and timestamps. Renders -- for missing percentages, never substituting misleading fallback numbers.

### Step 13: Presentation Across the Five Authoritative UI Pages
1. **OVERALL Page**: Displays authoritative FINAL ACTION (BUY / SELL / WAIT) in the hero card, moves directional bias to Overall Evidence Bias, suppresses price levels to -- on WAIT, displays Gate Status in the Risk & Gates card, and provides Demo Trading execution.
2. **MARKET INTELLIGENCE Page**: Presents the 4-component conviction ledger, dynamic component weights with nominal vs effective labeling, Gemini narrative or fallback status, and architectural reasoning flowchart.
3. **NOW MARKET / SIGNALS Page**: Displays the live Confluence metric, the 17 contributor score cards, technical indicator gauges (EMA, RSI, MACD, ATR, VWAP), and SMC/ICT structure breakdowns.
4. **HISTORICAL PERFORMANCE Page**: Strictly segregates **Block A** (CURRENT SETUP HISTORICAL MATCH: categorical score-band match N, win rate, expectancy) from **Block B** (CANONICAL HISTORICAL BASELINE: canonical completed run N, win rate, expectancy). Backtest signals table exposes SIGNAL ID and isolates canonical runs.
5. **MODELS & RESEARCH Page**: Displays the 3-layer architecture: **Part A** (Current ML Output: calibrated win probability %), **Part B** (ML Shadow Accumulation: continuous observations, resolved out-of-sample directional trades, accuracy), and **Part C** (Strategy Governance: Clean forward sample progress vs N=50 target, Production Gating: DISABLED).

---

## 3. EXAMPLE RUNTIME SNAPSHOT (PORT 8000 LIVE API)

`	ext
========================================================================================================================
                               EXAMPLE RUNTIME SNAPSHOT (SYNCHRONOUS API CAPTURE)
Captured: 2026-09-17T01:14:00Z
Target Asset: BTC/USD
========================================================================================================================
- Spot Market Price       : ,432.50
- Technical Score (16 ctx): 40.0 pts / 90.0 pts max
- Gemini AI Score (1 ctx) : 6.0 pts / 10.0 pts max
- Total Confluence Score  : 46.0 pts / 100.0 pts max
- MTF Alignment Contrib   : 8.0 pts / 8.0 pts max (4/4 Multi-Timeframe Consensus: BULLISH)
- Direction Gate Status   : PASS (2/3 Core Contributor Consensus: HTF Trend + MTF Alignment Bullish)
- Conflict Gate Status    : PASS (Opposing Bearish Weight = 18.2% <= 25.0% threshold)
- Quality Gate Status     : FAIL (Confluence 46.0 pts < 58.0 pts threshold)
- Authoritative Action    : WAIT (Quality Gate unmet)
- Trade Setup Levels      : Entry / Stop Loss / TP1 / TP2 = None (--)
- Signal Aggregator Output: Overall Evidence Bias = BUY 51% (Net Directional Score Magnitude)
- Canonical Historical N  : N = 1,032 (Win Rate: 44.1%, Avg R: +0.102R, Expectancy: +0.103R, Profit Factor: 1.18)
- ML Shadow Observations  : Continuous Observations = 1,893 (BTC-only), Resolved Directional Trades = 85 (52.9% Acc)
- Forward Strategy Status : Clean N = 0 / 50 (Target N=50 Unmet; Production Gating = DISABLED)
========================================================================================================================
`
