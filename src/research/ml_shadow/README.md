# Machine Learning Shadow Validation Layer

This module provides a non-destructive, downstream observer layer that validates machine learning prediction performance on forward live market data without modifying any production decision engine rules, thresholds, or execution.

## Architecture

```text
                    LIVE MARKET DATA
                           │
                           ▼
              ┌─────────────────────────┐
              │ PRODUCTION PIPELINE     │
              │ (100% Unchanged)        │
              │                         │
              │ • Technical Engine      │
              │ • Confluence Engine     │
              │ • Quality Gates         │
              │ • Decision Engine       │
              └────────────┬────────────┘
                           │
                      BUY/SELL/WAIT
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
          PRODUCTION UI          ML SHADOW (Observer Only)
          (Unchanged)                 │
                                      ▼
                              ML Probability Snapshot (T0)
                                      │
                                      ▼
                              Forward Market Candlesticks
                                      │
                                      ▼
                              Outcome Resolution (WIN/LOSS/EXPIRED)
                                      │
                                      ▼
                              Validation Metrics (Brier, WR, EV)
```

## Guarantees

1. **Failure Safety**: If ML model loading or prediction fails, production continues without interruption.
2. **Zero Production Mutation**: Production decisions, entries, stop-losses, take-profits, and scores are never altered.
3. **Snapshot Immutability**: The $T_0$ feature vector is never updated or overwritten by post-trade data.
4. **Asset Separation**: BTC and XAU use strictly separate model artifacts and feature pipelines.
5. **Reversibility**: This layer can be disabled or deleted without any effect on the trading platform.
