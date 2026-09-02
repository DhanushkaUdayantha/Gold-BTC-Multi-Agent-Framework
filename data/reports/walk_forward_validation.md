# Walk-Forward Cross-Validation Report

**Windows Evaluated:** 4 Chronological Folds  
**Positive Windows:** **4/4 (100.0%)**  
**Improved Windows vs Base:** **4/4 (100.0%)**  
**Median OOS Expectancy:** **+0.2363R** (vs Base +0.0985R, Delta: +0.1691R)  
**Worst Window Expectancy:** **+0.1574R**  
**Worst Window Drawdown:** **30.00R**  
**Average Winner Retention / Loser Elimination:** **42.4% Win Ret** / **66.7% Lose Red**  
**Stability Classification:** **STABLE (ALL FOLDS POSITIVE)**

---

## 1. Fold-by-Fold Breakdown

| Window | Test Date Range | Trades (Base → Shadow) | Base Exp | Shadow Exp | Delta Exp | PF (Base → Shadow) | Shadow DD | Win Ret % | Loser Red % |
|:---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|
| Window 1 | 2023-01-06 → 2024-05-10 | 609 → 162 (-73.4%) | -0.072R | **+0.157R** | +0.230R | 0.89 → **1.29** | 30.0R | 33.2% | 77.3% |
| Window 2 | 2024-05-10 → 2024-12-29 | 609 → 227 (-62.7%) | +0.093R | **+0.256R** | +0.163R | 1.17 → **1.51** | 8.0R | 42.9% | 67.0% |
| Window 3 | 2024-12-29 → 2025-09-15 | 609 → 252 (-58.6%) | +0.104R | **+0.280R** | +0.175R | 1.19 → **1.57** | 13.0R | 48.0% | 63.8% |
| Window 4 | 2025-09-15 → 2026-08-27 | 611 → 265 (-56.6%) | +0.158R | **+0.217R** | +0.059R | 1.29 → **1.42** | 12.0R | 45.6% | 58.5% |

---

## 2. Walk-Forward Governance Finding

Under 4-fold walk-forward cross-validation, the hypothetical gating policy maintains positive expectancy in **4 out of 4 windows** with zero negative folds. Loser elimination systematically exceeds winner reduction in all rolling regimes.
