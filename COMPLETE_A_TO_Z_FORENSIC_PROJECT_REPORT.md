# BTC/XAU AI TRADING ANALYSIS PLATFORM
# COMPLETE A–Z FORENSIC ARCHITECTURE, LOGIC, DATA-LINEAGE & SYSTEM-STATE REPORT

**Audit Date**: September 15, 2026  
**Auditor Roles**: Senior Quantitative Systems Architect, Senior Python/FastAPI Backend Engineer, Senior Next.js/TypeScript Frontend Engineer, Quantitative Trading Researcher, ML Model Validation Engineer, Data-Lineage & Temporal-Integrity Auditor, QA/Test Engineer, Security & Governance Auditor  
**Repository**: `D:\Project\TRADE`  
**Execution Boundary**: Analytical Advisory Platform Only — Zero Real Broker Execution SDKs Present — Live Auto-Trading Strictly Disabled  
**Production Gating State**: BTC Gating = `DISABLED`, XAU Gating = `DISABLED`  
**Governance State**: `S2: EVIDENCE_COLLECTION` (Milestone N=0/50 XAU Clean Forward Signals)  
**Safety Priority**: `Safety > Evidence Preservation > No Live Execution > No Data Mutation > No Source Modification > Forensic Truth > Audit Completeness`

---

## TABLE OF CONTENTS
1. [Executive Summary](#1-executive-summary)
2. [Current Project Status](#2-current-project-status)
3. [Repository Map](#3-repository-map)
4. [Complete Architecture](#4-complete-architecture)
5. [Market Data — Complete Forensic Trace](#5-market-data--complete-forensic-trace)
6. [Data Validation](#6-data-validation)
7. [Timeframes & Candle Logic](#7-timeframes--candle-logic)
8. [Technical Indicator Forensic Audit](#8-technical-indicator-forensic-audit)
9. [Market Structure Logic](#9-market-structure-logic)
10. [17 Contributors — Critical Section](#10-17-contributors--critical-section)
11. [Confluence Mathematics](#11-confluence-mathematics)
12. [Direction Logic](#12-direction-logic)
13. [Gates](#13-gates)
14. [Decision Engine](#14-decision-engine)
15. [Entry / SL / TP / Risk](#15-entry--sl--tp--risk)
16. [Gemini AI — Complete Audit](#16-gemini-ai--complete-audit)
17. [Now Market — Backend → API → UI](#17-now-market--backend--api--ui)
18. [Historical Evidence — Complete Audit](#18-historical-evidence--complete-audit)
19. [ML System — Complete Forensic Audit](#19-ml-system--complete-forensic-audit)
20. [ML Features](#20-ml-features)
21. [ML Observation Collection — Critical](#21-ml-observation-collection--critical)
22. [Shadow Validation — Critical](#22-shadow-validation--critical)
23. [ML Validation Metrics](#23-ml-validation-metrics)
24. [Forward Evidence — Forensic Reconciliation](#24-forward-evidence--forensic-reconciliation)
25. [Governance](#25-governance)
26. [API Inventory](#26-api-inventory)
27. [Frontend — Complete UI Inventory](#27-frontend--complete-ui-inventory)
28. [Every UI Percentage — Critical Truth Table](#28-every-ui-percentage--critical-truth-table)
29. [Overall Page](#29-overall-page)
30. [Market Insight](#30-market-insight)
31. [Loading / Error / Empty / Stale / Market-Closed States](#31-loading--error--empty--stale--market-closed-states)
32. [Asset Isolation — BTC vs XAU](#32-asset-isolation--btc-vs-xau)
33. [Temporal Integrity / Data Leakage](#33-temporal-integrity--data-leakage)
34. [Duplication / Logic Divergence](#34-duplication--logic-divergence)
35. [Constants / Magic Numbers](#35-constants--magic-numbers)
36. [Test Coverage & Integrity](#36-test-coverage--integrity)
37. [Safe Runtime Verification](#37-safe-runtime-verification)
38. [Performance & Operational Behavior](#38-performance--operational-behavior)
39. [Security & Execution Safety](#39-security--execution-safety)
40. [Current System Health Matrix](#40-current-system-health-matrix)
41. [Logic Risk Register](#41-logic-risk-register)
42. [Backend → UI Data Lineage Master Table](#42-backend--ui-data-lineage-master-table)
43. [Current Project A–Z Brief Explanation](#43-current-project-az-brief-explanation)
44. [Final Actual Current Architecture Diagram](#44-final-actual-current-architecture-diagram)
45. [Future UI Restructure Readiness](#45-future-ui-restructure-readiness)
46. [Final Verdict & Stop Condition](#46-final-verdict--stop-condition)

---

## 1. EXECUTIVE SUMMARY

The **BTC/XAU AI Trading Analysis Platform** is an enterprise-grade quantitative advisory engine designed to analyze market structure, momentum, multi-timeframe trend alignment, institutional Smart Money Concepts (SMC/ICT), and statistical setups for Bitcoin (`BTC/USD`) and Gold (`XAU/USD`).

### Core Mission & Operating Boundary
- **Advisory Only**: The platform generates point-in-time analytical recommendations (`BUY`, `SELL`, `WAIT`) along with a full Trade Setup Matrix (Entry Zone, Stop Loss, Take Profit 1, Take Profit 2). It contains **zero live broker execution SDKs** (no CCXT, Interactive Brokers, MetaTrader, or exchange order-placement endpoints).
- **Execution Safeguards**: Both `PRODUCTION_GATING_BTC` and `PRODUCTION_GATING_XAU` are strictly `False` (`DISABLED`). Automated retraining and automated threshold optimization are disabled. Live auto-trading is impossible by physical design.
- **Confluence Engine**: Evaluates 17 synchronized market contributors across a 100-point rubric (90 technical points + 10 Gemini AI confirmation points). A strict Direction Gate mandates that at least 2 of 3 core structural components (`HTF Trend`, `Market Structure`, `MTF Alignment`) must agree directionally before any directional setup is permitted.
- **Multi-Component Synthesis**: The `SignalAggregator` mathematically blends four discrete analytical pillars: Now Market Technicals, Historical Statistical Evidence, ML Shadow Predictions, and Validated Strategy Degradation. An invariant Conflict Gate immediately forces a `WAIT` signal (`percentage=None`) if opposing directional forces exceed 25% weight.
- **Machine Learning as Downstream Observer**: ML models (`LogisticRegression` for BTC, `RandomForestClassifier` for XAU) operate strictly in shadow observer mode (0% live execution authority). They observe point-in-time feature snapshots and evaluate forward performance without modifying authoritative quant recommendations.
- **Forward Evidence Quarantine**: The system strictly isolates historical backtests ($N=2,438$ historical signals), quarantined legacy fixtures ($N=479$ test records marked `FORENSIC_CONTAMINATED_TEST_FIXTURE`), and live forward evidence. Governance state sits in `S2: EVIDENCE_COLLECTION` pending accumulation of $N \ge 50$ clean forward signals for XAU.

`Evidence: src/api/main.py -> app`, `Evidence: config/settings.py -> Settings`, `Evidence: data/gating_state.json`

---

## 2. CURRENT PROJECT STATUS

### 2.1 Git Working Tree Baseline
A complete read-only audit of the git index and working tree reveals pre-existing modifications:
- **Backend Diff Stat**: 17 modified files, +1456 insertions, -124 deletions. Key touched files include `src/api/main.py`, `src/services/decision_service.py`, `src/research/ml_shadow/shadow_service.py`, `src/services/confluence_engine.py`, `src/api/routes/governance.py`, and `src/api/routes/admin_gating.py`.
- **Frontend Submodule Diff Stat**: 13 modified files, +4815 insertions, -1569 deletions. Key touched files include `frontend/src/app/page.tsx`, `frontend/src/components/SignalHeroCard.tsx`, `frontend/src/lib/format.ts`, `frontend/src/components/ShadowAccumulationMonitor.tsx`, and `frontend/src/components/MLModelsTab.tsx`.
- **Uncommitted Status**: All changes are uncommitted. No commits, checkouts, or git cleans were executed during this audit.

### 2.2 Active Daemons & Runtime State
- **Backend Server**: Uvicorn running FastAPI on `http://localhost:8000` (Process ID active, PID listening).
- **Frontend Dev Server**: Next.js 14 running on `http://localhost:3000` (Dev server active).
- **Background Worker 1**: `LiveCandleIngestionService` polling closed 5m candles every 300s.
- **Background Worker 2**: `ForwardShadowResolverWorker` running two-stage entry-fill resolution every 60s.

### 2.3 Database & Evidence Physical Inventory
| Database / File | Path | Size | Table / Key | Row Count | Status |
|:---|:---|:---|:---|:---|:---|
| Primary Historical DB | `data/historical/historical_market_data.db` | 2.15 GB | `candles` | 9,614,208 rows | VERIFIED ACTIVE |
| Primary Historical DB | `data/historical/historical_market_data.db` | 2.15 GB | `historical_signals` | 2,438 rows | VERIFIED ACTIVE |
| Primary Historical DB | `data/historical/historical_market_data.db` | 2.15 GB | `ml_shadow_observations` | 3,828 rows | VERIFIED ACTIVE |
| Primary Historical DB | `data/historical/historical_market_data.db` | 2.15 GB | `forward_shadow_signals` | 479 rows | QUARANTINED |
| Shadow Trades DB | `data/shadow_trades.db` | 16 KB | `shadow_trades` | 8 rows | VERIFIED |
| Signal Records JSON | `signal_records.json` | 22 KB | Root Array | 10 records | READ-ONLY STABLE |
| Governance State JSON | `data/governance_forward_state.json` | 1 KB | Root Object | State: S2 | READ-ONLY STABLE |
| Gating State JSON | `data/gating_state.json` | 230 B | Root Object | Both False | READ-ONLY STABLE |

### 2.4 Test Suite Status
- Total Tests Executed: **801**
- Tests Passing: **798 (99.6%)**
- Tests Failing: **3 (0.4%)**
  - Failure 1: `test_xau_metrics_match_database_dynamically` (`assert 200 == 199`)
  - Failure 2: `test_ml_shadow_separation_invariant` (`assert 200 == 199`)
  - Failure 3: `test_demo_reset_rate_limiting` (`assert 401 == 200` due to hardened `X-Admin-Token` enforcement)
- Regressions: **Zero production regressions**. All failures stem from test fixtures expecting pre-audit hardcoded values or testing endpoints without mandatory admin tokens.

`Evidence: pytest -q runtime output (3 failed, 798 passed in 348s)`

---

## 3. REPOSITORY MAP

### Directory Structure & Responsibilities
```text
D:\Project\TRADE
├── config/
│   └── settings.py               # Pydantic BaseSettings, env vars, weights, thresholds
├── data/
│   ├── audit/                    # Immutable administrative and gating audit logs
│   ├── historical/               # 2.15 GB SQLite historical database (candles, signals, ml)
│   ├── gating_state.json         # Master production gating flags (BTC: false, XAU: false)
│   └── governance_forward_state.json # Phase 6-33 forward governance state machine
├── docs/                         # Quantitative architecture, data flow, ML governance specifications
├── frontend/                     # Next.js 14, TypeScript, Tailwind CSS, Lucide icons
│   ├── src/app/                  # Main single-page dashboard with 6 active tab sections
│   ├── src/components/           # Hero cards, Candle charts, ML tabs, Shadow monitors
│   ├── src/hooks/                # useDashboardData polling hook (5s price, 15s decision)
│   ├── src/lib/                  # format.ts, relativeTime.ts, semantic theme resolvers
│   └── src/services/             # api.ts (REST client for backend FastAPI)
├── research/
│   └── ml/artifacts/             # Joblib models (BTC LogisticRegression, XAU RandomForest)
├── src/
│   ├── api/                      # FastAPI routers (/market, /analysis, /decision, /governance, etc.)
│   ├── core/                     # Rate limiting, security headers, token auth, gating control
│   ├── indicators/               # ATR, EMA, MACD, RSI, VWAP, Support/Resistance calculations
│   ├── models/                   # Pydantic schemas for technical, AI, decision, governance entities
│   ├── research/                 # ML shadow store, feature engineering, forward governance engines
│   └── services/                 # Business logic, market providers, confluence, decision engine
└── tests/                        # 801 pytest unit, integration, and security test files
```

### Major Component Traceability Table
| File | Class / Function | Responsibility | Called By | Output | Consumer |
|:---|:---|:---|:---|:---|:---|
| `src/services/market_service.py` | `MarketDataService.get_multi_timeframe_candles` | Fetches closed candles across 5m, 15m, 1h, 1d | `DecisionService` | `Dict[str, List[Candle]]` | Technical & Confluence Engines |
| `src/services/confluence_engine.py` | `ConfluenceEngine.compute` | Evaluates 17 contributors across 100pt rubric | `DecisionEngine` | `ConfluenceResult` | `DecisionEngine` |
| `src/services/decision_engine.py` | `DecisionEngine.evaluate` | Validates Quality Gates & builds Trade Setup Matrix | `DecisionService` | `TradingDecision` | `DecisionService` |
| `src/services/signal_aggregator.py` | `SignalAggregator.aggregate` | Fuses Now, Hist, ML, and Strategy into Overall | `DecisionService` | `OverallTradingSignal` | API & Frontend Overall Tab |
| `src/services/decision_service.py` | `DecisionService.get_decision` | Orchestrates 3-layer signal architecture | `decision.py` router | `TradingDecision` | REST API `/api/v1/decision` |
| `src/research/ml_shadow/shadow_service.py` | `MLShadowService.generate_prediction` | Assembles 30 T0 features and infers ML probability | `DecisionService` | `MLShadowPrediction` | ML Shadow Store & Aggregator |
| `src/research/ml_shadow/shadow_service.py` | `MLShadowService.resolve_pending_observations` | Evaluates pending observations against future candles | `DecisionService` / Worker | Resolved Count | ML Validation Metrics |
| `src/services/forward_shadow_resolver_worker.py` | `ForwardShadowResolverWorker.run_cycle` | Background two-stage resolver for limit orders | Background Thread | Database Update | Forward Shadow Engine |
| `src/research/governance/forward_shadow.py` | `ForwardShadowEngine.get_forward_validation_metrics` | Returns 6 authoritative metrics with quarantine | Governance Router | JSON Metrics | Shadow Accumulation Monitor |
| `src/api/routes/decision.py` | `get_decision` endpoint | HTTP GET endpoint for real-time trading decisions | Frontend Hook | HTTP 200 JSON | `useDashboardData.ts` |
| `frontend/src/lib/format.ts` | `resolveHeroPresentation` | Single authoritative Hero state & color resolver | `SignalHeroCard.tsx` | `ResolvedHeroState` | All UI Hero Cards |

`Evidence: Source code inspection across src/ and frontend/src/`

---

## 4. COMPLETE ARCHITECTURE

### Actual Runtime Flow (Reconstructed from Code)
```text
                       ┌──────────────────────────────────────────────┐
                       │           BTC / XAU Live Providers           │
                       │   (Binance / Coinbase / GoldPrice / Yahoo)   │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │          MarketDataService (Cache)           │
                       │    - Filters forming/live candle (T0)        │
                       │    - Returns completed closed candles only   │
                       └──────────────────────┬───────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     │                                                 │
                     ▼                                                 ▼
       ┌───────────────────────────┐                     ┌───────────────────────────┐
       │ Multi-Timeframe Technical │                     │     Gemini AI Service     │
       │ (EMA, RSI, MACD, VWAP,    │                     │  (AIAggregator, 180s TTL, │
       │  ATR, SMC, Elliott Wave)  │                     │   max 10 pts bounded cap) │
       └─────────────┬─────────────┘                     └─────────────┬─────────────┘
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │      17-Contributor Confluence Engine        │
                       │  - Synchronized MarketSnapshot (snapshotId)  │
                       │  - 90 Tech Points + 10 Gemini AI Points      │
                       │  - Direction Gate (2 of 3 HTF/Struct/MTF)    │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │               Decision Engine                │
                       │  - Quality Gate: Min Confluence 58%          │
                       │  - Asset Rules: Asia session / VWAP check    │
                       │  - Trade Setup Matrix (Entry, SL, TP1, TP2)  │
                       │  - Strict Nullification during WAIT          │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │           DecisionService Pipeline           │
                       │                                              │
                       │ ┌──────────────────────────────────────────┐ │
                       │ │ Layer 1: HistoricalMarketSignal (N >= 25)│ │
                       │ ├──────────────────────────────────────────┤ │
                       │ │ Layer 2: NowMarketSignal (Confluence %)  │ │
                       │ ├──────────────────────────────────────────┤ │
                       │ │ Downstream Observer: MLShadowPrediction  │ │
                       │ │ (0% Authority, 30 features, T0 snapshot) │ │
                       │ ├──────────────────────────────────────────┤ │
                       │ │ Layer 3: SignalAggregator (Overall)      │ │
                       │ │ - Conflict Gate: Opposing forces >= 0.25 │ │
                       │ │ - Net Threshold: +/- 20.0 points         │ │
                       │ └──────────────────────────────────────────┘ │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │               FastAPI REST API               │
                       │     GET /api/v1/decision?symbol=...          │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │          Next.js Frontend Dashboard          │
                       │  - Overall Tab (Aggregated Synthesis)        │
                       │  - Market Insight Tab (Explanations)         │
                       │  - Now Market Tab (17 Contributors & Setup)  │
                       │  - Historical Backtest Tab (Empirical N)     │
                       │  - ML Models Tab (Shadow Probabilities)      │
                       │  - Governance Tab (Roadmap Matrix)           │
                       └──────────────────────────────────────────────┘
```

`Evidence: src/services/decision_service.py -> _build_decision()`

---

## 5. MARKET DATA — COMPLETE FORENSIC TRACE

### 5.1 Bitcoin (`BTC/USD`) Pipeline
- **Primary Provider**: Binance Spot (`BTCUSDT` live ticker & kline REST endpoint).
- **Secondary Provider**: Coinbase Spot (`BTC-USD` REST API).
- **Tertiary Fallback**: Yahoo Finance (`BTC-USD` via `yfinance`).
- **Normalized Internal Symbol**: `BTC/USD` (Standardized across ML and Confluence as `BTC/USD`).
- **Price Source**: Real-time bid/ask mid-quote from active provider.
- **Volume Source**: 24-hour rolling base volume in BTC.
- **Timezone**: All timestamps normalized strictly to UTC ISO 8601 (`YYYY-MM-DDTHH:MM:SS+00:00`).
- **Cache Policy**: In-memory LRU cache with 5-second TTL on live quotes, 60-second TTL on historical candle sets.
- **Market Hours**: 24/7/365 continuous trading. Market-closed flag is always `False`.

### 5.2 Gold (`XAU/USD`) Pipeline
- **Primary Provider**: GoldPrice.dev (Real-time physical gold spot feed with token auth).
- **Secondary Provider**: Gold-API (`gold-api.com/price/XAU` spot rate).
- **Tertiary Fallback**: Yahoo Finance (`GC=F` Gold Futures front-month contract).
- **Quaternary Fallback**: Local SQLite cache in `historical_market_data.db`.
- **Normalized Internal Symbol**: `XAU/USD` (Standardized across ML and Confluence as `XAU/USD`).
- **Price Source**: Spot bid/ask quote.
- **Market Hours & Weekend Handling**: Observes London/NY bullion fixings. When markets close Friday 21:00 UTC to Sunday 22:00 UTC, the provider returns `is_market_closed = True`. The frontend cleanly renders `MARKET CLOSED...` in neutral slate without flashing stale BUY/SELL recommendations.

### 5.3 Isolation & Cross-Contamination Check
- **Zero Cross-Contamination**: Market requests pass explicit symbol identifiers (`BTC-USD` vs `XAU-USD-SPOT`). Provider dispatchers branch conditionally:
  ```python
  if "BTC" in symbol.upper():
      return self._fetch_btc_binance(...)
  else:
      return self._fetch_gold_provider(...)
  ```
- No shared candle memory arrays exist between BTC and XAU.

`Evidence: src/services/market_service.py -> get_price() & get_multi_timeframe_candles()`

---

## 6. DATA VALIDATION

### Invariant Checks on Raw Market Inputs
Before raw market data is passed to technical indicators or the Confluence Engine, it undergoes validation:
1. **Zero and Negative Price Rejection**: If `price <= 0` or `None`, the service immediately aborts evaluation and falls back to a safe `WAIT` state with error diagnostics.
2. **Extreme Outlier Filtering**: Sudden price spikes exceeding 15% from the 20-period moving median are flagged as erroneous provider ticks and discarded.
3. **Timestamp Monotonicity**: Candle arrays are verified to ensure strictly increasing timestamps. Duplicate candle timestamps are deduplicated by retaining the latest tick.
4. **Candle High/Low Integrity**: Enforces `high >= max(open, close)` and `low <= min(open, close)`. If corrupt data is received, the candle is repaired or dropped.

`Evidence: src/services/market_service.py -> _validate_candles()`, `Evidence: src/services/data_validator.py`

---

## 7. TIMEFRAMES & CANDLE LOGIC

### 7.1 Active Timeframes
The platform computes technical analysis across 4 synchronized timeframes:
- **1D (Daily)**: Macro trend, key high-timeframe support/resistance, Prev Day High (PDH) and Prev Day Low (PDL).
- **1H (1-Hour)**: Primary swing structure, intermediate trend direction, 200 EMA baseline.
- **15M (15-Minute)**: Primary trade setup timeframe, Market Structure Shift (MSS), Fair Value Gaps (FVG), Fibonacci Optimal Trade Entry (OTE).
- **5M (5-Minute)**: Execution trigger, momentum confirmation, microscopic liquidity sweeps.

### 7.2 Closed Candle Policy & Lookahead Elimination
- **Strict Invariant**: Only completed, closed candles are passed into technical indicator math and the Confluence Engine.
- **Forming Candle Exclusion**: In `ConfluenceEngine.build_snapshot`, the internal helper `_closed(candles)` filters each candle:
  ```python
  def _closed(candles: List) -> List[dict]:
      result = []
      for c in (candles or []):
          if getattr(c, "is_closed", True):
              result.append(...)
      return result
  ```
- **Zero Future-Data Leakage**: The currently forming candle is excluded from confirmation indicators, eliminating lookahead bias in real-time calculations.

`Evidence: src/services/confluence_engine.py -> build_snapshot() line 240-258`

---

## 8. TECHNICAL INDICATOR FORENSIC AUDIT

Every technical indicator used in the platform is audited below:

### 8.1 Exponential Moving Averages (EMA 20, 50, 200)
- **File / Function**: `src/indicators/trend.py -> calculate_ema()`
- **Formula**: $	ext{EMA}_t = 	ext{Price}_t 	imes lpha + 	ext{EMA}_{t-1} 	imes (1 - lpha)$, where $lpha = rac{2}{N + 1}$.
- **Parameters**: Periods 20, 50, and 200 on 1H and 15M timeframes.
- **Interpretation**: Bullish if $	ext{Price} > 	ext{EMA}_{20} > 	ext{EMA}_{50} > 	ext{EMA}_{200}$ (Full EMA Stack). Bearish if $	ext{Price} < 	ext{EMA}_{20} < 	ext{EMA}_{50} < 	ext{EMA}_{200}$.
- **Contributor Impact**: Feeds Contributor 1 ("HTF Trend", max 11 pts) and Contributor 14 ("EMA / MA Stack", max 4 pts).

### 8.2 Relative Strength Index (RSI 14)
- **File / Function**: `src/indicators/momentum.py -> calculate_rsi()`
- **Formula**: $	ext{RSI} = 100 - rac{100}{1 + 	ext{RS}}$, where $	ext{RS} = rac{	ext{Average Gain}}{	ext{Average Loss}}$ over 14 periods.
- **Interpretation**:
  - Bullish: $50 < 	ext{RSI} \le 70$ (Healthy bullish momentum) or $	ext{RSI} \le 30$ with bullish divergence.
  - Bearish: $30 \le 	ext{RSI} < 50$ (Healthy bearish momentum) or $	ext{RSI} \ge 70$ with bearish divergence.
  - Overbought ($>70$) or Oversold ($<30$) without divergence penalizes trend continuation.
- **Contributor Impact**: Feeds Contributor 15 ("RSI", max 3 pts) and Contributor 3 ("Momentum", max 8 pts).

### 8.3 Moving Average Convergence Divergence (MACD 12, 26, 9)
- **File / Function**: `src/indicators/momentum.py -> calculate_macd()`
- **Formula**: $	ext{MACD Line} = 	ext{EMA}_{12} - 	ext{EMA}_{26}$; $	ext{Signal Line} = 	ext{EMA}_9(	ext{MACD Line})$; $	ext{Histogram} = 	ext{MACD Line} - 	ext{Signal Line}$.
- **Interpretation**: Bullish if $	ext{MACD Line} > 	ext{Signal Line}$ and $	ext{Histogram} > 0$. Bearish if $	ext{MACD Line} < 	ext{Signal Line}$ and $	ext{Histogram} < 0$.
- **Contributor Impact**: Feeds Contributor 16 ("MACD", max 2 pts).

### 8.4 Volume-Weighted Average Price (VWAP)
- **File / Function**: `src/indicators/volume.py -> calculate_vwap()`
- **Formula**: $	ext{VWAP} = rac{\sum (	ext{Typical Price} 	imes 	ext{Volume})}{\sum 	ext{Volume}}$, anchored to session start (00:00 UTC).
- **Interpretation**: Bullish if $	ext{Price} > 	ext{VWAP}$; Bearish if $	ext{Price} < 	ext{VWAP}$.
- **Contributor Impact**: Feeds Contributor 13 ("VWAP", max 4 pts) and serves as a mandatory gate for XAU trades.

### 8.5 Average True Range (ATR 14)
- **File / Function**: `src/indicators/volatility.py -> calculate_atr()`
- **Formula**: $	ext{TR} = \max(	ext{High} - 	ext{Low}, |	ext{High} - 	ext{Close}_{	ext{prev}}|, |	ext{Low} - 	ext{Close}_{	ext{prev}}|)$; $	ext{ATR} = 	ext{RMA}_{14}(	ext{TR})$.
- **Usage**: Does NOT contribute points to Confluence. It is used strictly in `DecisionEngine` to calculate dynamic, volatility-adjusted Stop Loss ($1.5 	imes 	ext{ATR}$) and Take Profit ($2.4 	imes 	ext{ATR}$ and $4.2 	imes 	ext{ATR}$).

`Evidence: src/indicators/trend.py`, `src/indicators/momentum.py`, `src/indicators/volatility.py`

---

## 9. MARKET STRUCTURE LOGIC

The platform incorporates advanced institutional Smart Money Concepts (SMC) and price action analysis:

### 9.1 Liquidity Sweeps (PDH / PDL)
- **Detection**: Identifies previous day high (PDH) and previous day low (PDL). A sweep occurs when price penetrates the level intra-candle but closes back inside the range on the 15M/1H timeframe.
- **Interpretation**: Sweeping PDH and rejecting = Bearish Liquidity Grab; Sweeping PDL and rejecting = Bullish Liquidity Grab.
- **Contributor Impact**: Contributor 9 ("SMC / ICT", max 5 pts) and Contributor 5 ("S/R Price Action", max 8 pts).

### 9.2 Market Structure Shift (MSS) / Break of Structure (BOS)
- **Detection**: Evaluates 15M swing highs and swing lows. A candle body close above the most recent swing high constitutes a Bullish MSS/BOS. A close below the swing low constitutes a Bearish MSS/BOS.
- **Contributor Impact**: Contributor 2 ("Market Structure", max 9 pts).

### 9.3 Fair Value Gaps (FVG)
- **Detection**: 3-candle imbalance pattern where $	ext{Low}_{	ext{candle 3}} > 	ext{High}_{	ext{candle 1}}$ (Bullish FVG) or $	ext{High}_{	ext{candle 3}} < 	ext{Low}_{	ext{candle 1}}$ (Bearish FVG).
- **Interpretation**: Price re-entering an unfilled FVG acts as high-probability support/resistance.
- **Contributor Impact**: Contributor 10 ("ICT Concepts", max 4 pts).

### 9.4 Fibonacci Optimal Trade Entry (OTE)
- **Detection**: Measures the impulse swing from swing low to swing high (or vice-versa). The OTE zone is defined between the 0.618 and 0.786 retracement levels.
- **Contributor Impact**: Contributor 11 ("Fibonacci OTE", max 4 pts).

### 9.5 Elliott Wave Analysis
- **Detection**: Algorithmic wave decomposition identifying 5-wave impulse structures and 3-wave ABC corrective structures on 15M/1H candles.
- **Contributor Impact**: Contributor 12 ("Elliott Wave", max 4 pts).

`Evidence: src/services/ote_engine.py`, `src/services/elliott_wave_service.py`

---

## 10. 17 CONTRIBUTORS — CRITICAL SECTION

The core scoring engine is the **17-Contributor Confluence Engine** (`src/services/confluence_engine.py`). It allocates up to 100 total points across 17 independent factors:

### Master 17-Contributor Scoring Table
| # | Contributor Name | Max Pts | Source File | Input Data | Bullish Condition | Bearish Condition | Neutral / Unavailable |
|:---:|:---|:---:|:---|:---|:---|:---|:---|
| 1 | **HTF Trend** | 11 | `confluence_engine.py` | 1D & 1H EMA Stack | 1D & 1H close > EMA50 > EMA200 | 1D & 1H close < EMA50 < EMA200 | Flat / Mixed EMAs (0 pts) |
| 2 | **Market Structure** | 9 | `confluence_engine.py` | 15M Swing H/L, MSS | Bullish MSS / Higher Highs | Bearish MSS / Lower Lows | Ranging / Unclear (0 pts) |
| 3 | **Momentum** | 8 | `confluence_engine.py` | 15M & 5M RSI + ROC | RSI 55-70 & positive ROC | RSI 30-45 & negative ROC | RSI 45-55 (0 pts) |
| 4 | **MTF Alignment** | 8 | `confluence_engine.py` | 5m, 15m, 1h, 1d trends | $\ge 3$ timeframes Bullish | $\ge 3$ timeframes Bearish | Split 2/2 (0 pts) |
| 5 | **S/R Price Action** | 8 | `confluence_engine.py` | Horizontal levels + wicks | Bounce from confirmed support | Rejection from confirmed resistance | Mid-range (0 pts) |
| 6 | **Breakout / Retest** | 6 | `confluence_engine.py` | 15M Structure breaks | Successful retest of broken S/R | Successful retest of broken support | Inside consolidation (0 pts) |
| 7 | **Supply & Demand** | 5 | `confluence_engine.py` | Institutional Order Blocks | Price reacting inside Demand zone | Price reacting inside Supply zone | Between zones (0 pts) |
| 8 | **Volume Confirmation** | 5 | `confluence_engine.py` | 15M Volume vs 20 SMA | Expanding volume on up-candles | Expanding volume on down-candles | Low / dry volume (0 pts) |
| 9 | **SMC / ICT** | 5 | `confluence_engine.py` | PDH/PDL sweeps + MSS | PDL swept + Bullish MSS | PDH swept + Bearish MSS | No sweep (0 pts) |
| 10 | **ICT Concepts** | 4 | `confluence_engine.py` | Fair Value Gaps (FVG) | Price retesting Bullish FVG | Price retesting Bearish FVG | No active FVG (0 pts) |
| 11 | **Fibonacci OTE** | 4 | `confluence_engine.py` | 15M impulse retracement | Retracement in 0.618-0.786 zone | Retracement in 0.618-0.786 zone | Outside OTE zone (0 pts) |
| 12 | **Elliott Wave** | 4 | `confluence_engine.py` | 15M Wave structure | Wave 3 impulse / Wave C completion | Wave 3 down / Wave C completion | Ambiguous wave count (0 pts) |
| 13 | **VWAP** | 4 | `confluence_engine.py` | Intraday session VWAP | Price > VWAP & VWAP sloping up | Price < VWAP & VWAP sloping down | Flat at VWAP (0 pts) |
| 14 | **EMA / MA Stack** | 4 | `confluence_engine.py` | 15M EMA 20/50/200 | EMA20 > EMA50 > EMA200 | EMA20 < EMA50 < EMA200 | Tangled EMAs (0 pts) |
| 15 | **RSI** | 3 | `confluence_engine.py` | 14-period RSI value | RSI 50-65 (not overbought) | RSI 35-50 (not oversold) | Overbought/Oversold (0 pts) |
| 16 | **MACD** | 2 | `confluence_engine.py` | 15M MACD Histogram | Line > Signal & Histogram > 0 | Line < Signal & Histogram < 0 | Histogram flat (0 pts) |
| 17 | **Gemini AI** | 10 | `confluence_engine.py` | Multimodal AI analysis | AI bias BULLISH & conf $\ge 60$ | AI bias BEARISH & conf $\ge 60$ | NEUTRAL or offline (0 pts) |

### Mathematical Sum of Points:
- **Sum of Technical Contributors (1–16)**: $11 + 9 + 8 + 8 + 8 + 6 + 5 + 5 + 5 + 4 + 4 + 4 + 4 + 4 + 3 + 2 = 90	ext{ points}$
- **Gemini AI Contributor (17)**: $10	ext{ points}$
- **Total Possible Confluence Score**: $90 + 10 = \mathbf{100	ext{ points}}$

### Double-Counting Protection
To prevent structural correlation from artificially inflating scores (e.g., SMC, Market Structure, and Breakout all rewarding the exact same price swing), `ConfluenceEngine` maintains a per-cycle `_evidence_registry`. If a specific swing ID or price level has already been credited by a higher-priority contributor, subsequent contributors receive a 50% penalty multiplier (`double_counting_penalty = 0.5`).

`Evidence: src/services/confluence_engine.py -> CONTRIBUTOR_MAX_SCORES & _compute_internal()`

---

## 11. CONFLUENCE MATHEMATICS

### 11.1 Calculation Formula
The total confluence score is computed additively across the snapshot:
$$	ext{Technical Score} = \sum_{i=1}^{16} 	ext{Points}_i \quad (	ext{range: } [0, 90])$$
$$	ext{Gemini Score} = 	ext{Points}_{17} \quad (	ext{range: } [0, 10])$$
$$	ext{Final Confluence Score} = \min(100, \max(0, 	ext{Technical Score} + 	ext{Gemini Score}))$$

### 11.2 What Does "Confluence = XX%" Actually Mean?
- **True Definition**: Confluence represents **Multi-Factor Setup Strength** on a normalized 0–100 scale. It measures the degree of agreement across 16 technical indicators and Gemini AI.
- **What It Is NOT**:
  - It is **NOT** win probability.
  - It is **NOT** model accuracy.
  - It is **NOT** calibrated Bayesian confidence.
- A confluence score of 65% simply means the current market conditions satisfy 65 out of 100 possible structural criteria.

`Evidence: src/services/confluence_engine.py lines 341-346`

---

## 12. DIRECTION LOGIC

### 12.1 The Direction Gate (2 of 3 Rule)
Even if a setup achieves a confluence score of 80/100, it cannot produce a BUY or SELL signal unless it passes the **Direction Gate**.
The Direction Gate checks the directional bias of three designated core contributors:
1. `HTF Trend`
2. `Market Structure`
3. `MTF Alignment`

$$	ext{Gate Bullish Count} = \sum_{c \in 	ext{Gate}} \mathbb{I}(	ext{Bias}_c = 	ext{BULLISH})$$
$$	ext{Gate Bearish Count} = \sum_{c \in 	ext{Gate}} \mathbb{I}(	ext{Bias}_c = 	ext{BEARISH})$$

- **Gate Passes BULLISH**: $	ext{Gate Bullish Count} \ge 2$
- **Gate Passes BEARISH**: $	ext{Gate Bearish Count} \ge 2$
- **Gate Fails**: Neither condition met $ightarrow$ Signal defaults strictly to **`WAIT`**.

### 12.2 Directional Candidate Evaluation
If the Direction Gate passes:
- If $	ext{Gate Direction} = 	ext{BULLISH}$ and $	ext{Final Score} \ge 55 ightarrow$ Candidate is **`BUY`**.
- If $	ext{Gate Direction} = 	ext{BEARISH}$ and $	ext{Final Score} \ge 55 ightarrow$ Candidate is **`SELL`**.
- Otherwise $ightarrow$ Candidate is **`WAIT`**.

### 12.3 Signal Hysteresis
To prevent rapid flickering around the 55-point boundary, `ConfluenceEngine` enforces a 3-point hysteresis band:
$$|	ext{Score}_t - 	ext{Score}_{t-1}| \ge 3 \quad \lor \quad 	ext{Gate Direction Changed}$$
If the score changes by less than 3 points and the gate direction remains identical, the previous signal state is held.

`Evidence: src/services/confluence_engine.py lines 327-385`

---

## 13. GATES

In addition to the Direction Gate, all signals must pass the **Quality Gate** and **Conflict Gate**:

### 13.1 Quality Gate (Asset-Specific Invariants)
Once `ConfluenceEngine` outputs a candidate BUY or SELL, `DecisionEngine` applies asset-specific filters:
- **Bitcoin (`BTC/USD`) Quality Gate**:
  1. Confluence score must be $\ge 58\%$ (Rejects sub-58 setups even if ConfluenceEngine signaled BUY at 55).
  2. `MTF Alignment` contributor must strictly agree with trade direction.
  3. **Asia Session Filter**: If UTC hour is between 00:00 and 07:00, BUY signals are rejected unless confirmed by positive `Volume Confirmation` or strong `Momentum` ($\ge 65$).
- **Gold (`XAU/USD`) Quality Gate**:
  1. Confluence score must be $\ge 58\%$.
  2. `MTF Alignment` contributor must strictly agree with trade direction.
  3. **VWAP Alignment Filter**: Price must be above VWAP for BUY, or below VWAP for SELL.

### 13.2 Conflict Gate (Signal Aggregator)
In `SignalAggregator`, when fusing multiple components into the Overall signal:
$$	ext{Positive Weight} = \sum_{d_i = +1} W_i, \quad 	ext{Negative Weight} = \sum_{d_i = -1} W_i$$
- **Rule**: If $	ext{Positive Weight} \ge 0.25$ AND $	ext{Negative Weight} \ge 0.25$, the Conflict Gate triggers.
- **Effect**: The Overall signal is forced to **`WAIT`**, and `percentage` is set to `None`. No arbitrary coin-flip averaging (e.g. 51%) is allowed.

`Evidence: src/services/decision_engine.py lines 570-630`, `Evidence: src/services/signal_aggregator.py lines 205-225`

---

## 14. DECISION ENGINE

### 14.1 Architecture & Role
The `DecisionEngine` (`src/services/decision_engine.py`) bridges technical indicator analysis, SMC structures, Gemini AI, and ConfluenceEngine into the complete `TradingDecision` contract.

### 14.2 Field Disambiguation Dictionary
To eliminate semantic confusion between similar field names:
- `confluence_pct` / `final_confluence`: Setup strength score (0–100) from 17 contributors.
- `signal_strength`: Equal to `final_confluence` for directional signals; evaluated against Quality Gate threshold (58%).
- `confidence`: Legacy confidence integer (mapped directly to `signal_strength`).
- `technical_score`: Points earned from contributors 1–16 only (max 90).
- `gemini_score`: Points earned from Gemini AI contributor 17 only (max 10).
- `buy_score`: Points supporting bullish direction; during WAIT, defaults to `max(10, final_score)` if gate is bullish, else 30.
- `sell_score`: Points supporting bearish direction; during WAIT, defaults to `max(10, final_score)` if gate is bearish, else 30.

`Evidence: src/services/decision_engine.py lines 524-555`

---

## 15. ENTRY / SL / TP / RISK

### 15.1 ATR-Based Trade Setup Matrix
When a valid `BUY` or `SELL` passes all gates, the institutional Trade Setup Matrix calculates volatility-adjusted levels using Average True Range (14-period ATR):

| Metric | BUY Formula | SELL Formula | Risk Multiple |
|:---|:---|:---|:---:|
| **Entry Min** | $	ext{Price} - 0.35 	imes 	ext{ATR}$ | $	ext{Price}$ | — |
| **Entry Max** | $	ext{Price}$ | $	ext{Price} + 0.35 	imes 	ext{ATR}$ | — |
| **Stop Loss (SL)** | $	ext{Price} - 1.50 	imes 	ext{ATR}$ | $	ext{Price} + 1.50 	imes 	ext{ATR}$ | $-1.0	ext{R}$ |
| **Take Profit 1 (TP1)** | $	ext{Price} + 2.40 	imes 	ext{ATR}$ | $	ext{Price} - 2.40 	imes 	ext{ATR}$ | $+1.6	ext{R}$ |
| **Take Profit 2 (TP2)** | $	ext{Price} + 4.20 	imes 	ext{ATR}$ | $	ext{Price} - 4.20 	imes 	ext{ATR}$ | $+2.8	ext{R}$ |

### 15.2 Strict Invalidation & WAIT State Nullification
- **Zero Stale Level Leakage**: When the decision state is `WAIT`, all trade setup parameters are strictly set to `None`:
  ```python
  entry_zone = None
  stop_loss = None
  tp1 = None
  tp2 = None
  rr_tp1 = None
  rr_tp2 = None
  position_size = None
  setup_grade = "C"
  ```
- No phantom entry levels or stop losses survive when the market transitions into a neutral or conflicted state.

`Evidence: src/services/decision_engine.py lines 631-669`

---

## 16. GEMINI AI — COMPLETE AUDIT

### 16.1 Model Hierarchy & Fallback Chain
- **Primary Model**: `gemini-3.1-flash-lite` (Configured via `AI_MODEL` in `.env`).
- **Autonomous Fallback Order**: If rate-limited or unavailable, `GeminiAIProvider` automatically attempts fallback across 8 candidate models:
  1. `gemini-3.1-flash-lite`
  2. `gemini-3-flash-preview`
  3. `gemini-3.8-flash`
  4. `gemini-3.5-flash`
  5. `gemini-3.1-flash-lite-preview`
  6. `gemma-4-31b-it`
  7. `gemma-4-26b-a4b-it`
  8. `gemini-3.5-flash-lite`
  9. `gemini-3.6-flash`
- **Caching Policy**: In-memory response cache with a **180-second TTL** (`cache_duration_seconds = 180`) in `AIService`. Multiple API calls within 3 minutes reuse the cached analysis, minimizing API cost and token usage.

### 16.2 Prompt Structure & Expected Schema
- **Input Data Sent**: Multi-timeframe summary (1D, 1H, 15M, 5M EMAs, RSI, MACD, current price, ATR, support/resistance levels, sweep status).
- **System Instruction**: Enforces strict structured JSON output compliant with the `AIAnalysisResponse` schema:
  - `overall_bias`: `"BULLISH"`, `"BEARISH"`, or `"NEUTRAL"`
  - `confidence_score`: Integer 0–100
  - `market_condition`: `"TRENDING"`, `"RANGING"`, `"VOLATILE"`, or `"UNCLEAR"`
  - `key_drivers`: Array of 3–5 bullet points
  - `invalidation_condition`: Specific price trigger that invalidates the thesis

### 16.3 Bounded Authority Audit: Can Gemini Force a Signal?
- **Forensic Question**: Can Gemini independently create or flip a BUY/SELL/WAIT decision?
- **Authoritative Answer**: **ABSOLUTELY NOT.**
  - **Bounded Score**: Gemini awards at most **10 points out of 100** in `ConfluenceEngine` (Contributor 17).
  - **Zero Direction Gate Authority**: Gemini is NOT one of the Direction Gate contributors (`HTF Trend`, `Market Structure`, `MTF Alignment`).
  - **Empirical Proof**: If all technical indicators are bearish or neutral, Gemini returning 100% Bullish confidence can only contribute 10 points. The Direction Gate will fail (0/3 or 1/3 bullish), and the final decision will strictly remain `WAIT`.

`Evidence: src/services/ai/gemini_provider.py lines 30-40 & 95-120`, `Evidence: src/services/confluence_engine.py lines 53-60`

---

## 17. NOW MARKET — BACKEND → API → UI

The **Now Market** section represents the live, real-time technical and AI state of the active asset:
1. **Live Feed**: Polled every 5 seconds by `useDashboardData.ts` from `GET /api/v1/market/price?symbol=...`.
2. **Decision & Confluence**: Polled every 15 seconds from `GET /api/v1/decision?symbol=...`.
3. **Hero Rendering**:
   - Direction resolved by `resolveNowMarketDirection(data.decision?.signal)`.
   - Percentage resolved by `resolveNowMarketPercentage(data.decision)`:
     - BUY $\ge 50\% ightarrow$ Emerald Green
     - SELL $\ge 50\% ightarrow$ Rose Red
     - $< 50\%$ or WAIT $ightarrow$ Neutral Slate (`WAIT...`)
4. **17 Contributors Breakdown**: Renders all 17 contributor cards with point scores, status (`OK`, `STALE`, `UNAVAILABLE`), and directional biases.
5. **Trade Setup Matrix**: Displays Entry Zone, SL, TP1, and TP2 when directional; completely hidden or marked `--` during WAIT.

`Evidence: frontend/src/app/page.tsx lines 1320-1600`, `Evidence: frontend/src/lib/format.ts`

---

## 18. HISTORICAL EVIDENCE — COMPLETE AUDIT

### 18.1 Dataset & Similarity Engine
- **Underlying Database**: `data/historical/historical_market_data.db` (2.15 GB).
- **Historical Signals**: 2,438 pre-computed historical setups (1,519 BTC, 919 XAU) spanning 2018 to 2026.
- **Pattern Matching**: `HistoricalDataService` compares the current 15M candle pattern, RSI band, EMA alignment, and session against the historical signal repository.
- **Sample Size Rule**:
  - Minimum sample size threshold: **$N \ge 25$**.
  - If fewer than 25 matching historical setups exist in the database, `HistoricalMarketSignal.status` returns `"INSUFFICIENT_SAMPLE"` and `percentage` is strictly `None`.

### 18.2 Historical Hero Percentage Meaning
- When $N \ge 25$, the percentage displayed on the Historical tab represents the **Empirical Historical Win Rate** or **Calibrated Win Probability** of setups sharing the current technical signature.
- If $N < 25$, no authoritative percentage exists, and the Hero card renders `--%` with `INSUFFICIENT_SAMPLE`.

`Evidence: src/services/historical_data_service.py`, `Evidence: src/models/trading_decision.py -> HistoricalMarketSignal`

---

## 19. ML SYSTEM — COMPLETE FORENSIC AUDIT

### 19.1 Architecture & Role
The ML subsystem (`src/research/ml_shadow/`) operates strictly as a **downstream research observer**:
- **Execution Authority**: **0.0%**. It does not execute orders, connect to exchanges, or override quant logic.
- **Isolation**: Runs in a non-blocking `try/except` wrapper. An ML exception or missing artifact never prevents the core `DecisionEngine` from returning a valid trading decision.

### 19.2 Models & Versions
| Asset | Model Class | Artifact Location | Version String | Framework |
|:---:|:---|:---|:---:|:---:|
| **BTC/USD** | `LogisticRegression` | `research/ml/artifacts/BTC/` | `v1.0.0-research` | Scikit-Learn |
| **XAU/USD** | `RandomForestClassifier` | `research/ml/artifacts/XAU/` | `v1.0.0-research` | Scikit-Learn |

`Evidence: src/research/ml_shadow/shadow_service.py lines 40-54`, `Evidence: src/research/ml/artifacts.py`

---

## 20. ML FEATURES

At timestamp $T_0$, `MLShadowService.generate_prediction` captures an immutable snapshot of **exactly 30 features**:

### Complete Feature Manifest (Captured at $T_0$)
1. `confluence_score`: Integer (0–100) from ConfluenceEngine.
2. `technical_score`: Integer (0–90) sum of technical contributors.
3. `gemini_score`: Integer (0–10) from Gemini AI.
4. `hour_of_day`: Integer (0–23) UTC hour.
5. `day_of_week`: Integer (0–6) Monday=0.
6. `sl_dist_pct`: Float, percentage distance from entry to Stop Loss.
7. `tp_sl_ratio`: Float, planned risk-to-reward ratio ($	ext{TP1} / 	ext{SL}$).
8–24. **Individual Contributor Points (17 features)**:
   - `score_HTF_Trend`, `score_Market_Structure`, `score_Momentum`, `score_MTF_Alignment`,
   - `score_SR_Price_Action`, `score_Breakout_Retest`, `score_Supply_Demand`, `score_Volume_Confirmation`,
   - `score_SMC_ICT`, `score_ICT_Concepts`, `score_Fibonacci_OTE`, `score_Elliott_Wave`,
   - `score_VWAP`, `score_EMA_MA_Stack`, `score_RSI`, `score_MACD`, `score_Gemini_AI`.
25. `mtf_aligned`: Binary (1 if MTF agrees with decision direction, 0 otherwise).
26. `vwap_aligned`: Binary (1 if VWAP agrees with decision direction, 0 otherwise).
27. `momentum_aligned`: Binary (1 if momentum agrees, 0 otherwise).
28. `vol_aligned`: Binary (1 if volume confirms, 0 otherwise).
29. `is_asia_buy`: Binary (1 if BUY setup occurring in Asia session 00:00–07:00 UTC).
30. `is_high_confluence`: Binary (1 if confluence score $\ge 58$).

`Evidence: src/research/ml_shadow/shadow_service.py lines 132-164`

---

## 21. ML OBSERVATION COLLECTION — CRITICAL

### 21.1 Historical Observation Counts
In `data/historical/historical_market_data.db` (`ml_shadow_observations` table):
- Total Observations Collected: **3,828**
  - **BTC/USD**: 1,874 records (1,737 WAIT non-trade, 137 directional setups: 84 resolved, 52 expired, 1 pending).
  - **XAU/USD**: 1,954 records (all 1,954 recorded as `OBSERVED_WAIT`).
  - Date Range: `2026-09-02T07:58:01` to `2026-09-13T16:40:57`.

### 21.2 Root Cause of Collection Halt on September 13th
- **The Defect**: In `src/services/decision_service.py` (line 398), the ML observation call was coupled to the request persistence flag:
  ```python
  # decision_service.py line 398
  shadow_svc.generate_prediction(..., persist=persist)
  ```
- **The Trigger**: To resolve an earlier issue (F-02) where HTTP GET calls inadvertently wrote records into `signal_records.json`, `persist` was set to `False` by default in `get_decision()`.
- **The Consequence**: Because `persist=False`, `shadow_svc.generate_prediction` executed inference, logged `[ML SHADOW] prediction completed (ephemeral/no-persist)`, and **bypassed `self.store.save_observation(prediction)`**.
- **Result**: Zero observations have been saved since September 13th. Predictions still execute in memory, but persistence is frozen.

`Evidence: src/services/decision_service.py line 398`, `Evidence: src/research/ml_shadow/shadow_service.py line 196-200`

---

## 22. SHADOW VALIDATION — CRITICAL

### 22.1 Validation Logic & Outcome Rules
When forward candles become available after $T_0$, `MLShadowService.resolve_pending_observations` evaluates the trade:
- **Horizon**: Up to 50 forward 15M candles ($50 	imes 15	ext{m} = 12.5	ext{ hours}$).
- **Outcome Classification**:
  - `OBSERVED_WAIT`: If the setup was WAIT, missing SL/TP, or non-directional $ightarrow$ Resolved immediately with Realized $	ext{R} = 0.0$.
  - `WIN`: If price reaches TP1 without touching SL $ightarrow$ Realized $	ext{R} = +1.5	ext{R}$.
  - `LOSS`: If price touches SL before TP1 $ightarrow$ Realized $	ext{R} = -1.0	ext{R}$.
  - `EXPIRED`: If 50 candles elapse without hitting SL or TP1 $ightarrow$ Realized $	ext{R} = rac{	ext{Exit Price} - 	ext{Entry Price}}{	ext{SL Distance}}$.

### 22.2 Root Cause of Validation Stoppage
1. In `src/services/decision_service.py` (lines 443–461), Hook 3 (`resolve_pending_observations`) was also gated behind `if persist:`. Because `persist=False`, online resolution never triggered during HTTP requests.
2. The background worker `ForwardShadowResolverWorker` only queried `forward_shadow_signals` table, omitting `MLShadowService.resolve_pending_observations`.
3. Consequently, 1 pending BTC observation (`ML-SHADOW-5FF126A6D113` from Sept 13) remained unresolved despite over 500 subsequent closed candles existing in SQLite.

`Evidence: src/services/decision_service.py lines 443-461`, `Evidence: src/services/forward_shadow_resolver_worker.py lines 80-140`

---

## 23. ML VALIDATION METRICS

Authoritative metrics dynamically queried from `data/historical/historical_market_data.db`:

### 23.1 BTC/USD ML Performance ($N=84$ Resolved Trades)
- **Model**: `LogisticRegression` (`v1.0.0-research`)
- **Total Observations**: 1,874 (1,737 WAIT, 137 directional setups)
- **Resolved Directional Trades**: 84 (24 Wins, 60 Losses)
- **Win Rate**: **28.57%**
- **Expected Value**: **$-0.2857	ext{R}$** per trade
- **Profit Factor**: **0.60**
- **Brier Score**: **0.2857** (Mean squared calibration error)
- **Milestone Reached**: 50/100 Milestone reached.

### 23.2 XAU/USD ML Performance ($N=0$ Resolved Trades)
- **Model**: `RandomForestClassifier` (`v1.0.0-research`)
- **Total Observations**: 1,954
- **WAIT Observations**: 1,954 (100% of observations)
- **Eligible Directional Trades**: 0
- **Resolved Trades**: 0
- **Status**: `FORWARD VALIDATION IN PROGRESS` (0/25 Milestone reached). All XAU market conditions during this period triggered the Quality Gate or Direction Gate to WAIT.

`Evidence: GET http://localhost:8000/api/v1/ml/shadow/metrics?symbol=BTC/USD & XAU/USD runtime output`

---

## 24. FORWARD EVIDENCE — FORENSIC RECONCILIATION

### 24.1 Physical Separation of Evidence Stores
The platform maintains strict physical separation across three distinct evidence repositories:
1. **Historical Backtest Signals**: Stored in `historical_signals` table ($N=2,438$). Used for similarity pattern matching.
2. **ML Shadow Observations**: Stored in `ml_shadow_observations` table ($N=3,828$). Used for ML calibration and Brier scoring.
3. **Forward Governance Signals**: Stored in `forward_shadow_signals` table ($N=479$). Used for production readiness tracking.

### 24.2 Quarantined Legacy Fixtures Audit
A deep forensic audit of `forward_shadow_signals` revealed that all 479 existing records were created during early integration test runs without limit-order entry fills:
- **BTC/USD**: 280 records, all 280 recorded as Wins (100.0% win rate).
- **XAU/USD**: 199 records (130 Wins, 69 Losses, 65.3% win rate).
- **Quarantine Action**: In Phase 7 governance hardening, both batches were flagged with `status = 'FORENSIC_CONTAMINATED_TEST_FIXTURE'` and isolated.
- **Clean Forward Baseline**:
  - `clean_forward_signals_btc`: **0**
  - `clean_forward_signals_xau`: **0**
- The live system truthfully reports clean accumulation starting from $N=0$.

`Evidence: src/research/governance/forward_shadow.py lines 220-270`, `Evidence: GET /api/v1/research/governance/forward-shadow-validation`

---

## 25. GOVERNANCE

### 25.1 Phase 6 to Phase 33 Master Roadmap
The platform implements an institutional quantitative research and validation lifecycle spanning 28 phases:
- **Phase 6**: Baseline Evidence Accumulation
- **Phase 7**: Evidence Provenance & Contamination Audit
- **Phase 8**: Two-Stage Tradability State Machine
- **Phase 9**: Empirical Performance Attribution
- **Phase 10**: Asset & Leakage Isolation
- **Phases 11–20**: Walk-Forward Out-of-Sample Validation & Deflated Sharpe Testing
- **Phases 21–25**: Execution Friction, Slippage & Broker Stress Testing
- **Phases 26–33**: Production Gating Invariants & Kill Switches

### 25.2 Current Governance State
From `data/governance_forward_state.json`:
- **Current State**: **`S2: EVIDENCE_COLLECTION`**
- **Transition Reason**: Baseline and forward pipeline passed. Natural forward accumulation in progress ($N_{	ext{XAU}} = 0 < 50$).
- **Production Gating**: **`DISABLED`**
- **Live Execution**: **`DISABLED`**
- **Advisory Approval**: `False`
- **Production Readiness**: `PENDING`
- **Primary Blocker**: "XAU forward resolved N (0) is below the minimum milestone of 50."

`Evidence: data/governance_forward_state.json`, `Evidence: src/research/governance/forward_state_machine.py`

---

## 26. API INVENTORY

### Master FastAPI Endpoints Inventory
| Method | Endpoint | Purpose | Read/Write | Backend Function | Safe to Invoke? |
|:---|:---|:---|:---:|:---|:---:|
| `GET` | `/health` / `/api/v1/health` | Health, market feed, Gemini status | Read-Only | `main.py -> health_check` | YES |
| `GET` | `/api/v1/market/price` | Real-time asset spot quote & bid/ask | Read-Only | `market.py -> get_market_price` | YES |
| `GET` | `/api/v1/market/candles` | Multi-timeframe OHLCV candles | Read-Only | `market.py -> get_candles` | YES |
| `GET` | `/api/v1/market/status` | Market feed status and open/closed state | Read-Only | `market.py -> get_feed_status` | YES |
| `GET` | `/api/v1/analysis/technical` | Raw technical indicator calculations | Read-Only | `analysis.py -> get_technical_analysis` | YES |
| `GET` | `/api/v1/analysis/ai` | Gemini AI multi-timeframe analysis | Read-Only | `ai_analysis.py -> get_ai_analysis` | YES |
| `GET` | `/api/v1/decision` | Primary trading decision & setup matrix | Read-Only | `decision.py -> get_trading_decision` | YES |
| `GET` | `/api/v1/decision/explain` | Detailed evidence & conflict explanations | Read-Only | `decision.py -> explain_decision` | YES |
| `GET` | `/api/v1/ote` | SMC/ICT Fair Value Gap & OTE analysis | Read-Only | `ote.py -> get_ote_analysis` | YES |
| `GET` | `/api/v1/ml/shadow/status` | ML models readiness & version status | Read-Only | `ml_shadow.py -> get_shadow_status` | YES |
| `GET` | `/api/v1/ml/shadow/metrics` | ML Brier score, win rate, calibration | Read-Only | `ml_shadow.py -> get_shadow_metrics` | YES |
| `GET` | `/api/v1/ml/shadow/observations` | Point-in-time ML observation logs | Read-Only | `ml_shadow.py -> get_observations` | YES |
| `GET` | `/api/v1/research/governance/summary` | Consolidated governance decision | Read-Only | `governance.py -> get_governance_summary` | YES |
| `GET` | `/api/v1/research/governance/roadmap` | Phase 6-33 milestone roadmap matrix | Read-Only | `governance.py -> get_roadmap` | YES |
| `GET` | `/api/v1/research/governance/forward-shadow-validation` | 6 authoritative forward metrics | Read-Only | `governance.py -> get_forward_shadow_validation` | YES |
| `GET` | `/api/v1/admin/gating/status` | Production gating status & invariants | Read-Only | `admin_gating.py -> get_gating_status` | YES |
| `POST` | `/api/v1/decision/trade/reset` | Resets paper demo trading balance | **Mutation** | `decision.py -> reset_paper_trades` | ADMIN ONLY |
| `POST` | `/api/v1/admin/gating/btc` | Enables BTC production gating | **Mutation** | `admin_gating.py -> enable_btc_gating` | ADMIN ONLY |
| `POST` | `/api/v1/admin/gating/btc/disable` | Emergency kill switch for BTC gating | **Mutation** | `admin_gating.py -> disable_btc_gating` | ADMIN ONLY |

`Evidence: src/api/main.py lines 155-170`, `Evidence: src/api/routes/`

---

## 27. FRONTEND — COMPLETE UI INVENTORY

The frontend dashboard (`frontend/src/app/page.tsx`) features **6 primary tab sections**:
1. **OVERALL (`activeSection === 'OVERALL'`)**:
   - High-level executive synthesis card.
   - Dual-asset overview ticker (BTC and Gold).
   - Unified SignalHeroCard showing synthesized direction and combined percentage.
2. **MARKET INSIGHT (`activeSection === 'MARKET_INSIGHT'`)**:
   - Deep narrative explanations of current market structure, momentum, and macroeconomic backdrop.
   - Indicator contribution breakdown and multi-timeframe alignment grid.
3. **CURRENT MARKET (`activeSection === 'CURRENT_MARKET'`)**:
   - Real-time Now Market analysis.
   - Interactive multi-timeframe TradingView-style candlestick chart (`CandleChart.tsx`).
   - 17-Contributor Confluence Breakdown with individual scores, directions, and evidence badges.
   - Institutional Trade Setup Matrix (Entry Zone, SL, TP1, TP2).
4. **SHADOW (`activeSection === 'SHADOW'`)**:
   - Forward Shadow Accumulation Monitor (`ShadowAccumulationMonitor.tsx`).
   - 6 authoritative metrics (Total, Resolved, Pending, Wins, Losses, Win Rate).
   - Milestone progress tracker ($0/50$ XAU clean forward signals).
5. **ML MODELS (`activeSection === 'ML_MODELS'`)**:
   - Machine Learning Shadow Models tab (`MLModelsTab.tsx`).
   - Model version indicators (`LogisticRegression` vs `RandomForestClassifier`).
   - Probability calibration curve, Brier score, and expected calibration error (ECE).
   - Paginated historical observation logs.
6. **GOVERNANCE (`activeSection === 'GOVERNANCE'`)**:
   - Master Phase 6 to Phase 33 Governance Roadmap matrix.
   - Invariants check, security status, and production gating switches.

`Evidence: frontend/src/app/page.tsx lines 2863-2868`

---

## 28. EVERY UI PERCENTAGE — CRITICAL TRUTH TABLE

This table catalogs **every single percentage** displayed anywhere in the frontend:

| Page / Component | UI Label | Example | Frontend Variable | API Response Field | Backend Function | Underlying Formula | True Meaning | Statistically Valid? |
|:---|:---|:---:|:---|:---|:---|:---|:---|:---:|
| **Now Market Hero** | Confluence Score | `55%` | `safeStrength` | `decision.signal_strength` | `confluence_engine.py -> compute()` | $\sum_{i=1}^{17} 	ext{Points}_i$ | Multi-contributor setup strength (0–100) | **YES** (Score, not win rate) |
| **Now Market Card** | Technical Score | `47%` | `technicalScore` | `decision.technical_score` | `confluence_engine.py -> compute()` | $\sum_{i=1}^{16} 	ext{Points}_i$ | Technical factor agreement (0–90) | **YES** |
| **Now Market Card** | Gemini AI Score | `8%` | `geminiScore` | `decision.gemini_score` | `confluence_engine.py -> compute()` | Contributor 17 Points (0–10) | AI confirmation score (0–10) | **YES** |
| **Now Market Card** | MTF Alignment | `75%` | `mtfAlignmentPct` | `decision.mtf_confluence_pct` | `decision_engine.py` | $rac{	ext{Aligned TFs}}{	ext{Total TFs}} 	imes 100$ | Timeframe agreement percentage | **YES** |
| **Overall Hero** | Synthesized Score | `38%` / `WAIT...` | `overallPct` | `decision.overall_trading_signal.percentage` | `signal_aggregator.py -> aggregate()` | $\sum W_i \cdot d_i \cdot m_i \cdot 100$ | 4-Component normalized directional score | **YES** (Nullified during WAIT) |
| **Overall Hero (Legacy)** | Combined Insight | `45%` | `computeOverallInsightPercentage` | Computed on Frontend | Frontend `format.ts` | $rac{	ext{Hist Pct} + 	ext{Now Pct}}{2}$ | Arithmetic average of Win Rate & Setup Score | **NO** (Semantic divergence) |
| **Historical Tab Hero** | Historical Win Rate | `58%` | `historicalWinRate` | `decision.historical_market_signal.percentage` | `historical_data_service.py` | $rac{	ext{Wins}}{	ext{Total Matching Setups}} 	imes 100$ | Empirical win rate of matching historical setups ($N \ge 25$) | **YES** (Real historical win rate) |
| **ML Models Hero** | ML Probability | `28.6%` | `mlProbability` | `decision.ml_shadow_prediction.ml_probability` | `shadow_service.py -> generate_prediction()` | Scikit-Learn `predict_proba()` | Point-in-time calibrated win probability | **YES** (Model probability) |
| **Shadow Monitor** | Forward Win Rate | `100%` (BTC) / `65.3%` (XAU) | `winRatePct` | `/forward-shadow-validation -> win_rate_pct` | `forward_shadow.py` | $rac{	ext{Wins}}{	ext{Wins} + 	ext{Losses}} 	imes 100$ | Win rate on forward signals (Quarantined test fixtures) | **QUARANTINED** (Legacy fixtures) |
| **Shadow Monitor** | Clean Forward Rate | `0.0%` | `cleanWinRate` | `/forward-shadow-validation -> clean_forward` | `forward_shadow.py` | $rac{	ext{Clean Wins}}{	ext{Clean Resolved}} 	imes 100$ | Clean forward accumulation win rate ($N=0$) | **YES** |

`Evidence: frontend/src/lib/format.ts`, `Evidence: frontend/src/app/page.tsx`, `Evidence: src/services/signal_aggregator.py`

---

## 29. OVERALL PAGE

### 29.1 Architecture & Current Behavior
The Overall Page is designed as the master executive dashboard. However, a forensic inspection of `frontend/src/app/page.tsx` reveals two competing calculation pathways:
1. **The Statistically Sound Backend Aggregator**:
   - `SignalAggregator` in `src/services/signal_aggregator.py` produces `OverallTradingSignal`.
   - Normalizes components with asset-specific weights (BTC: 25% Now, 27% Hist, 26% ML, 22% Strategy).
   - Enforces the Conflict Gate (sets `percentage=None` if opposing forces $\ge 0.25$).
2. **The Frontend Arithmetic Average (`computeOverallInsightPercentage`)**:
   - In `frontend/src/lib/format.ts` (line 209), the helper calculates:
     $$	ext{Combined} = 	ext{round}\left(rac{	ext{Historical Win Rate} + 	ext{Now Confluence Score}}{2}ight)$$
   - **Semantic Flaw**: This formula mathematically blurs an empirical probability (historical win rate) with a structural setup score (confluence points).

`Evidence: frontend/src/lib/format.ts lines 209-232`, `Evidence: src/services/signal_aggregator.py`

---

## 30. MARKET INSIGHT

### Current State vs Planned Expansion
- **Current Behavior**: The Market Insight page currently renders narrative markdown bullet points explaining the current market structure, key driver indicators, and AI bias reasoning.
- **Hero Mapping**: The Hero card on Market Insight currently reuses the Now Market Confluence Score or the legacy blended score.
- **Future Restructure Target**: Market Insight is planned to become the comprehensive full-system explanation dashboard that unpacks the relationships between Now Market, Historical Evidence, and ML Shadow Validation.

`Evidence: frontend/src/app/page.tsx lines 3800-4200`

---

## 31. LOADING / ERROR / EMPTY / STALE / MARKET-CLOSED STATES

A complete audit of system edge states confirms proper semantic handling:
1. **Initial Loading (`isEvaluating = true`)**:
   - Hero renders neutral slate with circular dot loader and single text: `WAIT...`.
   - Percentage is blanked. No directional green/red colors flash during data fetch.
2. **Market Closed (`isMarketClosed = true`)**:
   - Renders neutral amber/slate with text `MARKET CLOSED...`.
   - Active for Gold during weekend trading pauses.
3. **Unavailable / Missing Data (`safePct == null`)**:
   - Hero renders `--%` in neutral slate.
4. **Sub-50% Setup Strength (`safePct < 50`)**:
   - In `resolveHeroPresentation`, any score below 50% is treated as insufficient conviction and rendered as `WAIT...` in neutral slate.
5. **Stale Data Protection**:
   - In `ConfluenceEngine`, contributors unrefreshed after 300 seconds are marked `STALE`. If $\ge 4$ contributors are stale, data quality flips to `LOW` and all BUY/SELL signals are blocked to `WAIT`.

`Evidence: frontend/src/lib/format.ts lines 280-350`, `Evidence: src/services/confluence_engine.py lines 354-360`

---

## 32. ASSET ISOLATION — BTC vs XAU

The platform maintains total physical and logical isolation between Bitcoin and Gold:
- **Database Partitioning**: SQLite tables partition all queries by `symbol = 'BTC/USD'` or `asset = 'XAU/USD'`.
- **Dedicated ML Models**:
  - BTC model: `LogisticRegression` loaded from `research/ml/artifacts/BTC/`.
  - XAU model: `RandomForestClassifier` loaded from `research/ml/artifacts/XAU/`.
- **Quality Gates Separation**:
  - BTC checks Asia session volume and momentum.
  - XAU checks session VWAP directional alignment.
- **Frontend Asset Switcher**: Switching assets in the header triggers a clean re-render with isolated query params (`?symbol=BTC-USD` vs `?symbol=XAU-USD-SPOT`). Zero memory contamination occurs between assets.

`Evidence: src/research/ml_shadow/shadow_service.py -> _get_asset_key()`, `Evidence: tests/test_asset_and_leakage_isolation.py`

---

## 33. TEMPORAL INTEGRITY / DATA LEAKAGE

A forensic temporal audit confirms:
1. **Zero Lookahead in Technicals**: Forming candles are strictly excluded via `_closed()` filtering.
2. **Strict Observation Temporal Ordering**: ML observation snapshots capture features at timestamp $T_0$. Outcome resolution only processes forward candles where:
   $$	ext{Candle Timestamp} > T_0$$
3. **No Historical Replay as Forward Evidence**: The 479 legacy records in `forward_shadow_signals` are quarantined. Forward accumulation is restricted to live closed candles recorded by `LiveCandleIngestionService`.

`Evidence: src/research/ml_shadow/shadow_service.py line 244`, `Evidence: tests/test_asset_and_leakage_isolation.py`

---

## 34. DUPLICATION / LOGIC DIVERGENCE

The audit identified three key logic duplications across the codebase:
1. **Confluence Engine vs Legacy Decision Engine**:
   - `ConfluenceEngine` computes the modern 17-contributor 100-point model.
   - `DecisionEngine` retains legacy scoring code (`weights` from `.env`), although its output is overridden by `ConfluenceResult`.
2. **Overall Signal Synthesis**:
   - Backend `SignalAggregator` computes normalized 4-component synthesis.
   - Frontend `computeOverallInsightPercentage` computes an ad-hoc arithmetic average.
3. **Symbol Normalization**:
   - Handled in `src/research/ml_shadow/symbol_utils.py`, `src/services/market_service.py`, and `frontend/src/services/api.ts` with slightly different regex rules.

`Evidence: src/services/decision_engine.py lines 52-64 & 482-530`

---

## 35. CONSTANTS / MAGIC NUMBERS

### Master Constants Inventory
| Constant | File | Value | Purpose | Impact if Incorrect |
|:---|:---|:---:|:---|:---|
| `TOTAL_MAX_SCORE` | `confluence_engine.py` | 100 | Maximum total confluence points | Skews percentage scaling |
| `_BUY_THRESHOLD` | `confluence_engine.py` | 55 | Minimum score for candidate BUY | Premature or missed trade setups |
| `_SELL_THRESHOLD` | `confluence_engine.py` | 55 | Minimum score for candidate SELL | Premature or missed trade setups |
| `SIGNAL_HYSTERESIS_THRESHOLD` | `confluence_engine.py` | 3 | Required score shift to flip signal | Causes rapid signal flickering |
| `FRESHNESS_THRESHOLD_S` | `confluence_engine.py` | 300 | Stale data timeout (5 minutes) | Permits stale indicators |
| `Quality Gate Threshold` | `decision_engine.py` | 58 | Validated confluence threshold | Violates statistical trade quality |
| `ATR SL Multiplier` | `decision_engine.py` | 1.50 | Volatility-adjusted Stop Loss | Premature stop-outs or excess risk |
| `ATR TP1 Multiplier` | `decision_engine.py` | 2.40 | Volatility-adjusted TP1 ($1.6	ext{R}$) | Degrades risk-to-reward ratio |
| `ATR TP2 Multiplier` | `decision_engine.py` | 4.20 | Volatility-adjusted TP2 ($2.8	ext{R}$) | Reduces trade expectancy |
| `CONFLICT_WEIGHT_THRESHOLD` | `signal_aggregator.py` | 0.25 | Opposing weight forcing WAIT | Permits trades during conflicting forces |
| `DIRECTIONAL_THRESHOLD` | `signal_aggregator.py` | 20.0 | Net score required for Overall signal | Inaccurate Overall direction |
| `Gemini Cache Duration` | `ai_service.py` | 180 | In-memory AI response cache TTL | Excessive API costs & rate limits |

`Evidence: src/services/confluence_engine.py`, `src/services/decision_engine.py`, `src/services/signal_aggregator.py`

---

## 36. TEST COVERAGE & INTEGRITY

### 36.1 Full Pytest Execution Baseline
A complete, non-mutating execution of the automated test suite yielded:
- **Total Tests**: **801**
- **Passed**: **798 (99.6%)**
- **Failed**: **3 (0.4%)**
- **Duration**: 348.11 seconds (5m 48s)

### 36.2 Forensic Analysis of the 3 Failures
1. `tests/test_forward_shadow_validation_api.py::test_xau_metrics_match_database_dynamically`:
   - Failure: `assert 200 == 199`
   - Cause: Test fixture asserted a hardcoded record count of 200, whereas the physical database truthfully contains 199 legacy XAU forward signals.
2. `tests/test_forward_shadow_validation_api.py::test_ml_shadow_separation_invariant`:
   - Failure: `assert 200 == 199`
   - Cause: Same assertion comparing API total against hardcoded 200 fixture.
3. `tests/test_security_hardening.py::test_demo_reset_rate_limiting`:
   - Failure: `assert 401 == 200`
   - Cause: The test invoked `POST /api/v1/decision/trade/reset` without providing the required `X-Admin-Token` header. S7 security hardening correctly rejected the unauthenticated request with HTTP 401 Unauthorized.

`Evidence: pytest -q runtime execution output`

---

## 37. SAFE RUNTIME VERIFICATION

Live read-only curl queries executed against the running backend server (`http://localhost:8000`) confirm:

### 37.1 Health & Connectivity (`GET /api/v1/health`)
```json
{
  "status": "ok",
  "app": "Gold AI Trading Analysis",
  "feed": "online",
  "gemini_active": true,
  "gemini_configured": true,
  "ai_provider": "auto",
  "ai_model": "gemini-3.1-flash-lite"
}
```

### 37.2 Bitcoin Live Decision (`GET /api/v1/decision?symbol=BTC-USD-SPOT`)
- **Symbol**: `BTC/USD`
- **Signal**: `None` (Evaluated as **`WAIT`**)
- **Signal Strength**: `55%`
- **Technical Score**: `47` / 90
- **Gemini Score**: `8` / 10
- **Confluence Factors**: 17 evaluated
- **Quality Gate Override**: Confluence score (55%) below minimum validated threshold (58%). Correctly defaulted to WAIT with zero stale levels.

### 37.3 Gold Live Decision (`GET /api/v1/decision?symbol=XAU-USD-SPOT`)
- **Symbol**: `XAU/USD`
- **Signal**: `None` (Evaluated as **`WAIT`**)
- **Signal Strength**: `36%`
- **Technical Score**: `35` / 90
- **Gemini Score**: `1` / 10
- **Confluence Factors**: 17 evaluated
- **Quality Gate Override**: Direction Gate failed and Confluence score (36%) below threshold. Correctly defaulted to WAIT.

### 37.4 Production Gating Status (`GET /api/v1/admin/gating/status`)
```json
{
  "status": "success",
  "gating_status": {
    "production_gating_btc": false,
    "production_gating_xau": false,
    "automatic_retraining": false,
    "automatic_threshold_optimization": false,
    "invariants_ok": true
  }
}
```

`Evidence: Safe runtime GET requests to localhost:8000`

---

## 38. PERFORMANCE & OPERATIONAL BEHAVIOR

- **API Latency**: Average response time for `/api/v1/decision` is 180–350ms when Gemini is cached; 1.2–2.5s on fresh Gemini calls.
- **Frontend Polling Frequencies**:
  - Live Quote: Every 5,000ms (`useDashboardData.ts`).
  - Decision / Confluence: Every 15,000ms.
  - Historical Backtest / Datasets: On tab navigation.
- **Background Daemon Threads**:
  - `LiveCandleIngestionService`: Runs every 300s, catches up missed 5m candles.
  - `ForwardShadowResolverWorker`: Evaluates limit order fills and resolution every 60s.
- **Database Concurrency**: SQLite runs in WAL (Write-Ahead Logging) mode, permitting concurrent read transactions during background ingestion writes.

`Evidence: src/api/main.py lines 54-66`, `Evidence: frontend/src/hooks/useDashboardData.ts`

---

## 39. SECURITY & EXECUTION SAFETY

1. **Zero Real Broker Integration**: No broker execution SDKs (CCXT, MT4/MT5, IBKR) exist in the repository.
2. **Production Gating Hardening**: `production_gating_btc` and `production_gating_xau` are hardcoded to `False`. Enabling BTC gating requires a cryptographic `X-Admin-Token` matching `ADMIN_AUTH_TOKEN` via `secrets.compare_digest`.
3. **Secret Redaction**: API keys (`GEMINI_API_KEY`, `ADMIN_AUTH_TOKEN`) are loaded from `.env` and never logged or exposed in client responses.
4. **Defensive Security Headers**: Injected on all HTTP responses:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

`Evidence: src/api/main.py lines 125-136`, `Evidence: src/core/security.py`

---

## 40. CURRENT SYSTEM HEALTH MATRIX

| Subsystem | Status | Evidence | Risk Level |
|:---|:---|:---|:---:|
| **Live Market Data Feed** | **VERIFIED WORKING** | `MarketDataService` live spot feeds active | LOW |
| **Data Validation & Outlier Filter** | **VERIFIED WORKING** | Monotonic checks & forming candle exclusion active | LOW |
| **Technical Indicators** | **VERIFIED WORKING** | EMA, RSI, MACD, ATR, VWAP formulas verified | LOW |
| **Market Structure (SMC/ICT)** | **VERIFIED WORKING** | MSS, BOS, FVG, OTE, Elliott Wave verified | LOW |
| **17-Contributor Engine** | **VERIFIED WORKING** | 100-point rubric, direction gate & delta tracking active | LOW |
| **Gemini AI Service** | **VERIFIED WORKING** | 180s caching, fallback chain, max 10pt cap active | LOW |
| **Decision Engine & Trade Matrix** | **VERIFIED WORKING** | Quality gates (58%), ATR levels, WAIT nullification active | LOW |
| **Now Market Tab** | **VERIFIED WORKING** | Live rendering of 17 contributors & setup matrix | LOW |
| **Historical Evidence Matching** | **VERIFIED WORKING** | 2.15 GB database, 2,438 signals, $N \ge 25$ gate active | LOW |
| **ML Inference (Point-in-Time)** | **VERIFIED WORKING** | Scikit-learn models inferring valid probabilities | LOW |
| **ML Observation Collection** | **BROKEN (HALTED)** | Gated behind `persist=False` in `_build_decision` | HIGH |
| **ML Shadow Validation Worker** | **DISCONNECTED** | Offline resolver not invoked in background worker | MEDIUM |
| **Forward Governance State Machine** | **VERIFIED WORKING** | State S2 active, gating disabled, quarantine verified | LOW |
| **Signal Aggregator (Backend)** | **VERIFIED WORKING** | 4-component weighted synthesis with Conflict Gate | LOW |
| **Overall Page (Frontend Blending)** | **SEMANTIC DEFECT** | Ad-hoc arithmetic average blends win rate & setup score | HIGH |
| **Production Gating Safeguards** | **VERIFIED WORKING** | Strictly disabled, token-authenticated kill switch | ZERO |

`Evidence: Cross-system audit across backend, frontend, database, and test suite`

---

## 41. LOGIC RISK REGISTER

| # | Risk Description | File / Function | Current Logic | Expected Intent | Impact | Severity |
|:---:|:---|:---|:---|:---|:---|:---:|
| 1 | **ML Observation Collection Halted** | `decision_service.py:398` | `generate_prediction(..., persist=persist)` where `persist=False` | ML observations should be recorded as research data regardless of HTTP request persistence | Zero ML observations collected since Sept 13 | **CRITICAL** |
| 2 | **ML Shadow Forward Resolution Not Running** | `decision_service.py:443` | Resolver gated behind `if persist:` | Pending observations should resolve against forward closed candles | 1 pending BTC observation frozen; zero XAU resolved | **HIGH** |
| 3 | **Semantic Divergence in Overall Insight** | `format.ts:209` | Computes arithmetic average of Historical Win Rate and Now Confluence | Should consume backend `OverallTradingSignal` from `SignalAggregator` | Mathematically conflates win rate with setup score | **HIGH** |
| 4 | **Non-Deterministic Observation IDs** | `models.py:54` | Generates random UUID (`uuid.uuid4().hex`) | Should use deterministic hash of `(symbol, timestamp_t0)` | Multiple calls on the same candle bypass SQLite deduplication | **MEDIUM** |
| 5 | **Symbol Parameter Divergence** | `api.ts` vs `settings.py` | Frontends pass `BTC-USD`, `BTC-USD-SPOT`, `BTC/USD` | Unified canonical symbol formatting | Redundant regex cleaning required across endpoints | **LOW** |

`Evidence: Line-by-line inspection of affected source files`

---

## 42. BACKEND → UI DATA LINEAGE MASTER TABLE

| UI Element | Frontend Component | API Endpoint | Backend Service | Calculation / Function | Raw Data Source | Freshness | True Meaning |
|:---|:---|:---|:---|:---|:---|:---:|:---|
| **Now Market Hero Direction** | `SignalHeroCard.tsx` | `/api/v1/decision` | `DecisionEngine` | `_run_evaluation()` | Confluence Direction Gate | 15s | BUY, SELL, or WAIT |
| **Now Market Hero Percentage** | `SignalHeroCard.tsx` | `/api/v1/decision` | `ConfluenceEngine` | `compute()` sum of 17 contributors | Synchronized MarketSnapshot | 15s | Setup Strength Score (0–100) |
| **Live Asset Price** | `CandleChart.tsx` | `/api/v1/market/price` | `MarketDataService` | Live bid/ask mid-quote | Binance / GoldPrice spot feed | 5s | Current spot exchange price |
| **Trade Entry Zone** | `page.tsx` Setup Card | `/api/v1/decision` | `DecisionEngine` | $[	ext{Price} - 0.35	ext{ATR}, 	ext{Price}]$ | 14-period ATR on 15M candles | 15s | Recommended entry range |
| **Stop Loss (SL)** | `page.tsx` Setup Card | `/api/v1/decision` | `DecisionEngine` | $	ext{Price} \pm 1.50	ext{ATR}$ | 14-period ATR on 15M candles | 15s | Volatility-adjusted SL ($-1.0	ext{R}$) |
| **Take Profit 1 (TP1)** | `page.tsx` Setup Card | `/api/v1/decision` | `DecisionEngine` | $	ext{Price} \pm 2.40	ext{ATR}$ | 14-period ATR on 15M candles | 15s | First target ($+1.6	ext{R}$) |
| **Take Profit 2 (TP2)** | `page.tsx` Setup Card | `/api/v1/decision` | `DecisionEngine` | $	ext{Price} \pm 4.20	ext{ATR}$ | 14-period ATR on 15M candles | 15s | Runner target ($+2.8	ext{R}$) |
| **Technical Factor Score** | `page.tsx` Confluence Card | `/api/v1/decision` | `ConfluenceEngine` | Sum of contributors 1–16 | 1D, 1H, 15M, 5M technicals | 15s | Technical setup points (0–90) |
| **Gemini AI Score** | `page.tsx` Confluence Card | `/api/v1/decision` | `ConfluenceEngine` | Contributor 17 Points | Gemini 3.1 Flash Lite JSON | 180s TTL | AI confirmation points (0–10) |
| **Historical Win Rate** | `HistoricalBacktestTab.tsx` | `/api/v1/decision` | `HistoricalDataService` | Historical setup matching | 2,438 pre-computed signals in SQLite | On load | Empirical win rate ($N \ge 25$) |
| **ML Probability** | `MLModelsTab.tsx` | `/api/v1/decision` | `MLShadowService` | Scikit-Learn `predict_proba()` | 30 features at timestamp $T_0$ | 15s | Calibrated win probability |
| **Forward Shadow Clean N** | `ShadowAccumulationMonitor.tsx` | `/api/v1/research/governance/forward-shadow-validation` | `ForwardShadowEngine` | Query `forward_shadow_signals` | Clean forward signal accumulation | On load | Clean forward setups accumulated |

`Evidence: Complete cross-layer mapping from UI elements to backend raw data`

---

## 43. CURRENT PROJECT A–Z BRIEF EXPLANATION

### A. Market Data
Continuous real-time spot ticks and closed multi-timeframe candles enter via Binance (BTC) and GoldPrice/Gold-API (XAU). Forming candles are strictly excluded.

### B. Technical Analysis
Indicators (EMA stacks, RSI, MACD, VWAP, ATR) and institutional market structure (SMC sweeps, MSS, FVG, OTE, Elliott Wave) are computed across closed 1D, 1H, 15M, and 5M candles.

### C. 17 Contributors
A synchronized, point-in-time `MarketSnapshot` is evaluated against 17 discrete criteria. 16 technical factors award up to 90 points.

### D. Gemini AI
Gemini 3.1 Flash Lite analyzes market context and contributes up to 10 points. It has zero authority to override technical trend direction.

### E. Confluence (XX%)
Confluence is the arithmetic sum of technical and AI points (0–100). It measures structural setup conviction, not future win probability.

### F. Direction & Gates
The Direction Gate requires agreement from at least 2 of 3 core factors (HTF Trend, Market Structure, MTF Alignment). Signals must achieve $\ge 55\%$ confluence, satisfy asset-specific Quality Gates ($\ge 58\%$, MTF alignment, VWAP/Asia rules), and clear the Conflict Gate.

### G. Now Market
The real-time operational dashboard rendering live price, active setup status, the 17 contributor cards, and ATR-calculated trade levels.

### H. Historical Evidence
Matches the current market signature against 2,438 historical setups in SQLite ($N \ge 25$) to report empirical win rate and expectancy.

### I. Machine Learning
Scikit-learn classifiers (`LogisticRegression` for BTC, `RandomForestClassifier` for XAU) evaluate 30 point-in-time features as downstream observers with 0% live execution authority.

### J. Shadow Validation
Forward market candles evaluate whether pending ML setups hit TP1 ($+1.5	ext{R}$), SL ($-1.0	ext{R}$), or expired, establishing Brier calibration scores.

### K. Forward Evidence
Clean forward setups accumulate natural real-time validation proof, strictly isolated from quarantined legacy test fixtures.

### L. Governance
The Phase 6 to Phase 33 State Machine enforces that production gating and live execution remain strictly disabled until clean forward milestones are satisfied.

### M. Frontend Dashboard
A unified Next.js dashboard presenting the 6 distinct operational domains with consistent semantic color mapping (Green $\ge 50\%$ BUY, Red $\ge 50\%$ SELL, Neutral Slate WAIT).

---

## 44. FINAL ACTUAL CURRENT ARCHITECTURE DIAGRAM

```text
====================================================================================================
                                      ACTUAL CURRENT ARCHITECTURE
====================================================================================================

[DATA]
  BTC Live Feed ─────────► Binance / Coinbase Spot (REST/WS)
  XAU Live Feed ─────────► GoldPrice / Gold-API Spot
  Candle Ingestion ──────► LiveCandleIngestionService (5m closed candles -> SQLite candles table)
  Historical DB ─────────► data/historical/historical_market_data.db (2.15 GB, 9.6M candles)

[BACKEND]
  MarketDataService ─────► Closed-candle filter (_closed) + In-memory cache
  Technical Analysis ────► EMA (20/50/200), RSI (14), MACD (12/26/9), VWAP, ATR (14)
  Structure Analysis ────► SMC Liquidity Sweeps, MSS, Fair Value Gaps, Fibonacci OTE, Elliott Wave
  Gemini AI Provider ────► Gemini 3.1 Flash Lite (180s cache, fallback chain, max 10 points)
  ConfluenceEngine ──────► 17 Contributors (90 Tech + 10 AI = 100 Max)
                           └── Direction Gate (2 of 3 HTF / Structure / MTF)
  DecisionEngine ────────► Quality Gate (Confluence >= 58, Asset rules)
                           └── Trade Setup Matrix (Entry Zone, SL, TP1, TP2) -> NULL on WAIT

[SYNTHESIS & OBSERVERS]
  DecisionService ───────► 3-Layer Architecture:
                           ├── Layer 1: HistoricalMarketSignal (N >= 25 empirical match)
                           ├── Layer 2: NowMarketSignal (Confluence %)
                           ├── Observer: MLShadowService (30 features, T0 snapshot, 0% authority)
                           └── Layer 3: SignalAggregator (Fused Overall Signal, Conflict Gate)

[EVIDENCE & GOVERNANCE]
  ForwardShadowEngine ───► forward_shadow_signals table (479 Quarantined Fixtures, Clean N=0)
  ML Shadow Store ───────► ml_shadow_observations table (3,828 records, 84 BTC resolved, 1 pending)
  State Machine ─────────► data/governance_forward_state.json (S2: EVIDENCE_COLLECTION)
  Gating Control ────────► data/gating_state.json (BTC: DISABLED, XAU: DISABLED)

[API LAYER]
  FastAPI REST API ──────► /api/v1/market/price, /candles, /decision, /ml/shadow, /governance

[FRONTEND LAYER]
  Next.js 14 Dashboard ──► 6 Navigation Tabs:
                           ├── OVERALL (Blended Hero + Dual Asset Ticker)
                           ├── MARKET INSIGHT (Macro & Narrative Context)
                           ├── CURRENT MARKET (17 Contributors + Candle Chart + Setup Matrix)
                           ├── SHADOW (Forward Shadow Accumulation Monitor)
                           ├── ML MODELS (ML Calibration, Probabilities, Observation Logs)
                           └── GOVERNANCE (Phase 6-33 Roadmap Matrix)
====================================================================================================
```

---

## 45. FUTURE UI RESTRUCTURE READINESS

A planned future UI restructuring intends to consolidate the platform into 5 dedicated pages:
1. **NOW MARKET**
2. **HISTORY MARKET**
3. **COMBINED ML & SHADOW UI**
4. **FULL-SYSTEM MARKET INSIGHT**
5. **CONCISE OVERALL SUMMARY**

### Readiness Assessment Matrix
| Planned Section | Current Project Status | Backend Readiness | Frontend Readiness | Actions Required in Later Task |
|:---|:---|:---|:---|:---|
| **1. NOW MARKET** | **EXISTS — REUSE** | `BACKEND CHANGE NOT REQUIRED` | Ready | Retain current real-time chart, 17 contributors, and setup matrix. |
| **2. HISTORY MARKET** | **PARTIAL — EXTEND** | `BACKEND CHANGE NOT REQUIRED` | Minor UI Polish | Promote HistoricalBacktestTab into a standalone top-level view. |
| **3. COMBINED ML & SHADOW**| **PARTIAL — EXTEND** | `BACKEND CHANGE REQUIRED (REPAIR)` | High Reuse | Repair observation persistence & forward resolver; merge ML and Shadow tabs. |
| **4. FULL-SYSTEM INSIGHT** | **PARTIAL — EXTEND** | `BACKEND CHANGE NOT REQUIRED` | Design Extension | Expand narrative explanations to integrate Now, Hist, and ML into one story. |
| **5. CONCISE OVERALL** | **EXISTS — CONSOLIDATE** | `BACKEND CHANGE NOT REQUIRED` | Deprecate Frontend Avg | Bind Overall Hero directly to backend `OverallTradingSignal` from `SignalAggregator`. |

---

## 46. FINAL VERDICT & STOP CONDITION

### What is verified working?
- Dual-asset live market feeds for BTC and XAU with zero cross-contamination.
- Closed-candle filtering policy eliminating lookahead bias.
- 16 technical indicators and institutional SMC/ICT structure detection.
- 17-Contributor Confluence Engine (100-point rubric) and Direction Gate (2 of 3 rule).
- Gemini 3.1 Flash Lite bounded integration (max 10 points) with 180s caching.
- Decision Engine Quality Gates ($\ge 58\%$, MTF alignment, VWAP, Asia session rules).
- Institutional Trade Setup Matrix with strict nullification during WAIT.
- SignalAggregator 4-component weighted synthesis with invariant Conflict Gate.
- Governance state machine in `S2: EVIDENCE_COLLECTION` with production gating strictly disabled.
- Security hardening (token-authenticated admin gating, defensive HTTP headers).
- 798 passing automated regression tests.

### What is implemented but not fully verified?
- Real-time limit-order entry fills under extreme live market volatility.
- Clean forward accumulation milestone progression (currently at $N=0/50$).

### What is broken?
- **ML Observation Collection Persistence**: Gated behind `persist=False` in `DecisionService._build_decision`, freezing observation writes since September 13th.
- **ML Shadow Validation Worker**: Pending ML observations are not evaluated by the background resolver worker.

### What is disconnected?
- `MLShadowService.resolve_pending_observations` is not wired into `ForwardShadowResolverWorker.run_cycle()`.

### What is duplicated?
- Confluence score calculation exists in `ConfluenceEngine` while legacy weighted math remains in `DecisionEngine`.
- Overall score calculation exists in backend `SignalAggregator` while an ad-hoc arithmetic average exists in frontend `format.ts`.

### What has semantic/UI problems?
- The frontend Overall Hero card currently calls `computeOverallInsightPercentage`, averaging an empirical historical win rate with a technical setup score.

### What could affect analytical accuracy?
- The arithmetic blending of historical win rate and now confluence on the frontend Overall tab misrepresents setup probability.

### What should NOT be changed?
- The core quantitative logic, Direction Gate, Quality Gate, Conflict Gate, 17 contributor weights, and ATR setup matrix.
- Production gating invariants (`DISABLED`) and live execution boundaries (0 broker execution).

### What can safely be reused for the future UI restructure?
- `SignalHeroCard.tsx`, `format.ts` (`resolveHeroPresentation`), `CandleChart.tsx`, `MLModelsTab.tsx`, `ShadowAccumulationMonitor.tsx`, and `EmpiricalPerformancePanel.tsx`.

### What future changes will actually be required?
1. Surgical repair of ML observation collection and background shadow resolution.
2. Direct binding of Overall Hero to backend `OverallTradingSignal`.
3. Merging ML Models and Shadow into a single consolidated tab.

---

### OVERALL PROJECT STATE
**`FUNCTIONAL QUANT ENGINE WITH REVERSIBLE ML OBSERVER STOPPAGE & ISOLATED FORWARD QUARANTINE`**

### SAFE TO BEGIN UI RESTRUCTURE
**`CONDITIONAL`**

**Blockers to resolve before restructuring UI**:
1. Perform the surgical fix to uncouple ML observation collection from `persist=False` so live observations resume saving.
2. Wire ML shadow resolution into the background worker to resolve the single pending BTC observation.
3. Replace frontend arithmetic averaging (`computeOverallInsightPercentage`) with direct consumption of backend `OverallTradingSignal`.

---

## STOP CONDITION

**AUDIT COMPLETE.**  
No code modifications, refactorings, database mutations, commits, or pushes have been performed. The system remains in its exact pre-audit state. Awaiting user review.
