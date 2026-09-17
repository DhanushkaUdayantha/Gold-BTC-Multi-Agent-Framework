# DEF-01 & DEF-02 REMEDIATION REPORT

**Repository**: `D:\Project\TRADE`  
**Date**: September 12, 2026  
**Status**: REMEDIATION COMPLETE  
**Scope**: Targeted Surgical Fix for DEF-01 (Backend) and DEF-02 (Frontend) ONLY  

---

## 1. DEF-01 REMEDIATION: OUTCOME TRACKER ATTRIBUTE ACCESS

### Root Cause
In [`src/services/outcome_tracker.py`](file:///D:/Project/TRADE/src/services/outcome_tracker.py), `OutcomeTracker._scan_candles` previously accessed candlestick fields via dictionary subscripting:
```python
c.get("timestamp", "")
c.get("high", 0)
c.get("low", 0)
```
In live operation, `DecisionService` passes `candles_history` derived from `MarketService.get_candles()`, which contains instances of [`OHLCVCandle`](file:///D:/Project/TRADE/src/models/market_data.py) (a Pydantic `BaseModel`). Because Pydantic models do not implement `.get()`, this raised:
```text
AttributeError: 'OHLCVCandle' object has no attribute 'get'
```
This unhandled exception caused `_evaluate_signal` to abort evaluation for open recorded signals in `signal_records.json`.

### Exact Fix
In `OutcomeTracker._scan_candles`, implemented an explicit, readable compatibility helper `_candle_value`:
```python
def _candle_value(candle: Any, field: str, default: Any = None) -> Any:
    if isinstance(candle, dict):
        return candle.get(field, default)
    return getattr(candle, field, default)
```
Field accesses were updated:
- `c.get("timestamp", "")` → `_candle_value(c, "timestamp", "")`
- `c.get("high", 0)` → `_candle_value(c, "high", 0)`
- `c.get("low", 0)` → `_candle_value(c, "low", 0)`
Also updated type annotations on `candles_history` and `candles` parameters from `List[Dict[str, Any]]` to `List[Any]` to reflect real polymorphic runtime usage.

### Files Changed
- [`src/services/outcome_tracker.py`](file:///D:/Project/TRADE/src/services/outcome_tracker.py)

### Tests Added / Updated
In [`tests/test_backtesting.py`](file:///D:/Project/TRADE/tests/test_backtesting.py):
- Imported `OHLCVCandle` from `src.models.market_data`.
- Added `test_candle_pydantic_model_evaluation` proving that `OutcomeTracker._scan_candles`:
  1. Scans real `OHLCVCandle` Pydantic model objects without `AttributeError`.
  2. Correctly detects TP1 hits on `candle.high`.
  3. Correctly detects SL hits on `candle.low`.
  4. Preserves backward compatibility with existing dictionary fixtures.

### Before vs After Behavior
- **Before**: When evaluating open signals against 5m candles, `OutcomeTracker` raised `AttributeError: 'OHLCVCandle' object has no attribute 'get'`, caught by the outer logger, leaving signals un-evaluated.
- **After**: Both `OHLCVCandle` instances and `dict` fixtures evaluate cleanly without exception.

### Outcome Semantics Unchanged
- Look-ahead barrier (`sig_ts`) is strictly preserved.
- Conditions for WIN (TP1 hit) and LOSS (SL hit) remain identical.
- Running excursion tracking (MFE/MAE) semantics are identical.
- Expiration rules remain 72 hours.

### Forward Evidence & Database Impact
- **Clean Forward N**: Unaffected ($N=0$ for XAU, $N=58$ for BTC).
- **Historical DB**: Unaffected.
- **Shadow DB**: Unaffected.
- **Risk**: Extremely Low.

---

## 2. DEF-02 REMEDIATION: CONFLICT WEIGHT UI TRUTH

### Root Cause
In [`frontend/src/app/page.tsx`](file:///D:/Project/TRADE/frontend/src/app/page.tsx) (lines 4643 and 5295), the Conflict Gate cards attempted to access:
```tsx
(data.decision as any)?.conflict_weight
```
Neither `TradingDecision` nor `OverallTradingSignal` exposes a root `conflict_weight` property. As a result, the expression always evaluated to `undefined`, falling back to `"0.0%"` even when a conflict was actively detected.

### Authoritative Source & Truthful Fallback
1. Checked backend schema: No numeric opposing weight is currently exposed at the top level of the decision payload.
2. Implemented strict truthfulness per prompt requirements:
   - If an authoritative numeric field exists on `overall_signal.conflict_weight` or `decision.conflict_weight`, format and display that actual value.
   - If no numeric field exists, display `"--"`.
   - **NEVER** fabricate `"0.0%"`, `"25.0%"`, or `">=25.0%"`.

### Exact UI Change
In `frontend/src/app/page.tsx` (lines 4643 and 5301):
```tsx
<div>Threshold: <strong className="text-white">&le; 25.0% Opposing</strong></div>
<div>Weight: <strong className={data.decision?.overall_signal?.conflict_detected ? "text-rose-400" : "text-emerald-400"}>{
  typeof (data.decision?.overall_signal as any)?.conflict_weight === "number"
    ? `${(((data.decision?.overall_signal as any).conflict_weight) * ((data.decision?.overall_signal as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
    : typeof (data.decision as any)?.conflict_weight === "number"
    ? `${(((data.decision as any).conflict_weight) * ((data.decision as any).conflict_weight <= 1.0 ? 100 : 1)).toFixed(1)}%`
    : "--"
}</strong></div>
```
Exported `formatConflictWeight(value: unknown): string` in [`frontend/src/lib/format.ts`](file:///D:/Project/TRADE/frontend/src/lib/format.ts).

### Files Changed
- [`frontend/src/app/page.tsx`](file:///D:/Project/TRADE/frontend/src/app/page.tsx)
- [`frontend/src/lib/format.ts`](file:///D:/Project/TRADE/frontend/src/lib/format.ts)
- [`frontend/src/lib/__tests__/conflictWeight.test.ts`](file:///D:/Project/TRADE/frontend/src/lib/__tests__/conflictWeight.test.ts) (NEW)

### Tests Added / Updated
Created `frontend/src/lib/__tests__/conflictWeight.test.ts` covering:
- **Case A**: Authoritative numeric conflict weight exists → formats and displays actual value (e.g. `0.18` → `"18.0%"`).
- **Case B**: Numeric conflict weight is unavailable (null, undefined, string, NaN) → displays `"--"`.
- **Case C**: Conflict detected but numeric weight absent → asserts output is `"--"` and explicitly verifies it does NOT fabricate `"0.0%"` or `"25.0%"`.

### Backend & API Immutability
- Backend decision engine, signal aggregator, and API routes were **NOT modified**.
- Zero fabricated numbers.
- Risk: Zero.

---

## 3. REGRESSION TEST EXECUTION

### Backend Targeted Tests
- `pytest tests/test_backtesting.py -q` → **62 passed in 0.99s**
- `pytest tests/test_overall_ai_evidence.py tests/test_phase5_live_validation.py -q` → **25 passed in 45.94s**

### Frontend Targeted Tests
- `npm --prefix frontend test` → **28 passed across 5 test suites**
  - `conflictWeight.test.ts`: 3 passed
  - `formatRAsUSD.test.ts`: 3 passed
  - `heroPercentage.test.ts`: 14 passed
  - `overallInsight.test.ts`: 4 passed
  - `relativeTime.test.ts`: 4 passed

### Full Pytest Run 1
- Command: `pytest -q`
- Result: **796 passed in 221.71s (100%)**

### Full Pytest Run 2
- Command: `pytest -q`
- Result: **796 passed in 169.16s (100%)**

### Frontend Production Build
- Command: `npm --prefix frontend run build`
- Result: **Compiled successfully, static generation 4/4 complete, exit code 0**

### Backend Health & Endpoints
- `GET /health` → **HTTP 200 OK** (`feed: online`, `gemini_active: True`)
- `GET /api/v1/decision?symbol=BTC-USD` → **HTTP 200 OK** (`decision: WAIT`, `symbol: BTC/USD`)
- `GET /api/v1/decision?symbol=XAU-USD-SPOT` → **HTTP 200 OK** (`decision: WAIT`, `symbol: XAU/USD`)

---

## 4. INTEGRITY & IMMUTABILITY AUDIT

| Component | Status | Verification Details |
| :--- | :---: | :--- |
| **Historical DB** | **UNCHANGED** | Evidence & backtest tables immutable. Live 5m ingestion active. |
| **Forward Evidence** | **UNCHANGED** | Clean Forward Resolved: XAU $N=0$, BTC $N=58$. No synthetic contamination. |
| **Shadow DB** | **UNCHANGED** | `data/shadow_trades.db` SHA-256 matches baseline. |
| **Signal Records** | **UNCHANGED** | `signal_records.json` SHA-256 matches baseline. |
| **Governance State** | **UNCHANGED** | `data/governance_forward_state.json` SHA-256 matches baseline (`S2: EVIDENCE_COLLECTION`). |
| **Production Gating** | **DISABLED** | `data/gating_state.json` SHA-256 matches baseline (`False`). |
| **Live Execution** | **DISABLED** | Live execution flag disabled across state machine and runners. |
| **Quantitative Logic** | **UNCHANGED** | Zero diff in `decision_engine.py`, `signal_aggregator.py`, `confluence_engine.py`. |
| **ML Models & Artifacts** | **UNCHANGED** | LogisticRegression (BTC) & RandomForest (XAU) artifacts untouched. |
| **Security Controls** | **UNCHANGED** | CORS allowlist, security headers, exception sanitization untouched. |

---

## 5. FILE CHANGES CLASSIFICATION

### Expected Files Changed
1. `src/services/outcome_tracker.py` — DEF-01 candle attribute compatibility helper.
2. `tests/test_backtesting.py` — DEF-01 regression test with real `OHLCVCandle` model.
3. `frontend/src/app/page.tsx` — DEF-02 truthful conflict weight binding (lines 4643, 5301).
4. `frontend/src/lib/format.ts` — DEF-02 exported `formatConflictWeight` formatter.
5. `frontend/src/lib/__tests__/conflictWeight.test.ts` — DEF-02 unit test suite.

### Unexpected Files Changed
- **NONE**
