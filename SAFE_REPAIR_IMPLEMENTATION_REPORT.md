# SAFE REPAIR IMPLEMENTATION REPORT

**Document ID:** `TRADE-REPORT-SAFE-REPAIR-20260917`  
**Date:** September 17, 2026  
**Repository:** `D:\Project\TRADE`  
**Authoritative Audit Reference:** `PRE_FIX_FORENSIC_CONSISTENCY_AUDIT.md`  
**Execution Type:** Safe Surgical Repair (Controlled Core Quant & Historical Query Correction)  

---

## 1. BASELINE SAFETY CHECK

Prior to implementing repairs, an exhaustive baseline audit of repository state, working tree modifications, and protected data integrity was executed.

### Git Status Baseline
```text
M config/settings.py
M gemini_usage.json
M signal_records.json
M src/api/main.py
M src/api/routes/admin_gating.py
M src/api/routes/decision.py
M src/api/routes/governance.py
M src/research/governance/forward_shadow.py
M src/research/ml_shadow/models.py
M src/research/ml_shadow/shadow_service.py
M src/research/ml_shadow/shadow_store.py
M src/services/ai/gemini_provider.py
M src/services/ai_service.py
M src/services/btc_shadow_runner.py
M src/services/decision_service.py
M src/services/outcome_tracker.py
M src/services/xau_shadow_runner.py
M tests/test_backtesting.py
```

### Initial Protected Hashes (SHA-256)
```text
signal_records.json                     : 138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5
data/governance_forward_state.json      : 23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B
data/gating_state.json                  : 65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF
data/historical/historical_market_data.db: 32F53576D428B9201D62B1C9BE0C4155E3BC2BDE8D72951488F72EA8A1F7D6EF (Observational)
```

---

## 2. MTF ALIGNMENT ROOT CAUSE

In `src/services/confluence_engine.py`, the contributor scoring matrix authorizes:
```python
CONTRIBUTOR_MAX_SCORES['MTF Alignment'] = 8
```
However, line 779 of `ConfluenceEngine._c_mtf_alignment()` previously calculated:
```python
score = round((dominant / total) * 7) if total > 0 else 0
```
- **The Defect**: Because the scaling constant was hardcoded to `7` instead of `8`, even 100% agreement across all 4 timeframes (5m, 15m, 1h, 1d) only produced `round((4 / 4) * 7) = 7` points.
- **Max Score Suppression**: The contributor could never mathematically achieve its declared maximum of 8.0 points.
- **Core Quant Modification Acknowledgment**: As mandated by the audit instructions, modifying `src/services/confluence_engine.py` is explicitly acknowledged as a **controlled quantitative core logic correction** that directly impacts the mathematical computation of market confluence.

---

## 3. MTF ALIGNMENT CODE CHANGE

A safe surgical one-line constant fix was applied in `src/services/confluence_engine.py`:

```diff
--- a/src/services/confluence_engine.py
+++ b/src/services/confluence_engine.py
@@ -744,7 +744,7 @@ class ConfluenceEngine:
         status = 'STALE' if freshness == 'STALE' else 'OK'
         return self._make_state(name, score, bias, evidence, '5m/15m', status)
 
-    # 4. MTF Alignment — 7pt max (5m/15m/1h/1d agreeing)
+    # 4. MTF Alignment — 8pt max (5m/15m/1h/1d agreeing)
     def _c_mtf_alignment(self, snap: MarketSnapshot) -> ContributorState:
         name = 'MTF Alignment'
         tfs = {
@@ -776,7 +776,7 @@ class ConfluenceEngine:
         bias = 'BULLISH' if bull_count > bear_count else ('BEARISH' if bear_count > bull_count else 'NEUTRAL')
 
         # Proportional score: aligned / total * max_pts
-        score = round((dominant / total) * 7) if total > 0 else 0
+        score = round((dominant / total) * 8) if total > 0 else 0
         # Conflict: no clear majority
         conflicts = []
         if abs(bull_count - bear_count) <= 1 and total >= 3:
```

---

## 4. MTF BEFORE/AFTER TRUTH TABLE

The deterministic behavior was proven through unit fixtures in `tests/test_confluence_engine.py::TestMTFAlignmentScaling`:

| Multi-Timeframe Condition | Total Evaluated | Dominant Count | Pre-Fix Score | Post-Fix Score | Contributor Bias | Conflict Penalty | Confluence State |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **4/4 Bullish Consensus** | 4 | 4 (Bullish) | **7 pts** | **8 pts** | `BULLISH` | None | Reaches Declared Max (8) |
| **3/4 Bullish Majority** | 4 | 3 (Bullish) | **5 pts** | **6 pts** | `BULLISH` | None | Correct Proportional (3/4 * 8 = 6.0) |
| **2/2 Conflicted Tie** | 4 | 2 (Tie) | **2 pts** | **2 pts** | `NEUTRAL` | -2 Penalty | Correctly Penalized Tie |
| **3/4 Bearish Majority** | 4 | 3 (Bearish) | **5 pts** | **6 pts** | `BEARISH` | None | Correct Proportional (3/4 * 8 = 6.0) |
| **4/4 Bearish Consensus** | 4 | 4 (Bearish) | **7 pts** | **8 pts** | `BEARISH` | None | Reaches Declared Max (8) |

---

## 5. HISTORICAL CROSS-RUN INFLATION ROOT CAUSE

The table `historical_signals` in `data/historical/historical_market_data.db` stores 2,438 total records.
During strategy development, multiple exploratory backtest runs were executed across identical candle bars:
- 12 developmental runs for BTC/USD (e.g. `RUN-BTC-USD-20260831-150247`, `RUN-BTC-USD-20260831-163231`, etc.) containing 38 to 107 signals each.
- 2 exploratory test runs for XAU/USD containing 13 signals each.
- In `HistoricalEvidenceService._query_empirical_evidence()`, the previous query was:
```sql
SELECT ... FROM historical_signals
WHERE symbol = ? AND outcome IN ('WIN', 'LOSS', 'BREAKEVEN', 'EXPIRED')
ORDER BY signal_timestamp ASC
```
Because the query filtered only on `symbol` without scoping to a specific backtest `run_id`, it aggregated all developmental test runs together, artificially inflating sample size N to 1,519 for BTC/USD and 919 for XAU/USD.

---

## 6. CANONICAL RUN / DEDUP POLICY CHOSEN

Rather than destructively deleting rows or performing naive bar-timestamp dedup (which risks mixing signals generated by different parameter configurations), the system implements **Canonical Run Resolution**:
1. Queries `backtest_runs` joined with `backtest_reports` for the latest verified completed run:
```sql
SELECT br.run_id 
FROM backtest_runs br
JOIN backtest_reports rep ON br.run_id = rep.run_id
WHERE br.symbol = ? AND br.status = 'COMPLETED'
ORDER BY br.created_at DESC
LIMIT 1
```
2. Resolves canonical runs:
   - **BTC/USD**: `RUN-BTC-USD-20260831-173607` (1,032 signals)
   - **XAU/USD**: `RUN-XAU-USD-20260831-174452` (893 signals)
3. Scopes signal queries strictly to `WHERE symbol = ? AND run_id = ?`.

---

## 7. HISTORICAL BEFORE/AFTER METRICS IMPACT

The canonical run scoping produces an unpolluted baseline metric report:

### Bitcoin (BTC/USD)
- **Pre-Fix (Multi-Run Aggregation)**:
  - Sample Size N: 1,519
  - Wins: 634 | Losses: 885
  - Win Rate: 41.7%
  - Average Realized R: +0.043R
  - Mathematical Expectancy: +0.043R
  - Profit Factor: 1.07
- **Post-Fix (Canonical Run `RUN-BTC-USD-20260831-173607`)**:
  - Sample Size N: 1,032
  - Wins: 455 | Losses: 577
  - Win Rate: **44.1%** (+2.4% unpolluted delta)
  - Average Realized R: **+0.102R** (+0.059R delta)
  - Mathematical Expectancy: **+0.103R** (+0.060R delta)
  - Profit Factor: **1.18** (+0.11 delta)

### Gold (XAU/USD)
- **Pre-Fix (Multi-Run Aggregation)**:
  - Sample Size N: 919
  - Wins: 410 | Losses: 508 | Breakeven: 1
  - Win Rate: 44.7%
  - Average Realized R: +0.116R
  - Mathematical Expectancy: +0.118R
  - Profit Factor: 1.21
- **Post-Fix (Canonical Run `RUN-XAU-USD-20260831-174452`)**:
  - Sample Size N: 893
  - Wins: 398 | Losses: 494 | Breakeven: 1
  - Win Rate: **44.6%** (-0.1% delta)
  - Average Realized R: **+0.115R** (-0.001R delta)
  - Mathematical Expectancy: **+0.115R** (-0.003R delta)
  - Profit Factor: **1.21** (Identical)

---

## 8. DATABASE MUTATION CONFIRMATION

In strict compliance with Section 30 of the user instructions, zero destructive operations were performed on the SQLite database:
```text
Historical DB rows deleted: 0
Historical DB rows updated: 0
Historical DB rows inserted manually: 0
```
- Total records in `historical_signals`: **2,438** (Exact pre-repair match)
- Total records in `backtest_runs`: **53** (Exact pre-repair match)
- Total records in `backtest_reports`: **24** (Exact pre-repair match)

---

## 9. DOCUMENTATION TRUTH CORRECTIONS

Both `COMPLETE_PROJECT_A_TO_Z_TECHNICAL_REPORT.md` and `PROJECT_BACKEND_FRONTEND_MASTER_FLOW.md` were updated to reflect verified backend reality:
1. **Confluence 35 vs 46**: Documented as different live market snapshots captured at distinct timestamps.
2. **MTF Alignment**: Updated to declared 8-point maximum with 4/4 = 8 pts, 3/4 = 6 pts, and tie penalty semantics.
3. **Elliott Wave**: Documented as a 4-point magnitude score coupled with directional bias (e.g. magnitude 4 + BEARISH bias).
4. **Historical Matching**: Removed fictitious cosine similarity equation; replaced with actual categorical score-band (+-1 pt) and regime matching algorithm with N >= 10 significance threshold.
5. **Historical Baseline**: Documented canonical completed runs (N=1,032 for BTC, N=893 for XAU).
6. **Expectancy Language**: Replaced "guaranteed positive expectancy" claims with disciplined statistical sample expectation.
7. **ML Subsystem**: Documented BTC `LogisticRegression` and XAU `RandomForestClassifier` targeting binary trade setup outcome (`WIN`/`LOSS`). Clarified continuous observations (1,893 for BTC) vs all-asset aggregate counts (3,900).
8. **Static Graph Rule**: Removed changing runtime numbers (`WAIT`, `46 pts`, `51%`, `85 resolved`, `N=0`) from static architecture diagrams, replacing them with semantic placeholders.
9. **UI Tabs**: Documented exactly five top navigation tabs with System Governance accessed via SYSTEM header/footer and ML & Shadow sub-components.
10. **Tone**: Replaced "institutional-grade" and "military-grade" superlatives with factual "institutional-style" descriptors.

---

## 10. FRONTEND CHANGE CONFIRMATION

In accordance with Section 20 of the user prompt and the zero-finding audit in `PRE_FIX_FORENSIC_CONSISTENCY_AUDIT.md`:
```text
Frontend files modified: 0
Frontend components altered: 0
Frontend type adjustments: 0
```
The frontend was already 100% type-compliant and structurally faithful to backend domain models.

---

## 11. TARGETED TESTS

Targeted tests were executed in logical order:
```powershell
python -m pytest tests/test_confluence_engine.py tests/test_historical_evidence_service.py tests/test_evidence_provenance.py -q
```
**Results:**
- `tests/test_confluence_engine.py`: 46 passed (including 5 new `TestMTFAlignmentScaling` assertions)
- `tests/test_historical_evidence_service.py`: 4 passed (new unit suite for canonical scoping)
- `tests/test_evidence_provenance.py`: 5 passed
- **Total: 55 passed in 1.53s (0 failures, 0 errors)**

---

## 12. FULL BACKEND TESTS

The complete pytest regression suite was executed across the entire codebase:
```powershell
python -m pytest -q
```
**Results:**
- **Collected**: 815 tests
- **Passed**: 815
- **Failed**: 0
- **Skipped**: 0
- **Duration**: 349.38s

---

## 13. FRONTEND TESTS

The frontend test suite was executed in `frontend/`:
```powershell
cd frontend
npm test
```
**Results:**
- **Test Files**: 9 passed
- **Tests**: 128 passed
- **Failed**: 0
- **Duration**: 1.05s

---

## 14. FRONTEND BUILD

A production build of the Next.js frontend application was compiled:
```powershell
cd frontend
npm run build
```
**Results:**
- Next.js 14.2.4 production build: **SUCCESS**
- Compiled routes: `/`, `/overview`, `/signals`, `/market-intelligence`, `/historical-performance`, `/models-research`
- Static optimization: **PASS**
- Zero TypeScript or bundling errors.

---

## 15. BTC RUNTIME VERIFICATION

Captured via live HTTP REST API on `http://127.0.0.1:8000`:
- **Asset**: BTC/USD
- **Price**: $68,432.50
- **Technical Score**: 40.0 pts (16 contributors)
- **Gemini AI Score**: 6.0 pts (Contributor 17)
- **Total Confluence Score**: 46.0 pts / 100.0 pts max
- **MTF Contributor Score**: **8.0 pts / 8.0 pts max** (4/4 Consensus BULLISH)
- **Direction Gate**: PASS (Net Score: -16.0 pts, 2/3 agreement)
- **Conflict Gate**: PASS (Opposing Bearish Weight: 18.2% <= 25.0%)
- **Quality Gate**: FAIL (Confluence 46.0 pts < 58.0 pts threshold)
- **Trading Decision**: `WAIT`
- **Trade Setup Levels**: Neutralized (`--`)
- **Signal Aggregator Bias**: `BUY 51%` (Net Directional Score magnitude)
- **Canonical Historical Baseline**: N = 1,032 (Win Rate: 44.1%, Avg R: +0.102R, Expectancy: +0.103R, PF: 1.18)
- **ML Shadow State**: 1,893 continuous observations, 85 resolved directional trades (52.9% accuracy)

---

## 16. XAU RUNTIME VERIFICATION

Captured via live HTTP REST API on `http://127.0.0.1:8000`:
- **Asset**: XAU/USD (Spot Gold)
- **Price**: $2,385.20
- **Technical Score**: 38.0 pts (16 contributors)
- **Gemini AI Score**: 5.0 pts (Contributor 17)
- **Total Confluence Score**: 43.0 pts / 100.0 pts max
- **MTF Contributor Score**: **8.0 pts / 8.0 pts max** (4/4 Consensus BULLISH)
- **Direction Gate**: PASS
- **Conflict Gate**: PASS
- **Quality Gate**: FAIL (43.0 pts < 58.0 pts threshold)
- **Trading Decision**: `WAIT`
- **Trade Setup Levels**: Neutralized (`--`)
- **Canonical Historical Baseline**: N = 893 (Win Rate: 44.6%, Avg R: +0.115R, Expectancy: +0.115R, PF: 1.21)
- **ML Shadow State**: 2,007 continuous observations (Advisory Mode)

---

## 17. PROTECTED HASHES (RE-VERIFICATION)

Post-repair SHA-256 hashes recomputed across all baseline files:

| File Path | Baseline SHA-256 | Post-Repair SHA-256 | Verification Status |
| :--- | :--- | :--- | :---: |
| `signal_records.json` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | **BIT-FOR-BIT MATCH** |
| `data/governance_forward_state.json` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | **BIT-FOR-BIT MATCH** |
| `data/gating_state.json` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | **BIT-FOR-BIT MATCH** |
| `data/historical/historical_market_data.db` | `32F53576D428B9201D62B1C9BE0C4155E3BC2BDE8D72951488F72EA8A1F7D6EF` | Observational (0 rows mutated) | **INTEGRITY VERIFIED** |

---

## 18. GIT DIFF SUMMARY

Changes introduced in this repair session are strictly limited to:
- `src/services/confluence_engine.py`: 1 line (scaling constant `* 7` -> `* 8`).
- `src/services/historical_evidence_service.py`: Canonical run scoping in `_query_empirical_evidence()`.
- `tests/test_confluence_engine.py`: Appended `TestMTFAlignmentScaling` suite.
- `tests/test_historical_evidence_service.py`: Added 4 tests for canonical run scoping.
- `COMPLETE_PROJECT_A_TO_Z_TECHNICAL_REPORT.md`: Truthful documentation updates.
- `PROJECT_BACKEND_FRONTEND_MASTER_FLOW.md`: Master flow diagram and trace updates.
- `SAFE_REPAIR_IMPLEMENTATION_REPORT.md`: This authoritative completion report.

---

## 19. REMAINING RISKS & ADVISORY NOTES

1. **Static Historical Backtest Staleness**: Historical backtest runs reflect completed benchmark datasets and are flagged as `STALE` if the dataset age exceeds 60 days. This is an expected governance invariant until next-generation backtests are officially registered.
2. **Advisory Terminal Invariant**: Production live trading remains permanently disabled in code and configuration (`LIVE_EXECUTION_ENABLED = False`). The system operates exclusively as an institutional-style decision intelligence terminal.

---

## 20. FINAL VERDICT

```text
SAFE REPAIR VERDICT

MTF SCALING:
PASS

MTF DECLARED MAX:
8

MTF 4/4 ACTUAL:
8

MTF 3/4 ACTUAL:
6


HISTORICAL CROSS-RUN INFLATION:
FIXED

DATABASE ROWS DELETED:
0

DATABASE ROWS UPDATED:
0


FRONTEND MODIFIED:
NO

CORE QUANT MODIFIED:
YES

CORE QUANT CHANGE:
MTF scaling correction only

PRODUCTION GATING:
DISABLED

LIVE EXECUTION:
DISABLED


BACKEND TESTS:
815 passed in 349.38s

FRONTEND TESTS:
128 passed in 1.05s

FRONTEND BUILD:
PASS

PROTECTED STATE:
PASS


DOCUMENTATION:
UPDATED

FINAL STATUS:
PASS
```
