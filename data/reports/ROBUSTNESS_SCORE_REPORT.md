# Robustness Score Report

**Generated:** 2026-09-01T16:06:34.016956+00:00
**Strategy:** Phase3_Research
**Score:** 56/100  —  Grade: ⚠️ C

## Summary
Total: 56/100 (Grade C). Strong: [wf_stability, regime_stability, session_stability, stress_robustness]. Weak: [profit_factor, drawdown_quality, asset_stability]. Overfitting risk: HIGH (5pt penalty).

## Dimension Scores
| Dimension | Max | Earned | % | Status | Detail |
| --- | --- | --- | --- | --- | --- |
| expectancy_quality | 15 | 7 | 47% | 🟡 ADEQUATE | Expectancy +0.1081R ≥ 0.05R |
| oos_stability | 15 | 10 | 67% | 🟡 ADEQUATE | OOS expectancy +0.1220R ≥ 0.05R |
| wf_stability | 10 | 10 | 100% | ✅ STRONG | WF: 100% positive, median +0.1247R |
| profit_factor | 10 | 4 | 40% | ⚠️ WEAK | PF 1.19 ≥ 1.1 |
| drawdown_quality | 10 | 3 | 30% | ⚠️ WEAK | Max DD 21.5R ≤ 35R |
| calibration | 10 | 6 | 60% | 🟡 ADEQUATE | Brier=0.2472, ECE=0.0226 |
| regime_stability | 8 | 8 | 100% | ✅ STRONG | 75% regimes positive |
| asset_stability | 8 | 3 | 38% | ⚠️ WEAK | Asset DD ratio 0.61 — one asset dominates drawdown |
| session_stability | 5 | 5 | 100% | ✅ STRONG | 75% sessions positive |
| stress_robustness | 5 | 5 | 100% | ✅ STRONG | Passes slippage and execution stress tests |
| statistical_evidence | 4 | 0 | 0% | ➖ UNAVAILABLE | p-value not computed or sample too small |

## Strong Areas
- wf_stability
- regime_stability
- session_stability
- stress_robustness

## Weak Areas
- profit_factor
- drawdown_quality
- asset_stability