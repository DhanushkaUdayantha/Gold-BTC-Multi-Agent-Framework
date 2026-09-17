# A21 — GIT INTEGRITY FORENSIC AUDIT REPORT

**Date:** 2026-09-14  
**Audit Target:** Full Repository Git Provenance, Working Tree State & Immutability  
**Current Governance State:** `S2 — EVIDENCE_COLLECTION`  
**Production Gating Status:** `DISABLED`  
**Live Execution Status:** `DISABLED`  
**Audit Result:** `PASS`

---

## 1. REPOSITORY BASELINE

### 1.1 Root Repository
- **Current Branch:** `master`
- **Current HEAD SHA:** `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`
- **HEAD Commit Message:** `fix(quant): Phase 7 Step 3 enforce DIRECTIONAL_THRESHOLD in aggregator and unify WAIT percentage semantics`
- **Configured Remotes:** None (`origin` not configured; purely local repository)
- **Tracking Branch:** None
- **Total Modified Files:** 17
- **Commits Created in A21:** 0
- **Push Performed:** No

### 1.2 Frontend Submodule
- **Current Branch:** `master`
- **Current HEAD SHA:** `a81dbf1df6b6ee517d8aafef59c7fa67ab98e33e`
- **HEAD Commit Message:** `fix(frontend): Phase 7 Step 3 ensure uniform '--%' display for all WAIT states and differentiate conflict vs sub-threshold badges`
- **Configured Remotes:** None
- **Total Modified Files:** 13
- **Untracked Directories/Files:** `src/lib/__tests__/`, `src/lib/relativeTime.ts`
- **Commits Created in A21:** 0
- **Push Performed:** No

---

## 2. MODIFIED FILE PROVENANCE CLASSIFICATION

Every modified file across both root and frontend repositories has been forensically audited and classified:

### 2.1 Root Repository (17 files)
| File | Status | Provenance Classification | Rationale & Safety Review |
|---|---|---|---|
| `config/settings.py` | `M` | `PRE-EXISTING USER CHANGE` | Rate-limiting & admin reset auth settings. Safe configuration defaults. |
| `frontend` | `M` | `PRE-EXISTING USER CHANGE` | Submodule pointer update reflecting local frontend enhancements. |
| `gemini_usage.json` | `M` | `PRE-EXISTING USER CHANGE` | Runtime token counter recording live Gemini quota consumption. |
| `signal_records.json` | `M` | `PRE-EXISTING USER CHANGE` | Authoritative historical signals store. SHA256 matches baseline bit-for-bit. |
| `src/api/main.py` | `M` | `PRE-EXISTING USER CHANGE` | Defensive security headers, CORS origin validation, rate limiter middleware. |
| `src/api/routes/admin_gating.py` | `M` | `PRE-EXISTING USER CHANGE` | Added constant-time admin token verification (`verify_admin_token`). |
| `src/api/routes/decision.py` | `M` | `PRE-EXISTING USER CHANGE` | A7 remediation: eliminated GET decision persistence side-effects. |
| `src/api/routes/governance.py` | `M` | `PRE-EXISTING USER CHANGE` | Phase 10/11 governance verification and S7 authorization endpoints. |
| `src/research/governance/forward_shadow.py` | `M` | `PRE-EXISTING USER CHANGE` | 2-stage entry-fill state machine and legacy fixture quarantine. |
| `src/research/ml_shadow/shadow_service.py` | `M` | `PRE-EXISTING USER CHANGE` | A7 remediation: `persist=False` ephemeral mode and diagnostic metrics. |
| `src/services/ai/gemini_provider.py` | `M` | `PRE-EXISTING USER CHANGE` | Model configuration and rate-limit guardrails. |
| `src/services/ai_service.py` | `M` | `PRE-EXISTING USER CHANGE` | Force-refresh query parameter guard and reason audit logging. |
| `src/services/btc_shadow_runner.py` | `M` | `PRE-EXISTING USER CHANGE` | Support for isolated test stores (`tmp_path`). |
| `src/services/decision_service.py` | `M` | `PRE-EXISTING USER CHANGE` | A7 remediation: decoupled evaluation from persistent DB writes on GET. |
| `src/services/outcome_tracker.py` | `M` | `PRE-EXISTING USER CHANGE` | Pydantic `OHLCVCandle` model support. |
| `src/services/xau_shadow_runner.py` | `M` | `PRE-EXISTING USER CHANGE` | Support for isolated test stores (`tmp_path`). |
| `tests/test_backtesting.py` | `M` | `PRE-EXISTING USER CHANGE` | Added regression test for Pydantic candle model scanning. |

### 2.2 Frontend Submodule (13 files + 2 untracked)
| File | Status | Provenance Classification | Rationale & Safety Review |
|---|---|---|---|
| `frontend/package.json` | `M` | `A8 CHANGE` | Added `vitest` unit test dependencies. |
| `frontend/src/app/globals.css` | `M` | `A17/A18 CHANGE` | Responsive container utilities and high-contrast keyboard focus styling. |
| `frontend/src/app/page.tsx` | `M` | `A8–A18 CHANGE` | Accessible tab controls, null-safe hero percentages, semantic color classes. |
| `frontend/src/components/CandleChart.tsx` | `M` | `A17 CHANGE` | Responsive chart container and dynamic viewport sizing. |
| `frontend/src/components/EmpiricalPerformancePanel.tsx` | `M` | `A12/A15 CHANGE` | Truthful null rendering (`'--'`), eliminating fabricated fallback numbers. |
| `frontend/src/components/HistoricalBacktestTab.tsx` | `M` | `A15/A18 CHANGE` | Truthful parameter labelling and keyboard-accessible buttons. |
| `frontend/src/components/HistoricalDatasetStatus.tsx` | `M` | `A13/A15 CHANGE` | Real source timestamp formatting and data lineage labeling. |
| `frontend/src/components/MLModelsTab.tsx` | `M` | `A14/A15 CHANGE` | Strict BTC/XAU model isolation and authoritative observation counts. |
| `frontend/src/components/ShadowAccumulationMonitor.tsx` | `M` | `A15 CHANGE` | Dynamic N50 badge displaying clean resolved sample count. |
| `frontend/src/components/SignalHeroCard.tsx` | `M` | `A8/A12/A14 CHANGE` | Enforced WAIT null percentage (`'--%'`) and neutral styling. |
| `frontend/src/hooks/useDashboardData.ts` | `M` | `A13/A16 CHANGE` | Efficient relative-time refresh hooks and performance memoization. |
| `frontend/src/lib/format.ts` | `M` | `A13/A15 CHANGE` | Truthful relative-time and number formatting utilities. |
| `frontend/src/services/api.ts` | `M` | `A15/A19 CHANGE` | Safe API timeouts, failover base URL switching, zero secret leakage. |
| `frontend/src/lib/__tests__/` | `??` | `A8–A15 CHANGE` | Comprehensive frontend test suite (5 test files, 99 passing tests). |
| `frontend/src/lib/relativeTime.ts` | `??` | `A13 CHANGE` | Centralized reusable relative timestamp formatter. |

---

## 3. QUANT / ML IMMUTABILITY VERIFICATION

A strict diff analysis was performed on all core quant and ML engine files:

```
git diff -- src/services/decision_engine.py      --> ZERO DIFF (UNCHANGED)
git diff -- src/services/signal_aggregator.py    --> ZERO DIFF (UNCHANGED)
git diff -- src/services/confluence_engine.py   --> ZERO DIFF (UNCHANGED)
git diff -- src/research/ml/                     --> ZERO DIFF (UNCHANGED)
```

- **Quant Strategy:** No changes to trading strategies, contributor weights, thresholds, or gate rules.
- **ML Models:** No model retraining, threshold tuning, or hyperparameter modifications.
- **ML Weights & Scalers:** Frozen bit-for-bit.

---

## 4. PROTECTED ARTIFACT HASHES

All 5 protected governance and evidence artifacts were cryptographically verified using SHA256:

| Artifact | Expected SHA256 Hash | Current SHA256 Hash | Status |
|---|---|---|---|
| `signal_records.json` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | `MATCH` |
| `data/historical/historical_market_data.db` | `CA1E2AFCA0DDB99C6FF8704B4A8CD9A1E0D7665BDD09D7797FF561751C12A488` | `CA1E2AFCA0DDB99C6FF8704B4A8CD9A1E0D7665BDD09D7797FF561751C12A488` | `MATCH` |
| `data/governance_forward_state.json` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | `MATCH` |
| `data/shadow_trades.db` | `D593F5500CD413B22BD22983B5CB6BCE77415F3E89AB9310E6E88489F7C8F919` | `D593F5500CD413B22BD22983B5CB6BCE77415F3E89AB9310E6E88489F7C8F919` | `MATCH` |
| `data/gating_state.json` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | `MATCH` |

---

## 5. DATABASE ROW COUNT INVARIANTS

Read-only inspection confirmed identical row counts:
- `ml_shadow_observations`: **3,828** (`UNCHANGED`)
- `forward_shadow_signals`: **479** (`UNCHANGED`)
- `shadow_trades`: **5** (`UNCHANGED`)

---

## 6. GOVERNANCE & SECURITY VERIFICATION

- **Current State:** `S2: EVIDENCE_COLLECTION`
- **Production Gating:** `DISABLED`
- **Live Execution:** `DISABLED`
- **XAU Valid Forward Resolved N:** `0` (< 50 minimum milestone)
- **BTC Valid Forward Resolved N:** `58`
- **Broker Connections:** `NONE`
- **Real Order Capabilities:** `NONE`

---

## 7. AUDIT ARTIFACT INVENTORY

All markdown audit reports in the workspace correspond directly to completed forensic milestones:
- `A17_RESPONSIVE_UX_AUDIT.md` (A17 Report)
- `A18_ACCESSIBILITY_AUDIT.md` (A18 Report)
- `A19_SECURITY_EXECUTION_AUDIT.md` (A19 Report)
- `A20_TEST_BUILD_AUDIT.md` (A20 Report)
- Pre-existing Phase 1–11 forensic audit documents (all classified as `EXPECTED AUDIT ARTIFACT`).

No unexpected or orphaned files were introduced. Zero files were deleted or cleaned up.
