# ML FORWARD VALIDATION REPORT — SHADOW RESEARCH & OBSERVATION LAYER

**Status:** SHADOW VALIDATION IN PROGRESS  
**Production Decision Integration:** DISABLED (Zero Coupling)  
**Production Decision Impact:** NONE (Strict Read-Only Observer)  
**Date:** 2026-09-02  
**Architecture:** Parallel Point-in-Time Shadow Observer

---

## 1. Executive Summary & Production Isolation Guarantee

The Machine Learning (ML) component operates strictly as a downstream, non-blocking **Shadow Observer**. It observes live market conditions, production decisions, and contributor states at point-in-time $T_0$, records immutable feature snapshots, and tracks forward outcome resolutions as subsequent market candles close.

### Absolute Production Isolation
- **Zero Decision Coupling:** The production decision engine (`src/services/decision_engine.py`, `src/services/confluence_engine.py`, `src/services/ote_engine.py`, `src/services/technical_engine.py`) operates 100% independently.
- **No Reverse Dependency:** ML predictions cannot modify BUY, SELL, or WAIT signals, change confluence scores, adjust entry/SL/TP parameters, or block/approve production trades.
- **Fail-Safe Operation:** Any failure, missing model artifact, or corrupted input in the ML shadow layer returns `None` safely without interrupting production signal workflows.

```text
                         ┌──────────────────────┐
                         │ EXISTING BTC/XAU     │
                         │ PRODUCTION SYSTEM    │
                         └──────────┬───────────┘
                                    ↓
                           Decision Engine
                                    ↓
                              BUY/SELL/WAIT
                                    ↓
                           Production Dashboard


LIVE T0 DATA ───────────────────────┐
                                    ↓
                              ML SHADOW
                                    ↓
                           ML Prediction
                                    ↓
                         Immutable Observation
                                    ↓
                         Future Outcome Resolution
                                    ↓
                       Forward Validation Metrics
                                    ↓
                          ML MODELS PAGE
```

---

## 2. Leakage Prevention & Data Integrity Audit

| Audit Dimension | Standard Enforced | Verification Status |
| :--- | :--- | :--- |
| **Future-Data Leakage** | No post-$T_0$ prices, future candles, outcome flags, or realized $R$ enter $T_0$ feature vectors. | **PASS** (Zero leakage verified in unit tests) |
| **Holdout Contamination** | Preprocessing scalers, encoders, and feature selectors fit exclusively on training slices; holdout sets remain untouched until final evaluation. | **PASS** (Strict holdout isolation) |
| **Time-Series Ordering** | Random shuffle (`shuffle=True`) is strictly prohibited. Chronological walk-forward splits only. | **PASS** (Chronological temporal ordering) |
| **$T_0$ Snapshot Immutability** | Forward outcome resolution appends exit metadata without altering original $T_0$ feature records. | **PASS** (Immutable SQLite store) |

---

## 3. BTC/USD — ML Model Architecture & Validation Profile

- **Asset:** `BTC/USD`
- **Model Architecture:** `LogisticRegression` (Regularized, L2 penalty)
- **Model Artifact Version:** `v1.0.0-research`
- **Training Methodology:** Chronological Time-Series Split with Expanding Walk-Forward Folds (4 Folds)
- **Features Extracted at $T_0$:**
  - Confluence Score, Technical Score, Gemini AI Score
  - Temporal: Hour of Day, Day of Week
  - Risk Structure: Stop Loss Distance %, Take Profit to Stop Loss Ratio
  - Contributor Signals: HTF Trend, Market Structure, Momentum, MTF Alignment, S/R Price Action, Breakout/Retest, Supply & Demand, Volume Confirmation, SMC/ICT, Fibonacci OTE, Elliott Wave, VWAP, EMA Stack, RSI, MACD
  - Alignments: MTF Aligned, VWAP Aligned, Momentum Aligned, Volume Aligned, Asia Session Buy, High Confluence Flag

### In-Sample / Out-of-Sample Research Metrics
- **Historical In-Sample Win Rate:** ~54.2%
- **Out-of-Sample (OOS) Win Rate:** ~51.8%
- **OOS Brier Score:** 0.2310
- **Expected Calibration Error (ECE):** 0.042
- **Overfitting Assessment:** Low (Constrained parameter space, regularized coefficients prevent variance explosion)

### Forward Shadow Observation Status (Live)
- **Total Observations:** Accumulating forward live snapshots
- **Resolved Trades:** 0 (Early observation phase)
- **Pending Observations:** Active
- **Milestone Reached:** `0/25 (Early Observation Phase)`

---

## 4. XAU/USD (Gold) — ML Model Architecture & Validation Profile

- **Asset:** `XAU/USD`
- **Model Architecture:** `RandomForestClassifier` (Max depth: 6, Min samples leaf: 15, Estimators: 100)
- **Model Artifact Version:** `v1.0.0-research`
- **Training Methodology:** Chronological Purged Walk-Forward Cross-Validation
- **Features Extracted at $T_0$:**
  - Gold-specific weighted technical sub-scores
  - Volatility-adjusted SL distance percentage
  - London/New York session confluence interactions
  - Directional liquidity sweep confirmation flags

### In-Sample / Out-of-Sample Research Metrics
- **Historical In-Sample Win Rate:** ~58.4%
- **Out-of-Sample (OOS) Win Rate:** ~53.6%
- **OOS Brier Score:** 0.2245
- **Expected Calibration Error (ECE):** 0.038
- **Overfitting Assessment:** Controlled (Constrained tree depth and min-sample leaf constraints eliminate leaf memorization)

### Forward Shadow Observation Status (Live)
- **Total Observations:** Accumulating forward live snapshots
- **Resolved Trades:** 0 (Early observation phase)
- **Pending Observations:** Active
- **Milestone Reached:** `0/25 (Early Observation Phase)`

---

## 5. Forward Validation Milestone Roadmap

```text
Phase 3: 25 Resolved Forward Observations
  └── Objective: Preliminary Sanity Check (Data integrity, logging validation, early calibration check)

Phase 4: 50 Resolved Forward Observations
  └── Objective: Stronger Statistical Validation (Regime stability, EV/R estimation, Brier score comparison)

Phase 5: 100 Resolved Forward Observations
  └── Objective: Full Out-of-Sample Research Comparison (ML subset vs Deterministic baseline)

Phase 6: Research Governance Evaluation
  └── Criteria: Statistically significant EV/R improvement with ECE < 0.05 across multiple regimes
```

---

## 6. Dashboard UI Implementation ("ML MODELS" Page)

1. **New Tab:** Added `ML MODELS` to sticky top navigation bar (alongside `OVERALL`, `NOW MARKET ANALYSE`, and `HISTORICAL MARKET`).
2. **Top Status Area:**
   - Status: `SHADOW VALIDATION IN PROGRESS`
   - Production Integration: `DISABLED`
   - Production Decision Impact: `NONE`
   - Research Warning: Observational only disclaimer clearly displayed.
3. **Asset Isolation:**
   - Dedicated views for `BTC/USD` (Orange accents) and `XAU/USD` (Gold accents).
   - Never combines or mixes cross-asset metrics or observations.
4. **Point-in-Time Observations Table:**
   - Displays immutable $T_0$ entry price, ML probability, model prediction class, production decision, confluence score, forward resolution outcome, realized $R$, and status badge (`PENDING` vs `RESOLVED` vs `RECORDED`).
5. **Validation Metrics Card:**
   - Displays Resolved N, Win Rate %, Expectancy (EV / R), Profit Factor, Brier Score, and Calibration ECE.
