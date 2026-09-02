# Statistical Validation & Confidence Report

**Sample Sizes:** Base = 2,438 trades | Hypothetical Gated = 906 trades  
**Base Expectancy (95% Bootstrap CI):** **+0.071R** [+0.022R, +0.120R]  
**Hypothetical Gated Expectancy (95% Bootstrap CI):** **+0.233R** [+0.151R, +0.314R]  
**Expectancy Delta (Shadow - Base 95% CI):** **+0.163R** [+0.068R, +0.257R]  
**Standardized Effect Size (Cohen's d):** **d = 0.131 (NEGLIGIBLE)**  
**Non-parametric Permutation p-value:** **p = 0.0008** (Statistically Significant at α=0.05)  

---

## 1. Metric Summary Table

| Metric | Base Engine | Hypothetical Gated | Delta / Improvement | 95% Confidence Interval |
|---|---:|---:|---:|:---:|
| **Win Rate** | 42.8% | **49.3%** | +6.5% | [46.1%, 52.6%] (Wilson) |
| **Expectancy** | +0.071R | **+0.233R** | **+0.163R** | [+0.068R, +0.257R] (Bootstrap) |
| **Permutation p** | — | — | **p = 0.0008** | 5,000 resamples (p < 0.05: YES) |
| **Effect Size (d)** | — | — | **0.131** | NEGLIGIBLE magnitude separation |

---

## 2. Multiple Comparisons & Selection Bias Assessment

> [!WARNING]
> MULTIPLE COMPARISONS RISK NOTICE: Multiple policies, thresholds, regimes, and ablation combinations were tested in this research phase. While the primary validated strategies BTC-SELL-P40-REGIME_LOW_VOL and XAU-BUY-P42-VWAP_ALIGNED were pre-specified prior to gating tests, family-wise selection bias is mitigated by out-of-sample chronological walk-forward and untouched holdout verification.
