# Forensic Audit: Analysis of Remaining 4 Pre-Existing Test Failures

**Repository**: `D:/Project/TRADE`  
**Audit Date**: September 11, 2026  
**Status**: **READ-ONLY AUDIT COMPLETE — ZERO TEST EDITS PERFORMED**  
**Pytest Baseline**: 791 Passed, 4 Failed  
**Objective**: Determine the exact root cause, production lineage, and validity of each failure without artificially modifying code or weakening assertions.

---

## 1. Executive Summary & Failure Classification

All 4 test failures were subjected to deep forensic investigation across production source code, git history, governance baselines, and database records.

| Test ID | Test Function | File | Classification | Root Cause |
|:---:|:---|:---|:---:|:---|
| **1** | `test_resolver_candle_evaluation_outcomes` | `tests/test_pipeline_e2e_connections.py:321` | **`STALE TEST`** | Calls deleted private helper `_evaluate_candles_against_signal` from pre-tradability single-stage resolver. |
| **2** | `test_btc_separate_pipeline` | `tests/test_pipeline_e2e_connections.py:435` | **`STALE TEST`** | Same deleted helper call on resolver step. |
| **3** | `test_xau_separate_pipeline` | `tests/test_pipeline_e2e_connections.py:549` | **`STALE TEST`** | Same deleted helper call on resolver step. |
| **4** | `test_xau_observations_confluence_below_threshold` | `tests/test_xau_resolution_forensics.py:258` | **`EXPECTED BEHAVIOR MISMATCH`** / **`STALE TEST`** | Asserts `max_score < 58.0` based on a historical snapshot from Sept 8 ($N=861$). Subsequent live data ($N=1349$) truthfully recorded genuine confluence scores up to 65. |

### Critical Findings:
1. **Production Code is 100% Correct**:
   - The resolver's two-stage entry-fill state machine (`_evaluate_two_stage_signal`) is mathematically and physically sound. The old single-stage helper `_evaluate_candles_against_signal` was intentionally eliminated because it generated impossible 100% win-rate artifacts on unfilled limit orders.
   - The recording of XAU confluence scores up to 65 in `ml_shadow_observations` is genuine market reality. Technical confluence is an indicator score (0–100); capping it below 58 would break the system and prevent Gold from ever satisfying the Quality Gate (`signal_strength >= 58`).
2. **Zero Production Regressions**:
   - None of the 4 failures represent a regression in quant algorithms, ML models, API endpoints, security, or trading decisions.
   - Dedicated test suites (`tests/test_forward_shadow_resolver_worker.py` and `tests/test_forward_shadow_isolation_and_tradability.py`) test the resolver and pass 100%.
   - Updating these tests to match the current approved system will **NOT** hide any regression; it will restore test suite accuracy against approved platform contracts.

---

## 2. Deep Forensic Analysis: Failures 1, 2, and 3 (Resolver Worker Helper)

### 2.1 Context & Exact Call Sites
In `tests/test_pipeline_e2e_connections.py`:

#### Call Site 1 (Lines 330-333):
```python
worker = ForwardShadowResolverWorker(db_path=DB_PATH)
res_win = worker._evaluate_candles_against_signal(
    direction="BUY", entry=100.0, sl=95.0, tp1=110.0,
    sig_epoch_ms=sig_epoch_ms, candles=candles_win
)
```

#### Call Site 2 (Lines 443-450):
```python
worker = ForwardShadowResolverWorker(db_path=DB_PATH)
res = worker._evaluate_candles_against_signal(
    direction="BUY",
    entry=65000.0,
    sl=64200.0,
    tp1=66600.0,
    sig_epoch_ms=1700000000000,
    candles=candles,
)
```

#### Call Site 3 (Lines 557-564):
```python
worker = ForwardShadowResolverWorker(db_path=DB_PATH)
res = worker._evaluate_candles_against_signal(
    direction="SELL",
    entry=2650.0,
    sl=2665.0,
    tp1=2620.0,
    sig_epoch_ms=1700000000000,
    candles=candles_sell_win,
)
```

All 3 fail with:
```text
AttributeError: 'ForwardShadowResolverWorker' object has no attribute '_evaluate_candles_against_signal'
```

---

### 2.2 Production Implementation Evolution: Old vs Current

#### The Old Flawed Resolver (`_evaluate_candles_against_signal`):
Prior to Phase 14 tradability hardening, `ForwardShadowResolverWorker` evaluated signals using an immediate, single-stage candle check:
```python
# OBSOLETE & FLAWED (PRE-PHASE 14):
def _evaluate_candles_against_signal(direction, entry, sl, tp1, sig_epoch_ms, candles):
    for c in candles:
        if direction == "BUY":
            if c["low"] <= sl:
                return ("RESOLVED_LOSS", sl, -1.0)
            elif c["high"] >= tp1:
                return ("RESOLVED_WIN", tp1, realized_r)
```
**The Fatal Defect**:
This logic evaluated Take Profit and Stop Loss without ever checking whether the market traded down to the limit entry price.
As documented in `FORWARD_SHADOW_CORRECTION_BASELINE.md` (Section 3.2):
> *"Because BTC market candles were trading at $78,000+ while an injected static BUY order had Entry = $64,000 and TP = $65,880: Candle High was $78,000+ (which is > $65,880 TP). The resolver immediately triggered RESOLVED_WIN, resulting in an impossible 100% win rate on unfilled orders."*

#### The Current Approved Resolver (`_evaluate_two_stage_signal`):
In Phase 14, `ForwardShadowResolverWorker` was completely refactored to implement the **Two-Stage Entry-Fill State Machine** (lines 305–407 of `src/services/forward_shadow_resolver_worker.py`):

```text
[NEW SIGNAL]
      ↓
  PENDING / PENDING_ENTRY
      │
      ├── Price touches entry within 48h?
      │      │
      │      ├── NO (>48h elapsed) ──→ NOT_TRIGGERED (R = 0.0, Excluded from Governance N)
      │      │
      │      └── YES ──→ Transitions to ACTIVE_POSITION
      │                   (Calls mark_entry_filled, records entry_filled_at = candle_timestamp)
      │
      └── ACTIVE_POSITION
             │
             ├── Low <= SL and High >= TP (Same Candle) ──→ AMBIGUOUS (R = 0.0)
             ├── Hit TP (BUY: High >= TP1 / SELL: Low <= TP1) ──→ RESOLVED_WIN (R = +X.XX)
             ├── Hit SL (BUY: Low <= SL / SELL: High >= SL) ──→ RESOLVED_LOSS (R = -1.0)
             └── Duration from fill > 48h ──→ RESOLVED_EXPIRED (R = 0.0)
```

**Production Invariant**:
> *"No TP or SL check is EVER executed while in PENDING_ENTRY."*

The old private helper `_evaluate_candles_against_signal` was intentionally deleted because maintaining an unphysical single-stage evaluator in production would violate governance tradability mandates.

### 2.3 Verdict for Failures 1, 2, and 3:
* **Classification**: **`STALE TEST`**
* **Production Status**: Correct and authoritative.
* **Test Status**: Stale. The tests in `test_pipeline_e2e_connections.py` were written before the two-stage entry-fill hardening and directly invoked the retired private helper.
* **Regression Risk**: Zero. `tests/test_forward_shadow_resolver_worker.py` and `tests/test_forward_shadow_isolation_and_tradability.py` already thoroughly validate the two-stage engine.

---

## 3. Deep Forensic Analysis: Failure 4 (`test_xau_resolution_forensics.py`)

### 3.1 Context & Exact Assertion
In `tests/test_xau_resolution_forensics.py:258-270`:

```python
def test_xau_observations_confluence_below_threshold():
    # Verify all historical XAU observations had confluence score < 58 (DIRECTIONAL_THRESHOLD)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT MAX(confluence_score) FROM ml_shadow_observations 
        WHERE symbol IN ('XAU/USD', 'XAU-USD-SPOT', 'GOLD')
    ''')
    max_score = cursor.fetchone()[0]
    conn.close()
    assert max_score is not None
    assert max_score < 58.0, f"Expected max confluence score < 58.0, got {max_score}"
```

Fails with:
```text
AssertionError: Expected max confluence score < 58.0, got 65
assert 65 < 58.0
```

---

### 3.2 Provenance & Root Cause

1. **Origin of the Assertion**:
   * On September 8, 2026, during the initial XAU resolution audit (`XAU_FORWARD_RESOLUTION_FORENSIC_AUDIT.md`), the audit examined $N=861$ historical XAU observations in `ml_shadow_observations`.
   * At that specific historical moment, XAU technical confluence scores happened to range between 13.0 and 57.0 (max = 57.0).
   * The auditor documented in Section 3:
     > *"For all 861 XAU observations, confluence scores ranged from 13.0 to 57.0 (average: 36.51)... DIRECTIONAL_THRESHOLD = 58.0 was never breached by Gold during this period."*
   * The test author wrote `test_xau_observations_confluence_below_threshold()` asserting that `max_score < 58.0` for all time.

2. **Evolution of Forward Data ($N=861 \to N=1349$)**:
   * As live market data ingestion continued on September 9 and 10, 2026, the system recorded 488 additional live observations (reaching 1,349 total).
   * During strong gold momentum sessions on September 9–10, the technical engine genuinely calculated confluence scores reaching 59, 60, 63, and 65:
     * `ML-SHADOW-BE09050BFD36` (`2026-09-09T08:16:17Z`): Confluence = **65**, Decision = `WAIT`, Quality Gate = `0`, Outcome = `OBSERVED_WAIT`
     * `ML-SHADOW-5EE7F9E92B68` (`2026-09-09T08:22:19Z`): Confluence = **59**, Decision = `WAIT`, Quality Gate = `0`, Outcome = `OBSERVED_WAIT`
     * `ML-SHADOW-8383AD10DE8D` (`2026-09-10T12:10:16Z`): Confluence = **60**, Decision = `WAIT`, Quality Gate = `0`, Outcome = `OBSERVED_WAIT`
     * `ML-SHADOW-DB1C33B3FA00` (`2026-09-10T12:13:16Z`): Confluence = **63**, Decision = `WAIT`, Quality Gate = `0`, Outcome = `OBSERVED_WAIT`

3. **Authoritative Semantic Distinction**:
   * **Technical Confluence Score** (0–100): An objective measure of multi-indicator alignment. It CAN and SHOULD be able to exceed 58.
   * **Quality Gate** ($Score \ge 58$): Requires overall conviction and technical confluence $\ge 58$ before a trade setup can be considered.
   * **Directional Threshold** ($|Net Score| \ge 20.0$): Governs whether directional consensus exists.
   * Crucially, in all 4 cases where confluence exceeded 58, the system **correctly and defensively issued `WAIT`** and **kept `quality_gate_passed = 0`** because opposing indicators or gate criteria prevented trade execution!
   * In fact, the sibling test on line 271 (`test_xau_observations_quality_gate_failed`) asserts:
     ```python
     SELECT COUNT(*) FROM ml_shadow_observations 
     WHERE symbol IN ('XAU/USD', 'XAU-USD-SPOT', 'GOLD') AND quality_gate_passed != 0
     ```
     This test **PASSES 100%** (0 quality gate passes out of 1,349 observations).

4. **Would Changing Production Code Be Incorrect?**:
   * **YES, CATASTROPHICALLY INCORRECT**. Capping technical confluence score below 58 in production would be an artificial distortion of genuine quantitative math, permanently disabling the system from ever allowing XAU to qualify for a trade when market confluence is legitimately high.

### 3.3 Verdict for Failure 4:
* **Classification**: **`EXPECTED BEHAVIOR MISMATCH`** / **`STALE TEST`**
* **Production Status**: Correct and authoritative.
* **Test Status**: Stale snapshot assumption. The assertion `assert max_score < 58.0` was valid only for the initial $N=861$ dataset on September 8; it is mathematically invalid for the growing forward evidence set ($N=1349$).
* **Regression Risk**: Zero. The test should verify what is genuinely invariant: that non-directional observations have `quality_gate_passed == 0` and resolve to `OBSERVED_WAIT`.

---

## 4. Remediation Recommendations

### Recommendation for Failures 1, 2, and 3 (`tests/test_pipeline_e2e_connections.py`):
Update the resolver test calls in `tests/test_pipeline_e2e_connections.py` to use the approved two-stage API:
* Pass the required parameters to `worker._evaluate_two_stage_signal(...)` with an initial `status="PENDING_ENTRY"` and verify the realistic two-stage flow:
  1. Entry fill detection (`low <= entry` for BUY / `high >= entry` for SELL)
  2. Resolution outcome (`RESOLVED_WIN` on TP, `RESOLVED_LOSS` on SL, or `AMBIGUOUS` if both hit).
* This preserves strict verification of candle evaluation outcomes while honoring the production two-stage contract.

### Recommendation for Failure 4 (`tests/test_xau_resolution_forensics.py`):
Update `test_xau_observations_confluence_below_threshold`:
* Replace the brittle static snapshot assertion (`max_score < 58.0`) with the true architectural invariant:
  1. Confluence scores are valid probabilities/points within $[0, 100]$.
  2. All XAU observations in `ml_shadow_observations` where `production_decision == 'WAIT'` have `quality_gate_passed == 0` and `outcome == 'OBSERVED_WAIT'`.
  3. Verify that directional trade qualification adheres to the approved Quality Gate ($Score \ge 58$).

---

## 5. Explicit Hold & User Review Gate

> [!IMPORTANT]
> **NO TESTS OR SOURCE FILES HAVE BEEN MODIFIED.**  
> This forensic report provides the complete read-first audit.  
> Any test alignment will strictly await explicit user instruction.
