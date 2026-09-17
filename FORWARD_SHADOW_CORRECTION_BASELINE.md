# FORWARD SHADOW CORRECTION — BASELINE AUDIT & QUARANTINE SPECIFICATION

**Date**: 2026-09-09  
**Branch**: `master`  
**Git Commit**: `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`  
**Governance State**: `S2 — EVIDENCE_COLLECTION`  
**Production Gating**: `DISABLED`  
**Live Execution**: `DISABLED`  

---

## 1. EXECUTIVE SUMMARY

Following the comprehensive read-only forensic investigation documented in `FORWARD_SHADOW_TRADABILITY_FORENSIC_AUDIT.md`, this document establishes the authoritative pre-implementation baseline for correcting the Forward Shadow Validation architecture.

The forensic audit conclusively demonstrated that the **479 existing records** in `forward_shadow_signals` (280 BTC/USD, 199 XAU/USD) are **NOT valid forward trading evidence**. They originated from test executions injecting static unit test fixture values ($64,000 / $64,200 for BTC; $2,700 for XAU) into the production database due to missing test database isolation in `BTCShadowRunner` and `XAUShadowRunner`. Furthermore, the previous outcome resolver evaluated TP and SL directly against current market candles ($78,000+ for BTC; $4,450+ for XAU) without verifying whether the limit order was ever filled at entry price.

### Mandatory Quarantine Rule
1. **Zero Data Deletion**: The existing 479 records MUST NOT be deleted or overwritten. They remain preserved as immutable historical forensic evidence.
2. **Lineage Segregation**: All historical 479 records are segregated under `evidence_generation = 'FORENSIC_CONTAMINATED_TEST_FIXTURE'`.
3. **Zero Governance Credit**: The 479 contaminated records contribute exactly **0** to Governance validation count $N$.
4. **Clean Baseline Restart**: Forward evidence collection begins cleanly at $N = 0$ using dynamic live $T_0$ market data and the two-stage entry-fill state machine.

---

## 2. PRE-IMPLEMENTATION INTEGRITY CHECKSUMS

### 2.1 File Hashes (Pre-Implementation Baseline)
| Asset / File | Pre-Implementation SHA-256 Checksum |
| :--- | :--- |
| `data/historical/historical_market_data.db` | `B914FD5E0DFF522C5C4B9E399814AA4633F8FA3B2949858CF31D32772D25A90E` |
| `signal_records.json` | `1F8C002FAEDD2EB75E0B9442A0B964E7C5E96810A1CD4ECE9DFC52AA4F98DF19` |

*(Note: Periodic live ingestion of 5-minute market candles into `candles` table by the running background application updates the database file dynamically. However, records in `forward_shadow_signals` and test isolation ensure tests never write to these production files).*

### 2.2 Pre-Implementation `forward_shadow_signals` Table Breakdown
| Asset | Total Signals | PENDING | RESOLVED_WIN | RESOLVED_LOSS | Reported Win Rate | Audit Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **BTC/USD** | 280 | 0 | 280 | 0 | 100.0% | **CONTAMINATED** (Static Fixture $64k vs $78k market) |
| **XAU/USD** | 199 | 0 | 130 | 69 | 65.33% | **CONTAMINATED** (Static Fixture $2.7k vs $4.45k market) |
| **TOTAL** | **479** | **0** | **410** | **69** | **85.59%** | **QUARANTINED AS FORENSIC EVIDENCE** |

---

## 3. ROOT CAUSE FORENSIC SUMMARY

### 3.1 Contamination Vector: Test Fixture Bleed
In `src/services/btc_shadow_runner.py` and `src/services/xau_shadow_runner.py`:
```python
def __init__(
    self,
    shadow_store: Optional[ShadowTradingStore] = None,
    forward_engine: Optional[ForwardShadowEngine] = None,
):
    self.store = shadow_store or get_shadow_trading_store()
    self.forward_engine = forward_engine or get_forward_shadow_engine() # <-- ROOT CAUSE
```
When test suites (such as `test_btc_shadow_step1.py`, `test_btc_shadow_rollout.py`, `test_dual_asset_isolation.py`, etc.) instantiated runners with isolated shadow stores (`tmp_path / "test.db"`), they did not pass `forward_engine`. The runners defaulted to `get_forward_shadow_engine()`, directly invoking `capture_forward_signal()` against the authoritative production database `data/historical/historical_market_data.db`.

### 3.2 Tradability Failure: Missing Entry-Fill Verification
The previous resolver in `ForwardShadowResolverWorker` directly queried candles starting from $T_0$ and evaluated:
```python
# FLAWED LOGIC: Checks TP and SL before order is filled
if high >= tp:
    resolve_win()
elif low <= sl:
    resolve_loss()
```
Because BTC market candles were trading at $78,000+ while the injected static BUY order had Entry = $64,000 and TP = $65,880:
- Candle Low was $78,000 (never dropped to $64,000, so the limit order was NEVER filled).
- Candle High was $78,000+ (which is $> $65,880 TP).
- The resolver immediately triggered `RESOLVED_WIN`, resulting in an impossible 100% win rate (280/280) on unfilled orders.

---

## 4. ARCHITECTURAL CORRECTION SPECIFICATION

### Phase 1: Test Database Isolation (Triple Layer Defense)
1. **Layer 1 (Runner Fallback Isolation)**: If `shadow_store` is provided with a custom `db_path` and `forward_engine` is `None`, `BTCShadowRunner` and `XAUShadowRunner` automatically bind `forward_engine` to `ForwardShadowEngine(db_path=self.store.db_path)`.
2. **Layer 2 (Pytest Conftest Interception)**: `tests/conftest.py` intercepts `ForwardShadowEngine` default path and patches the singleton to an isolated SQLite file in `_TEMP_DIR`.
3. **Layer 3 (Explicit Test Fixtures)**: Test suites explicitly pass `ForwardShadowEngine(db_path=str(tmp_path / "fwd_test.db"))`.

### Phase 2: Schema Migration & Lineage Boundary
Add backward-compatible columns to `forward_shadow_signals`:
- `evidence_generation TEXT DEFAULT 'FORENSIC_CONTAMINATED_TEST_FIXTURE'`
- `entry_filled_at TEXT DEFAULT NULL`
- `entry_distance_pct REAL DEFAULT 0.0`

All existing 479 rows are tagged `'FORENSIC_CONTAMINATED_TEST_FIXTURE'`. Future signals generated by live decision capture will be stamped with `evidence_generation = 'CLEAN_FORWARD'`.

### Phase 3: Dynamic Live $T_0$ Capture
Ensure `DecisionService` (Hook 5) captures real dynamic live prices and ATR-derived SL/TP levels from incoming market candles, eliminating any static fallbacks.

### Phase 4: Two-Stage Entry-Fill State Machine
State transitions in `ForwardShadowResolverWorker`:
```text
[PENDING_ENTRY] (or initial PENDING)
       │
       ├──────────────────────────────────────────────┐
       │ (Candle touches Entry within 48 hours)       │ (48 hours expire without entry touch)
       ▼                                              ▼
[ACTIVE_POSITION]                              [NOT_TRIGGERED]
 (entry_filled_at recorded)                     (realized_r = 0.0)
       │
       ├──────────────────────┬──────────────────────┐
       │ (High >= TP)         │ (Low <= SL)          │ (Both hit in same candle)
       ▼                      ▼                      ▼
[RESOLVED_WIN]         [RESOLVED_LOSS]        [AMBIGUOUS]
```
- **Invariant**: No TP or SL check is EVER executed while in `PENDING_ENTRY`.
- If 48 hours elapse after entry fill without hitting TP or SL: transitions to `RESOLVED_EXPIRED`.

### Phase 5: Governance Exclusion & Clean Baseline $N = 0$
- `ForwardExecutionStateMachine` and `get_forward_validation_metrics()` filter strictly by:
  `evidence_generation = 'CLEAN_FORWARD' AND status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')`
- The 479 contaminated records contribute $N = 0$.
- Clean Forward Evidence starts at $N = 0$.
