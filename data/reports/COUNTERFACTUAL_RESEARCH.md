# Counterfactual Research & Parameter Exploration Report — Phase 4

**Generated:** 2026-09-02T19:26:33.615161+00:00
**Trades Analyzed:** 60  |  **Scenarios Tested:** 4

## Summary
Counterfactual Exploration completed across 4 scenarios. Evaluated stop distances, profit targets, and confirmation variations.

> ⚠️ **DISCLAIMER:**
> *"Counterfactual research is purely exploratory. No production parameters, entry points, stop losses, or take profits are modified."*

## Counterfactual Scenarios Comparison
| Scenario ID | Name | Category | Sample N | Baseline Exp | CF Exp | Exp Delta | Base WR | CF WR | Base PF | CF PF | Base DD | CF DD | Verdict |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `CF_SL_TIGHTER` | Tighter Stop-Loss (0.8x ATR Distance) | SL_DISTANCE | 60 | +0.2500R | +0.4375R | +0.1875R | 50.0% | 50.0% | 1.50 | 1.88 | 1.0R | 1.0R | `PROMISING_HYPOTHESIS` |
| `CF_SL_WIDER` | Wider Stop-Loss (1.3x ATR Breathing Room) | SL_DISTANCE | 60 | +0.2500R | +0.0775R | -0.1725R | 50.0% | 50.0% | 1.50 | 1.16 | 1.0R | 1.0R | `INFERIOR` |
| `CF_TP_EXTENDED` | Extended Take-Profit (1:2.5 RR on High Confluence) | TP_TARGET | 60 | +0.2500R | +0.2500R | +0.0000R | 50.0% | 50.0% | 1.50 | 1.50 | 1.0R | 1.0R | `NEUTRAL` |
| `CF_FILTER_CONFIRMATION` | Minimum 2 Confirmations Filter | FILTER_VARIATION | 30 | +0.2500R | +1.5000R | +1.2500R | 50.0% | 100.0% | 1.50 | 99.00 | 1.0R | 0.0R | `PROMISING_HYPOTHESIS` |

## Detailed Scenario Hypotheses & Insights

### CF_SL_TIGHTER: Tighter Stop-Loss (0.8x ATR Distance) [PROMISING_HYPOTHESIS]
- **Hypothesis:** Tighter SL increases win R-multiples to 1.25x but causes early stops on trades with MAE >= 0.8R.
- **Result & Insight:** Counterfactual Exp: +0.4375R (Delta: +0.1875R vs Base +0.2500R). WR: 50.0% (Base: 50.0%), PF: 1.88 (Base: 1.50), Max DD: 1.0R.

### CF_SL_WIDER: Wider Stop-Loss (1.3x ATR Breathing Room) [INFERIOR]
- **Hypothesis:** Wider SL avoids wick stopouts on trades with MFE >= 1.5R at the cost of slightly lower R-multiples.
- **Result & Insight:** Counterfactual Exp: +0.0775R (Delta: -0.1725R vs Base +0.2500R). WR: 50.0% (Base: 50.0%), PF: 1.16 (Base: 1.50), Max DD: 1.0R.

### CF_TP_EXTENDED: Extended Take-Profit (1:2.5 RR on High Confluence) [NEUTRAL]
- **Hypothesis:** Extends TP target to 2.5R on high confluence setups (>=70) that reach MFE >= 2.5R.
- **Result & Insight:** Counterfactual Exp: +0.2500R (Delta: +0.0000R vs Base +0.2500R). WR: 50.0% (Base: 50.0%), PF: 1.50 (Base: 1.50), Max DD: 1.0R.

### CF_FILTER_CONFIRMATION: Minimum 2 Confirmations Filter [PROMISING_HYPOTHESIS]
- **Hypothesis:** Filters out trades with fewer than 2 directional indicator confirmations.
- **Result & Insight:** Counterfactual Exp: +1.5000R (Delta: +1.2500R vs Base +0.2500R). WR: 100.0% (Base: 50.0%), PF: 99.00 (Base: 1.50), Max DD: 0.0R.