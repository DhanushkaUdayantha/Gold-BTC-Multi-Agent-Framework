# Market Regime & Trading Session Robustness Report

---

## 1. Market Regime Analysis

| Market Regime | Trades (Base → Shadow) | Base Exp | Shadow Exp | Delta Exp | Profit Factor | Max DD | Classification |
|:---|---:|---:|---:|---:|---:|---:|:---:|
| LOW_VOLATILITY | 1474 → 796 | +0.086R | **+0.259R** | +0.174R | 1.52 | 12.0R | STABLE |
| TRENDING | 919 → 106 | +0.053R | **+0.061R** | +0.009R | 1.11 | 30.0R | INSUFFICIENT_SAMPLE |
| RANGING | 39 → 4 | +0.026R | **-0.375R** | -0.401R | 0.50 | 2.0R | UNSTABLE |
| HIGH_VOLATILITY | 6 → 0 | -0.583R | **+0.000R** | +0.583R | 1.00 | 0.0R | INSUFFICIENT_SAMPLE |

---

## 2. Trading Session Analysis

| Session | Trades (Base → Shadow) | Base Exp | Shadow Exp | Delta Exp | Profit Factor | Max DD |
|:---|---:|---:|---:|---:|---:|---:|
| LONDON | 449 → 192 | +0.091R | **+0.107R** | +0.015R | 1.19 | 10.0R |
| NEW_YORK | 519 → 171 | -0.031R | **+0.082R** | +0.113R | 1.14 | 12.5R |
| ASIA | 783 → 269 | +0.038R | **+0.310R** | +0.273R | 1.65 | 20.0R |
| OVERLAP | 687 → 274 | +0.172R | **+0.341R** | +0.169R | 1.74 | 10.0R |
