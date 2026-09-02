# Drawdown Root-Cause Report

**Generated:** 2026-09-01T17:59:18.493594+00:00

**Total Trades:** 2049  |  **Total R:** +221.54  |  **Max DD:** 21.46R  |  **Expectancy:** +0.1081R

## Key Findings
- Largest per-asset DD: BTC/USD (22.0R, 102% of total)
- Worst regime for DD: TRENDING (26.0R DD, 43.8% WR)
- Worst session for DD: NEW_YORK (24.5R DD)
- Worst direction for DD: BUY (23.5R DD)
- Losses appear INDEPENDENT (lag1=0.036). DD is likely inherent to the strategy's win rate distribution.
- Largest single DD episode: 21.5R (247 bars, 2024-07-27 → 2024-10-27)

## Largest DD Episode
- **Size:** 21.46R
- **Period:** 2024-07-27 → 2024-10-27
- **Duration:** 247 bars
- **Assets:** XAU/USD, BTC/USD
- **Regimes:** TRENDING, LOW_VOLATILITY, RANGING

## By Asset
| Slice | Trades | WR% | Exp R | PF | Max DD | DD% |
|---|---|---|---|---|---|---|
| BTC/USD | 1143 | 44.1% | +0.102 | 1.18 | 22.00R | 102% |
| XAU/USD | 906 | 44.6% | +0.115 | 1.21 | 13.50R | 63% |

## By Direction
| Slice | Trades | WR% | Exp R | PF | Max DD | DD% |
|---|---|---|---|---|---|---|
| BUY | 1196 | 42.6% | +0.066 | 1.12 | 23.50R | 110% |
| SELL | 853 | 46.7% | +0.167 | 1.31 | 15.00R | 70% |

## By Regime
| Slice | Trades | WR% | Exp R | PF | Max DD | DD% |
|---|---|---|---|---|---|---|
| TRENDING | 658 | 43.8% | +0.094 | 1.17 | 26.00R | 121% |
| LOW_VOLATILITY | 1347 | 44.8% | +0.120 | 1.22 | 15.00R | 70% |
| RANGING | 38 | 42.1% | +0.053 | 1.09 | 8.00R | 37% |
| HIGH_VOLATILITY | 6 | 16.7% | -0.583 | 0.30 | 4.00R | 19% |

## By Session
| Slice | Trades | WR% | Exp R | PF | Max DD | DD% |
|---|---|---|---|---|---|---|
| NEW_YORK | 432 | 39.1% | -0.021 | 0.97 | 24.46R | 114% |
| ASIA | 623 | 45.4% | +0.136 | 1.25 | 18.00R | 84% |
| LONDON | 389 | 42.4% | +0.060 | 1.10 | 15.00R | 70% |
| OVERLAP | 605 | 48.1% | +0.203 | 1.39 | 12.50R | 58% |

## Loss Clustering
- **Lag-1 Autocorrelation:** 0.036
- **Clustered:** False
- **Max Consecutive Losses:** 9
- **Interpretation:** Losses appear INDEPENDENT (lag1=0.036). Consistent with random sampling from a distribution.

## Recommendations