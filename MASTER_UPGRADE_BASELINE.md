# MASTER UPGRADE BASELINE AUDIT

**Generated**: 2026-09-04T10:56:00+05:30  
**Authority**: Senior Quantitative Systems Architect + ML Engineer + Backend Engineer + Frontend Engineer + QA Engineer + Security Engineer + Forensic Auditor  
**Repository**: `d:\Project\TRADE`  
**Git Commit**: `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`  

---

## 1. Working Tree & Core File Hashes

| File Path | SHA256 Hash | Notes |
| :--- | :--- | :--- |
| `signal_records.json` | `546a8040e708a3e1fc4fa0e28763f30474d3972d9b08d9428696ba53fd420dfa` | Fully isolated in pytest conftest |
| `src/services/decision_engine.py` | `55c9373280801ead505baba90d8a3cf4f4742d1883d8dd0d3e42e15f97aff940` | Frozen quant decision engine |
| `src/services/signal_aggregator.py` | `bd32a99a86755f2142d4659bc9eb0892ff3ac62a712660f3c47d6a3ece497da0` | Frozen technical scoring & weights |
| `config/settings.py` | `a7b6e54a0d59f3ea45191fe73205ecc9ef862edbdb1e145e73a5beee1b741d95` | Environment & safety settings |
| `src/research/governance/forward_shadow.py` | `11fa78b7e768a784c1f9ec35e3203b70ba0db9761abe6b0715f388c838670832` | Authoritative forward shadow engine |
| `src/research/governance/forward_state_machine.py` | `bb19f195714a8df551a61adde0b14f63cf2ab344026e0c9328e7475fc2ca6ca9` | Governance state machine (S0-S8) |
| `src/services/forward_shadow_resolver_worker.py` | `019bac35a827ab51d5d76a9963e9ea2d7c8faf119e96429ee0eefb2c722d36e7` | Non-blocking periodic resolver daemon |
| `research/ml/artifacts/BTC/model.joblib` | `0978b52d9b23a12099935eeb72cc260a470c283e0e4e54fc278596ebb9f482a5` | Frozen BTC model (`v1.0.0-research`) |
| `research/ml/artifacts/XAU/model.joblib` | `c12a0f09101dad9547618d6ddf68f99105d539f8618486d59cfe16f586dc8f2e` | Frozen XAU model (`v1.0.0-research`) |

---

## 2. Historical & Shadow Databases

### `data/historical/historical_market_data.db`
* **File Size**: 2,216,726,528 bytes (2.2 GB)
* **SQLite Integrity**: `ok`
* **Table Breakdown**:
  * `candles`: 9,608,718 closed bars (5m, 15m, 1h, 4h, 1d)
  * `datasets`: 4 rows
  * `backtest_runs`: 53 rows
  * `historical_signals`: 2,438 rows
  * `backtest_reports`: 24 rows
  * `macro_dxy`: 2,098 rows
  * `macro_fed`: 101 rows
  * `live_ingestion_status`: 2 rows
  * `ml_shadow_observations`: 466 rows
  * `forward_shadow_signals`: 318 rows

### `data/historical/xau_shadow_paper_trades.json`
* **Purpose**: Tracks manual / simulated paper trades independently from forward shadow signals.
* **Separation**: Strictly isolated from `forward_shadow_signals` table.

---

## 3. Forward Evidence Lineage & Status

* **Total Live Observations**: 318 rows
* **Time Range**: `2026-09-02T12:00:00Z` to `2026-09-03T22:02:34.795665+00:00`
* **Temporal Firewall**: `outcome_timestamp > signal_timestamp` (0 violations)
* **Asset Isolation**: BTC and XAU stored and resolved completely independently
* **Benchmark Reconciled Lineage**:
  * Historical holdout reference benchmarks: BTC $N=68$, XAU $N=45$
  * Authoritative forward store: distinct table `forward_shadow_signals`

---

## 4. Current Governance State Machine

* **State**: `S2: EVIDENCE_COLLECTION` transitioning to `S3` / `S5` as empirical evidence resolves
* **Production Gating**: `DISABLED` (Hard-locked)
* **Live Execution**: `DISABLED` (Hard-locked)
* **Advisory State**: Active (zero automated orders)

---

## 5. Security & Rate Limiting

* **Admin Gating Token**: `src/core/security.py` using `hmac.compare_digest`
* **Sliding Window Rate Limiter**: `src/core/rate_limiter.py` with in-memory thread-safe queues
* **CORS**: Strict allowlist with regex restricted to non-production environments
* **Error Sanitization**: No raw traceback leakage through API endpoints

---

## 6. Endpoints, Tests, & Build Health

* **OpenAPI Registered Endpoints**: 90 endpoints across 13 routers
* **Pytest Suite**: 711 passing tests across 2 consecutive runs (0 failures)
* **Frontend Build**: Next.js 14.2.4 production build clean (0 errors, 4/4 static pages)
* **Backend Health**: `/health` returning `status = "ok"` on port 8000
