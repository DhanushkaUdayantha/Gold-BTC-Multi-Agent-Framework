# BTC/XAU FORWARD SHADOW — CORRECTIVE ARCHITECTURE & ENTRY-FILL FORENSIC AUDIT

**Audit Date**: September 9, 2026  
**Auditor**: Senior Quantitative Systems Auditor & Software Forensic Engineer  
**Repository**: `D:\Project\TRADE`  
**Database**: `data/historical/historical_market_data.db`  
**Authoritative Table**: `forward_shadow_signals`  
**Governance State**: `S2 — EVIDENCE_COLLECTION` (Production Gating: `DISABLED` | Live Execution: `DISABLED`)

---

## 1. EXECUTIVE SUMMARY

A forensic investigation was conducted into the 479 historical records in `forward_shadow_signals` (280 BTC/USD and 199 XAU/USD). The investigation established that the currently reported forward shadow validation metrics:

* **BTC/USD**: 280 WIN / 0 LOSS (100.0% Win Rate)
* **XAU/USD**: 130 WIN / 69 LOSS (65.3% Win Rate)

**DO NOT REPRESENT EXECUTABLE TRADING PERFORMANCE OR EMPIRICAL STRATEGY EDGE.**

### Root Cause Summary:
1. **Price Disconnection Artifact**: The records in `forward_shadow_signals` contain static test fixture prices (BTC Entry $\approx \$64,000.00$, TP $\approx \$65,880.00$; XAU Entry $\approx \$2,700.00$, TP $\approx \$2,736.00$, SL $\approx \$2,720.00$). However, the underlying market candles during the signal capture window (September 2–8, 2026) were trading at **\$76,264.00 – \$82,300.00** for BTC and **\$4,329.00 – \$4,558.00** for Gold.
2. **Missing Entry-Fill Validation**: The outcome resolver worker evaluates whether completed 5m candle prices cross TP or SL **without first verifying whether market price ever reached the Entry price**.
3. **Guaranteed 100% Win / Loss Bias**:
   * For BTC (100% BUY signals): Every 5m candle high ($\ge \$76,826.00$) was far above the TP level (\$65,880.00), triggering an instantaneous WIN on candle 1 for **100% of signals**, even though market price never reached the entry order (\$64,000.00).
   * For XAU: Every BUY signal instantly hit TP (\$4,450.00 $\ge \$2,736.00$ $\to$ **100% WIN**), and every SELL signal instantly hit SL (\$4,450.00 $\ge \$2,720.00$ $\to$ **100% LOSS**). The reported 65.3% win rate is simply the ratio of BUY setups in the dataset ($130 / 199 = 65.326\%$).
4. **Test/Production Pipeline Bleed**: Unit test suites (`test_btc_shadow_step1.py`, `test_btc_shadow_step2.py`, etc.) instantiated `BTCShadowRunner` and `XAUShadowRunner` with isolated mock paper stores (`tmp_path / "test_shadow.db"`), but did not override the default `ForwardShadowEngine` singleton, which defaulted to writing test fixture payloads directly into the live production SQLite database (`data/historical/historical_market_data.db`).

---

## 2. CURRENT SHADOW RESULTS (DATABASE TRUTH)

Authoritative counts directly queried from `data/historical/historical_market_data.db`:

```sql
SELECT 
    asset,
    COUNT(*) as total,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN outcome = 'PENDING' THEN 1 ELSE 0 END) as pending,
    ROUND(CAST(SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS FLOAT) / 
          NULLIF(SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END), 0) * 100.0, 1) as win_rate
FROM forward_shadow_signals
GROUP BY asset;
```

| Asset | Raw Signals | Current Resolved | Pending | Current Wins | Current Losses | Current Win Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BTC/USD** | **280** | **280** | **0** | **280** | **0** | **100.0%** |
| **XAU/USD** | **199** | **199** | **0** | **130** | **69** | **65.3%** |

---

## 3. ENTRY PRICE PROVENANCE & SOURCE CODE TRACE

The source code was audited to determine how `entry_price`, `stop_loss`, `take_profit_1`, and `take_profit_2` were generated:

### A. Live Decision Engine (Real Strategy Logic)
In [`src/services/decision_engine.py`](file:///D:/Project/TRADE/src/services/decision_engine.py#L997-L1060), `DecisionEngine._calculate_levels()` dynamically calculates ATR-based and Support/Resistance-based levels from the live market price:
* `stop_loss = round(min(price - safe_atr * 1.5, support_sl), 2)`
* `tp1 = round(entry_mid + risk * 1.5, 2)`
* When running against live data, the engine dynamically produces realistic levels around current market price.

### B. Shadow Runner Capture Layer
In [`src/services/btc_shadow_runner.py`](file:///D:/Project/TRADE/src/services/btc_shadow_runner.py#L43-L86) and [`src/services/xau_shadow_runner.py`](file:///D:/Project/TRADE/src/services/xau_shadow_runner.py#L39-L80):
* `evaluate_live_market_setup` takes `current_price`, `direction`, `stop_loss`, `take_profit_1`, `take_profit_2` as arguments.
* It forwards these arguments directly into `self.forward_engine.capture_forward_signal(entry_price=current_price, ...)` without price-distance verification.

### C. Test Runner Invocation (The Bleed Vector)
In test files such as [`tests/test_btc_shadow_step1.py`](file:///D:/Project/TRADE/tests/test_btc_shadow_step1.py#L21-L140) and [`tests/test_btc_shadow_step2.py`](file:///D:/Project/TRADE/tests/test_btc_shadow_step2.py#L28-L70):
```python
# Test fixture payload:
runner.evaluate_live_market_setup(
    current_price=64000.0,
    direction="BUY",
    stop_loss=63000.0,
    take_profit_1=65880.0,
    take_profit_2=66500.0,
    ...
)
```
* **Origin Classification**: **STATIC TEST FIXTURE VALUES**.
* These values did not originate from the live market price feed or dynamic live strategy calculations. They were hardcoded parameters inside test routines that bypassed mock database isolation.

---

## 4. T0 MARKET PRICE COMPARISON & DISTANCE DISTRIBUTION

For every signal in `forward_shadow_signals`, the nearest valid market candle in `candles` at or immediately prior to `signal_timestamp` ($T_0$) was extracted, and the relative distance was calculated:

$$\text{entry\_distance\_pct} = \frac{|\text{market\_price}_{T_0} - \text{entry\_price}|}{\text{market\_price}_{T_0}} \times 100$$

### Summary Statistics:

| Metric | BTC/USD (280 signals) | XAU/USD (199 signals) |
| :--- | :---: | :---: |
| **Minimum Absolute Distance** | \$12,523.31 | \$1,723.60 |
| **Median Absolute Distance** | \$16,769.91 | \$1,813.60 |
| **Mean Absolute Distance** | \$15,680.28 | \$1,791.81 |
| **Maximum Absolute Distance** | \$17,614.52 | \$1,840.60 |
| **Minimum Distance (%)** | 16.32% | 38.96% |
| **Median Distance (%)** | 20.75% | 40.18% |
| **Mean Distance (%)** | 19.63% | 39.89% |
| **Maximum Distance (%)** | 21.58% | 40.54% |
| **Entry Below Market** | **280 (100.0%)** | **199 (100.0%)** |
| **Entry Above Market** | **0 (0.0%)** | **0 (0.0%)** |
| **Entry At Market ($\pm 0.1\%$)** | **0 (0.0%)** | **0 (0.0%)** |

* **Zero signals** were created within reasonable proximity ($\pm 0.5\%$) of the actual market price at $T_0$.
* All 280 BTC entry prices were **16% to 22% below market**.
* All 199 XAU entry prices were **39% to 41% below market**.

---

## 5. ENTRY SEMANTICS

Based on system documentation and `DecisionEngine` specifications:
* Intended Semantics: **LIMIT_ENTRY** (or pullback entry to support/SR/EMA confluence zones).
* In real execution, a limit order placed 20% below current market on a BUY setup requires market price to retrace downwards to the entry price before a position is opened:
  $$\text{Fill Condition (BUY)}: \text{Market Low} \le \text{Entry Price}$$
* **Resolver Flaw**: The resolver currently treats all signals as **MARKET_ENTRY** filled instantaneously at $T_0$ regardless of price discrepancy.

---

## 6. ENTRY FILL & FIRST-EVENT ORDER ANALYSIS

For every signal, all subsequent 5m completed market candles within a 48-hour observation window were evaluated chronologically to determine whether Entry, TP, or SL was reached first:

### Chronological Event Categories:
1. `TP_BEFORE_ENTRY`: Market touched the Take Profit target before ever dropping down to fill the Entry limit order.
2. `SL_BEFORE_ENTRY`: Market touched the Stop Loss target before ever filling the Entry order.
3. `SAME_CANDLE_ENTRY_AND_EXIT`: Candle range spanned both Entry and Exit on the initial bar.
4. `ENTRY_FIRST`: Entry was filled, followed by normal TP/SL tracking on subsequent bars.
5. `NO_EVENT`: Neither Entry, TP, nor SL was touched within 48 hours.

### Chronological Event Distribution:

| Event Sequence | BTC/USD Signals | XAU/USD Signals | Tradability Meaning |
| :--- | :---: | :---: | :--- |
| **`TP_BEFORE_ENTRY`** | **280 (100.0%)** | **130 (65.3%)** | **Order never filled; TP reached in vacuum $\to$ NOT TRIGGERED** |
| **`SAME_CANDLE_ENTRY_AND_EXIT`** | **0 (0.0%)** | **69 (34.7%)** | **Candle opened far above Entry & SL $\to$ AMBIGUOUS / GAP** |
| **`ENTRY_FIRST`** | **0 (0.0%)** | **0 (0.0%)** | **Valid filled trade** |
| **`SL_BEFORE_ENTRY`** | **0 (0.0%)** | **0 (0.0%)** | Order never filled |
| **`NO_EVENT`** | **0 (0.0%)** | **0 (0.0%)** | Expired without event |

---

## 7. CRITICAL OUTCOME RECLASSIFICATION (READ-ONLY FORENSIC DERIVATION)

Per Section 5 of the audit specification, existing records were reclassified using realistic execution semantics without modifying database records:

### Reclassification Definitions:
* **`NOT_TRIGGERED`**: Entry was never reached during the observation window. The order expired unfilled.
* **`TRIGGERED_WIN`**: Entry was filled first, and TP was touched before SL.
* **`TRIGGERED_LOSS`**: Entry was filled first, and SL was touched before TP.
* **`TRIGGERED_EXPIRED`**: Entry was filled, but position closed after 48h without hitting SL or TP.
* **`AMBIGUOUS`**: Both Entry and SL/TP were crossed on the same candle, preventing intrabar order resolution.

### Forensic Reclassification Results:

| Forensic Status | BTC/USD Count | BTC/USD % | XAU/USD Count | XAU/USD % |
| :--- | :---: | :---: | :---: | :---: |
| **`NOT_TRIGGERED`** | **280** | **100.0%** | **130** | **65.3%** |
| **`AMBIGUOUS`** | **0** | **0.0%** | **69** | **34.7%** |
| **`TRIGGERED_WIN`** | **0** | **0.0%** | **0** | **0.0%** |
| **`TRIGGERED_LOSS`** | **0** | **0.0%** | **0** | **0.0%** |
| **`TRIGGERED_EXPIRED`** | **0** | **0.0%** | **0** | **0.0%** |
| **Total Reclassified** | **280** | **100.0%** | **199** | **100.0%** |

---

## 8. CURRENT WIN RATE VS REALISTIC TRIGGERED WIN RATE

$$\text{Current Win Rate} = \frac{\text{Recorded Wins}}{\text{Recorded Wins} + \text{Recorded Losses}} \times 100$$

$$\text{Triggered Win Rate} = \frac{\text{TRIGGERED\_WIN}}{\text{TRIGGERED\_WIN} + \text{TRIGGERED\_LOSS}} \times 100$$

### Comparative Metrics:

| Metric | BTC/USD | XAU/USD |
| :--- | :---: | :---: |
| **Current Recorded Shadow Win Rate** | **100.0%** (280/280) | **65.3%** (130/199) |
| **Forensic Triggered Win Rate** | **N/A** (0 triggered trades) | **N/A** (0 triggered trades) |
| **Not-Triggered Rate** | **100.0%** (280/280) | **65.3%** (130/199) |
| **Triggered Executable Rate** | **0.0%** (0/280) | **0.0%** (0/199) |
| **Ambiguous / Gap Rate** | **0.0%** (0/280) | **34.7%** (69/199) |

* **Conclusion**: Out of 479 historical forward shadow records across BTC and XAU, **exactly 0 represent valid, filled, executed trading positions**.

---

## 9. SIGNAL INDEPENDENCE & SETUP CLUSTERING

A cryptographic and temporal clustering audit was conducted on all records:

* **Raw Records**: 280 BTC, 199 XAU.
* **Unique Setup Fingerprints** `(Direction, Entry, SL, TP, Strategy)`:
  * **BTC**: **Only 3 unique setups** across 280 records.
    * Setup 1 (`BUY @ 64,000.0 | SL 63,000.0 | TP 65,880.0`): **207 records** (73.9%)
    * Setup 2 (`BUY @ 64,200.0 | SL 63,200.0 | TP 66,000.0`): **72 records** (25.7%)
    * Setup 3 (`BUY @ 64,200.0 | SL 63,500.0 | TP 65,500.0`): **1 record** (0.4%)
  * **XAU**: **Only 2 unique setups** across 199 records.
    * Setup 1 (`BUY @ 2,700.0 | SL 2,680.0 | TP 2,736.0`): **130 records** (65.3%)
    * Setup 2 (`SELL @ 2,700.0 | SL 2,720.0 | TP 2,664.0`): **69 records** (34.7%)
* **Temporal Overlap**:
  * **BTC**: 217 signals (77.5%) were captured while a prior identical signal was still open.
  * **XAU**: 106 signals (53.3%) overlapped with an active trade.
* **Burst Clusters**:
  * 72 distinct minutes contain 2 to 4 identical signal entries created within milliseconds of each other.
* **Independent Market Events**:
  * The 479 records represent at most **4 to 5 unique test execution batches**, not 479 independent market opportunities.

---

## 10. TEST / PRODUCTION PATH SEPARATION ANALYSIS

```text
[ Test Suite / Rollout Test ]
            │
            ▼
    [ Runner Class ] (BTCShadowRunner / XAUShadowRunner)
      ├── shadow_store = Isolated temp DB (tmp_path / test_shadow.db)  <-- ISOLATED
      └── forward_engine = get_forward_shadow_engine()                  <-- LEAKAGE VECTOR
                                   │
                                   ▼ (Defaults to live DB!)
            [ historical_market_data.db: forward_shadow_signals ]
                                   │
                                   ▼
            [ Background ForwardShadowResolverWorker ]
              (Evaluates real 5m market candles at $78k against $64k test setups)
```

### Architectural Defect Identified:
1. `BTCShadowRunner` and `XAUShadowRunner` allowed test callers to inject custom mock paper stores via `shadow_store=test_db`.
2. However, the runners defaulted `forward_engine` to `get_forward_shadow_engine()`, which connects to `data/historical/historical_market_data.db`.
3. Consequently, running pytest suites or integration scripts generated mock test signals into the authoritative historical database.
4. **Required Fix for Future Phase**: Decouple `forward_engine` in test environments to guarantee that test suites run against in-memory or `tmp_path` databases exclusively.

---

## 11. PROPOSED CORRECTIVE ARCHITECTURE (FUTURE PHASE SPECIFICATION)

The forward-shadow observation engine must be upgraded from a naive candle-touch tracker to an **Authoritative Order Lifecycle Engine**:

```text
                                 [ Live Market Feed (T0) ]
                                             │
                                             ▼
                                 [ DecisionService Pipeline ]
                                  (Dynamic ATR Levels at T0)
                                             │
                                             ▼
                           [ ForwardShadowEngine: T0 Capture ]
                           ├── Verify: |Entry - T0_Price| / T0_Price <= Threshold
                           ├── Status: 'PENDING_ENTRY'
                           └── Cryptographic Snapshot Minted
                                             │
                                             ▼
                            [ Order Lifecycle Resolver Worker ]
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [ Entry Fill Check ]                        [ Expiration Check ]
             Low <= Entry (BUY) or                      Observation window > 48h
             High >= Entry (SELL)                       without fill
                       │                                           │
          ┌────────────┴────────────┐                              ▼
          ▼                         ▼                     'NOT_TRIGGERED'
       [ YES ]                    [ NO ]                  (Excluded from WR)
          │                         │
          ▼                         ▼
   'ACTIVE_POSITION'        Continue Monitoring
   (Entry Timestamp Logged)  Until Expiry
          │
          ▼
   [ TP / SL Monitoring ]
   (Strictly on post-fill bars)
          │
   ┌──────┴──────┐
   ▼             ▼
 'WIN'        'LOSS'
```

### Key Architectural Invariants:
1. **Entry Distance Filter at Capture**: Signals where `abs(entry - market_price) / market_price > MAX_ENTRY_DRIFT` (e.g. 1.0%) must be rejected as invalid or stale before capture.
2. **Two-Stage State Machine**:
   * Stage 1: `PENDING_ENTRY` (Monitors for entry touch).
   * Stage 2: `ACTIVE_POSITION` (Monitors for TP/SL touch strictly after entry fill).
   * Stage 3: `RESOLVED_WIN`, `RESOLVED_LOSS`, `NOT_TRIGGERED` (unfilled expiry).
3. **Tradability Win Rate Formula**:
   $$\text{Tradable Win Rate} = \frac{\text{Filled Wins}}{\text{Filled Wins} + \text{Filled Losses}} \times 100$$
   * `NOT_TRIGGERED` orders must be reported separately as execution efficiency metrics, never counted as trade wins.

---

## 12. GOVERNANCE IMPACT & REMEDIATION ROADMAP

1. **Governance State Preservation**:
   * Current governance state: **`S2: EVIDENCE_COLLECTION`**.
   * Production Gating: **`DISABLED`** (Maintained).
   * Live Execution: **`DISABLED`** (Maintained).
   * The 280 BTC and 199 XAU forward-shadow records **MUST NOT** be used to satisfy governance milestones $N \ge 50$ or $N \ge 100$.
2. **Recommended Safe Sequence**:
   * **Phase A (Current)**: Architecture & forensic audit completed. Zero code or data modifications made.
   * **Phase B (Future Plan)**: Implement test-database isolation so tests cannot write to `historical_market_data.db`.
   * **Phase C (Future Plan)**: Implement the two-stage entry fill state machine (`PENDING_ENTRY` $\to$ `ACTIVE` $\to$ `RESOLVED`) in `forward_shadow_resolver_worker.py`.
   * **Phase D (Future Plan)**: Re-initialize live forward shadow observation with dynamic real-time market pricing.

---

```text
========================================
FORWARD SHADOW TRADABILITY VERDICT
========================================

BTC RAW SIGNALS: 280
BTC CURRENT WINS: 280
BTC CURRENT LOSSES: 0

BTC ENTRY REACHED: 0
BTC ENTRY NOT REACHED: 280
BTC TRIGGERED WINS: 0
BTC TRIGGERED LOSSES: 0
BTC TRIGGERED EXPIRED: 0
BTC AMBIGUOUS: 0

BTC CURRENT SHADOW WR: 100.0%
BTC FORENSIC TRIGGERED WR: N/A (0 triggered trades)

XAU RAW SIGNALS: 199
XAU CURRENT WINS: 130
XAU CURRENT LOSSES: 69

XAU ENTRY REACHED: 69
XAU ENTRY NOT REACHED: 130
XAU TRIGGERED WINS: 0
XAU TRIGGERED LOSSES: 0
XAU TRIGGERED EXPIRED: 0
XAU AMBIGUOUS: 69

XAU CURRENT SHADOW WR: 65.3%
XAU FORENSIC TRIGGERED WR: N/A (0 triggered trades)

BTC UNIQUE SETUPS: 3
XAU UNIQUE SETUPS: 2

BTC INDEPENDENTNESS:
NOT PROVEN

XAU INDEPENDENCE:
NOT PROVEN

STATIC FIXTURE CONTAMINATION:
YES

ENTRY FILL TRACKING:
ABSENT

RESOLVER TP/SL BEFORE ENTRY:
YES

CURRENT RESULTS TRUSTWORTHY AS EXECUTABLE TRADES:
NO

STRATEGY CHANGE:
NO

ML CHANGE:
NO

DATABASE MUTATION:
NONE

PRODUCTION GATING:
DISABLED

LIVE EXECUTION:
DISABLED

OVERALL:
PASS WITH FINDINGS

BLOCKING ISSUE:
All 479 forward-shadow signals originated from static test fixture parameters ($64k BTC, $2.7k XAU) that leaked into historical_market_data.db via unisolated test runners. The resolver evaluated real $78k / $4.45k candles without verifying entry fill, causing 100% false-positive wins on BUYs.

NEXT SAFE ACTION:
Keep Production Gating and Live Execution strictly DISABLED. In a planned future phase, isolate test suite runners to prevent mock fixture database writes, implement the two-stage entry fill state machine (PENDING_ENTRY -> ACTIVE -> RESOLVED), and re-commence natural forward accumulation with dynamic live market prices.
========================================
```
