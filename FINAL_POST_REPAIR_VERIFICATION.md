# FINAL POST-REPAIR FORENSIC VERIFICATION REPORT

**Document ID:** `TRADE-REPORT-POST-REPAIR-VERIFICATION-20260917`  
**Date:** September 17, 2026  
**Repository:** `D:\Project\TRADE`  
**Mode:** STRICT READ-ONLY FORENSIC AUDIT (Zero Code, Zero DB, Zero Doc Edits)  
**Authoritative Reference:** `PRE_FIX_FORENSIC_CONSISTENCY_AUDIT.md` & `SAFE_REPAIR_IMPLEMENTATION_REPORT.md`  

---

## 1. EXECUTIVE SUMMARY

Following the safe surgical repair of the MTF Alignment scaling defect and the historical evidence cross-run inflation, a final forensic verification was conducted to investigate three specific potential concerns:
1. **Timeframe Truth**: The exact authoritative definition of core vs auxiliary timeframes across all subsystems.
2. **Direction Gate Evaluation**: The apparent paradox of `Direction Gate: PASS` when `Net Score = -16.0` against a documented threshold of `|Net Score| >= 20.0`.
3. **Canonical Backtest Run Future Safety**: The algorithmic resilience of `ORDER BY br.created_at DESC LIMIT 1` when future exploratory or test backtest runs are executed.

All findings are grounded strictly in current source code, live API payloads, database schemas, and isolated in-memory test fixtures.

---

## 2. READ-ONLY GUARANTEE

In accordance with Section 1 of the instructions:
- Zero Python files were modified.
- Zero TypeScript / React files were modified.
- Zero existing Markdown documentation files were modified.
- Zero JSON state files were altered.
- Zero SQLite rows were deleted, updated, or inserted.
- Zero Git commits or pushes were executed.
- Only one new document (`FINAL_POST_REPAIR_VERIFICATION.md`) was created.

---

## 3. TIMEFRAME TRUTH AUDIT

An exhaustive inspection of every timeframe constant, enum, and dictionary across the repository was conducted:

1. **Core Decision Engine (`src/services/decision_service.py:48`)**:
   ```python
   _TIMEFRAMES = ["5m", "15m", "1h", "1d"]
   ```
   Evaluates technical analysis and closed candle series across exactly these 4 horizons concurrently (`ThreadPoolExecutor(max_workers=4)`).

2. **Google Gemini / AI Aggregator (`src/services/ai/ai_aggregator.py:18-23`)**:
   ```python
   class AIAggregator:
       TARGET_TIMEFRAMES = [
           Timeframe.M5,
           Timeframe.M15,
           Timeframe.H1,
           Timeframe.D1,
       ]
   ```
   Gathers technical profiles across `5m`, `15m`, `1h`, and `1d` to build the multi-timeframe JSON payload for Gemini AI.

3. **Confluence MTF Alignment Contributor (`src/services/confluence_engine.py:750-755`)**:
   ```python
   tfs = {
       "5m": snap.ta_5m,
       "15m": snap.ta_15m,
       "1h": snap.ta_1h,
       "1d": snap.ta_1d,
   }
   ```
   Contributor 4 evaluates directional consensus across exactly these 4 timeframes.

4. **Technical Analysis Engine (`src/services/technical_service.py:37` & `src/models/market_data.py:8-14`)**:
   ```python
   class Timeframe(str, Enum):
       M1 = "1m"
       M5 = "5m"
       M15 = "15m"
       H1 = "1h"
       D1 = "1d"
   ```
   The platform's domain model defines exactly five valid intervals: `1m, 5m, 15m, 1h, 1d`. Neither `4h` nor `1w` exists in this enum.

5. **Market REST API (`src/api/routes/market.py:53-58`)**:
   ```python
   timeframe: Timeframe = Query(
       default=Timeframe.M15,
       description="Candle timeframe: 1m, 5m, 15m, 1h, 1d"
   )
   ```
   The candle query endpoint explicitly validates against `1m, 5m, 15m, 1h, 1d`.

6. **Historical Database (`data/historical/historical_market_data.db`)**:
   - Distinct values in table `candles`: `['15m', '1d', '1h', '1m', '4h', '5m']`.
   - The database contains historical archived `4h` bars from earlier exploratory dataset ingestions. However, `4h` is NOT part of the live operational pipeline.
   - The interval `1w` does not exist in any database table.

7. **Frontend UI Chart & MTF Gauges (`frontend/src/app/page.tsx:91-98`)**:
   ```typescript
   const TIMEFRAMES = [
     { label: "5m", value: "5m" },
     { label: "15m", value: "15m" },
     { label: "1H", value: "1h" },
     { label: "1D", value: "1d" },
   ];
   const MTF_KEYS = ["5m", "15m", "1h", "1d"] as const;
   ```
   The frontend chart offers exactly four interval toggle buttons: `5m`, `15m`, `1H`, `1D`.

---

## 4. TIMEFRAME MATRIX

| Subsystem | Active Timeframes | Primary Source File | Operational Role |
| :--- | :--- | :--- | :--- |
| **Core Decision Engine** | `5m`, `15m`, `1h`, `1d` | `src/services/decision_service.py:48` | Core decision evaluation quartet |
| **Gemini / AI Input** | `5m`, `15m`, `1h`, `1d` | `src/services/ai/ai_aggregator.py:18` | Multi-timeframe LLM prompt payload |
| **Confluence MTF Contributor** | `5m`, `15m`, `1h`, `1d` | `src/services/confluence_engine.py:750` | Contributor 4 (8 pts max) consensus |
| **Technical Analysis** | `1m`, `5m`, `15m`, `1h`, `1d` | `src/models/market_data.py:8` | Indicator calculations & trend stacks |
| **Market REST API** | `1m`, `5m`, `15m`, `1h`, `1d` | `src/api/routes/market.py:56` | Historical & live candle queries |
| **Historical Database** | `1m`, `5m`, `15m`, `1h`, `4h`, `1d` | `historical_market_data.db` (`candles`) | Historical research & backtest archive |
| **Frontend UI Chart** | `5m`, `15m`, `1h`, `1d` | `frontend/src/app/page.tsx:91` | Interactive candlestick chart toggles |

---

## 5. DOCUMENTATION TIMEFRAME VERDICT

```text
CORE DECISION TIMEFRAMES:
5m, 15m, 1h, 1d

CORE MTF ALIGNMENT TIMEFRAMES:
5m, 15m, 1h, 1d

AI INPUT TIMEFRAMES:
5m, 15m, 1h, 1d

AUXILIARY / SUPPORTED TIMEFRAMES:
1m (Supported in API & Data Models)
4h (Archived in Historical DB table 'candles' only; not in live pipeline)
1w (Non-existent in codebase)
```

### Classification
**DOCUMENTATION REGRESSION**

### Forensic Rationale
During documentation cleanup, the text introduced claims that the core quartet was `15m, 1h, 4h, 1d` with auxiliary `5m, 1w`. This was inaccurate:
- In current source code, **`5m, 15m, 1h, 1d` is the 100% consistent, unanimous core quartet** across `DecisionService`, `AIAggregator`, `ConfluenceEngine`, and the Next.js `Frontend`.
- `4h` is purely archived data in SQLite.
- `1w` does not exist anywhere in code or database.

---

## 6. DIRECTION GATE LOGIC AUDIT

The apparent contradiction in the runtime report:
```text
Direction Gate: PASS
Net Score: -16.0
Threshold: |Net Score| >= 20.0
```
was traced through source code to determine why the gate passed.

### Actual Direction Gate Implementation
In `src/services/confluence_engine.py:330-336`:
```python
GATE_CONTRIBUTORS = {"HTF Trend", "Market Structure", "MTF Alignment"}

gate_bullish = sum(
    1 for c in contributors
    if c.name in GATE_CONTRIBUTORS and c.bias == "BULLISH"
)
gate_bearish = sum(
    1 for c in contributors
    if c.name in GATE_CONTRIBUTORS and c.bias == "BEARISH"
)
gate_passed = gate_bullish >= 2 or gate_bearish >= 2
gate_dir = "BULLISH" if gate_bullish >= 2 else ("BEARISH" if gate_bearish >= 2 else "NONE")
```

In `src/models/trading_decision.py:251-253`:
```python
gate_passed: Optional[bool] = Field(
    default=None,
    description="Whether the direction gate was satisfied (≥2 of HTF/Structure/MTF agree)"
)
gate_direction: Optional[str] = Field(
    default=None,
    description="Direction gate result: BULLISH | BEARISH | NONE"
)
```

### Forensic Discovery
1. **The Backend Direction Gate does NOT use `Net Score`**:
   The backend `gate_passed` boolean in `ConfluenceEngine` is strictly a **qualitative consensus gate**. It evaluates whether at least 2 of the 3 core gate contributors (`HTF Trend`, `Market Structure`, `MTF Alignment`) agree in bias. It has **no numerical net score threshold**.
2. **Where does `|Net Score| >= 20.0` actually live?**:
   In `src/services/signal_aggregator.py:61-357`:
   ```python
   DIRECTIONAL_THRESHOLD = 20.0  # Net score >= +20 -> BUY; <= -20 -> SELL; else WAIT
   net_score = pts1 + pts2 + pts3 + pts4
   ...
   if net_score >= DIRECTIONAL_THRESHOLD:
       final_dir = "BUY"
   elif net_score <= -DIRECTIONAL_THRESHOLD:
       final_dir = "SELL"
   else:
       final_dir = "WAIT"
   ```
   The `|Net Score| >= 20.0` rule is the **downstream multi-component directional threshold** of `SignalAggregator`, NOT the upstream `Direction Gate` of `ConfluenceEngine`!
3. **The Root of the Confusion**:
   The documentation and earlier reports conflated the two separate systems into an invented composite rule:
   `Requires |Net Score| >= 20.0 pts AND at least 2 of 3 core gate contributors agree`
   When the live snapshot was captured, `ConfluenceEngine` had 2 of 3 core contributors in agreement (`gate_passed: True`). Meanwhile, downstream `SignalAggregator` computed `net_score = -16.0`, which fell below $\pm 20.0$, causing `SignalAggregator` to output `WAIT`. The report author copied `-16.0` next to `Direction Gate: PASS`, creating an apparent contradiction.

---

## 7. NET SCORE FIELD LINEAGE

| Field Name | Subsystem / Producer | Value Range | Used For Direction Gate? | Exposed in API? | Displayed in Reports? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `gate_passed` | `ConfluenceEngine` | `True` / `False` | **YES (Sole Condition: $\ge 2$ agree)** | `TradingDecision.gate_passed` | Displayed as Gate Status |
| `gate_direction` | `ConfluenceEngine` | `BULLISH`/`BEARISH`/`NONE` | **YES (Consensus Direction)** | `TradingDecision.gate_direction` | Displayed as Gate Direction |
| `net_score` | `SignalAggregator` | $[-100.0, +100.0]$ | **NO** (Used for `OverallTradingSignal`) | In `overall_signal.reasons` | Misattributed to Direction Gate |
| `net_directional_score` | `ConfluenceEngine` (Doc) | $[-100.0, +100.0]$ | **NO** (Doc concept for Bull - Bear pts) | Calculated in documentation | Referenced in text |
| `total_score` | `TechnicalAnalysisService` | $[0.0, 1.0]$ | **NO** (Legacy normalized score) | `decision.composite_score` | Internal metric |
| `final_confluence` | `ConfluenceEngine` | $[0, 100]$ | **Used for Quality Gate ($\ge 58$)** | `TradingDecision.final_confluence`| Live Confluence Score |

---

## 8. SAME-SNAPSHOT DIRECTION GATE VERIFICATION

A live HTTP GET request was executed against `http://127.0.0.1:8000/api/v1/decision?symbol=BTC-USD`:

```json
{
  "symbol": "BTC-USD",
  "decision": "WAIT",
  "gate_passed": false,
  "gate_direction": "NONE",
  "final_confluence": 46,
  "overall_signal": {
    "signal": "BUY",
    "confidence": null,
    "evidence_score": null,
    "reasons": [
      "Synthesized BUY signal across 2/4 active components with Net Directional Score +51.0."
    ]
  }
}
```

### Observation
- At this moment, core contributors did not have 2-of-3 agreement, so `gate_passed == False` and `gate_direction == "NONE"`.
- Meanwhile, downstream `SignalAggregator` computed `Net Directional Score +51.0` across active components, which exceeds $\ge +20.0$, producing `overall_signal.signal = "BUY"`.
- This definitively proves that `gate_passed` (Direction Gate) and `Net Directional Score` (SignalAggregator) are completely distinct metrics evaluated by separate subsystems.

---

## 9. DIRECTION GATE VERDICT

```text
DIRECTION GATE CLASSIFICATION:
C. DOCUMENTATION ERROR (and B. NO BUG — THRESHOLD APPLIES TO DIFFERENT INTERNAL METRIC)
```

### Forensic Summary
- **Backend Bug**: **NO**. The backend code behaves 100% deterministically according to its source specification in `ConfluenceEngine.py:335`.
- **API Serialization Bug**: **NO**. Pydantic accurately serializes `gate_passed` and `gate_direction`.
- **Root Cause**: The documentation erroneously synthesized a composite gate definition by taking the `DIRECTIONAL_THRESHOLD = 20.0` from `SignalAggregator.py:61` and asserting that `ConfluenceEngine`'s Direction Gate required both conditions.

---

## 10. CANONICAL HISTORICAL RUN POLICY AUDIT

The canonical completed backtest run query added to `HistoricalEvidenceService._query_empirical_evidence()`:
```sql
SELECT br.run_id 
FROM backtest_runs br
JOIN backtest_reports rep ON br.run_id = rep.run_id
WHERE br.symbol = ? AND br.status = 'COMPLETED'
ORDER BY br.created_at DESC
LIMIT 1
```
was audited for long-term algorithmic safety.

---

## 11. CANONICAL METADATA SEARCH

An audit of SQLite table schemas in `historical_market_data.db` and source code was conducted:

### `backtest_runs` Columns
`['run_id', 'dataset_id', 'dataset_version', 'engine_version', 'symbol', 'config_json', 'status', 'progress_pct', 'current_step', 'error', 'created_at', 'started_at', 'completed_at', 'execution_time_seconds', 'total_signals_evaluated', 'total_trades_generated']`

### Findings
1. There is **no explicit canonical metadata column** (e.g. `is_canonical`, `is_baseline`, `is_official`, `approved`, `run_type`) in `backtest_runs` or `backtest_reports`.
2. The architecture does **NOT** define "latest completed" as inherently canonical.
3. On the current static database, the latest completed runs happen to be the authoritative full backtests (`RUN-BTC-USD-20260831-173607` with 1,032 signals, and `RUN-XAU-USD-20260831-174452` with 893 signals).

---

## 12. FUTURE EXPLORATORY RUN FIXTURE TEST

To test the future resilience of this query, an isolated in-memory SQLite fixture was created simulating a future researcher running an exploratory test run:
- **Baseline Full Run**: Created 2026-08-31 with N = 1,032 completed signals (`status = 'COMPLETED'`).
- **Future Exploratory Run**: Created 2026-09-15 with N = 20 test signals (`status = 'COMPLETED'`).

### Execution Result
```text
Executing query: ORDER BY br.created_at DESC LIMIT 1
Selected Run ID: RUN-BTC-USD-20260915-120000
Signals in selected run: 20
```

### Result Analysis
The current query selected the N = 20 exploratory run simply because its `created_at` timestamp was newer. The 1,032-signal canonical baseline was completely ignored.

---

## 13. CANONICAL POLICY VERDICT

```text
CANONICAL RUN POLICY CLASSIFICATION:
C. CURRENTLY CORRECT BUT FUTURE-FRAGILE
```

### Forensic Summary
- **Current Data Correctness**: On the current database, the query resolves the correct canonical baseline ($N=1,032$ for BTC, $N=893$ for XAU) and successfully eliminates developmental cross-run inflation.
- **Future Risk**: The policy is fragile. Any future exploratory backtest run with status `COMPLETED` will unintentionally hijack the historical baseline and shrink sample size $N$.
- **Recommendation for Future Hardening**: The resolver should either:
  1. Pin the canonical run IDs explicitly (or via configuration), or
  2. Order by `total_signals_evaluated DESC, created_at DESC`, or
  3. Require an explicit `is_canonical` / `dataset_version = 'CANONICAL_V1'` metadata filter.

---

## 14. REPAIR INTEGRITY RECHECK

Read-only confirmation of previous repairs:
- **MTF Alignment Scaling**: `round((dominant / total) * 8)` verified in source; 4/4 yields 8 pts, 3/4 yields 6 pts.
- **Historical Evidence Query**: Scoped by `run_id`, preventing multi-run cross-inflation on current data.
- **Database Immutability**:
  - `historical_signals`: 2,438 rows (0 deleted, 0 updated, 0 inserted).
  - `backtest_runs`: 53 rows (0 deleted, 0 updated, 0 inserted).
  - `backtest_reports`: 24 rows (0 deleted, 0 updated, 0 inserted).
- **Production Gating**: `DISABLED` (`PRODUCTION_GATING_BTC = False`, `PRODUCTION_GATING_XAU = False`).
- **Live Execution**: `DISABLED` (`LIVE_EXECUTION_ENABLED = False`).

---

## 15. PROTECTED HASHES

Recomputed SHA-256 hashes against baseline:

| File Path | Baseline SHA-256 | Current Verification SHA-256 | Status |
| :--- | :--- | :--- | :---: |
| `signal_records.json` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | **MATCH (BIT-FOR-BIT)** |
| `data/governance_forward_state.json` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | **MATCH (BIT-FOR-BIT)** |
| `data/gating_state.json` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | **MATCH (BIT-FOR-BIT)** |

---

## 16. GIT STATE

Current working tree verification:
- Tracked code and test files match the verified safe repair state.
- No new tracked files modified.
- No deletions or resets.
- Zero Git commits or pushes.

---

## 17. FINAL CLASSIFICATION TABLE

| Issue | Actual Truth | Classification | Severity | Fix Needed? |
| :--- | :--- | :--- | :---: | :---: |
| **Timeframe documentation** | Core quartet is strictly `5m, 15m, 1h, 1d` across all subsystems; `1m` is supported; `4h` is archived DB data only; `1w` does not exist. | **DOCUMENTATION REGRESSION** | **LOW** | **YES** (Doc text correction only) |
| **Direction Gate PASS + Net 16** | Direction Gate in `ConfluenceEngine` is strictly qualitative $\ge 2$ of 3 consensus with NO net score threshold. The 20.0 threshold belongs to downstream `SignalAggregator`. Backend code executed correctly. | **DOCUMENTATION ERROR** | **LOW** | **YES** (Doc clarification only) |
| **Latest-completed canonical policy** | Correct on current database ($N=1,032$ BTC, $N=893$ XAU), but fragile against future small exploratory backtests due to absence of canonical metadata column. | **CURRENTLY CORRECT BUT FUTURE-FRAGILE** | **MEDIUM** | **YES** (Add secondary ordering / pinning) |

---

## 18. FINAL POST-REPAIR VERDICT

```text
FINAL POST-REPAIR VERDICT

TIMEFRAME ISSUE:
DOCUMENTATION REGRESSION

DIRECTION GATE ISSUE:
DOCUMENTATION ERROR

CANONICAL RUN POLICY:
FUTURE-FRAGILE


SOURCE MODIFIED:
NO

FRONTEND MODIFIED:
NO

DATABASE MODIFIED:
NO

DOCUMENTATION MODIFIED:
NO

TESTS MODIFIED:
NO


PROTECTED STATE:
UNCHANGED

PRODUCTION GATING:
DISABLED

LIVE EXECUTION:
DISABLED


SAFE TO PERFORM FINAL TINY FIX:
YES

SAFE TO COMMIT AFTER TINY FIX:
YES
```
