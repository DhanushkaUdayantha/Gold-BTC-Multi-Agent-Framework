# BTC/USD — Independent Robustness Report

**Generated:** 2026-09-01T16:06:33.248399+00:00
**Classification:** PROMISING  |  **Score:** 72/100

## Core Metrics
| Metric | Value |
| --- | --- |
| Total Signals | 1143 |
| Total Trades | 1143 |
| Win Rate | 44.1% [41.2–47.0%] |
| Expectancy | +0.1024R [+0.030–+0.174] |
| Profit Factor | 1.18 |
| Max Drawdown | 22.00R |
| Total R | +117.00R |

## Chronological Splits
| Split | Trades | WR% | Exp R |
| --- | --- | --- | --- |
| Train (60%) | 685 | 43.1% | +0.0766 |
| Val (20%) | 229 | 45.0% | +0.1245 |
| OOS (20%) | 229 | 46.3% | +0.1572 |
| Holdout (15%) | 172 | 48.3% | +0.2064 |

## Walk-Forward
- Positive windows: 4/4
- Median OOS expectancy: +42.7500R
- Worst OOS expectancy: +40.8000R

## Regime Breakdown
| Regime | Trades | WR% | Exp R | PF | DD |
| --- | --- | --- | --- | --- | --- |
| HIGH_VOLATILITY | 3 | 0.0% | -1.0000 | 0.00 | 3.00R |
| LOW_VOLATILITY | 511 | 45.0% | +0.1252 | 1.23 | 16.00R |
| RANGING | 34 | 41.2% | +0.0294 | 1.05 | 8.50R |
| TRENDING | 595 | 43.7% | +0.0924 | 1.16 | 29.00R |

## Session Breakdown
| Session | Trades | WR% | Exp R | PF |
| --- | --- | --- | --- | --- |
| ASIA | 349 | 43.0% | +0.0745 | 1.13 |
| LONDON | 202 | 47.5% | +0.1881 | 1.36 |
| NEW_YORK | 274 | 44.2% | +0.1040 | 1.19 |
| OVERLAP | 318 | 43.1% | +0.0770 | 1.14 |

## Findings
- BTC/USD: 1143 trades, WR=44.1%, Exp=+0.1024R, PF=1.18, DD=22.0R
- OOS (229 trades): WR=46.3%, Exp=+0.1572R
- Walk-forward: 4/4 positive folds, median exp=+42.7500R
- Best regime: LOW_VOLATILITY (exp=+0.1252R)
- Worst regime: HIGH_VOLATILITY (exp=-1.0000R)