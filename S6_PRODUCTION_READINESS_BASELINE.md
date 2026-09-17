# S6 PRODUCTION READINESS BASELINE AUDIT

**Generated**: 2026-09-04T11:17:00+05:30  
**Authority**: Senior Quant Systems Engineer & Production Readiness Auditor  
**Repository**: `d:\Project\TRADE`  
**Git Commit**: `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`  

---

## 1. Immutable File Hashes (SHA256)

| File Path | SHA256 Hash | Notes |
| :--- | :--- | :--- |
| `signal_records.json` | `d999c7a9cfc059d0e55f0fb8078456cb9f95339df305754772736ce43b8e9825` | Current pre-regression baseline hash (isolated in pytest) |
| `research/ml/artifacts/BTC/model.joblib` | `0978b52d9b23a12099935eeb72cc260a470c283e0e4e54fc278596ebb9f482a5` | Frozen BTC model (`v1.0.0-research`) |
| `research/ml/artifacts/XAU/model.joblib` | `c12a0f09101dad9547618d6ddf68f99105d539f8618486d59cfe16f586dc8f2e` | Frozen XAU model (`v1.0.0-research`) |
| `src/services/decision_engine.py` | `55c9373280801ead505baba90d8a3cf4f4742d1883d8dd0d3e42e15f97aff940` | Frozen quant decision engine |
| `src/services/signal_aggregator.py` | `bd32a99a86755f2142d4659bc9eb0892ff3ac62a712660f3c47d6a3ece497da0` | Frozen technical scoring (17 indicators) |
| `src/research/governance/forward_shadow.py` | `11fa78b7e768a784c1f9ec35e3203b70ba0db9761abe6b0715f388c838670832` | Authoritative forward shadow engine |
| `src/research/governance/forward_state_machine.py` | `bb19f195714a8df551a61adde0b14f63cf2ab344026e0c9328e7475fc2ca6ca9` | Finite-state machine governance |
| `src/services/forward_shadow_resolver_worker.py` | `bc73269bddc9b7b77a0020ae9cb9c6fb99d80fc2bb3c587c8f7a6993166270bd` | Background resolver daemon worker |
| `config/settings.py` | `a7b6e54a0d59f3ea45191fe73205ecc9ef862edbdb1e145e73a5beee1b741d95` | Global configuration & safety controls |
| `src/api/main.py` | `c4df157cdac7da79ec9c22fede786ab6185bcb55e3ed569e39414257d2538c38` | FastAPI app entrypoint & lifespan |
| `src/api/routes/governance.py` | `3e682e9a1fa5a9b2eff919f5d45cbfc5f47331121855c64fb634484e7f0c2b9a` | Governance & telemetry routes |

---

## 2. System State Baseline

* **Current Governance State**: `S5 — N100_MILESTONE_AUDIT`
* **Production Gating**: `DISABLED`
* **Live Execution**: `OFF` (NO LIVE ORDER EXECUTION)
* **Historical DB Status**: `HEALTHY` (SQLite PRAGMA quick_check = ok, 2.2 GB)
* **ML Model Version**: `v1.0.0-research` (Frozen)

---

## 3. Forward Evidence Breakdown

* **Total Forward Signals**: 332
  * BTC/USD Resolved: **187** (`RESOLVED_WIN`)
  * BTC/USD Pending: **8**
  * XAU/USD Resolved: **131** (86 `RESOLVED_WIN`, 45 `RESOLVED_LOSS`)
  * XAU/USD Pending: **6**
* **XAU Authoritative Resolved N**: **131** ($131 \ge 100 \implies$ N50 and N100 Milestones Passed)
* **Temporal Violations (`outcome <= signal`)**: **0**
