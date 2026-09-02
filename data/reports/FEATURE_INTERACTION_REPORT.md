# Feature Interaction Analysis Report — Phase 4

**Generated:** 2026-09-01T17:59:18.401684+00:00
**Total Interactions Evaluated:** 8

## Feature Interaction Matrix
| Interaction | Sample N | Win Rate | Expectancy | PF | Max DD | OOS Exp | Holdout Exp | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `PROB_HIGH + TRENDING_REGIME` | 0 | 0.0% | +0.0000R | 0.00 | 0.0R | +0.0000R | +0.0000R | `NO VALUE` |
| `PROB_HIGH + HTF_ALIGNED` | 0 | 0.0% | +0.0000R | 0.00 | 0.0R | +0.0000R | +0.0000R | `NO VALUE` |
| `HTF_ALIGNED + SR_ALIGNED` | 555 | 43.4% | +0.0856R | 1.15 | 12.5R | +0.0360R | +0.0119R | `NO VALUE` |
| `VWAP_ALIGNED + EMA_ALIGNED` | 1676 | 44.6% | +0.1146R | 1.21 | 20.5R | +0.1384R | +0.1607R | `NO VALUE` |
| `TRENDING_REGIME + HTF_ALIGNED` | 591 | 44.5% | +0.1125R | 1.20 | 22.5R | +0.1134R | +0.1236R | `NO VALUE` |
| `HIGH_CONFLUENCE + MOMENTUM_ALIGNED` | 173 | 50.9% | +0.2717R | 1.55 | 6.0R | +0.2143R | +0.3462R | `ROBUST INTERACTION` |
| `LONDON_SESSION + TRENDING_REGIME` | 80 | 51.2% | +0.2812R | 1.58 | 5.0R | +0.2500R | +0.4583R | `ROBUST INTERACTION` |
| `HIGH_CONFIDENCE + HIGH_CONFLUENCE` | 0 | 0.0% | +0.0000R | 0.00 | 0.0R | +0.0000R | +0.0000R | `NO VALUE` |

## Detailed Interaction Insights

### `PROB_HIGH + TRENDING_REGIME` [NO VALUE]
- Sample size 0 < 25 minimum threshold.

### `PROB_HIGH + HTF_ALIGNED` [NO VALUE]
- Sample size 0 < 25 minimum threshold.

### `HTF_ALIGNED + SR_ALIGNED` [NO VALUE]
- Combined Exp: +0.0856R (Delta: -0.0225R vs Base). WR: 43.4%, PF: 1.15, OOS: +0.0360R, Holdout: +0.0119R.

### `VWAP_ALIGNED + EMA_ALIGNED` [NO VALUE]
- Combined Exp: +0.1146R (Delta: +0.0065R vs Base). WR: 44.6%, PF: 1.21, OOS: +0.1384R, Holdout: +0.1607R.

### `TRENDING_REGIME + HTF_ALIGNED` [NO VALUE]
- Combined Exp: +0.1125R (Delta: +0.0044R vs Base). WR: 44.5%, PF: 1.20, OOS: +0.1134R, Holdout: +0.1236R.

### `HIGH_CONFLUENCE + MOMENTUM_ALIGNED` [ROBUST INTERACTION]
- Combined Exp: +0.2717R (Delta: +0.1636R vs Base). WR: 50.9%, PF: 1.55, OOS: +0.2143R, Holdout: +0.3462R.

### `LONDON_SESSION + TRENDING_REGIME` [ROBUST INTERACTION]
- Combined Exp: +0.2812R (Delta: +0.1731R vs Base). WR: 51.2%, PF: 1.58, OOS: +0.2500R, Holdout: +0.4583R.

### `HIGH_CONFIDENCE + HIGH_CONFLUENCE` [NO VALUE]
- Sample size 0 < 25 minimum threshold.