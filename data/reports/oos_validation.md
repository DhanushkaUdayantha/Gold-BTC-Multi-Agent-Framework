# Out-of-Sample & Untouched Holdout Validation Report

Strict Chronological Partitioning:
- **60% Development Split:** 1,462 signals (2023-01-06 → 2025-04-10)
- **20% Validation Split:** 488 signals (2025-04-10 → 2025-11-20)
- **20% Untouched Holdout Split:** 488 signals (2025-11-20 → 2026-08-27)

---

## 1. Split Performance Comparison Table

| Partition | Total Signals | Trades (Base → Shadow) | Base Exp | Shadow Exp | Delta Exp | Base PF → Shadow PF | Shadow Max DD | Total R |
|:---|---:|---:|---:|---:|---:|:---:|---:|---:|
| **60% Dev Split** | 1,462 | 1462 → 488 | +0.025R | **+0.209R** | +0.184R | 1.04 → **1.41** | 30.0R | +102.0R |
| **20% Validation** | 488 | 488 → 214 | +0.147R | **+0.344R** | +0.196R | 1.27 → **1.74** | 11.0R | +73.5R |
| **20% Holdout** | 488 | 488 → 204 | +0.132R | **+0.176R** | +0.044R | 1.24 → **1.33** | 12.0R | +36.0R |

---

## 2. Key OOS Finding
The hypothetical gating policy achieves **+0.176R expectancy** and **1.33 Profit Factor** on the completely untouched 20% holdout split.
