# CLEAN FORWARD PRODUCTION PATH VERIFICATION

## AUDIT EXECUTIVE SUMMARY

- **Repository**: `D:\Project\TRADE`
- **Auditor Roles**: Senior Quantitative Systems Auditor, Data Integrity Engineer, ML Governance Auditor, Production Safety Engineer
- **Governance State**: `S2 — EVIDENCE_COLLECTION`
- **Production Gating**: `DISABLED`
- **Live Execution**: `DISABLED`
- **Clean Forward Evidence Resolved N**: `0` (BTC: 0, XAU: 0)
- **Quarantined Legacy/Contaminated Records**: `479` (BTC: 280, XAU: 199)
- **Authoritative Database**: `data/historical/historical_market_data.db` (Table: `forward_shadow_signals`)
- **Audit Conclusion**: **PASS — FULL VERIFICATION SUCCESSFUL**

---

## A. PRODUCTION CALL PATH

The production call path for forward shadow evidence generation is verified end-to-end:

```text
LIVE MARKET DATA (Candles from CCXT/Binance/Hybrid Provider)
      ↓
DecisionService.analyze_market(symbol)
      ↓ (Fetches live multi-timeframe candles: current_price = ta.current_price > 0)
DecisionEngine._calculate_levels(signal, price, supports, resistances, atr)
      ↓ (Generates dynamic stop_loss, take_profit_1, take_profit_2 based on ATR and S/R)
DecisionService Hook 5: Shadow Runner Integration (Lines 478-533)
      ↓
BTCShadowRunner.evaluate_live_market_setup() / XAUShadowRunner.evaluate_live_market_setup()
      ↓
ForwardShadowEngine.capture_forward_signal(
    asset, direction, entry_price=current_price, stop_loss, take_profit_1,
    evidence_generation="CLEAN_FORWARD"
)
      ↓
forward_shadow_signals (SQLite Table in data/historical/historical_market_data.db)
      ↓ (Initial Status: 'PENDING', evidence_generation: 'CLEAN_FORWARD')
ForwardShadowResolverWorker (Periodic Background Service)
      ↓
Two-Stage Entry-Fill State Machine (_evaluate_two_stage_signal)
      │
      ├── Stage 1: PENDING/PENDING_ENTRY → verifies price touches entry
      │            (If unfilled > 48h → NOT_TRIGGERED, R=0.0)
      │            (Upon touch → transitions to ACTIVE_POSITION, entry_filled_at = candle_ts)
      │
      └── Stage 2: ACTIVE_POSITION → monitors dynamic TP and SL levels
                   (Hits TP → RESOLVED_WIN)
                   (Hits SL → RESOLVED_LOSS)
                   (Hits both on same bar → AMBIGUOUS)
                   (Active > 48h → RESOLVED_EXPIRED)
      ↓
ForwardExecutionStateMachine._query_counts()
      ↓ (Queries COUNT(*) WHERE evidence_generation = 'CLEAN_FORWARD' AND status IN ('RESOLVED_WIN', 'RESOLVED_LOSS'))
GOVERNANCE MILESTONE TRACKER (XAU N accumulates toward N50/N100)
```

### Detailed Path Specifications

| Step | Component | File | Function | Caller | Callee | Primary Database |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Ingestion | [`src/services/technical_service.py`](file:///d:/Project/TRADE/src/services/technical_service.py) | `analyze()` | `DecisionService._fetch_analysis` | Market API / DB | `historical_market_data.db` (Read-only) |
| 2 | Level Gen | [`src/services/decision_engine.py`](file:///d:/Project/TRADE/src/services/decision_engine.py) | `_calculate_levels()` | `DecisionEngine.evaluate()` | Math / ATR / S/R | In-memory |
| 3 | Pipeline Hook | [`src/services/decision_service.py`](file:///d:/Project/TRADE/src/services/decision_service.py#L478-L533) | `analyze_market()` (Hook 5) | API Route `/api/v1/decision` | `evaluate_live_market_setup()` | Isolated Runner Store |
| 4 | Runner | [`src/services/btc_shadow_runner.py`](file:///d:/Project/TRADE/src/services/btc_shadow_runner.py#L88) / [`xau_shadow_runner.py`](file:///d:/Project/TRADE/src/services/xau_shadow_runner.py#L83) | `evaluate_live_market_setup()` | DecisionService Hook 5 | `capture_forward_signal()` | `data/shadow_trades.db` + `forward_shadow_signals` |
| 5 | Forward Engine | [`src/research/governance/forward_shadow.py`](file:///d:/Project/TRADE/src/research/governance/forward_shadow.py#L164) | `capture_forward_signal()` | Shadow Runner | `INSERT OR IGNORE` | `historical_market_data.db` |
| 6 | Resolver Worker | [`src/services/forward_shadow_resolver_worker.py`](file:///d:/Project/TRADE/src/services/forward_shadow_resolver_worker.py#L205) | `run_cycle()` | Worker Loop Thread | `_evaluate_two_stage_signal()` | `historical_market_data.db` |
| 7 | Two-Stage Logic | [`src/services/forward_shadow_resolver_worker.py`](file:///d:/Project/TRADE/src/services/forward_shadow_resolver_worker.py#L305) | `_evaluate_two_stage_signal()` | `run_cycle()` | `mark_entry_filled()` / `resolve_forward_signal()` | `historical_market_data.db` |
| 8 | Governance SM | [`src/research/governance/forward_state_machine.py`](file:///d:/Project/TRADE/src/research/governance/forward_state_machine.py#L230) | `_query_counts()` | `evaluate_state()` | SQLite Query | `historical_market_data.db` (Read-only) |

---

## B. T0 PRICE VERIFICATION

- **Source of `entry_price`**:
  In [`src/services/decision_service.py`](file:///d:/Project/TRADE/src/services/decision_service.py#L126-L154), `current_price` is fetched dynamically from the live technical analysis service (`ta.current_price` where `ta.current_price > 0`).
- **Propagation**:
  `current_price` is passed directly into Hook 5:
  ```python
  get_btc_shadow_runner().evaluate_live_market_setup(current_price=current_price, ...)
  get_xau_shadow_runner().evaluate_live_market_setup(current_price=current_price, ...)
  ```
- **Forward Shadow Snapshot Capture**:
  In [`BTCShadowRunner`](file:///d:/Project/TRADE/src/services/btc_shadow_runner.py#L91) and [`XAUShadowRunner`](file:///d:/Project/TRADE/src/services/xau_shadow_runner.py#L86):
  ```python
  snapshot = self.forward_engine.capture_forward_signal(
      asset="BTC/USD",  # or "XAU/USD"
      direction=direction,
      entry_price=current_price, # <-- REAL LIVE T0 MARKET PRICE
      stop_loss=stop_loss,
      take_profit_1=take_profit_1,
      ...
      evidence_generation="CLEAN_FORWARD",
  )
  ```
- **Zero Static Test Fixture Injection**:
  Verified: Static fixture prices (e.g., $64,000 / $64,200 for BTC, $2,700 for XAU) are NEVER injected into production forward evidence. Every new observation records the real-time live price at signal creation.

---

## C. DYNAMIC SL/TP VERIFICATION

- **Level Generation Origin**:
  Calculated dynamically in [`src/services/decision_engine.py`](file:///d:/Project/TRADE/src/services/decision_engine.py#L987-L1040) via `_calculate_levels(signal, price, supports, resistances, atr)`.
  - **BUY**:
    - `stop_loss`: `min(entry_mid - atr * self.atr_multiplier, nearest_sup - atr * 0.3)`
    - `take_profit_1`: `min(res_above)` if resistance exists above `entry_max * 1.001`, else `entry_mid + atr * 2.0`
    - `take_profit_2`: second resistance or `tp1 + risk`
  - **SELL**:
    - `stop_loss`: `max(entry_mid + atr * self.atr_multiplier, nearest_res + atr * 0.3)`
    - `take_profit_1`: `max(sup_below)` if support exists below `entry_min * 0.999`, else `entry_mid - atr * 2.0`
    - `take_profit_2`: second support or `tp1 - risk`
- **Propagation**:
  Passed through `decision.stop_loss`, `decision.take_profit_1`, `decision.take_profit_2` to Hook 5, into the shadow runners, and recorded in `forward_shadow_signals`.
- **Integrity**:
  Verified zero static brackets ($64,000 / $63,000 / $65,880 or $2,700 / $2,680 / $2,736) in production pathways.

---

## D. EVIDENCE LINEAGE VERIFICATION

- **Clean Forward Lineage**:
  Every future signal created through the production runner sets:
  ```python
  evidence_generation = "CLEAN_FORWARD"
  ```
- **Quarantined Legacy Lineage**:
  All 479 pre-existing contaminated test fixture records in `forward_shadow_signals` remain strictly flagged as:
  ```python
  evidence_generation = "FORENSIC_CONTAMINATED_TEST_FIXTURE"
  ```
- **Governance Segregation**:
  [`ForwardExecutionStateMachine._query_counts()`](file:///d:/Project/TRADE/src/research/governance/forward_state_machine.py#L241-L253) executes:
  ```sql
  SELECT COUNT(*) FROM forward_shadow_signals
  WHERE asset = 'XAU/USD'
    AND evidence_generation = 'CLEAN_FORWARD'
    AND status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')
  ```
  The 479 quarantined records evaluate to **0** in this query. Clean Governance N is strictly **0**.

---

## E. ENTRY-FILL STATE MACHINE VERIFICATION

Implemented in [`ForwardShadowResolverWorker._evaluate_two_stage_signal()`](file:///d:/Project/TRADE/src/services/forward_shadow_resolver_worker.py#L305-L407):

```text
[NEW SIGNAL]
      ↓
  PENDING / PENDING_ENTRY
      │
      ├── Price touches entry within 48h?
      │      │
      │      ├── NO (>48h elapsed) ──→ NOT_TRIGGERED (R = 0.0, Excluded from Governance N)
      │      │
      │      └── YES ──→ Transitions to ACTIVE_POSITION
      │                   (Calls mark_entry_filled, records entry_filled_at = candle_timestamp)
      │
      └── ACTIVE_POSITION
             │
             ├── Low <= SL and High >= TP (Same Candle) ──→ AMBIGUOUS (R = 0.0)
             ├── Hit TP (BUY: High >= TP1 / SELL: Low <= TP1) ──→ RESOLVED_WIN (R = +X.XX)
             ├── Hit SL (BUY: Low <= SL / SELL: High >= SL) ──→ RESOLVED_LOSS (R = -1.0)
             └── Duration from fill > 48h ──→ RESOLVED_EXPIRED (R = 0.0)
```

### Invariant Verification:
1. **TP/SL Before Entry Blocked**: While in `PENDING`/`PENDING_ENTRY`, TP and SL conditions are NEVER checked. If market moves to TP or SL without first touching entry, the signal remains `PENDING` until 48h elapse, resolving as `NOT_TRIGGERED`.
2. **Deterministic R-Multiple**: Realized R is calculated strictly from `(exit_price - entry_price) / risk` (or `-1.0` for SL) after confirmed fill.

---

## F. TEST MATRIX RESULTS

All 14 comprehensive test conditions were executed against isolated temporary databases (`tmp_path`) in [`tests/test_forward_shadow_isolation_and_tradability.py`](file:///d:/Project/TRADE/tests/test_forward_shadow_isolation_and_tradability.py):

| # | Test Scenario | Description | Result |
| :---: | :--- | :--- | :---: |
| 1 | **BUY unfilled** | BUY limit entry not touched for >48h resolves as `NOT_TRIGGERED` ($R=0.0$) | **PASS** |
| 2 | **BUY entry $\rightarrow$ TP** | BUY touches entry $\rightarrow$ `ACTIVE_POSITION` $\rightarrow$ hits TP $\rightarrow$ `RESOLVED_WIN` | **PASS** |
| 3 | **BUY entry $\rightarrow$ SL** | BUY touches entry $\rightarrow$ `ACTIVE_POSITION` $\rightarrow$ hits SL $\rightarrow$ `RESOLVED_LOSS` | **PASS** |
| 4 | **SELL entry $\rightarrow$ TP** | SELL touches entry $\rightarrow$ `ACTIVE_POSITION` $\rightarrow$ hits TP $\rightarrow$ `RESOLVED_WIN` | **PASS** |
| 5 | **SELL entry $\rightarrow$ SL** | SELL touches entry $\rightarrow$ `ACTIVE_POSITION` $\rightarrow$ hits SL $\rightarrow$ `RESOLVED_LOSS` | **PASS** |
| 6 | **TP before entry blocked** | Price touches TP without touching entry $\rightarrow$ remains `PENDING` (Never claims WIN) | **PASS** |
| 7 | **SL before entry blocked** | Price touches SL without touching entry $\rightarrow$ remains `PENDING` (Never claims LOSS) | **PASS** |
| 8 | **Same-candle ambiguity** | Post-fill bar touches both TP and SL $\rightarrow$ resolves as `AMBIGUOUS` ($R=0.0$) | **PASS** |
| 9 | **Gap ambiguity** | Volatility bar spans both TP and SL in indeterminate order $\rightarrow$ `AMBIGUOUS` | **PASS** |
| 10 | **Idempotency** | Resolver run twice against identical DB $\rightarrow$ 0 duplicate transitions, identical state | **PASS** |
| 11 | **Duplicate protection** | Identical signal captured twice $\rightarrow$ `INSERT OR IGNORE` ensures exactly 1 row | **PASS** |
| 12 | **BTC/XAU isolation** | BTC signal increments only BTC count; XAU signal increments only XAU count | **PASS** |
| 13 | **Governance counting** | Only `CLEAN_FORWARD` and `('RESOLVED_WIN', 'RESOLVED_LOSS')` count toward N | **PASS** |
| 14 | **479 quarantine protection**| Authoritative DB maintains exactly 479 legacy rows; contribute 0 to N | **PASS** |

---

## G. INTEGRITY & IMMUTABILITY AUDIT

### Authoritative Database Row Preservation
- Table: `forward_shadow_signals` in `data/historical/historical_market_data.db`
- **Total Rows**: `479`
- **BTC Quarantined Rows**: `280` (`FORENSIC_CONTAMINATED_TEST_FIXTURE`)
- **XAU Quarantined Rows**: `199` (`FORENSIC_CONTAMINATED_TEST_FIXTURE`)
- **Clean Rows**: `0`
- **Pending Rows**: `0`
- **Resolved Clean N**: `0`
- **Total Mutations to 479 Quarantined Records**: `0` (Zero deletes, zero updates, zero reclassifications)

### File Hash Immutability (Double Pytest Pass Verification)
A double full-suite pytest pass was executed with before/after SHA256 validation:

| Target File | Initial SHA256 | Pass 1 SHA256 | Pass 2 SHA256 | Mutation Status |
| :--- | :--- | :--- | :--- | :---: |
| `data/historical/historical_market_data.db` | `a142181ee58252c2...` | `a142181ee58252c2...` | `a142181ee58252c2...` | **ZERO MUTATION** |
| `data/shadow_trades.db` | `d477f87fe3bcd8e5...` | `d477f87fe3bcd8e5...` | `d477f87fe3bcd8e5...` | **ZERO MUTATION** |
| `signal_records.json` | `548fdfad0ad7842d...` | `548fdfad0ad7842d...` | `548fdfad0ad7842d...` | **ZERO MUTATION** |

- **Double Test Pass Verification**: **PERFECT SUCCESS (69/69 passed twice, zero file mutations)**.

---

## H. GOVERNANCE STATUS

- **Current State**: `S2 — EVIDENCE_COLLECTION`
- **Clean XAU Resolved N**: `0`
- **Clean BTC Resolved N**: `0`
- **Milestone N50 Reached**: `NOT REACHED` ($0 < 50$)
- **Milestone N100 Reached**: `NOT REACHED` ($0 < 100$)
- **Production Gating**: `DISABLED`
- **Live Execution**: `DISABLED`
- **Blocking Reason**: `XAU forward resolved N (0) is below the minimum milestone of 50.`

---

## I. QUANT / ML / SAFETY AUDIT

1. **Quant Parameters**:
   - `DIRECTIONAL_THRESHOLD`: `20.0` (Unchanged in [`src/services/signal_aggregator.py`](file:///d:/Project/TRADE/src/services/signal_aggregator.py#L61))
   - `CONFLICT_WEIGHT_THRESHOLD`: `0.25` (Unchanged in [`src/services/signal_aggregator.py`](file:///d:/Project/TRADE/src/services/signal_aggregator.py#L59))
   - 17 Contributor Weights: Unchanged
   - Quant Logic Change: **NO**
2. **ML Models & Thresholds**:
   - ML model files in `src/models/` and `src/research/ml_research/`: Unchanged (`git status` clean)
   - ML Calibration / Thresholds: Unchanged
   - ML Change: **NO**
3. **`entry_distance_pct` Usage Audit**:
   - Ripgrep search confirmed `entry_distance_pct` is used ONLY as diagnostic schema metadata in `forward_shadow_signals`.
   - Zero rejection rules (no `if distance > 1% reject`).
   - Threshold Change: **NO**
4. **Broker / Live Execution Audit**:
   - Codebase search for `ccxt`, `MetaTrader`, `MT5`, `Alpaca`, `Interactive Brokers`, `place_order`, `create_order`, `live_trade`, `real_trade`: **0 unintended execution paths found**.
   - Broker execution: **ABSENT / DISABLED**.

---

## J. SYSTEM HEALTH & UI VERIFICATION

1. **Backend Health Check**:
   - Endpoint: `/health`
   - Response: `200 OK`
   - Status: `ok`, Feed: `online`, Gemini: `active` (`gemini-3.1-flash-lite`)
2. **Forward Shadow Validation API**:
   - Endpoint: `/api/v1/research/governance/forward-shadow-validation`
   - Response: `200 OK`
   - Data: Accurately separates `clean_forward` (Resolved N=0, Wins=0, Losses=0) from `quarantined_legacy` (BTC=280, XAU=199).
   - Filter `?generation=CLEAN_FORWARD`: Returns `resolved_signals: 0` for both BTC and XAU.
3. **Frontend Build**:
   - Command: `npm --prefix frontend run build`
   - Result: `Compiled successfully`, `Generating static pages (4/4)`, Exit Code: `0` (`PASS`).
