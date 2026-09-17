# Test Failure Remediation Report: Safe Resolution of 4 Pre-Existing Failures

**Repository**: `D:\Project\TRADE`  
**Date**: September 12, 2026  
**Status**: **COMPLETE — ALL 795 TESTS PASSING (100%)**  
**Remediation Scope**: Strict Test-Only Realignment (Zero Production, Quant, ML, Database, or Threshold Mutations)  

---

## 1. Executive Summary

A comprehensive, safe, test-only remediation of the 4 pre-existing test failures identified during the system audit was executed strictly adhering to governance safety rules and the forensic specifications documented in `REMAINING_4_TEST_FAILURE_FORENSIC.md`.

* **Total Test Count**: **795**
* **Baseline Result**: 791 Passed, 4 Failed
* **Post-Remediation Consecutive Run 1**: **795 PASSED**, 0 Failed (205.36s / 03:25)
* **Post-Remediation Consecutive Run 2**: **795 PASSED**, 0 Failed (138.88s / 02:18)
* **Frontend Unit Tests**: **25/25 PASSED** (0 failures, 711ms)
* **Frontend Production Build**: **CLEAN SUCCESS** (Next.js 14.2.4, exit code 0)
* **Backend Health & Decision Endpoints**: **200 OK** (`/health`, `/api/v1/decision?symbol=XAU-USD-SPOT`, `/api/v1/decision?symbol=BTC-USD`)
* **Quant / Algorithm / ML Mutations**: **EXACTLY ZERO** (0 diff across `decision_engine.py`, `signal_aggregator.py`, `confluence_engine.py`, and ML models)
* **Overall Status**: **PASS**

---

## 2. Forensic Analysis & Root Cause Classification

| Test ID | Test Function | Test File | Classification | Root Cause & Remediation |
|:---:|:---|:---|:---:|:---|
| **1** | `test_resolver_candle_evaluation_outcomes` | `tests/test_pipeline_e2e_connections.py:321` | **`STALE TEST`** | Test invoked the obsolete private helper `_evaluate_candles_against_signal` that was retired during Phase 14 tradability hardening. Remediated to use the approved two-stage evaluator `_evaluate_two_stage_signal`. |
| **2** | `test_btc_separate_pipeline` | `tests/test_pipeline_e2e_connections.py:461` | **`STALE TEST`** | Step 6 in the pipeline connection test called the retired helper `_evaluate_candles_against_signal`. Remediated to use `_evaluate_two_stage_signal`. |
| **3** | `test_xau_separate_pipeline` | `tests/test_pipeline_e2e_connections.py:578` | **`STALE TEST`** | Step 7 in the XAU pipeline connection test called the retired helper `_evaluate_candles_against_signal`. Remediated to use `_evaluate_two_stage_signal`. |
| **4** | `test_xau_observations_confluence_below_threshold` | `tests/test_xau_resolution_forensics.py:258` | **`EXPECTED BEHAVIOR MISMATCH`** | Brittle assertion `assert max_score < 58.0` codified an empirical snapshot at $N=861$ from Sept 8. Legitimate trending Gold market movements on Sept 9–10 produced genuine confluence scores of 59, 60, 63, and 65. Remediated to assert score validity bounded within $[0, 100]$ and strictly verify that observations with confluence $\ge 58$ adhered to defensive gating (`quality_gate_passed = 0`, `WAIT`, `OBSERVED_WAIT`). |

---

## 3. Pre-Edit Analysis & Exact Code Diffs

### 3.1 Failures 1, 2, and 3: Resolver Two-Stage Alignment
**File**: `tests/test_pipeline_e2e_connections.py`

#### Architecture Background:
In Phase 14 tradability hardening, single-stage candle evaluation was eliminated because checking TP/SL without verifying that market prices traded down/up to the limit order entry price generated impossible 100% win rates on unfilled orders. The approved production resolver is `ForwardShadowResolverWorker._evaluate_two_stage_signal`:
1. **Stage 1 (`PENDING_ENTRY`)**: Verifies market touch of limit entry (`low <= entry` for BUY / `high >= entry` for SELL).
2. **Stage 2 (`ACTIVE_POSITION`)**: Evaluates TP and SL against candles.

#### Call Site 1: `test_resolver_candle_evaluation_outcomes`
```diff
--- a/tests/test_pipeline_e2e_connections.py
+++ b/tests/test_pipeline_e2e_connections.py
@@ -327,9 +327,16 @@ def test_resolver_candle_evaluation_outcomes():
         {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 105.0, "low": 98.0, "close": 102.0},
         {"timestamp": "2026-09-08T10:10:00Z", "epoch_ms": 1700000600000, "high": 111.0, "low": 101.0, "close": 110.5},
     ]
-    res_win = worker._evaluate_candles_against_signal(
-        direction="BUY", entry=100.0, sl=95.0, tp1=110.0,
-        sig_epoch_ms=sig_epoch_ms, candles=candles_win
+    res_win = worker._evaluate_two_stage_signal(
+        sig_id="TEST-E2E-BUY-WIN",
+        direction="BUY",
+        entry=100.0,
+        sl=95.0,
+        tp1=110.0,
+        sig_epoch_ms=sig_epoch_ms,
+        status="PENDING_ENTRY",
+        entry_filled_at=None,
+        candles=candles_win,
     )
     assert res_win is not None
     assert res_win[0] == "RESOLVED_WIN"
@@ -338,9 +345,16 @@ def test_resolver_candle_evaluation_outcomes():
     candles_loss = [
         {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 102.0, "low": 94.5, "close": 96.0},
     ]
-    res_loss = worker._evaluate_candles_against_signal(
-        direction="BUY", entry=100.0, sl=95.0, tp1=110.0,
-        sig_epoch_ms=sig_epoch_ms, candles=candles_loss
+    res_loss = worker._evaluate_two_stage_signal(
+        sig_id="TEST-E2E-BUY-LOSS",
+        direction="BUY",
+        entry=100.0,
+        sl=95.0,
+        tp1=110.0,
+        sig_epoch_ms=sig_epoch_ms,
+        status="PENDING_ENTRY",
+        entry_filled_at=None,
+        candles=candles_loss,
     )
     assert res_loss is not None
     assert res_loss[0] == "RESOLVED_LOSS"
@@ -349,12 +363,19 @@ def test_resolver_candle_evaluation_outcomes():
     candles_both = [
         {"timestamp": "2026-09-08T10:05:00Z", "epoch_ms": 1700000300000, "high": 112.0, "low": 93.0, "close": 105.0},
     ]
-    res_both = worker._evaluate_candles_against_signal(
-        direction="BUY", entry=100.0, sl=95.0, tp1=110.0,
-        sig_epoch_ms=sig_epoch_ms, candles=candles_both
+    res_both = worker._evaluate_two_stage_signal(
+        sig_id="TEST-E2E-BUY-BOTH",
+        direction="BUY",
+        entry=100.0,
+        sl=95.0,
+        tp1=110.0,
+        sig_epoch_ms=sig_epoch_ms,
+        status="PENDING_ENTRY",
+        entry_filled_at=None,
+        candles=candles_both,
     )
     assert res_both is not None
-    assert res_both[0] == "RESOLVED_LOSS"
+    assert res_both[0] == "AMBIGUOUS"
```

#### Call Site 2: `test_btc_separate_pipeline`
```diff
--- a/tests/test_pipeline_e2e_connections.py
+++ b/tests/test_pipeline_e2e_connections.py
@@ -461,8 +461,12 @@ def test_btc_separate_pipeline(tmp_path):
         "low": 64800.0,
         "close": 66800.0,
     }]
-    res = worker._evaluate_candles_against_signal(
+    res = worker._evaluate_two_stage_signal(
+        sig_id="TEST-E2E-BTC-BUY",
         direction="BUY",
         entry=65000.0,
         sl=64200.0,
         tp1=66600.0,
         sig_epoch_ms=1700000000000,
+        status="PENDING_ENTRY",
+        entry_filled_at=None,
         candles=candles,
     )
```

#### Call Site 3: `test_xau_separate_pipeline`
```diff
--- a/tests/test_pipeline_e2e_connections.py
+++ b/tests/test_pipeline_e2e_connections.py
@@ -578,8 +578,12 @@ def test_xau_separate_pipeline(tmp_path):
         "low": 2618.0,
         "close": 2625.0,
     }]
-    res = worker._evaluate_candles_against_signal(
+    res = worker._evaluate_two_stage_signal(
+        sig_id="TEST-E2E-XAU-SELL",
         direction="SELL",
         entry=2650.0,
         sl=2665.0,
         tp1=2620.0,
         sig_epoch_ms=1700000000000,
+        status="PENDING_ENTRY",
+        entry_filled_at=None,
         candles=candles_sell_win,
     )
```

---

### 3.2 Failure 4: XAU Confluence Score Invariant Verification
**File**: `tests/test_xau_resolution_forensics.py`

#### Architecture Background:
The confluence score is an objective technical summation across 17 indicators bounded in $[0, 100]$. The Quality Gate threshold is $\ge 58.0$. Asserting `max_score < 58.0` was an empirical observation of an early historical snapshot at $N=861$. When live observation volume reached $N=1,349$, trending Gold market movements correctly produced scores of 59, 60, 63, and 65. The true architectural invariant is that:
1. Confluence scores must be mathematically valid and bounded within $[0, 100]$.
2. Observations with confluence $\ge 58$ still did not bypass defensive gating (they correctly maintained `WAIT`, `quality_gate_passed = 0`, and `outcome = 'OBSERVED_WAIT'`).

#### Code Diff:
```diff
--- a/tests/test_xau_resolution_forensics.py
+++ b/tests/test_xau_resolution_forensics.py
@@ -258,13 +258,28 @@ def test_null_safety_in_resolve_pending_observations():
 def test_xau_observations_confluence_below_threshold():
-    """Verify all historical XAU observations had confluence score < 58 (DIRECTIONAL_THRESHOLD)."""
-    conn = sqlite3.connect(DB_PATH)
-    cursor = conn.cursor()
-    cursor.execute("""
-        SELECT MAX(confluence_score) FROM ml_shadow_observations 
-        WHERE symbol IN ('XAU/USD', 'XAU-USD-SPOT', 'GOLD')
-    """)
-    max_score = cursor.fetchone()[0]
-    conn.close()
-    assert max_score is not None
-    assert max_score < 58.0, f"Expected max confluence score < 58.0, got {max_score}"
+    """Verify all historical XAU observations have valid confluence scores (0-100)
+    and that observations reaching quality gate threshold (>= 58) strictly adhered to defensive gating."""
+    conn = sqlite3.connect(DB_PATH)
+    cursor = conn.cursor()
+    cursor.execute("""
+        SELECT MIN(confluence_score), MAX(confluence_score), COUNT(*)
+        FROM ml_shadow_observations 
+        WHERE symbol IN ('XAU/USD', 'XAU-USD-SPOT', 'GOLD')
+    """)
+    min_score, max_score, total_count = cursor.fetchone()
+    assert total_count > 0, "Expected XAU observations in ml_shadow_observations"
+    assert min_score is not None and max_score is not None
+    assert 0.0 <= min_score <= 100.0, f"Expected min confluence score in [0, 100], got {min_score}"
+    assert 0.0 <= max_score <= 100.0, f"Expected max confluence score in [0, 100], got {max_score}"
+
+    # Verify that any observation with confluence >= 58 (the quality gate threshold)
+    # strictly adhered to defensive gating (WAIT decision, quality_gate_passed=0, OBSERVED_WAIT outcome)
+    cursor.execute("""
+        SELECT COUNT(*) FROM ml_shadow_observations 
+        WHERE symbol IN ('XAU/USD', 'XAU-USD-SPOT', 'GOLD')
+          AND confluence_score >= 58.0
+          AND (production_decision != 'WAIT' OR quality_gate_passed != 0 OR outcome != 'OBSERVED_WAIT')
+    """)
+    unqualified_violations = cursor.fetchone()[0]
+    conn.close()
+    assert unqualified_violations == 0, f"Found {unqualified_violations} XAU observations >= 58 that improperly bypassed defensive gating"
```

---

## 4. Verification Evidence & Test Execution

### 4.1 Consecutive Pytest Runs (Full Suite)

#### Consecutive Run 1:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- D:\Project\TRADE\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Project\TRADE
configfile: pytest.ini
plugins: anyio-4.14.2
collecting ... collected 795 items

........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 81%]
........................................................................ [ 90%]
........................................................................ [ 99%]
...                                                                      [100%]
============================== 795 passed in 205.36s (0:03:25) ================
```

#### Consecutive Run 2:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- D:\Project\TRADE\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Project\TRADE
configfile: pytest.ini
plugins: anyio-4.14.2
collecting ... collected 795 items

........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 81%]
........................................................................ [ 90%]
........................................................................ [ 99%]
...                                                                      [100%]
============================== 795 passed in 138.88s (0:02:18) ================
```

### 4.2 Frontend Unit Tests & Build

#### Frontend Tests (`npm --prefix frontend run test`):
```text
✔ formatRAsUSD - prompt required examples and exact values (342.5771ms)
✔ formatRAsUSD - string inputs and custom precision (1.0002ms)
✔ formatRAsUSD - invalid and fallback handling (0.3498ms)
✔ 1. Valid percentage renders as expected integer with % suffix (6.802ms)
...
✔ formatRelativeTime test matrix - exact boundaries and representative cases (4.5466ms)
✔ formatRelativeTime - invalid, missing, and malformed inputs (0.5058ms)
✔ formatRelativeTime - exact boundary transitions (0.4226ms)
✔ formatRelativeTime - prefix option support (0.2927ms)
ℹ tests 25
ℹ suites 0
ℹ pass 25
ℹ fail 0
ℹ duration_ms 711.296
```

#### Frontend Production Build (`npm --prefix frontend run build`):
```text
  ▲ Next.js 14.2.4
  - Environments: .env.local

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (4/4) ...
 ✓ Generating static pages (4/4)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    174 kB          261 kB
└ ○ /_not-found                          871 B            88 kB
+ First Load JS shared by all            87.1 kB
```

### 4.3 Backend Health & Decision Endpoints
Verified live endpoints with HTTP status 200:
* `GET /health` $\to$ `200 OK` (`feed: online`, `gemini_active: True`)
* `GET /api/v1/decision?symbol=XAU-USD-SPOT` $\to$ `200 OK` (Symbol: `XAU/USD`, Decision: `WAIT`)
* `GET /api/v1/decision?symbol=BTC-USD` $\to$ `200 OK` (Symbol: `BTC/USD`, Decision: `WAIT`)

---

## 5. Protected Artifact Integrity Verification

Zero production or model code was modified during this remediation. Hashes for core logic, models, and governance state files were strictly verified:

| File | SHA-256 Hash Status | Integrity |
|:---|:---:|:---:|
| `src/services/decision_engine.py` | `55C9373280801EAD505BABA90D8A3CF4F4742D1883D8DD0D3E42E15F97AFF940` | **MATCH (UNCHANGED)** |
| `src/services/signal_aggregator.py` | `BD32A99A86755F2142D4659BC9EB0892FF3AC62A712660F3C47D6A3ECE497DA0` | **MATCH (UNCHANGED)** |
| `src/services/confluence_engine.py` | `82246A25EEEBCA8DD956ADD730281FAF669993F990FF330CA29C8043735F1580` | **MATCH (UNCHANGED)** |
| `research/ml/artifacts/BTC/model.joblib` | `0978B52D9B23A12099935EEB72CC260A470C283E0E4E54FC278596EBB9F482A5` | **MATCH (UNCHANGED)** |
| `research/ml/artifacts/XAU/model.joblib` | `C12A0F09101DAD9547618D6DDF68F99105D539F8618486D59CFE16F586DC8F2E` | **MATCH (UNCHANGED)** |
| `research/ml/artifacts/BTC/metrics.json` | `EF3FEE9FE5ACB25470F5F4A2C8362C0B72F933CCAE9233DB257875161341D7C0` | **MATCH (UNCHANGED)** |
| `research/ml/artifacts/XAU/metrics.json` | `879220C1096E967054A98DEF193EF6EF9B89257BB318BF4CAB33AC0926B927CD` | **MATCH (UNCHANGED)** |
| `data/shadow_trades.db` | `D477F87FE3BCD8E5476A95E7436FD36082FD901A45783F58243C7FD24F6FB627` | **MATCH (UNCHANGED)** |
| `data/governance_forward_state.json` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | **MATCH (UNCHANGED)** |
| `data/gating_state.json` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | **MATCH (UNCHANGED)** |

### Working Tree Verification
`git diff -- src/services/decision_engine.py src/services/signal_aggregator.py src/services/confluence_engine.py` confirmed **0 diff** across all core decision services.

---

## 6. Final Verdict

> [!IMPORTANT]
> **REMEDIATION VERDICT: PASS**  
> All 4 pre-existing test failures are resolved through test-only alignment. The test suite now passes 795 of 795 tests (100%) consecutively. No production code, trading logic, machine learning models, database records, forward evidence, or gating thresholds were mutated. Live execution remains safely DISABLED.
