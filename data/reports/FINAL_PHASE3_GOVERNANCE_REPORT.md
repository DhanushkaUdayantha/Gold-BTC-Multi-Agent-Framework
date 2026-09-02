# Final Phase 3 Governance Report

**Generated:** 2026-09-01T16:06:34.018857+00:00
**Strategy:** Phase3_Research  |  **Dataset:** v1.0

## Decision: 🔴 REJECT
**Evidence Level:** WEAK  |  **Confidence:** MEDIUM
**Gates Passed:** 7  |  **Gates Failed:** 2

> ⚠️  RESEARCH ADVISORY ONLY.  This decision DOES NOT authorize any production change. PRODUCTION_CANDIDATE requires explicit written human approval before any deployment. Past performance does not guarantee future results.

## Supporting Evidence
- ✅ SAMPLE_SIZE: 2049 trades
- ✅ POSITIVE_EXPECTANCY: +0.1081R
- ✅ OOS_POSITIVE: +0.1220R (n=410)
- ✅ WALK_FORWARD: 100% positive folds
- ✅ PROFIT_FACTOR: PF=1.19
- ✅ HOLDOUT_POSITIVE: +0.1445R (n=308)
- ✅ STRESS_TESTS: Slippage=OK

## Counter Evidence
- ❌ MONTE_CARLO_DD: MC P5 DD = 43.0R — REQUIRED
- ❌ OVERFITTING_RISK: Risk = HIGH — REQUIRED
- ⚠️  AI_CALIBRATION: Brier=0.2472 (MIXED)
- ⚠️  FILTER_BCR: BCR=0.92
- ⚠️  ROBUSTNESS_GRADE: Score=56, Grade=C

## Gate Summary
| Gate | Required | Passed | Detail |
| --- | --- | --- | --- |
| SAMPLE_SIZE | YES | ✅ | 2049 trades |
| POSITIVE_EXPECTANCY | YES | ✅ | +0.1081R |
| OOS_POSITIVE | YES | ✅ | +0.1220R (n=410) |
| WALK_FORWARD | YES | ✅ | 100% positive folds |
| PROFIT_FACTOR | YES | ✅ | PF=1.19 |
| MONTE_CARLO_DD | YES | ❌ | MC P5 DD = 43.0R |
| OVERFITTING_RISK | YES | ❌ | Risk = HIGH |
| HOLDOUT_POSITIVE | no | ✅ | +0.1445R (n=308) |
| AI_CALIBRATION | no | ❌ | Brier=0.2472 (MIXED) |
| STRESS_TESTS | no | ✅ | Slippage=OK |
| FILTER_BCR | no | ❌ | BCR=0.92 |
| ROBUSTNESS_GRADE | no | ❌ | Score=56, Grade=C |

## Conditions to Promote
- Improve robustness score to ≥80 (current: 56)
- Reduce overfitting risk to LOW (current: HIGH)

## Required Actions
- Decision: REJECT — do NOT modify production until explicitly authorized

## Evidence Snapshot
| Metric | Value |
| --- | --- |
| Trades | 2049 |
| Expectancy | +0.1081R [+0.054–+0.161] |
| Profit Factor | 1.19 |
| Max Drawdown | 21.5R |
| OOS Expectancy | +0.1220R (n=410) |
| WF Positive Ratio | 100% |
| MC P5 Drawdown | 43.0R |
| Robustness Score | 56/100 (Grade C) |
| Brier Score | 0.2472 |
| Overfitting Risk | HIGH |
| BTC Robustness | PROMISING |
| XAU Robustness | PROMISING |