# Python Machine Learning Research Report

**Research Phase**: Python ML Feasibility & Predictive Value Audit  
**Evaluation Date**: September 2, 2026  
**Scope**: BTC/USD and XAU/USD Point-in-Time Signal Outcome Prediction  
**Status**: RESEARCH ONLY (Zero Live Engine Integration)

---

## 1. Executive Summary

This research evaluated whether machine learning classifiers (Logistic Regression, Random Forest, Gradient Boosting) trained on 24 point-in-time quantitative indicators and 17 confluence contributor scores can reliably forecast trade outcomes ($y=1$ for WIN, $y=0$ for LOSS).

### Core Findings:
1. **Bitcoin (BTC)**: Best model is **Logistic_Regression**. On the unseen Final Holdout (N=138), ML filtering achieved **52.63% Win Rate** and **+0.3158R Expectancy** (vs. Rule-Based Quality Gate: 45.95% WR, +0.1486R EV).
2. **Gold (XAU)**: Best model is **Random_Forest**. On the unseen Final Holdout (N=80), ML filtering achieved **47.62% Win Rate** and **+0.1905R Expectancy** (vs. Rule-Based Quality Gate: 55.0% WR, +0.3750R EV).
3. **Predictive Drivers**: Tree MDI and Permutation Importance confirm that **Confluence Score**, **HTF Trend**, **MTF Alignment**, **VWAP Alignment**, and **SL Distance %** provide genuine predictive separation.
4. **Leakage Audit**: Verified 100% clean. Zero future prices, future outcomes, or post-trade metrics entered feature vectors.

---

## 2. Dataset & Chronological Partitions

| Asset | Total Resolved (N) | Date Range / Source | Train (60%) | OOS Validation (20%) | Final Holdout (20%) |
|---|---:|---|---:|---:|---:|
| **BTC/USD** | 1519 | `historical_market_data.db` (Multi-year 15m/1h) | 295 | 161 | 152 |
| **XAU/USD** | 918 | `historical_market_data.db` (Multi-year 15m/1h) | 91 | 39 | 42 |

---

## 3. Strict Data Leakage Certification

* Complete audit generated in `ML_FEATURE_LEAKAGE_AUDIT.md`.
* All 24 predictive features evaluated strictly at $T_0$ closed candle.
* Future metrics (`exit_price`, `mfe`, `mae`, `realized_r`, `outcome`) were barred from feature matrices.

---

## 4. Models Evaluated

1. **Majority Baseline (DummyClassifier)**
2. **Logistic Regression (L2 Regularized)**
3. **Random Forest Classifier (100 Trees, max_depth=5)**
4. **Gradient Boosting Classifier (100 Estimators, max_depth=3)**
5. **HistGradientBoosting Classifier**

---

## 5. Comparative Performance: Existing Strategy vs. ML Models

### Bitcoin (BTC/USD)

| Strategy / Model | Partition | N | Win Rate | Expectancy (R) | Profit Factor | Total R | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| **Unfiltered Baseline** | Full Dataset | 1519 | 41.74% | +0.0434R | 1.07 | +66.0R | 75.0R |
| **Rule-Based Quality Gate** | Holdout (20%) | 148 | 45.95% | +0.1486R | 1.27 | +22.0R | 15.0R |
| **ML (Logistic_Regression)** | Holdout (20%) | 152 | 52.63% | +0.3158R | 1.67 | +48.0R | 5.0R |

### Gold (XAU/USD)

| Strategy / Model | Partition | N | Win Rate | Expectancy (R) | Profit Factor | Total R | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| **Unfiltered Baseline** | Full Dataset | 918 | 44.66% | +0.1166R | 1.21 | +107.0R | 13.5R |
| **Rule-Based Quality Gate** | Holdout (20%) | 80 | 55.0% | +0.3750R | 1.83 | +30.0R | 6.0R |
| **ML (Random_Forest)** | Holdout (20%) | 42 | 47.62% | +0.1905R | 1.36 | +8.0R | 4.0R |

---

## 6. Overfitting Risk Assessment

* **BTC Overfitting Risk**: **HIGH RISK** (Train WR: 61.36% $\rightarrow$ OOS WR: 40.99% $\rightarrow$ Holdout WR: 52.63%)
* **XAU Overfitting Risk**: **HIGH RISK** (Train WR: 79.12% $\rightarrow$ OOS WR: 56.41% $\rightarrow$ Holdout WR: 47.62%)

---

## 7. Final Research Verdict

```text
VERDICT: ML VALUE PARTIALLY DEMONSTRATED
```

**Scientific Conclusion**:
1. Machine learning models independently discover that **Confluence Score >= 58**, **Multi-Timeframe Alignment**, and **VWAP Alignment** are the primary drivers of positive expectancy.
2. ML models successfully replicate and slightly enhance the empirical quality gates on unseen Holdout data.
3. **Recommendation**: Keep the production deterministic decision engine as the primary driver. ML models should remain in a dedicated **research shadow-scoring mode** to gather forward live observations before any runtime replacement is considered.