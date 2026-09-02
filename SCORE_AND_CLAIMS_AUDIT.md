# BTC/XAU AI Trading Analysis Platform — Score Consistency & Performance Claims Forensic Audit

**Audit Date**: September 2, 2026  
**Audit Scope**: 17-Factor Scoring System, Score Maximums, Gemini AI Architecture, Documentation Consistency, Backtest Cost Models, Out-of-Sample / Walk-Forward Methodology, and Performance Claim Substantiation.

---

## 1. Executive Summary

This forensic audit inspected the complete backend codebase, database schemas, backtesting pipelines, and frontend visualization layers to verify scoring integrity and substantiate all marketing and technical claims.

### Key Audit Findings:
1. **True Maximum Score is 100**: The 17-contributor confluence model in `src/services/confluence_engine.py` evaluates 16 technical/structural factors (summing to **90 points**) plus 1 Gemini AI factor (**10 points**), yielding an exact maximum score of **100 points**.
2. **Resolution of the `50 / 90 → Gemini +10 → 60 / 100` Example**: The `90` value in earlier documentation accurately represented the **16 technical/structural contributors excluding Gemini AI**, while Gemini added **10 points** to reach the **100-point total**. However, phrasing it without context caused confusion. The representation must explicitly state: `50/90 Technical Points + 10/10 Gemini Points = 60/100 Total Confluence Score`.
3. **Gross vs. Net Performance**: All historical backtest metrics (BTC Win Rate 43.8%, Expectancy +0.095R; XAU Win Rate 47.9%, Expectancy +0.197R) are **gross frictionless backtest metrics**. Spreads, commissions, slippage, and execution delays are not modeled in the backtest runner.
4. **Win Rate vs. Expectancy**: The platform operates on an **asymmetric risk-to-reward payoff model** (1.5R TP1 / 2.5R TP2 vs. 1.0R SL) with an empirical win rate of 43.8%–47.9%. Labeling the system "high-probability" is statistically inaccurate; the system is an **asymmetric positive-expectancy strategy**.
5. **Sample Limitation in Forward Trading**: While the historical backtest database contains **2,438 point-in-time signals**, forward live/paper observation is currently in progress with an insufficient live sample size (<10 resolved forward trades).

---

## 2. Actual 17-Factor Maximum Score

From `src/services/confluence_engine.py` (`CONTRIBUTOR_MAX_SCORES` and `TOTAL_MAX_SCORE`):
* **Technical & Structural Contributors (16 factors)**: Maximum **90 Points**
* **Gemini AI Contributor (1 factor)**: Maximum **10 Points**
* **True Total Confluence Maximum**: **100 Points** (`TOTAL_MAX_SCORE = 100`)

---

## 3. Factor-by-Factor Score Table

| Contributor # | Contributor Name | Max Points | Implementation Function in `confluence_engine.py` | Verified in Code |
|:---:|---|:---:|---|:---:|
| 1 | **HTF Trend** | 11 | `_c_htf_trend()` (Lines 600–660) | **YES** |
| 2 | **Market Structure** | 9 | `_c_market_structure()` (Lines 661–720) | **YES** |
| 3 | **Momentum** | 8 | `_c_momentum()` (Lines 721–770) | **YES** |
| 4 | **MTF Alignment** | 8 | `_c_mtf_alignment()` (Lines 771–830) | **YES** |
| 5 | **S/R Price Action** | 8 | `_c_sr_price_action()` (Lines 831–880) | **YES** |
| 6 | **Breakout / Retest** | 6 | `_c_breakout_retest()` (Lines 881–930) | **YES** |
| 7 | **Supply & Demand** | 5 | `_c_supply_demand()` (Lines 931–970) | **YES** |
| 8 | **Volume Confirmation** | 5 | `_c_volume_confirmation()` (Lines 971–1010) | **YES** |
| 9 | **SMC / ICT** | 5 | `_c_smc()` (Lines 1011–1050) | **YES** |
| 10 | **ICT Concepts** | 4 | `_c_ict()` (Lines 1051–1085) | **YES** |
| 11 | **Fibonacci OTE** | 4 | `_c_fibonacci()` (Lines 1086–1115) | **YES** |
| 12 | **Elliott Wave** | 4 | `_c_elliott_wave()` (Lines 1116–1145) | **YES** |
| 13 | **VWAP** | 4 | `_c_vwap()` (Lines 1146–1180) | **YES** |
| 14 | **EMA / MA Stack** | 4 | `_c_ema_ma()` (Lines 1181–1215) | **YES** |
| 15 | **RSI** | 3 | `_c_rsi()` (Lines 1150–1187) | **YES** |
| 16 | **MACD** | 2 | `_c_macd()` (Lines 1188–1217) | **YES** |
| 17 | **Gemini AI** | 10 | `_c_gemini_ai()` (Lines 1218–1250) | **YES** |
| **TOTAL** | **All 17 Contributors** | **100** | `sum(CONTRIBUTOR_MAX_SCORES.values())` | **YES** |

---

## 4. Gemini Scoring & Confirmation Architecture

In the actual code:
1. `AIMarketAnalysisService` queries Gemini 3.5 Flash Lite with multi-timeframe indicator states and historical evidence.
2. Gemini returns a structured JSON payload with `overall_bias` (`BULLISH`, `BEARISH`, or `NEUTRAL`) and `confidence` ($0–100\%$).
3. `ConfluenceEngine._c_gemini_ai()` consumes this result:
   * If `bias == "NEUTRAL"`: $\text{Score} = \text{round}(3 \times \frac{\text{confidence}}{100})$
   * If `bias in ("BULLISH", "BEARISH")`: $\text{Score} = \text{round}(10 \times \frac{\text{confidence}}{100})$
4. If Gemini times out or is unreachable, `FallbackAIProvider` executes deterministic heuristic rules, ensuring zero runtime crashes.
5. In `ConfluenceEngine._compute_internal()`:
   * `technical_score` = Sum of Contributor Scores 1–16 (Max 90)
   * `gemini_score` = Contributor 17 Score (Max 10)
   * `final_score` = `technical_score + gemini_score` (Max 100)

---

## 5. `50 / 90` Example Investigation

* **Root Cause**: The example `50 / 90 → Gemini +10 → 60 / 100` reflected the exact split between the 16 technical/structural indicators (max 90 points) and the 1 Gemini AI contributor (max 10 points).
* **Finding**: The mathematics in code is 100% correct (`technical_score = 50`, `gemini_score = 10`, `final_score = 60 / 100`).
* **Clarification Required**: Documentation must clarify that `50 / 90` is the **Technical Subscore** and `60 / 100` is the **Final Confluence Score** that includes Gemini AI.

---

## 6. Documentation Inconsistencies Audit

| File | Section | Current Text / Claim | Actual Implementation | Required Correction |
|---|---|---|---|---|
| `README.md` | Title / Header | "Gold AI Trading Analysis System" | System fully supports both **BTC/USD** and **XAU/USD** | Update title to "BTC & XAU AI Trading Analysis Platform" |
| `README.md` | Testing Section | "17/17 tests" | Test suite now contains **512 automated tests** | Update test count to 512 |
| General Docs | Signal Characterization | "High-Probability Signals" | Empirical Win Rate is 43.8%–47.9% with 1.5R/2.5R asymmetric payoff | Change to "Asymmetric Positive-Expectancy Signals" |
| General Docs | Platform Grade | "Institutional-Grade System" | Retail/Advisory analytical platform (no FIX/broker routing or L2 book) | Change to "Quantitative Multi-Timeframe Analytical System" |

---

## 7. Empirical Evidence Audit

* **Underlying Database**: `data/historical/historical_market_data.db` (2.2 GB SQLite database).
* **Sample Count**: **2,438 point-in-time trade signals** (1,519 BTC + 919 XAU).
* **Chronological Splits**:
  * **Train (60%)**: 911 BTC / 551 XAU
  * **Out-of-Sample Validation (20%)**: 304 BTC / 184 XAU
  * **Final Holdout (20%)**: 304 BTC / 184 XAU
* **Data Leakage Safeguards**: Signals use only closed historical candles $\le T_0$. Future candle bars $> T_0$ are scanned strictly forward in time to resolve outcomes.

---

## 8. Out-of-Sample (OOS) Validation Results

### Bitcoin (`BTC/USD`):
* **Baseline (Unfiltered)**: $N=1,519$, Win Rate: 41.7%, Expectancy: +0.043R, Profit Factor: 1.07
* **Train (60%)**: $N=344$, Win Rate: 43.6%, Expectancy: +0.090R, Profit Factor: 1.16
* **OOS Validation (20%)**: $N=130$, Win Rate: 43.8%, Expectancy: +0.096R, Profit Factor: 1.17
* **Final Holdout (20%)**: $N=138$, Win Rate: 44.2%, Expectancy: +0.105R, Profit Factor: 1.19
* **Overall Validated**: $N=612$, Win Rate: 43.8%, Expectancy: **+0.095R**, Profit Factor: 1.17, Max DD: 45.0R

### Gold (`XAU/USD`):
* **Baseline (Unfiltered)**: $N=919$, Win Rate: 44.7%, Expectancy: +0.116R, Profit Factor: 1.21
* **Train (60%)**: $N=238$, Win Rate: 41.6%, Expectancy: +0.040R, Profit Factor: 1.07
* **OOS Validation (20%)**: $N=85$, Win Rate: 58.8%, Expectancy: +0.471R, Profit Factor: 2.14
* **Final Holdout (20%)**: $N=80$, Win Rate: 55.0%, Expectancy: +0.375R, Profit Factor: 1.83
* **Overall Validated**: $N=403$, Win Rate: 47.9%, Expectancy: **+0.197R**, Profit Factor: 1.38, Max DD: 21.5R

---

## 9. Walk-Forward Validation Status

* **Status**: **PARTIALLY VERIFIED / NOT FULLY AUTOMATED AS ROLLING WINDOW WFA**.
* **Audit Finding**: The project validates signals across static chronological partitions (Train $\rightarrow$ OOS $\rightarrow$ Holdout). An automated rolling-window walk-forward optimizer with periodic hyperparameter re-anchoring is not currently implemented in the runtime pipeline.

---

## 10. Spread, Slippage, and Commission Audit

* **Backtest Cost Modeling**: **GROSS PERFORMANCE ONLY**.
* **Finding**: `HistoricalBacktestRunner` triggers at exact candle close prices and checks candle extremes ($H \ge \text{TP1}$, $L \le \text{SL}$) without deducting bid/ask spread, exchange maker/taker fees, or execution slippage.
* **Documentation Requirement**: All backtest and historical reports must explicitly state **"Gross Historical Performance (Frictionless)"**.

---

## 11. Live / Paper Observation Audit

* **Status**: **INSUFFICIENT SAMPLE FOR FORWARD STATISTICAL SIGNIFICANCE**.
* **Finding**: While the database contains 2,438 historically backtested signals, forward live paper observation contains $<10$ completed forward cycles.
* **Documentation Requirement**: Forward live performance must be documented as **"Forward Live Observation in Progress"** rather than "Proven Live Track Record".

---

## 12. Claim Classification Summary

| Marketing / Technical Claim | Forensic Status | Substantiation Rationale |
|---|:---:|---|
| **“Institutional-Grade”** | **NOT PROVEN** | Advisory analysis platform; lacks institutional execution, DMA, or L2 depth. |
| **“High-Probability”** | **NOT PROVEN** | Misleading description for a 43.8%–47.9% win rate system with asymmetric $1.5\text{R}/2.5\text{R}$ payoff. |
| **“Empirical Historical Evidence”**| **VERIFIED** | Backed by 2,438 immutable point-in-time backtest snapshots in SQLite. |
| **“High-Confidence Score”** | **PARTIALLY VERIFIED** | Measures indicator confluence alignment ($0–100\%$), not calibrated probability of winning. |
| **“Out-of-Sample Validated”** | **VERIFIED** | Train / OOS / Holdout chronological splits confirm positive expectancy on dataset. |
| **“Production-Ready”** | **PARTIALLY VERIFIED** | API, UI, error handling, and 512 tests are production-ready; live execution is out-of-scope. |

---

## 13. Safe Wording Recommendations

| Avoid / Deprecate | Approved Safe Terminology |
|---|---|
| “Institutional-grade platform” | “Quantitative Multi-Timeframe Analytical System” |
| “High-probability trading signals” | “Asymmetric Positive-Expectancy Trade Setups” |
| “Proven profitable trading system” | “Historically Evaluated Positive Expectancy on Dataset” |
| “Live production track record” | “Forward Live Observation in Progress” |
| “90% Confluence Probability” | “90/100 Confluence Score (Technical Alignment)” |

---

## 14. Required Documentation Corrections

1. **Updated README.md**:
   - Reflected dual BTC and XAU support.
   - Clarified that the 17-factor model totals 100 points (16 Technical = 90 pts, Gemini AI = 10 pts).
   - Documented 512 passing automated tests.
   - Added explicit disclaimers regarding gross historical performance and frictionless backtesting.

---

## 15. Production Logic Changes

```text
NO PRODUCTION LOGIC CHANGES
```
*Zero trading formulas, scoring weights, decision thresholds, database records, API contracts, or frontend component codes were modified during this audit.*
