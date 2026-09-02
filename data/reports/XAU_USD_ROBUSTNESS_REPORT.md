# XAU/USD — Independent Robustness Report

**Generated:** 2026-09-01T16:06:33.285798+00:00
**Classification:** PROMISING  |  **Score:** 67/100

## Core Metrics
| Metric | Value |
| --- | --- |
| Total Signals | 906 |
| Total Trades | 906 |
| Win Rate | 44.6% [41.4–47.8%] |
| Expectancy | +0.1154R [+0.038–+0.200] |
| Profit Factor | 1.21 |
| Max Drawdown | 13.50R |
| Total R | +104.54R |

## Chronological Splits
| Split | Trades | WR% | Exp R |
| --- | --- | --- | --- |
| Train (60%) | 543 | 43.8% | +0.0968 |
| Val (20%) | 181 | 48.6% | +0.2155 |
| OOS (20%) | 182 | 42.9% | +0.0714 |
| Holdout (15%) | 136 | 43.4% | +0.0846 |

## Walk-Forward
- Positive windows: 4/4
- Median OOS expectancy: +46.1500R
- Worst OOS expectancy: +43.1000R

## Regime Breakdown
| Regime | Trades | WR% | Exp R | PF | DD |
| --- | --- | --- | --- | --- | --- |
| HIGH_VOLATILITY | 3 | 33.3% | -0.1667 | 0.75 | 1.00R |
| LOW_VOLATILITY | 836 | 44.6% | +0.1161 | 1.21 | 16.50R |
| RANGING | 4 | 50.0% | +0.2500 | 1.50 | 1.00R |
| TRENDING | 63 | 44.4% | +0.1111 | 1.20 | 4.00R |

## Session Breakdown
| Session | Trades | WR% | Exp R | PF |
| --- | --- | --- | --- | --- |
| ASIA | 274 | 48.5% | +0.2135 | 1.41 |
| LONDON | 187 | 36.9% | -0.0775 | 0.88 |
| NEW_YORK | 158 | 30.4% | -0.2371 | 0.66 |
| OVERLAP | 287 | 53.7% | +0.3415 | 1.74 |

## Findings
- XAU/USD: 906 trades, WR=44.6%, Exp=+0.1154R, PF=1.21, DD=13.5R
- OOS (182 trades): WR=42.9%, Exp=+0.0714R
- Walk-forward: 4/4 positive folds, median exp=+46.1500R
- Best regime: RANGING (exp=+0.2500R)
- Worst regime: HIGH_VOLATILITY (exp=-0.1667R)