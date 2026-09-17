# SHADOW ISOLATION & STORAGE ARCHITECTURE

**System**: BTC/USD & XAU/USD Quantitative AI Trading Analysis Platform  
**Document Classification**: Architectural Decoupling, Persistence Isolation, and Reset Safety  

---

## 1. Storage Boundaries & Isolation Matrix

The platform maintains five independent persistence layers. Each layer is strictly decoupled by storage mechanism, file paths, and execution context:

```
+-----------------------------------------------------------------------------------+
|                        PHYSICALLY ISOLATED STORAGE LAYERS                         |
+-----------------------------------------------------------------------------------+

   [Layer 1: User Paper Trading]               [Layer 2: Historical Core]
   File: paper_trading.json                    File: data/historical/historical_market_data.db
   Engine: JSON flat-file ledger               Engine: SQLite 3 (WAL mode)
   Tables: N/A (JSON objects)                  Tables: candles, historical_signals
   Access: Read/Write (Interactive UI)         Access: Strictly Read-Only for Analytics
   Reset: POST /trade/reset (unlinks file)     Reset: PROHIBITED (Zero delete paths)

   ---------------------------------------------------------------------------------

   [Layer 3: Automated Forward Shadow]         [Layer 4: ML Shadow Observations]
   File: data/historical/historical_market_data.db File: data/historical/historical_market_data.db
   Engine: SQLite 3 table                      Engine: SQLite 3 table
   Table: forward_shadow_signals               Table: ml_shadow_observations
   Access: Append & Resolution update only     Access: Append & Resolution update only
   Reset: PROHIBITED (Zero delete paths)       Reset: PROHIBITED (Zero delete paths)

   ---------------------------------------------------------------------------------

   [Layer 5: Dedicated Shadow Trades Ledger]
   File: data/shadow_trades.db
   Engine: SQLite 3 database
   Table: shadow_trades
   Access: Secondary shadow simulation runners (btc_shadow_runner.py, xau_shadow_runner.py)
   Reset: PROHIBITED (Zero delete paths)
```

---

## 2. Decoupling & Reset Safety Proof

### A. Proof that Manual Paper Trading Resets Do Not Affect Shadow Stores
- **Execution Path**: `POST /trade/reset` $\rightarrow$ `src/api/routes/decision.py` $\rightarrow$ `PaperTradingService.reset_account()`.
- **Implementation**:
  ```python
  if os.path.exists(self.file_path):
    os.remove(self.file_path)
  self._init_account()
```
- **Proof**: The file path is `paper_trading.json`. The method never calls SQLite drivers, executes SQL statements, or holds references to any database connection.
- **Verification**: Formally proven in regression test `test_a_manual_reset_preserves_forward_shadow` and `test_b_manual_reset_preserves_ml_shadow` in `tests/test_shadow_store_isolation.py`.

### B. Proof of Forward & ML Shadow Immutable Retention
- Neither `ForwardShadowEngine` nor `MLShadowStore` contains any `DELETE` or `DROP TABLE` SQL statements in production code.
- Trade lifecycles resolve deterministically by transitioning `status = 'PENDING'` to `status = 'RESOLVED_WIN'` or `'RESOLVED_LOSS'`. Historical observations remain permanently intact for auditability.

---

## 3. Asset Scoping & Cross-Contamination Firewalls

1. **Database Scoping**:
   - `forward_shadow_signals` includes an `asset` column (`BTC/USD` or `XAU/USD`).
   - `ml_shadow_observations` includes a `symbol` column (`BTC/USD` or `XAU/USD`).
   - All query functions (`list_signals`, `get_all_observations`, `get_forward_summary`) mandate asset filtering.
2. **Model Scoping**:
   - Pre-trained models and scalers are loaded from asset-specific directories (`research/ml/artifacts/BTC/` and `research/ml/artifacts/XAU/`).
   - BTC features cannot be scaled with XAU parameters, and XAU predictions cannot update BTC shadow observation records (verified via `tests/test_shadow_store_isolation.py` and `tests/test_asset_and_leakage_isolation.py`).
