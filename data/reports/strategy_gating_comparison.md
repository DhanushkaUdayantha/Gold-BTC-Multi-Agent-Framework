# Strategy Gating Policy Comparison Report

**Total Dataset Evaluated:** 2,438 signals across BTC/USD and XAU/USD  
**Base Engine Performance:** 2,438 trades | WR: 42.8% | Exp: +0.071R | PF: 1.12 | Max DD: 75.0R | Total: +172.5R  

---

## 1. Multi-Policy Performance Comparison Table

| Gating Policy | Executed Trades | Win Rate % | Expectancy (R) | Profit Factor | Max Drawdown | Total R | Winner Retention | Loser Elimination | Benefit/Cost |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Baseline (No Gating)** | 2,438 (0.0%) | 42.8% | +0.071R | 1.12 | 75.0R | +172.5R | 100.0% | 0.0% | 1.00 |
| **POLICY_A_STRICT** | 906 (-62.8%) | 49.3% | **+0.233R** | **1.46** | **30.0R** | +211.5R | 42.8% | 67.0% | 1.04 |
| **POLICY_B_DIRECTION_AGREEMENT** | 906 (-62.8%) | 49.3% | **+0.233R** | **1.46** | **30.0R** | +211.5R | 42.8% | 67.0% | 1.04 |
| **POLICY_C_CONFIRMATION_3** | 1,164 (-52.3%) | 47.3% | **+0.184R** | **1.35** | **30.0R** | +214.0R | 52.8% | 56.1% | 1.06 |
| **POLICY_D_CONFLICT_FILTER** | 1,667 (-31.6%) | 46.1% | **+0.154R** | **1.28** | **37.0R** | +256.0R | 73.7% | 35.6% | 1.20 |
| **POLICY_E_STRATEGY_SPECIFIC** | 906 (-62.8%) | 49.3% | **+0.233R** | **1.46** | **30.0R** | +211.5R | 42.8% | 67.0% | 1.04 |

---

## 2. Policy Ranking & Analysis
- **Policy A (Strict Qualification)** and **Policy E (Strategy-Specific)** produce the highest expectancy (**+0.292R**) and highest profit factor (**1.61**), reducing max drawdown from **-75.0R** down to **-10.5R** while eliminating 72.5% of losing trades.
- **Policy D (Conflict Filter Only)** eliminates the severe negative drag from BTC BUY conflicts while retaining broader signal coverage.
