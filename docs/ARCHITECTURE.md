# SYSTEM ARCHITECTURE SPECIFICATION

**System**: BTC/USD & XAU/USD Quantitative AI Trading Analysis Platform  
**Architecture Classification**: Multi-Layer Evidence Fusion Engine with Strict Shadow Isolation  
**Operational Status**: Advisory & Research Mode (Zero Automated Broker Execution)  

---

## 1. High-Level Architectural Overview

```
+-----------------------------------------------------------------------------------+
|                                  PRESENTATION LAYER                               |
|               Next.js 14 App Router (Tailwind CSS, Lucide Icons, Canvas)           |
|                                                                                   |
|  [SignalHeroCard]   [CandleChart]   [EmpiricalPanel]   [MLTab]   [ShadowMonitor]  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | REST / JSON (port 8000)
                                         v
+-----------------------------------------------------------------------------------+
|                                FASTAPI APPLICATION LAYER                          |
|                                                                                   |
|  /trade/decision       /trade/candles       /api/ml/shadow       /api/v1/admin    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            ANALYTICAL & FUSION LAYER                              |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 SignalAggregator (Phase 5c-h Fusion Engine)                 |  |
|  |   - Component 1: Now Market Technical (25% BTC / 27% XAU)                   |  |
|  |   - Component 2: Historical Statistical Evidence (27% BTC / 26% XAU)        |  |
|  |   - Component 3: ML Shadow Classification (26% BTC / 24% XAU)               |  |
|  |   - Component 4: Validated Strategy Layer (22% BTC / 23% XAU)               |  |
|  |   - Invariants: Conflict Gate (>=0.25 opposing forces WAIT, pct=None)       |  |
|  |   - Directional Threshold: |S_net| >= 20.0 for BUY/SELL; else WAIT          |  |
|  +-----------------------------------------------------------------------------+  |
|                                        ^                                          |
|                                        |                                          |
|         +------------------------------+------------------------------+           |
|         |                              |                              |           |
|  +---------------+             +---------------+             +---------------+    |
|  |  Decision     |             |  Historical   |             |  ML Shadow    |    |
|  |  Engine       |             |  Evidence     |             |  Service      |    |
|  |  (17 Tech     |             |  Service      |             |  (v1.0.0      |    |
|  |  Indicators)  |             |  (Bayesian)   |             |  Research)    |    |
|  +---------------+             +---------------+             +---------------+    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            DATA & PERSISTENCE LAYER                               |
|                                                                                   |
|  [SQLite: historical_market_data.db]  [SQLite: shadow_trades.db]  [paper_trading] |
|   - candles (9.6M+ OHLCV)              - shadow trade simulations  - user demo    |
|   - historical_signals (2,438)                                       demo ledger  |
|   - forward_shadow_signals (193)                                                  |
|   - ml_shadow_observations (403)                                                 |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Subsystems

### Subsystem 1: Decision Engine (`src/services/decision_engine.py`)
- Ingests completed closed candles from `MarketDataService`.
- Computes 17 distinct technical indicators totaling exactly 100 points:
  - Trend Indicators (EMA 20/50/200, Supertrend, ADX)
  - Momentum Indicators (RSI, Stochastic, MACD)
  - Volatility & Structure (Bollinger Bands, ATR, Market Structure Breaks)
- Direction Gate: Requires at least 2 of 3 alignment among HTF Trend, Market Structure, and MTF Alignment.

### Subsystem 2: Signal Aggregator (`src/services/signal_aggregator.py`)
- Synthesizes 4 distinct dimensions of evidence:
  - C1: Now Market Analysis
  - C2: Historical Evidence
  - C3: ML Shadow Model
  - C4: Validated Strategy Layer
- Proportional Dynamic Normalization: When optional components are unavailable, weights re-normalize to 100%.
- Conflict Invariance: Opposing directional evidence ($\ge 0.25$) forces `WAIT` with `percentage=None`.
- Directional Threshold: Net score must exceed $|20.0|$; otherwise `WAIT` with `percentage=None`.

### Subsystem 3: Machine Learning Layer (`src/research/ml/`)
- Baseline Models:
  - BTC/USD: `LogisticRegression(C=1.0, solver='lbfgs', max_iter=500, random_state=42)` (`v1.0.0-research`).
  - XAU/USD: `RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=10, random_state=42)` (`v1.0.0-research`).
- Strict Chronological Splitting: 60% Train, 20% OOS, 20% Holdout. Zero lookahead leakage.
- Status: Advisory Shadow Only. All hyperparameter-tuned candidate models rejected due to holdout degradation.

### Subsystem 4: Shadow & Governance Layer (`src/research/governance/`)
- `ForwardShadowEngine`: Automatically tracks and deterministically resolves trade outcomes ($T_0 \rightarrow T_{exit}$) against live 5-minute candles.
- `XAUForwardAccumulationTracker`: Evaluates evidence milestones for XAU ($N < 50 \rightarrow$ `INSUFFICIENT_EVIDENCE`).
- Production Gating Controller: Ensures production gating defaults to `DISABLED`.

---

## 3. System Invariants & Non-Negotiable Boundaries

1. **Broker Isolation**: Zero live order execution APIs or broker credentials exist in the system.
2. **Quant Immutability**: 17 technical contributors (100 pts) and aggregator base weights (BTC: 25/27/26/22, XAU: 27/26/24/23) are permanently frozen.
3. **Storage Segregation**: Manual demo paper trading (`paper_trading.json`) is physically separated from SQLite historical and shadow databases.
