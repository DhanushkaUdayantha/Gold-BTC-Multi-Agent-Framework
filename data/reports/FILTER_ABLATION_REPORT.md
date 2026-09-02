# Filter Ablation Report

**Generated:** 2026-09-01T16:06:33.403852+00:00
**Filters Tested:** 12
**Best Filter:** HIGH_CONFLUENCE  |  **Worst Filter:** HIGH_PROBABILITY

## Summary
- ADDS_VALUE: HIGH_CONFLUENCE
- MARGINAL: VWAP_ALIGNMENT, SR_ALIGNMENT, TRENDING_REGIME, LONDON_NY_SESSION
- NO_VALUE: MTF_ALIGNMENT, EMA_ALIGNMENT, MOMENTUM, SMC, MTF_PARTIAL
- HURTS: None
- Recommended combination: HIGH_CONFLUENCE

## Per-Filter Results
| Filter | Base Exp | Filtered Exp | Delta | OOS Delta | WR Ret% | LR Red% | BCR | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH_CONFLUENCE | +0.108 | +0.243 | +0.135 | +0.186 | 10% | 92% | 0.86 | ADDS_VALUE |
| VWAP_ALIGNMENT | +0.108 | +0.119 | +0.011 | +0.010 | 87% | 14% | 0.94 | MARGINAL |
| MTF_ALIGNMENT | +0.108 | +0.116 | +0.007 | +0.006 | 90% | 11% | 0.93 | NO_VALUE |
| EMA_ALIGNMENT | +0.108 | +0.115 | +0.007 | -0.002 | 88% | 12% | 0.91 | NO_VALUE |
| MOMENTUM | +0.108 | +0.115 | +0.007 | +0.015 | 93% | 8% | 0.97 | NO_VALUE |
| SMC | +0.108 | +0.113 | +0.005 | -0.002 | 95% | 6% | 0.97 | NO_VALUE |
| MTF_PARTIAL | +0.108 | +0.106 | -0.002 | +0.011 | 95% | 5% | 0.79 | NO_VALUE |
| LONDON_NY_SESSION | +0.108 | +0.096 | -0.012 | -0.018 | 69% | 30% | 0.80 | MARGINAL |
| TRENDING_REGIME | +0.108 | +0.094 | -0.014 | -0.024 | 32% | 68% | 0.83 | MARGINAL |
| SR_ALIGNMENT | +0.108 | +0.063 | -0.045 | -0.116 | 30% | 67% | 0.81 | MARGINAL |
| HIGH_PROBABILITY | +0.108 | +0.000 | -0.108 | -0.150 | 0% | 100% | 0.84 | INSUFFICIENT_DATA |
| HIGH_CONFIRMATION | +0.108 | +0.000 | -0.108 | -0.150 | 0% | 100% | 0.84 | INSUFFICIENT_DATA |