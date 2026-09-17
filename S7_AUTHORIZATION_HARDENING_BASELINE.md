# S7 AUTHORIZATION HARDENING BASELINE

**Generated At**: `2026-09-04T07:22:00Z` (`2026-09-04T12:52:00+05:30`)  
**Git Baseline Commit**: `62c7430a9a24fa43387d97ee9b7d967a3fb25a47`  
**Execution Boundary**: Read-Only Baseline Capture  

---

## 1. File & Component SHA-256 Hashes

| Path | SHA-256 Hash | Status |
| :--- | :--- | :---: |
| `signal_records.json` | `044C2D67CC8F2C53AE6361289E188CC14916E6E61A66E6E050DCF871C9D590D1` | Working Tree (Excursion Updated) |
| `research/ml/artifacts/BTC/model.joblib` | `0978B52D9B23A12099935EEB72CC260A470C283E0E4E54FC278596EBB9F482A5` | FROZEN (`v1.0.0-research`) |
| `research/ml/artifacts/XAU/model.joblib` | `C12A0F09101DAD9547618D6DDF68F99105D539F8618486D59CFE16F586DC8F2E` | FROZEN (`v1.0.0-research`) |
| `src/services/decision_engine.py` | `55C9373280801EAD505BABA90D8A3CF4F4742D1883D8DD0D3E42E15F97AFF940` | FROZEN Quant Rules |
| `src/services/signal_aggregator.py` | `BD32A99A86755F2142D4659BC9EB0892FF3AC62A712660F3C47D6A3ECE497DA0` | FROZEN 17 Indicators & Weights |
| `data/historical/historical_market_data.db` | Structural Integrity: `ok` (PRAGMA quick_check) | READ-ONLY SQLite (2.2 GB) |

---

## 2. Pre-Hardening Governance State (Unverified S7)

* **Current State in File**: `S7: APPROVED_ADVISORY`
* **Current Production Gating in File**: `ON`
* **Current Live Execution**: `OFF` (Hard-Locked)
* **Actor Recorded**: `Production Governance Authority` (Self-Declared String)
* **Vulnerability Identified**: No cryptographic token, no signature, no current-state enforcement (S5 -> S7 bypassable), plain unsealed JSON state file.

---

## 3. Authoritative Evidence Inventory (Live DB)

* **Total Forward Signals in DB**: 360
* **BTC Resolved N**: 211
* **BTC Pending N**: 0
* **XAU Resolved N**: 147 ($147 \ge 100 \implies$ N50 and N100 Milestones Satisfied)
* **XAU Pending N**: 2
* **Temporal Order Violations**: 0
* **Synthetic / Backfilled Evidence**: 0

---

## 4. Existing Governance Audit Log

* File: `data/audit/governance_state_audit.log`
* Total Entries: 3
  1. Entry 1: S5 -> S6 (In audit)
  2. Entry 2: S6 -> S7 (Unverified actor string)
  3. Entry 3: Empty trailing line
