# Project Cleanup Plan & Comprehensive Audit Inventory

**Repository**: `D:/Project/TRADE`  
**Audit Date**: September 11, 2026  
**Status**: INVENTORY & AUDIT ONLY — ZERO DELETIONS PERFORMED  
**Working Tree State**: Clean / Frozen (`master` @ `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`)  

---

## 1. Project Size Before Cleanup
* **Total Size (Bytes)**: `4,343,259,669 bytes`
* **Total Size (Megabytes)**: `4,142.06 MB`
* **Total Size (Gigabytes)**: `4.05 GB`

---

## 2. Total File Count Before Cleanup
* **Total Files**: `43,778` files

---

## 3. Total Directory Count Before Cleanup
* **Total Directories**: `4,175` directories

---

## 4. Top 20 Largest Files

| Rank | Path | Size (Bytes) | Size (MB) | Category & Role |
|:---:|:---|---:|---:|:---|
| 1 | `data/historical/historical_market_data.db` | 2,156,617,728 | 2,056.71 MB | `REQUIRED DATA` (Protected canonical SQLite database) |
| 2 | `New folder/xauusd_2018_2026.csv` | 220,476,944 | 210.26 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 3 | `.git/objects/ec/tmp_obj_NEVWGx` | 161,562,624 | 154.08 MB | `REQUIRED DEVELOPMENT` (Git pack/object loose buffer) |
| 4 | `frontend/node_modules/@next/swc-win32-x64-msvc/next-swc.win32-x64-msvc.node` | 135,786,496 | 129.50 MB | `REQUIRED DEVELOPMENT` (Next.js native compiler binary) |
| 5 | `.git/objects/ce/6499ebfe2764be4a8d64376362c762dad104d9` | 72,523,150 | 69.16 MB | `REQUIRED DEVELOPMENT` (Git history object) |
| 6 | `New folder/btc_usdt_binance_2025.csv` | 45,109,908 | 43.02 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 7 | `New folder/btc_usdt_binance_2021.csv` | 44,523,675 | 42.46 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 8 | `New folder/btc_usdt_binance_2022.csv` | 44,416,831 | 42.36 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 9 | `New folder/btc_usdt_binance_2023.csv` | 44,219,120 | 42.17 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 10 | `New folder/btc_usdt_binance_2024.csv` | 43,997,888 | 41.96 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 11 | `New folder/btc_usdt_binance_2020.csv` | 43,630,099 | 41.61 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 12 | `New folder/btc_usdt_binance_2019.csv` | 42,821,811 | 40.84 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 13 | `New folder/btc_usdt_binance_2018.csv` | 42,219,469 | 40.26 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 14 | `frontend/.next/cache/webpack/server-production/8.pack` | 36,333,079 | 34.65 MB | `CACHE/TEMPORARY` (Next.js webpack build cache) |
| 15 | `frontend/.next/cache/webpack/client-production/0.pack` | 22,055,846 | 21.03 MB | `CACHE/TEMPORARY` (Next.js webpack build cache) |
| 16 | `New folder/btc_usdt_binance_2026.csv` | 21,747,143 | 20.74 MB | `GENERATED/RECREATABLE` / Raw 1m Kaggle CSV (Ingested) |
| 17 | `.venv/Lib/site-packages/numpy.libs/libscipy_openblas64_-327b2e0bcffce2882e0dc04cdeb4eaa6.dll` | 20,495,360 | 19.55 MB | `REQUIRED DEVELOPMENT` (Numpy native OpenBLAS DLL) |
| 18 | `.venv/Lib/site-packages/scipy.libs/libscipy_openblas-197ee2fc9b4d071f7e048078cac74115.dll` | 20,262,912 | 19.32 MB | `REQUIRED DEVELOPMENT` (Scipy native OpenBLAS DLL) |
| 19 | `frontend/.next/cache/webpack/client-production/18.pack` | 16,495,682 | 15.73 MB | `CACHE/TEMPORARY` (Next.js webpack build cache) |
| 20 | `frontend/.next/cache/webpack/client-production/3.pack` | 16,190,355 | 15.44 MB | `CACHE/TEMPORARY` (Next.js webpack build cache) |

---

## 5. Top 20 Largest Directories

| Rank | Directory Path | Size (Bytes) | Size (MB) | Role / Purpose |
|:---:|:---|---:|---:|:---|
| 1 | `data` | 2,159,519,664 | 2,059.48 MB | Canonical runtime market databases, shadow signals, audit logs |
| 2 | `data/historical` | 2,156,650,496 | 2,056.74 MB | Historical market data database (`historical_market_data.db`) |
| 3 | `frontend` | 863,052,071 | 823.07 MB | Next.js frontend application root |
| 4 | `New folder` | 593,232,254 | 565.75 MB | Raw Kaggle 1m CSV import data 2018-2026 |
| 5 | `frontend/.next` | 501,802,755 | 478.56 MB | Next.js compilation artifacts and cache |
| 6 | `frontend/.next/cache` | 499,331,943 | 476.20 MB | Next.js build cache (webpack compilation packs) |
| 7 | `frontend/.next/cache/webpack` | 499,198,071 | 476.07 MB | Next.js Webpack cache |
| 8 | `.venv` | 363,606,347 | 346.76 MB | Python virtual environment |
| 9 | `.venv/Lib/site-packages` | 361,114,071 | 344.39 MB | Python 3rd-party installed wheels |
| 10 | `.venv/Lib` | 361,114,071 | 344.39 MB | Python virtual env libraries |
| 11 | `frontend/node_modules` | 359,178,304 | 342.54 MB | Node.js npm packages |
| 12 | `.git` | 354,596,628 | 338.17 MB | Git version control repository database |
| 13 | `.git/objects` | 354,508,976 | 338.09 MB | Git committed object store |
| 14 | `frontend/.next/cache/webpack/client-production` | 241,685,147 | 230.49 MB | Webpack client production cache packs |
| 15 | `frontend/.next/cache/webpack/server-production` | 175,532,226 | 167.40 MB | Webpack server production cache packs |
| 16 | `.git/objects/ec` | 161,572,335 | 154.09 MB | Git pack object shard |
| 17 | `frontend/node_modules/@next` | 135,877,368 | 129.58 MB | Next.js internal compiler binaries |
| 18 | `frontend/node_modules/@next/swc-win32-x64-msvc` | 135,787,017 | 129.50 MB | Next.js SWC rust binary for Windows |
| 19 | `.venv/Lib/site-packages/scipy` | 114,981,389 | 109.65 MB | Scipy scientific compute library |
| 20 | `frontend/node_modules/next` | 86,194,941 | 82.20 MB | Next.js core framework package |

---

## 6. Category Definitions

1. **`REQUIRED RUNTIME`**: Essential backend application code, API routes, models, services, configuration files, trained ML inference weights, frontend UI components, and static client assets needed for the system to boot and operate.
2. **`REQUIRED DEVELOPMENT`**: Files required to develop, build, package, or commit the project (e.g. `.git`, `.venv`, `node_modules`, `package.json`, `requirements.txt`, launch scripts `run.bat`/`run.ps1`).
3. **`REQUIRED TESTING`**: Test suites, test runners, pytest configuration (`pytest.ini`), test fixtures, and CLI test verification utilities (`test_ai_cli.py`, etc.).
4. **`REQUIRED DATA`**: Canonical operational databases, forward shadow databases, state machine persistence files, and seed fixture ledgers (`data/historical/historical_market_data.db`, `data/forward_shadow_signals.db`, `data/governance_forward_state.json`, `ote_trades.json`).
5. **`REQUIRED GOVERNANCE/AUDIT`**: Immutable evidence logs, forensic audit reports, leakage audits, Phase 1-14 verification documents, drift tracking logs, and shadow validation records.
6. **`DOCUMENTATION`**: Markdown architecture specifications, data flow diagrams, methodology references, and repository readmes (`docs/`, `README.md`).
7. **`OPTIONAL`**: Valid scripts or utilities that are not executed during standard runtime or continuous testing, but provide manual batch capabilities (e.g. `run_historical_learning.py`).
8. **`GENERATED/RECREATABLE`**: Output files that can be deterministically reproduced from source code or source databases (e.g. active Next.js build output in `frontend/.next/server/`, or raw CSVs in `New folder/` whose rows are already fully ingested into SQLite).
9. **`CACHE/TEMPORARY`**: Temporary compilation artifacts, webpack caches, Python bytecode (`.pyc`), and test caches (`.pytest_cache`) that are recreated automatically by tools.
10. **`DUPLICATE`**: Files whose exact data or code is present elsewhere and redundant.
11. **`OBSOLETE`**: Deprecated code or documents superseded by newer implementations.
12. **`PROVEN DEAD/UNUSED`**: Files with zero inbound references, zero runtime usage, zero test dependencies, and zero build relevance (safe for immediate removal).
13. **`UNKNOWN`**: Files whose exact origin or usage could not be proven (MUST BE KEPT). *Current count: 0 files.*

---

## 7. Category Breakdown & Inventory Summary

| Category | File Count | Size (MB) | % of Total Size | Retention Action |
|:---|---:|---:|---:|:---|
| **`REQUIRED DATA`** | 10 | 2,056.80 MB | 49.66% | **STRICTLY PROTECTED / DO NOT TOUCH** |
| **`REQUIRED DEVELOPMENT`** | 37,417 | 919.10 MB | 22.19% | **KEEP** (VCS, venv, node_modules, build configs) |
| **`CACHE/TEMPORARY`** | 5,776 | 590.99 MB | 14.27% | **SAFE TO PURGE** (`.next/cache`, `.pytest_cache`, `.pyc`) |
| **`GENERATED/RECREATABLE`** | 82 | 568.11 MB | 13.72% | **OPTIONAL CLEANUP** (`New folder/` 565.75 MB, `.next/server`) |
| **`REQUIRED RUNTIME`** | 212 | 3.30 MB | 0.08% | **STRICTLY PROTECTED / DO NOT TOUCH** |
| **`REQUIRED GOVERNANCE/AUDIT`** | 165 | 2.88 MB | 0.07% | **STRICTLY PROTECTED / DO NOT TOUCH** |
| **`REQUIRED TESTING`** | 90 | 0.71 MB | 0.02% | **STRICTLY PROTECTED / DO NOT TOUCH** |
| **`DOCUMENTATION`** | 22 | 0.17 MB | < 0.01% | **KEEP** |
| **`OPTIONAL`** | 1 | < 0.01 MB | < 0.01% | **KEEP** (`run_historical_learning.py`) |
| **`PROVEN DEAD/UNUSED`** | 3 | < 0.01 MB | < 0.01% | **SAFE TO PURGE** (`=`, `scratch/test.py`, `scratch/verify_phase14.py`) |
| **`UNKNOWN`** | 0 | 0.00 MB | 0.00% | **NONE (100% Accounted For)** |
| **TOTAL** | **43,778** | **4,142.06 MB** | **100.00%** | |

---

## 8. Candidate Inventory for Safe Deletion (Proven Non-Usage)

### Group A: Proven Dead / Unused (Immediate Safe Deletion)

#### 1. File: `=` (Root Typo File)
* **Path**: `D:/Project/TRADE/=`
* **Category**: `PROVEN DEAD/UNUSED`
* **Size**: 0 bytes
* **Proven Absence of Imports/References**: 0 references in any code or script. Created inadvertently via shell redirection syntax error.
* **Proven Absence from Runtime/APIs**: Not referenced by FastAPI, Uvicorn, or any service.
* **Proven Absence from Tests**: No test references this file.
* **Proven Absence from Build**: No build config or npm script references this file.
* **Reproduction**: Empty file; not needed.
* **Recommendation**: **DELETE**.

#### 2. File: `scratch/test.py`
* **Path**: `D:/Project/TRADE/scratch/test.py`
* **Category**: `PROVEN DEAD/UNUSED`
* **Size**: 53 bytes
* **Proven Absence of Imports/References**: 3 lines of disposable test code (`print('Testing python script execution')`).
* **Proven Absence from Runtime/APIs**: Not imported by `src/` or `config/`.
* **Proven Absence from Tests**: Pytest does not execute `scratch/`.
* **Proven Absence from Build**: Not part of build.
* **Reproduction**: Easily recreated if needed.
* **Recommendation**: **DELETE**.

#### 3. File: `scratch/verify_phase14.py`
* **Path**: `D:/Project/TRADE/scratch/verify_phase14.py`
* **Category**: `PROVEN DEAD/UNUSED`
* **Size**: 1,579 bytes (1.54 KB)
* **Proven Absence of Imports/References**: Standalone one-off script used during Phase 14 verification to print model hashes.
* **Proven Absence from Runtime/APIs**: Not imported anywhere.
* **Proven Absence from Tests**: Not part of `tests/` directory.
* **Proven Absence from Build**: None.
* **Reproduction**: Full script logic is recorded in git history and conversation transcripts.
* **Recommendation**: **DELETE**.

---

### Group B: Cache & Temporary Compilation Artifacts (Safe to Purge)

#### 4. Directory: `frontend/.next/cache/`
* **Path**: `D:/Project/TRADE/frontend/.next/cache/`
* **Category**: `CACHE/TEMPORARY`
* **Size**: `499,331,943 bytes` (**476.20 MB**) (58 files)
* **Proven Absence of Imports/References**: Internal Next.js webpack cache directory (`client-production`, `server-production`).
* **Proven Absence from Runtime/APIs**: At runtime, Next.js serves from `.next/server` and `.next/static`. The `.next/cache` is solely an acceleration cache for subsequent builds.
* **Proven Absence from Tests**: Not referenced by Jest or Pytest.
* **Proven Absence from Build Scripts**: Automatically managed by Next.js.
* **Reproduction**: 100% deterministically recreated by running `npm --prefix frontend run build`.
* **Recommendation**: **SAFE TO PURGE**. Reclaims **476.20 MB** instantly without affecting any source code.

#### 5. Directory: `.pytest_cache/`
* **Path**: `D:/Project/TRADE/.pytest_cache/`
* **Category**: `CACHE/TEMPORARY`
* **Size**: `1,048,576 bytes` (**1.00 MB**) (~50 files)
* **Proven Absence**: Pytest cache for step timing and failed test tracking.
* **Reproduction**: Recreated automatically on next `pytest` run.
* **Recommendation**: **SAFE TO PURGE**.

#### 6. Bytecode Files: `__pycache__/` in project source (`src/`, `config/`, `scripts/`, `tests/`)
* **Paths**: `src/**/__pycache__`, `config/__pycache__`, `scripts/__pycache__`, `tests/__pycache__`
* **Category**: `CACHE/TEMPORARY`
* **Size**: ~`2,621,440 bytes` (**2.50 MB**) (~120 files)
* **Proven Absence**: Python CPython bytecode cache (`.pyc`).
* **Reproduction**: Recompiled on-the-fly by Python interpreter on next execution.
* **Recommendation**: **SAFE TO PURGE**.

---

### Group C: Duplicate Raw Datasets (Requires User Review & Confirmation)

#### 7. Directory: `New folder/` (Raw Kaggle 1-minute CSVs)
* **Path**: `D:/Project/TRADE/New folder/`
* **Category**: `GENERATED/RECREATABLE` / `DUPLICATE`
* **Size**: `593,232,254 bytes` (**565.75 MB**) (12 files)
* **Contents**:
  * `btc_usdt_binance_2018.csv` to `btc_usdt_binance_2026.csv` (9 CSVs, 345.5 MB)
  * `xauusd_2018_2026.csv` (210.26 MB)
  * `fed_economic_data_2018_2026.csv` (24 KB)
  * `US_Dollar_Index_2018_2026.csv` (45 KB)
* **Proven Absence from Runtime/APIs**: Neither FastAPI nor Next.js reads from `New folder/`. The operational system queries `data/historical/historical_market_data.db` (2.15 GB SQLite database).
* **Proven Absence from Active Tests**: All 46 pytest tests use `data/historical/` or in-memory fixtures. No test reads `New folder/`.
* **Proven Reference Analysis**: Referenced only as a default directory string in `src/services/kaggle_dataset_importer.py` for raw CSV ingestion into SQLite. All raw rows have already been processed, resampled to 15m/1h, and ingested into `historical_market_data.db`.
* **Reproduction**: Raw CSVs originated from public Kaggle datasets (Binance BTC/USDT 1m and Gold 1m). The canonical resampled data is permanently preserved in `data/historical/historical_market_data.db`.
* **Recommendation**: **OPTIONAL CLEANUP**.
  * *Option 1*: User may choose to delete `New folder/`, saving **565.75 MB**.
  * *Option 2*: User may keep `New folder/` intact as a raw data archive.
  * *Action*: Default action is to **KEEP** unless explicitly requested by the user.

---

## 9. Estimated Size Reduction

### Scenario 1: Tier 1 Safe Cleanup (Caches & Proven Dead Files Only)
* Purge `frontend/.next/cache/` (476.20 MB)
* Purge `.pytest_cache/` (1.00 MB)
* Purge source `__pycache__/` (2.50 MB)
* Delete `=` (0 bytes), `scratch/test.py` (53 B), `scratch/verify_phase14.py` (1.54 KB)
* **Immediate Space Saved**: **`479.70 MB`**
* **New Project Size**: `3,662.36 MB` (3.58 GB)
* **Zero impact on code, build, data, or tests**.

### Scenario 2: Tier 2 Full Cleanup (Tier 1 + Purging Raw CSVs in `New folder/`)
* Include all Tier 1 purges
* Delete or archive `New folder/` (565.75 MB)
* **Total Space Saved**: **`1,045.45 MB`** (**~1.05 GB**)
* **New Project Size**: **`3,096.61 MB`** (**3.02 GB**)
* **Reduction**: **25.24% of entire repository footprint reclaimed**.

---

## 10. Risk Assessment by Category

| Category | Risk Level | Rationale |
|:---|:---:|:---|
| `PROVEN DEAD/UNUSED` | **NONE** | Files have 0 references across all codebase layers. |
| `CACHE/TEMPORARY` | **NONE** | Next.js and Python automatically recreate caches as needed. |
| `GENERATED/RECREATABLE` (`New folder`) | **LOW** | Raw data already ingested in SQLite database; only needed if re-importing raw 1m data from scratch. |
| `REQUIRED DATA` | **CRITICAL** | Must never be deleted. Contains canonical historical backtest signals and forward shadow records. |
| `REQUIRED RUNTIME` | **CRITICAL** | Must never be deleted. Core trading and UI system. |
| `REQUIRED GOVERNANCE/AUDIT` | **CRITICAL** | Must never be deleted. Legal, mathematical, and architectural evidence provenance. |
| `REQUIRED TESTING` | **HIGH** | Must never be deleted. Regression test harnesses. |

---

## 11. Protected Assets Manifest (MUST NEVER BE DELETED)

The following files and directories are strictly locked and exempt from deletion:

1. **Canonical Databases & State**:
   * `data/historical/historical_market_data.db` (2,438 reconciled signals, 15m/1h candle database)
   * `data/forward_shadow_signals.db` (Authoritative forward shadow signals database)
   * `data/shadow_trades.db` (Forward paper trade execution records)
   * `data/governance_forward_state.json` (Phase 14 state machine persistence)
   * `data/gating_state.json` (Gating control state)
   * `ote_trades.json` (OTE trade fixtures)
   * `paper_trading.json` & `signal_records.json`
2. **Machine Learning Model Artifacts**:
   * `research/ml/artifacts/BTC/model.joblib`
   * `research/ml/artifacts/BTC/metrics.json`
   * `research/ml/artifacts/BTC/feature_names.json`
   * `research/ml/artifacts/BTC/calibration_map.json`
   * `research/ml/artifacts/XAU/model.joblib`
   * `research/ml/artifacts/XAU/metrics.json`
   * `research/ml/artifacts/XAU/feature_names.json`
   * `research/ml/artifacts/XAU/calibration_map.json`
3. **Core Quant & Runtime Logic**:
   * `src/services/decision_engine.py` (Deterministic gate thresholds: `DIRECTIONAL_THRESHOLD = 20.0`, `CONFLICT_WEIGHT_THRESHOLD = 0.25`, Quality Gate = 58)
   * `src/services/signal_aggregator.py`
   * `src/services/forward_shadow.py`
   * `src/services/outcome_tracker.py`
   * `src/core/security.py`, `src/core/gating_control.py`
   * All `src/api/routes/*.py`
4. **Frozen Frontend Application**:
   * `frontend/src/app/page.tsx` (5-tab navigation: `OVERALL`, `MARKET INSIGHT`, `CURRENT MARKET`, `SHADOW`, `ML MODELS` + footer `⚙ System`)
   * `frontend/src/components/CurrentMarketTab.tsx`
   * `frontend/src/components/EagleLogo.tsx`
   * `frontend/src/components/EmpiricalPerformancePanel.tsx`
   * `frontend/src/components/HistoricalBacktestTab.tsx`
   * `frontend/src/components/HistoricalDatasetStatus.tsx`
   * `frontend/src/components/MLModelsTab.tsx`
   * `frontend/src/components/ShadowAccumulationMonitor.tsx`
   * `frontend/src/components/SignalHeroCard.tsx`
5. **Governance & Audit Provenance**:
   * `data/reports/` (all JSON and MD reports)
   * `data/audit/`
   * `archive/FINAL_HISTORICAL_VALIDATION_RECONCILIATION.md`
   * All root governance verification reports (`CLEAN_FORWARD_PRODUCTION_PATH_VERIFICATION.md`, `S7_AUTHORIZATION_HARDENING_FINAL_REPORT.md`, `FORWARD_EVIDENCE_ACCUMULATION_REPORT.md`, etc.)

---

## 12. Post-Cleanup Verification Plan

Whenever cleanup actions are executed, the following 4-step verification battery MUST be run immediately to verify zero regressions:

1. **Frontend Production Build Verification**:
   ```powershell
   npm --prefix frontend run build
   ```
   *Expectation*: Exit code 0, clean build.
2. **Frontend Test Suite**:
   ```powershell
   npm --prefix frontend run test
   ```
   *Expectation*: 25/25 tests PASS.
3. **Backend Python Test Suite**:
   ```powershell
   .\.venv\Scripts\pytest.exe tests/test_percentage_truth_and_semantics.py tests/test_confluence_engine.py tests/test_decision_engine.py tests/test_security_hardening.py tests/test_zero_regression.py -q
   ```
   *Expectation*: 46/46 tests PASS.
4. **Integrity & Git Diff Verification**:
   ```powershell
   git status --short
   git diff -- src/services/decision_engine.py src/services/signal_aggregator.py
   ```
   *Expectation*: Zero unwanted modifications to protected quant logic.

---

## 13. Recommended Execution Sequence

1. **Step 1 (Dry-Run)**: Review candidate list with user.
2. **Step 2 (Tier 1 Cleanup)**:
   * Remove 3 proven dead files (`=`, `scratch/test.py`, `scratch/verify_phase14.py`).
   * Purge `.next/cache`, `.pytest_cache`, and source `__pycache__` directories.
   * Verify frontend build, frontend tests, and python tests.
3. **Step 3 (Tier 2 Decision)**:
   * Consult user regarding `New folder/` (565.75 MB).
   * Delete or retain based on user choice.

---

## 14. EXPLICIT HOLD & USER APPROVAL GATE

> [!IMPORTANT]
> **NO FILES HAVE BEEN DELETED.**  
> This document completes the exhaustive audit and inventory phase.  
> Execution of any file deletion is strictly paused until explicit user approval is received.
