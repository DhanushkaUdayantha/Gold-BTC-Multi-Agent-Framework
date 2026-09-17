# FORWARD EVIDENCE PROVENANCE BASELINE SNAPSHOT

**Audit Timestamp**: 2026-09-04T18:55:00+05:30  
**Commit**: `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`  
**Branch**: `master`  
**Execution Boundary**: Read-Only Forensic Audit Mode  

---

## 1. Git State & Integrity

```text
git branch: master
git commit: 62c7430a9a24fa43387d97ee9b7d967a3fb25a47
git status: On branch master (Quant core unmodified; working tree clean of engine mutations)
git diff src/services/decision_engine.py: EMPTY (Zero diff)
git diff src/services/signal_aggregator.py: EMPTY (Zero diff)
```

---

## 2. Protected Store Hashes (SHA-256)

| Evidence Store Path | SHA-256 Hash | Size / Status |
| :--- | :--- | :--- |
| `data/historical/historical_market_data.db` | `b4ae2ad132c0f726a489c6eee8770f21775b63186c72db8dae5e7abb88fdd3b9` | 2,217,017,344 bytes (Live Ingestion Active) |
| `data/shadow_trades.db` | `d477f87fe3bcd8e5476a95e7436fd36082fd901a45783f58243c7fd24f6fb627` | 16,384 bytes (Read-Only / 0 Rows) |
| `signal_records.json` | `08f5a8185bd81fccdadb168183743f59ca48e6f10790185d538ec775afe2440a` | 60,989 bytes (Read-Only / 14 Closed Records) |
| `data/governance_forward_state.json` | `e5874fef66ae84bb79c70fc980c1651bb3d45884b66e4cfb895c8c2eef077038` | 890 bytes (Read-Only / State Locked) |
| `src/services/decision_engine.py` | `55c9373280801ead505baba90d8a3cf4f4742d1883d8dd0d3e42e15f97aff940` | 57,166 bytes (Frozen / Zero Diff) |
| `src/services/signal_aggregator.py` | `bd32a99a86755f2142d4659bc9eb0892ff3ac62a712660f3c47d6a3ece497da0` | 20,240 bytes (Frozen / Zero Diff) |

---

## 3. Current Empirical Observation Counts (Live Database: `ml_shadow_observations`)

| Asset | Total Captured | Pending / Unresolved (WAIT) | Authoritative Resolved | Invalid | Duplicates |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BTC/USD** | 284 | 247 | **0** | 0 | 0 |
| **XAU/USD** | 363 | 363 | **0** | 0 | 0 |
| **Combined** | 647 | 610 | **0** | 0 | 0 |

*Note: All 363 live XAU observations are defensive WAIT evaluations (`production_decision = 'WAIT'`). Zero directional trade setups have triggered on Gold during recent chop/closed market conditions. BTC observations include 247 defensive WAIT evaluations; no live forward trades are resolved.*

---

## 4. Reference Baseline Target Comparison

| Metric | Reference Benchmark Claim | Current Live DB Count | Discrepancy |
| :--- | :---: | :---: | :---: |
| **BTC Forward Resolved N** | 68 | 0 | -68 |
| **XAU Forward Resolved N** | 45 | 0 | -45 |
| **Governance State** | Reference Baseline / Holdout | `S2: EVIDENCE_COLLECTION` | Holdout Benchmark != Live Forward Rows |

---

## 5. Frozen Quant & Model Invariants

* `src/services/decision_engine.py`: Unmodified (SHA-256 Verified)
* `src/services/signal_aggregator.py`: Unmodified (SHA-256 Verified)
* ML Model Version: `v1.0.0-research` (Locked)
* Production Gating: `DISABLED`
* Live Execution: `DISABLED`
