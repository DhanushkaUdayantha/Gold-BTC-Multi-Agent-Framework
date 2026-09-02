# Feature Contribution Analysis Report — Phase 4

**Generated:** 2026-09-01T17:59:18.379072+00:00
**Total Features Evaluated:** 13

## Feature Contribution Table
| Feature | Sample N | Win Rate | Expectancy | PF | Max DD | OOS Exp | Holdout Exp | Win Ret | Loser Red | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HTF_ALIGNMENT` | 1840 | 44.6% | +0.1155R | 1.21 | 23.5R | +0.1413R | +0.1504R | 90.4% | 10.7% | `NEUTRAL` |
| `EMA_ALIGNMENT` | 1801 | 44.6% | +0.1150R | 1.21 | 25.0R | +0.1288R | +0.1439R | 88.4% | 12.5% | `NEUTRAL` |
| `VWAP_ALIGNMENT` | 1775 | 44.7% | +0.1186R | 1.21 | 16.0R | +0.1408R | +0.1610R | 87.4% | 14.0% | `NEUTRAL` |
| `MOMENTUM_ALIGNMENT` | 1902 | 44.6% | +0.1149R | 1.21 | 17.5R | +0.1352R | +0.1364R | 93.4% | 7.6% | `NEUTRAL` |
| `SR_ALIGNMENT` | 649 | 42.5% | +0.0632R | 1.11 | 13.5R | -0.0385R | -0.0816R | 30.4% | 67.3% | `NEGATIVE` |
| `SMC_ALIGNMENT` | 1936 | 44.5% | +0.1134R | 1.20 | 17.5R | +0.1211R | +0.1426R | 94.9% | 5.9% | `NEUTRAL` |
| `HIGH_CONFIDENCE` | 0 | 0.0% | +0.0000R | 0.00 | 0.0R | +0.0000R | +0.0000R | 0.0% | 0.0% | `INSUFFICIENT DATA` |
| `POSITIVE_PROBABILITY (>50%)` | 0 | 0.0% | +0.0000R | 0.00 | 0.0R | +0.0000R | +0.0000R | 0.0% | 0.0% | `INSUFFICIENT DATA` |
| `HIGH_CONFLUENCE (>=65)` | 181 | 49.7% | +0.2431R | 1.48 | 8.5R | +0.2162R | +0.2500R | 9.9% | 92.0% | `STRONG POSITIVE` |
| `CONFIRMATION_COUNT >= 3` | 1991 | 44.2% | +0.1052R | 1.19 | 21.5R | +0.1153R | +0.1455R | 96.9% | 2.6% | `NEUTRAL` |
| `TRENDING_REGIME` | 658 | 43.8% | +0.0942R | 1.17 | 26.0R | +0.1174R | +0.0859R | 31.7% | 67.6% | `NEUTRAL` |
| `LONDON_SESSION` | 389 | 42.4% | +0.0604R | 1.10 | 15.0R | -0.1026R | -0.0254R | 18.2% | 80.4% | `NEGATIVE` |
| `NEW_YORK_SESSION` | 432 | 39.1% | -0.0207R | 0.97 | 24.5R | +0.0632R | +0.0385R | 18.6% | 77.0% | `STRONGLY NEGATIVE` |

## Detailed Feature Insights

### `HTF_ALIGNMENT` [NEUTRAL]
- Expectancy delta: +0.0074R (Matched: +0.1155R vs Base: +0.1081R). OOS: +0.1413R, Holdout: +0.1504R, Winner Ret: 90.4%, Loser Red: 10.7%.

### `EMA_ALIGNMENT` [NEUTRAL]
- Expectancy delta: +0.0069R (Matched: +0.1150R vs Base: +0.1081R). OOS: +0.1288R, Holdout: +0.1439R, Winner Ret: 88.4%, Loser Red: 12.5%.

### `VWAP_ALIGNMENT` [NEUTRAL]
- Expectancy delta: +0.0105R (Matched: +0.1186R vs Base: +0.1081R). OOS: +0.1408R, Holdout: +0.1610R, Winner Ret: 87.4%, Loser Red: 14.0%.

### `MOMENTUM_ALIGNMENT` [NEUTRAL]
- Expectancy delta: +0.0068R (Matched: +0.1149R vs Base: +0.1081R). OOS: +0.1352R, Holdout: +0.1364R, Winner Ret: 93.4%, Loser Red: 7.6%.

### `SR_ALIGNMENT` [NEGATIVE]
- Expectancy delta: -0.0449R (Matched: +0.0632R vs Base: +0.1081R). OOS: -0.0385R, Holdout: -0.0816R, Winner Ret: 30.4%, Loser Red: 67.3%.

### `SMC_ALIGNMENT` [NEUTRAL]
- Expectancy delta: +0.0053R (Matched: +0.1134R vs Base: +0.1081R). OOS: +0.1211R, Holdout: +0.1426R, Winner Ret: 94.9%, Loser Red: 5.9%.

### `HIGH_CONFIDENCE` [INSUFFICIENT DATA]
- Sample size 0 < 30 minimum threshold.

### `POSITIVE_PROBABILITY (>50%)` [INSUFFICIENT DATA]
- Sample size 0 < 30 minimum threshold.

### `HIGH_CONFLUENCE (>=65)` [STRONG POSITIVE]
- Expectancy delta: +0.1350R (Matched: +0.2431R vs Base: +0.1081R). OOS: +0.2162R, Holdout: +0.2500R, Winner Ret: 9.9%, Loser Red: 92.0%.

### `CONFIRMATION_COUNT >= 3` [NEUTRAL]
- Expectancy delta: -0.0029R (Matched: +0.1052R vs Base: +0.1081R). OOS: +0.1153R, Holdout: +0.1455R, Winner Ret: 96.9%, Loser Red: 2.6%.

### `TRENDING_REGIME` [NEUTRAL]
- Expectancy delta: -0.0139R (Matched: +0.0942R vs Base: +0.1081R). OOS: +0.1174R, Holdout: +0.0859R, Winner Ret: 31.7%, Loser Red: 67.6%.

### `LONDON_SESSION` [NEGATIVE]
- Expectancy delta: -0.0477R (Matched: +0.0604R vs Base: +0.1081R). OOS: -0.1026R, Holdout: -0.0254R, Winner Ret: 18.2%, Loser Red: 80.4%.

### `NEW_YORK_SESSION` [STRONGLY NEGATIVE]
- Expectancy delta: -0.1288R (Matched: -0.0207R vs Base: +0.1081R). OOS: +0.0632R, Holdout: +0.0385R, Winner Ret: 18.6%, Loser Red: 77.0%.