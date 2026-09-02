# Institutional Historical Backtesting & Directional Strength Calibration Report

**Generated At:** `2026-09-02T19:54:43.036648+00:00`  
**Engine Version:** `HistoricalStrengthCalibrator-v2.0`  
**Evaluation Scope:** Zero-Lookahead Historical Outcome Replay & Walk-Forward Cross-Validation  
**Target Assets:** `BTC/USD` & `XAU/USD`  

---

## 1. Executive Summary

Historical Strength Backtesting & Calibration completed across BTC/USD (1,519 trades) and XAU/USD (919 trades). BTC OOS Expectancy: +0.14R (PF 1.26) | XAU OOS Expectancy: +0.12R (PF 1.21).

---

## 2. Key Performance Metrics Comparison

| Metric | BTC/USD (Overall) | BTC/USD (Out-of-Sample) | XAU/USD (Overall) | XAU/USD (Out-of-Sample) |
| :--- | :---: | :---: | :---: | :---: |
| **Dataset Range** | `2023-01-06 → 2026-06-29` | Last 30% | `2024-01-08 → 2026-08-27` | Last 30% |
| **Total Evaluated Trades** | **1,519** | 456 | **919** | 276 |
| **Win Rate (%)** | **41.7%** | **45.6%** | **44.7%** | **44.6%** |
| **95% Confidence Interval** | `39.3% – 44.2%` | `41.1% – 50.2%` | `41.5% – 47.9%` | `38.8% – 50.5%` |
| **Expectancy ($R$)** | **+0.04R** | **+0.14R** | **+0.12R** | **+0.12R** |
| **Profit Factor ($PF$)** | **1.07** | **1.26** | **1.21** | **1.21** |
| **Max Drawdown ($R$)** | `75.0R` | `11.5R` | `13.5R` | `13.5R` |
| **Total Realized Return ($R$)** | `+66.0R` | `+64.0R` | `+106.5R` | `+31.5R` |
| **TP1 Hit Rate (%)** | `41.7%` | `45.6%` | `44.6%` | `44.6%` |
| **TP2 Extended Hit Rate (%)** | `15.3%` | `12.9%` | `11.3%` | `13.4%` |
| **SL Hit Rate (%)** | `58.3%` | `54.4%` | `55.3%` | `55.4%` |
| **Avg Duration (Min)** | `182.0 min` | `177.2 min` | `275.2 min` | `217.6 min` |

---

## 3. Calibration by Strength Score Bucket (Reliability Curve)

### BTC/USD Calibration Breakdown
| Strength Bucket | Trade Count ($N$) | Mean Predicted (%) | Observed Win Rate (%) | Expectancy ($R$) | Profit Factor | Calibration Gap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **< 50%** | 0 | 24.5% | **0.0%** | +0.00R | 0.00 | 0.0% |
| **50% – 59%** | 1,084 | 56.4% | **43.1%** | +0.08R | 1.14 | 13.3% |
| **60% – 69%** | 425 | 62.6% | **38.4%** | -0.04R | 0.93 | 24.2% |
| **70% – 79%** | 10 | 71.2% | **40.0%** | +0.00R | 1.00 | 31.2% |
| **80% – 89%** | 0 | 84.5% | **0.0%** | +0.00R | 0.00 | 0.0% |
| **90% – 100%** | 0 | 95.0% | **0.0%** | +0.00R | 0.00 | 0.0% |

* **Brier Score:** `0.2710` (Baseline no-skill: 0.2500)
* **Expected Calibration Error (ECE):** `16.47%`
* **Maximum Calibration Error (MCE):** `31.2%`
* **Calibration Assessment:** `UNRELIABLE`

### XAU/USD Calibration Breakdown
| Strength Bucket | Trade Count ($N$) | Mean Predicted (%) | Observed Win Rate (%) | Expectancy ($R$) | Profit Factor | Calibration Gap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **< 50%** | 0 | 24.5% | **0.0%** | +0.00R | 0.00 | 0.0% |
| **50% – 59%** | 620 | 56.4% | **42.8%** | +0.07R | 1.12 | 13.6% |
| **60% – 69%** | 288 | 62.8% | **47.9%** | +0.20R | 1.38 | 14.9% |
| **70% – 79%** | 11 | 71.7% | **63.6%** | +0.59R | 2.62 | 8.1% |
| **80% – 89%** | 0 | 84.5% | **0.0%** | +0.00R | 0.00 | 0.0% |
| **90% – 100%** | 0 | 95.0% | **0.0%** | +0.00R | 0.00 | 0.0% |

* **Brier Score:** `0.2658`
* **Expected Calibration Error (ECE):** `13.96%`
* **Maximum Calibration Error (MCE):** `14.9%`
* **Calibration Assessment:** `UNRELIABLE`

---

## 4. BUY vs SELL Performance Breakdown

### BTC/USD Directional Comparison
* **BUY Trades:** 771 trades | Win Rate: **35.7%** [CI: 32.4%–39.1%] | Expectancy: **-0.11R** | Profit Factor: **0.83**
* **SELL Trades:** 748 trades | Win Rate: **48.0%** [CI: 44.4%–51.6%] | Expectancy: **+0.20R** | Profit Factor: **1.38**
* **Directional Asymmetry Note:** BUY WR: 35.7% (PF 0.83) vs SELL WR: 48.0% (PF 1.38). SELL performance is superior.

### XAU/USD Directional Comparison
* **BUY Trades:** 599 trades | Win Rate: **45.4%** [CI: 41.5%–49.4%] | Expectancy: **+0.14R** | Profit Factor: **1.25**
* **SELL Trades:** 320 trades | Win Rate: **43.3%** [CI: 37.9%–48.7%] | Expectancy: **+0.08R** | Profit Factor: **1.14**
* **Directional Asymmetry Note:** BUY WR: 45.4% (PF 1.25) vs SELL WR: 43.3% (PF 1.14). BUY performance is superior.

---

## 5. Walk-Forward Cross-Validation (Chronological 4 Folds)

### BTC/USD Walk-Forward Folds
| Fold | In-Sample Period | IS Count | IS Win Rate | Out-of-Sample Period | OOS Count | OOS Win Rate | OOS Expectancy | OOS Profit Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Fold 1 | `2023-01-06 → 2023-02-14` | 303 | 33.0% | `2023-02-14 → 2024-07-20` | 303 | **46.5%** | **+0.16R** | 1.31 |
| Fold 2 | `2023-01-06 → 2024-07-20` | 606 | 39.8% | `2024-07-21 → 2025-01-26` | 303 | **40.9%** | **+0.02R** | 1.04 |
| Fold 3 | `2023-01-06 → 2025-01-26` | 909 | 40.2% | `2025-01-26 → 2025-09-28` | 303 | **40.6%** | **+0.01R** | 1.02 |
| Fold 4 | `2023-01-06 → 2025-09-28` | 1,212 | 40.3% | `2025-09-29 → 2026-06-27` | 303 | **47.5%** | **+0.19R** | 1.36 |

### XAU/USD Walk-Forward Folds
| Fold | In-Sample Period | IS Count | IS Win Rate | Out-of-Sample Period | OOS Count | OOS Win Rate | OOS Expectancy | OOS Profit Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Fold 1 | `2024-01-08 → 2024-07-05` | 183 | 39.3% | `2024-07-15 → 2025-01-06` | 183 | **44.5%** | **+0.12R** | 1.20 |
| Fold 2 | `2024-01-08 → 2025-01-06` | 366 | 41.9% | `2025-01-06 → 2025-07-07` | 183 | **47.5%** | **+0.19R** | 1.36 |
| Fold 3 | `2024-01-08 → 2025-07-07` | 549 | 43.8% | `2025-07-07 → 2025-12-11` | 183 | **48.6%** | **+0.21R** | 1.42 |
| Fold 4 | `2024-01-08 → 2025-12-11` | 732 | 45.0% | `2025-12-15 → 2026-08-27` | 183 | **44.3%** | **+0.11R** | 1.19 |

---

## 6. Regulatory & Production Compliance Notice

> **DISCLAIMER:** This backtesting and calibration report is generated solely for analytical research and statistical verification. It does not execute live orders, connect to trading brokers, or guarantee future market returns. Past empirical performance does not guarantee future results.
