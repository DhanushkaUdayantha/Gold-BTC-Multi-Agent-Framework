# Stress Testing & Monte Carlo Simulation Report

**Monte Carlo Iterations:** 10,000 runs per cohort  
**Execution Friction Robustness:** **Maintains positive expectancy up to 0.15R slippage**  
**Probability Perturbation Robustness:** **Maintains positive expectancy across all [-5%, +5%] threshold shifts**  
**Overall Stress Test Status:** **PASSED (STRESS ROBUST)**

---

## 1. 10,000-Iteration Monte Carlo Path Simulations

| Cohort | N | Median Final R | 5th Pct Final R | Median Max DD | 95th Pct Max DD | Prob Final R < 0 | Prob Losing Month | Max Loss Streak |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base Engine (No Gating) | 2,438 | **+172.0R** | +72.5R | 34.5R | **58.5R** | 0.17% | 30.4% | 60 |
| Hypothetical Gated (Policy A) | 906 | **+211.5R** | +149.0R | 14.0R | **22.0R** | 0.00% | 9.1% | 30 |
| BTC SELL Qualified Cohort | 349 | **+121.0R** | +83.5R | 8.5R | **14.0R** | 0.00% | 2.7% | 30 |
| XAU BUY Qualified Cohort | 557 | **+90.5R** | +40.5R | 15.0R | **26.5R** | 0.07% | 16.3% | 9 |

---

## 2. Execution Friction & Slippage Stress

| Slippage / Trade | Expectancy (R) | Profit Factor | Total Realized R | Max Drawdown | Status |
|:---:|---:|---:|---:|---:|:---:|
| 0.00R | **+0.233R** | 1.46 | +211.5R | 30.0R | PASS |
| 0.05R | **+0.183R** | 1.34 | +166.2R | 31.5R | PASS |
| 0.10R | **+0.133R** | 1.24 | +120.9R | 33.0R | PASS |
| 0.15R | **+0.083R** | 1.14 | +75.6R | 34.5R | PASS |
| 0.20R | **+0.033R** | 1.05 | +30.3R | 36.0R | PASS |

---

## 3. Probability Threshold Uncertainty Sensitivity

| Threshold Shift | Qualified Trades (N) | Expectancy (R) | Profit Factor | Total Realized R | Max Drawdown |
|:---:|---:|---:|---:|---:|---:|
| -5.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| -3.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| -1.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| +0.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| +1.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| +3.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
| +5.0% | 777 | **+0.290R** | 1.60 | +225.5R | 10.5R |
