# Calibration Lookahead Bias Audit Report

**Generated:** `2026-09-02T22:11:15.298084+00:00`  
**Engine Version:** `1.0.0-calibration-phase`  
**Audit Verdict:** `CLEAN — ZERO LOOKAHEAD VIOLATIONS (100% TEMPORAL ISOLATION)`

---

## 1. Audit Methodology & Invariants

This audit verifies strict point-in-time temporal isolation across the 3-way chronological split (60% Training, 20% Validation, 20% Untouched Holdout):
1. **Zero Future Calibration Data**: Calibration models fitted on Training data ($[0 : N_{train}]$) never observe validation or holdout data during fitting.
2. **Zero Future Outcomes**: No trade outcome occurring after signal timestamp $T$ was accessible to strength calculation or calibration.
3. **Zero Future Signals**: Prediction sequences adhere strictly to chronological order.
4. **Untouched Holdout Invariant**: The latest 20% chronologically was evaluated exactly ONCE without any parameter tuning or threshold optimization.

---

## 2. Temporal Partitioning Summary

| Asset | Total Signals | Train (60%) | Val (20%) | Holdout (20%) | Train End Timestamp | Val Period | Holdout Period | Violations | Status |
|---|---:|---:|---:|---:|---|---|---|---:|---|
| **BTC/USD** | 1,519 | 911 | 304 | 304 | `2025-01-28T10:00:00+00:00` | `2025-01-28T20:45:00+00:00` to `2025-10-06T09:30:00+00:00` | `2025-10-09T21:30:00+00:00` to `2026-06-29T14:15:00+00:00` | 0 | **PASSED** |
| **XAU/USD** | 919 | 551 | 184 | 184 | `2025-07-08T23:30:00+00:00` | `2025-07-09T04:15:00+00:00` to `2025-12-16T12:45:00+00:00` | `2025-12-16T13:45:00+00:00` to `2026-08-27T17:15:00+00:00` | 0 | **PASSED** |

---

## 3. Lookahead Assertions Table

| Assertion Check | BTC/USD Result | XAU/USD Result | Invariant Condition |
|---|---|---|---|
| `future_calibration_data_used == false` | **PASSED (True)** | **PASSED (True)** | Training strictly precedes Validation & Holdout |
| `future_outcome_used == false` | **PASSED (True)** | **PASSED (True)** | Only completed trades with $T_{outcome} \le T$ used |
| `future_signal_used == false` | **PASSED (True)** | **PASSED (True)** | Sequential chronological indexing strictly preserved |
| `untouched_holdout_verified == true` | **PASSED (True)** | **PASSED (True)** | Final 20% untouched during fitting and threshold tuning |

---

## 4. Audit Notes & Sign-off

- **BTC/USD**: Zero lookahead bias detected across train, validation, and holdout splits.
- **XAU/USD**: Zero lookahead bias detected across train, validation, and holdout splits.
- **Conclusion**: The calibration datasets and validation protocols are 100% free of lookahead bias.
