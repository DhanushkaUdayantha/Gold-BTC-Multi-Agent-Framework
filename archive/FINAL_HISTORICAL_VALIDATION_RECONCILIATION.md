# Final Historical Validation & Performance Reconciliation

**Reconciliation Date**: September 2, 2026  
**Source of Truth**: `data/historical/historical_market_data.db` (2,438 total point-in-time signals)  
**Integrity Status**: Deterministic, Fully Reconciled & Frozen

---

## 1. Authoritative Summary Table

| Asset | Period | N | Wins | Losses | Win Rate | Avg Win | Avg Loss | EV (R) | Profit Factor | Total R | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **BTC** | **Train (60%)** | 344 | 150 | 194 | 43.60% | +1.50R | -1.00R | **+0.0901R** | 1.16 | +31.0R | 45.0R |
| **BTC** | **OOS (20%)** | 130 | 57 | 73 | 43.85% | +1.50R | -1.00R | **+0.0962R** | 1.17 | +12.5R | 12.5R |
| **BTC** | **Holdout (20%)** | 138 | 61 | 77 | 44.20% | +1.50R | -1.00R | **+0.1051R** | 1.19 | +14.5R | 15.0R |
| **BTC** | **Combined (Total)** | **612** | **268** | **344** | **43.79%** | **+1.50R** | **-1.00R** | **+0.0948R** | **1.17** | **+58.0R** | **45.0R** |
| **XAU** | **Train (60%)** | 238 | 99 | 139 | 41.60% | +1.50R | -1.00R | **+0.0399R** | 1.07 | +9.5R | 21.5R |
| **XAU** | **OOS (20%)** | 85 | 50 | 35 | 58.82% | +1.50R | -1.00R | **+0.4706R** | 2.14 | +40.0R | 4.0R |
| **XAU** | **Holdout (20%)** | 80 | 44 | 36 | 55.00% | +1.50R | -1.00R | **+0.3750R** | 1.83 | +30.0R | 6.0R |
| **XAU** | **Combined (Total)** | **403** | **193** | **210** | **47.89%** | **+1.50R** | **-1.00R** | **+0.1973R** | **1.38** | **+79.5R** | **21.5R** |

---

## 2. Mandatory Final Verdict on XAU +0.197R

```text
XAU +0.197R:
VALID (EXACT COMBINED SAMPLE EXPECTANCY)
```

### Forensic Proof:
The value `+0.197R` is the **exact, unrounded sample-weighted combined expectancy** across all 403 filtered XAU trade signals:

$$\text{Combined Total R} = \text{Train } (+9.5\text{R}) + \text{OOS } (+40.0\text{R}) + \text{Holdout } (+30.0\text{R}) = \mathbf{+79.5\text{R}}$$

$$\text{Combined EV} = \frac{+79.5\text{R}}{403} = \mathbf{+0.197270\text{R}} \approx \mathbf{+0.197\text{R}}$$

There is zero mathematical discrepancy. `+0.197R` is simply the overall sample average of the three sequential partitions ($N=238 \times 0.040\text{R} + N=85 \times 0.471\text{R} + N=80 \times 0.375\text{R}$).

---

## 3. Drawdown Discrepancy Reconciliation

### BTC Drawdown (`20R` vs `45R`):
* **Baseline (Unfiltered 1,519 signals)**: Peak cumulative drawdown = **75.0R**.
* **Filtered Combined (612 signals)**: True cumulative peak drawdown = **45.0R** (occurred early during the Train period).
* **Partition Drawdowns**: Train DD = **45.0R**, OOS DD = **12.5R**, Holdout DD = **15.0R**.
* **Root Cause of Confusion**: An earlier informal summary cited the OOS/Holdout sub-period drawdowns (~12.5–15.0R) or a partial run as "~20R". The authoritative full-sample cumulative peak drawdown is **45.0R**, representing a **30.0R reduction** from the 75.0R baseline.

### XAU Drawdown (`13.5R` vs `21.5R`):
* **Baseline (Unfiltered 919 signals)**: Peak cumulative drawdown = **13.5R**.
* **Filtered Combined (403 signals)**: True cumulative peak drawdown = **21.5R** (occurred in the initial Train partition).
* **Partition Drawdowns**: Train DD = **21.5R**, OOS DD = **4.0R**, Holdout DD = **6.0R**.
* **Root Cause of Confusion**: `13.5R` was the unfiltered baseline's max drawdown across all 919 signals. When the filter isolated the 403 highest-confluence setups, early clustering in Train yielded a 21.5R peak drawdown before accelerating sharply in OOS (+40.0R) and Holdout (+30.0R) to reach **+79.5R total return**.

---

## 4. Signal Filter Definitions Confirmed

Both filters were verified directly against `src/services/decision_engine.py` (Step 10g.1):

1. **Bitcoin (BTC)**:
   ```text
   Confluence Score >= 58
   AND MTF Alignment == BULLISH (for BUY) / BEARISH (for SELL)
   AND NOT (direction == BUY AND session == ASIA AND unconfirmed)
   ```
2. **Gold (XAU)**:
   ```text
   Confluence Score >= 58
   AND MTF Alignment == BULLISH (for BUY) / BEARISH (for SELL)
   AND VWAP Alignment == BULLISH (for BUY) / BEARISH (for SELL)
   ```

---

## 5. Underlying Database Inventory

From `data/historical/historical_market_data.db`:
* **Total Signals**: Exactly **2,438**
  * `BTC/USD`: **1,519**
  * `XAU/USD`: **919**
* **Duplicate Status**: Zero duplicate timestamps within identical run IDs.
* **Run ID Coverage**: 15 distinct backtest runs (12 BTC runs, 3 XAU runs) encompassing multi-year closed 15m/1h candle histories.

---

## 6. Historical Baseline Status

```text
STATUS: FROZEN & AUTHORITATIVE
```
The historical empirical baseline and quality gates are completely reconciled, mathematically validated, and locked. No further modifications or re-runs are needed.
