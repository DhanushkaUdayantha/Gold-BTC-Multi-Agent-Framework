# Confirmation Condition Ablation Report

---

## 1. BTC SELL Confirmation Contribution

| Feature Combination | Trades (N) | Win Rate % | Expectancy (R) | Profit Factor | Max Drawdown | Total R |
|:---|---:|---:|---:|---:|---:|---:|
| Probability Only (P>=0.40) | 738 | 47.3% | **+0.182R** | 1.35 | 36.0R | +134.5R |
| Prob + Regime (P>=0.40 + LOW_VOL) | 258 | 58.9% | **+0.473R** | 2.15 | 12.0R | +122.0R |
| Prob + HTF (P>=0.40 + HTF) | 627 | 48.0% | **+0.200R** | 1.39 | 35.0R | +125.5R |
| Prob + S/R (P>=0.40 + SR) | 238 | 49.2% | **+0.229R** | 1.45 | 30.0R | +54.5R |
| Prob + Regime + HTF | 207 | 58.9% | **+0.473R** | 2.15 | 10.0R | +98.0R |
| Full Strategy (Prob + Regime + HTF + SR) | 88 | 64.8% | **+0.619R** | 2.76 | 10.0R | +54.5R |

---

## 2. XAU BUY Confirmation Contribution

| Feature Combination | Trades (N) | Win Rate % | Expectancy (R) | Profit Factor | Max Drawdown | Total R |
|:---|---:|---:|---:|---:|---:|---:|
| Probability Only (P>=0.42) | 597 | 45.6% | **+0.139R** | 1.25 | 16.0R | +83.0R |
| Prob + VWAP (P>=0.42 + VWAP) | 517 | 48.2% | **+0.204R** | 1.39 | 14.0R | +105.5R |
| Prob + EMA (P>=0.42 + EMA) | 548 | 46.7% | **+0.168R** | 1.31 | 16.0R | +92.0R |
| Prob + HTF (P>=0.42 + HTF) | 588 | 45.9% | **+0.148R** | 1.27 | 16.0R | +87.0R |
| Prob + VWAP + EMA | 508 | 48.4% | **+0.211R** | 1.41 | 14.0R | +107.0R |
| Full Strategy (Prob + VWAP + EMA + HTF) | 508 | 48.4% | **+0.211R** | 1.41 | 14.0R | +107.0R |
