# BTC + XAU UI TRUTH CONSISTENCY AUDIT & SURGICAL REMEDIATION REPORT

**Date:** 2026-09-13  
**Auditor / Roles:** Senior Frontend Architect, Quantitative Systems Auditor, Data Integrity Auditor, ML Governance Auditor, Production Safety Engineer  
**Repository:** `D:\Project\TRADE`  
**Live Broker Execution:** STRICTLY DISABLED (HARD-LOCKED)  

---

## Executive Verdict

**PASS**

A forensic read-first audit and surgical remediation of the BTC/USD and XAU/USD frontend interfaces was executed. All 20 UI truth consistency requirements (Section 27), including data isolation, clean forward evidence milestone isolation (Clean N=0 -> NOT REACHED), 4-factor aggregator base weight alignment, sequential gate transparency, and real timestamp enforcement, are fully satisfied and verified.

---

## BTC

* **Final Decision:** WAIT (authoritative decision field)
* **Directional Bias:** BUY / WAIT (direction gate threshold: |Net Score| >= 20.0 pts)
* **Confluence:** 31% / 31 / 100 (Technical Score: 26 / 90, Gemini Confirmation: 5 / 10)
* **ML:** Nominal Weight: 26% (Aggregator base weight) · Execution Authority: 0% (Shadow Advisory Observer) · Probability: Authoritative model inference
* **Clean Forward N:** 0 (Authoritative clean forward governance count from `clean_forward.resolved_signals`)
* **Quarantined N:** 280 (Forensic development test fixtures quarantined and strictly segregated)
* **N50:** NOT REACHED (0 / 50 — NOT REACHED)
* **N100:** NOT REACHED (0 / 100 — NOT REACHED)
* **Risk:** Labeled by authoritative source: Gemini Environmental Risk ("MEDIUM") distinct from Model Volatility Risk
* **Timestamps:** Real source timestamp; missing/unavailable renders safe `"--"` (wall-clock fallback eliminated)
* **UI Issues Found:**
  1. `fmtClock()` fallback fabricated current wall-clock time when server timestamp was missing.
  2. Raw `resolved_signals: 280` in `ShadowAccumulationMonitor.tsx` included quarantined fixtures, falsely displaying `280/50 PASSED`, `280/100 PASSED`, and `100% WR`.
  3. Legacy hardcoded 15%/35% text in `MLModelsTab.tsx` conflicted with 26% BTC base weight in `SignalAggregator`.
  4. Confluence score and technical score lacked denominator clarification (/90 vs /100).
* **Fixes Applied:**
  1. Removed `fmtClock()` fallback in `useDashboardData.ts`; renders safe `""` / `"--"`.
  2. Sourced `cleanResolvedN` from `clean_forward.resolved_signals`; quarantined 280 fixtures isolated to dedicated card; clean milestones display `0 / 50 — NOT REACHED` and `Win Rate: --`.
  3. Dynamic 4-factor aggregator weights in `MLModelsTab.tsx` (25/27/26/22) and clarified 0% execution authority.
  4. Delineated `Technical Score: X / 90` vs `Confluence Score: Y / 100`, and added Gate Pipeline breakdown (`Directional Bias: BUY · Final Action: WAIT — Quality Gate <58%`).

---

## XAU

* **Final Decision:** WAIT (authoritative decision field; weekend market closed)
* **Directional Bias:** WAIT (authoritative aggregator direction)
* **Confluence:** Safe unavailable state (`--`) during market closure
* **ML:** Nominal Weight: 24% (Aggregator base weight) · Execution Authority: 0% (Shadow Advisory Observer)
* **Clean Forward N:** 0 (Authoritative clean forward governance count from `clean_forward.resolved_signals`)
* **Quarantined N:** 199 (Forensic development test fixtures quarantined and strictly segregated)
* **N50:** NOT REACHED (0 / 50 — NOT REACHED)
* **N100:** NOT REACHED (0 / 100 — NOT REACHED)
* **Risk:** Labeled by authoritative source; distinct from BTC risk metrics
* **Timestamps:** Real source timestamp (2026-09-11 Friday market close); strictly isolated from BTC
* **UI Issues Found:**
  1. Raw `resolved_signals: 199` falsely counted toward S2 milestones in shadow monitor.
  2. Hardcoded BTC 26% fallback in `page.tsx` was improperly applied to XAU.
  3. `fmtClock()` fallback fabricated current browser time for closed weekend market.
* **Fixes Applied:**
  1. Segregated 199 quarantined fixtures into dedicated isolated card; clean N=0 displays `NOT REACHED` and `--` for WR/EV.
  2. Made nominal weight fallback asset-aware (`activeAsset.id === 'BTC' ? '26%' : '24%'`).
  3. Strict real timestamp display preserves Friday market close without fabrication.

---

## Cross-Asset Isolation

**PASS**

* BTC state and XAU state are strictly isolated across all pages (Overall, Now Market, Market Insight, Shadow, ML Models).
* Asset switching immediately resets and decouples data; no BTC price, score, or timestamp leaks into XAU views, and vice versa.
* Verified by automated test cases 1, 2, 8, and 19.

---

## ML Consistency

**PASS**

* Nominal aggregator weights dynamically match `SignalAggregator` configuration: BTC (26%), XAU (24%).
* Execution authority is uniformly declared across all components as `0% (Observer Only)`.
* ML probability and prediction reflect authoritative model outputs without contradiction between ML Models tab and Market Insight.

---

## Forward Evidence Display

**PASS**

* Clean forward evidence is strictly decoupled from quarantined forensic test fixtures (280 BTC, 199 XAU).
* When Clean N = 0:
  - N50: `0 / 50 — NOT REACHED`
  - N100: `0 / 100 — NOT REACHED`
  - Win Rate: `--`
  - Expected Value: `-- (Awaiting Clean Evidence)`
  - Profit Factor: `--`
  - Max Drawdown: `--`
* Quarantined fixtures are housed in a dedicated audit-only container with status `QUARANTINED (EXCLUDED FROM GATING)`.

---

## Timestamp Integrity

**PASS**

* `fmtClock()` wall-clock fallback has been completely removed from `useDashboardData.ts`.
* Missing, null, or invalid timestamps consistently display `"--"`.
* Shared relative time formatter (`relativeTime.ts`) follows exact duration intervals (<60s -> `Xs ago`, 60-119s -> `1 min ago`, 120s+ -> `X mins ago`, 60m+ -> `1 hr ago`, 24h+ -> `1 day ago`) without firing additional API requests.

---

## Quant Mutation

**NONE**

* `git diff --stat src/services/decision_engine.py src/services/signal_aggregator.py src/services/confluence_engine.py` confirmed **0 bytes / 0 lines modified**.
* Direction Gate (20.0 pts), Conflict Gate (25.0%), and Quality Gate (58%) remain strictly unchanged.

---

## ML Mutation

**NONE**

* Model architectures, feature extractors, calibration tables, hyperparameters, and weights remain 100% untouched.

---

## Database Mutation

**NONE**

* `data/historical/historical_market_data.db`: Unchanged
* `data/forward_shadow_signals.db`: Unchanged
* `data/shadow_trades.db`: Unchanged
* `signal_records.json`: Unchanged
* Zero evidence records inserted, deleted, modified, or manually resolved.

---

## Tests

* **Frontend:** 59 / 59 passed (100%)
* **Backend Run 1:** 796 / 796 passed (100%)
* **Backend Run 2:** 796 / 796 passed (100%)

---

## Build

**PASS**

* Next.js 14.2.4 production build: Exit code 0 (4/4 static pages generated cleanly).

---

## Production Gating

**DISABLED**

* `PRODUCTION_GATING = DISABLED` hard-locked in governance and backend routes.

---

## Live Execution

**DISABLED**

* Real broker order routing and execution capabilities remain strictly disabled. System operates in read-only advisory / shadow observation mode.

---

## Remaining Issues

* None. All 20 UI truth consistency requirements, defect remediations, and verification criteria are satisfied without deferred items.
