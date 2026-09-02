# Signal Research Master Report — Phase 3

**Generated:** 2026-09-01T16:06:34.020819+00:00
**Pipeline Duration:** 3.2s
**Research Records:** 2049
**Policy Version:** `1.0`  |  **Threshold Spec Version:** `1.0`

---

## Summary Table
| Metric | Value |
| --- | --- |
| Total Trades | 2049 |
| Win Rate | 44.3% |
| Expectancy | +0.1081R |
| Profit Factor | 1.19 |
| Max Drawdown | 21.462R |
| OOS Expectancy | 0.122 |
| WF Positive Ratio | 1.0 |
| Brier Score | 0.2472 |
| Overfitting Risk | HIGH |
| Robustness Score | 56.0/100 (Grade C) |
| BTC Classification | PROMISING |
| XAU Classification | PROMISING |

## 🎯 Governance Decision
**REJECT**
Gates passed: 7 / Gates failed: 2

> ⚠️  **MANDATORY SAFETY STATEMENTS:**
> - *"Production decision behavior unchanged. All strategy gating, optimization, and adaptive research remain isolated from the live production decision path."*
> - *"Research results do not authorize production activation."*

## Failure Taxonomy (Top-3)

## Missed Winner Analysis
- Policy A classification: OVERLY_RESTRICTIVE
- Winner retention: 73.5%
- Loser reduction: 29.1%
- Benefit-cost ratio: 0.92
- Top rejecting filters: SR_ALIGNMENT, VWAP_ALIGNMENT, EMA_ALIGNMENT

## Drawdown Summary
- Max drawdown: 21.46R
- Primary source: TRENDING
- Clustered losses: False
- Lag-1 autocorrelation: 0.036

## Output Files
- `CURRENT_PROJECT_AUDIT.json`
- `CURRENT_PROJECT_AUDIT.md`
- `THRESHOLD_REGISTER.json`
- `THRESHOLD_REGISTER.md`
- `LOOKAHEAD_AUDIT_REPORT.json`
- `LOOKAHEAD_AUDIT_REPORT.md`
- `DRAWDOWN_ROOT_CAUSE_REPORT.json`
- `DRAWDOWN_ROOT_CAUSE_REPORT.md`
- `BTC_USD_ROBUSTNESS_REPORT.json`
- `BTC_USD_ROBUSTNESS_REPORT.md`
- `XAU_USD_ROBUSTNESS_REPORT.json`
- `XAU_USD_ROBUSTNESS_REPORT.md`
- `FILTER_ABLATION_REPORT.json`
- `FILTER_ABLATION_REPORT.md`
- `AI_CALIBRATION_REPORT.json`
- `AI_CALIBRATION_REPORT.md`
- `OVERFITTING_REPORT.json`
- `OVERFITTING_REPORT.md`
- `ROBUSTNESS_SCORE_REPORT.json`
- `ROBUSTNESS_SCORE_REPORT.md`
- `FINAL_PHASE3_GOVERNANCE_REPORT.json`
- `FINAL_PHASE3_GOVERNANCE_REPORT.md`