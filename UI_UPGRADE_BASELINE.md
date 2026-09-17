# Professional Quant Trading UI Upgrade Baseline Audit

**Repository**: `D:\Project\TRADE`  
**Date**: 2026-09-04  
**Audit Scope**: Frontend presentation layer, asset isolation, Hero card semantics, relative time formatting, and component hygiene across all four primary application sections.

---

## 1. Executive Summary & Audit Classification

| Section / Component | Current State | Audit Action | Rationale |
| :--- | :--- | :--- | :--- |
| **Sticky Header Asset Selector** | Liquid-glass `Gold [XAU/USD] \| Bitcoin [BTC/USD]` selector in `page.tsx` (lines 2790–2825) | **KEEP** | Authoritative selector with refined visual styling, state management, and direct integration with active trading parameters. |
| **AssetTabBar.tsx (Redundant)** | Duplicate tab bar previously created at `frontend/src/components/AssetTabBar.tsx` | **REMOVE** | Redundant duplicate selector violating single-selector requirement. Safely deleted; imports removed. |
| **Dashboard Hero Card** | `SignalHeroCard` in Section 1 | **KEEP & ENHANCE** | Single selected-asset decision card (`BUY 78%`, `WAIT --%`) displaying truthful percentage and action levels. Enhanced with auto-refreshing relative time. |
| **Market Insights Hero Card** | `NowMarketSignalHero` & `HistoricalMarketSignalHero` | **KEEP & ENHANCE** | Truthful live confluence grade and historical sample metrics. Wired to real source timestamps. |
| **ML Intelligence Hero Card** | `SignalHeroCard` inside `MLModelsTab.tsx` | **FIX & ENHANCE** | Mapped real out-of-sample probability (`ml.prob`). Fixed `--%` fallback when prob is null. Added real observation timestamp. Kept model evaluation metrics separated from trading confidence. |
| **Shadow Validation Hero Card** | `SignalHeroCard` inside `ShadowAccumulationMonitor.tsx` | **KEEP & ENHANCE** | Displays actual forward win rate, accumulation progress towards N≥100, and isolated active asset counts. Wired to real ISO timestamp. |
| **Relative Time Formatting** | Fragmented static time formats (`fmtTime` returning static HH:MM:SS) | **FIX / UNIFY** | Replaced with pure deterministic `formatRelativeTime` utility and non-polling `useRelativeTime` hook. |
| **Relative Time Test Matrix** | Missing deterministic boundary tests | **RESTORE / CREATE** | Implemented `relativeTime.test.ts` covering all 18 exact boundary cases, pluralization, and fallbacks. |
| **Dual BTC/XAU Side-by-Side Cards** | Former side-by-side layout on Dashboard | **REMOVE** | Completely eliminated in favor of strict single-asset view. |

---

## 2. Four Primary Sections Audit

### Section 1: Dashboard (`DASHBOARD`)
- **Asset Selector**: Header sticky selector controls `symbol` (`"XAU-USD-SPOT"` vs `"BTC-USD"`).
- **Hero Card**: `SignalHeroCard`
  - **Decision Representation**: Selected-asset decision (`BUY`, `SELL`, or `WAIT`).
  - **Percentage Source**: `data.decision?.percentage`. When `WAIT`, strictly displays `--%`.
  - **Action Levels**: Entry price, Stop Loss, TP1, TP2 displayed when directional setup is active; dashes when awaiting confluence.
  - **Timestamp**: Real source timestamp (`data.technical?.data_timestamp || data.price?.timestamp || data.decision?.timestamp`).
  - **Action**: **KEEP** existing layout and single-card isolation.

### Section 2: Market Insights (`MARKET_INSIGHTS`)
- **Sub-Tabs**:
  1. `now` (Now Market Analysis):
     - Hero: `NowMarketSignalHero` passing real confluence and live grade (`A`, `B`, `C`).
     - Technical Matrix: Real indicators (RSI14, MACD, Trend Structure).
     - MTF Alignment: Real multi-timeframe agreement (5m, 15m, 1h, 4h).
     - Gemini AI Analysis: Real AI structured synthesis.
  2. `history` (Historical Performance & Backtest):
     - Hero: `HistoricalMarketSignalHero` rendering empirical win rate, calibrated probability, sample size N.
     - Strategy Benchmarks: Strictly filtered to active asset (BTC Champion vs XAU Champion).
  - **Action**: **KEEP** and ensure all header freshness indicators use `RelativeTime`.

### Section 3: ML Intelligence (`ML_INTELLIGENCE`)
- **Hero Card**: `SignalHeroCard` (`ML MODEL RELIABILITY & SHADOW VALIDATION`)
  - **Percentage Source**: Real out-of-sample prediction probability (`ml.prob * 100`).
  - **Truth Policy**: When `prob == null`, displays `WAIT --%`. Never mislabels model evaluation metrics (Accuracy, ECE, Brier Score) as trading confidence.
  - **Observations**: Real recorded observation count for the active asset only.
  - **Timestamp**: Real observation timestamp or sync timestamp.
  - **Action**: **FIX & KEEP** (Enforced truthful null percentage and added relative timestamp).

### Section 4: Shadow Validation (`SHADOW_VALIDATION`)
- **Hero Card**: `SignalHeroCard` (`FORWARD SHADOW VALIDATION ACCUMULATION ENGINE`)
  - **Percentage Source**: Real forward win rate percentage calculated strictly from resolved shadow trades.
  - **Sample Counts**: Sample count $N$ presented as sample progression ($N / 100$), NEVER as trading confidence.
  - **Asset Isolation**: Card 1 renders strictly active asset metrics (`{assetTicker} Resolved N`, `{assetTicker} Pending N`).
  - **Timestamp**: Real ISO timestamp from `lastRefreshedAt`.
  - **Action**: **KEEP** with isolated metrics.

---

## 3. Signal Semantics Verification

Approved project visual language:
- `BUY` $\rightarrow$ Emerald / Green (`#10b981` / `#34d399`)
- `SELL` $\rightarrow$ Rose / Red (`#f43f5e` / `#fb7185`)
- `WAIT` $\rightarrow$ Neutral Slate / Zinc (`#64748b` / `#cbd5e1`), with zero artificial glow (`textGlow: "none"`).
- `MARKET CLOSED` $\rightarrow$ Amber badge (`#fbbf24`), directional levels disabled.

---

## 4. Reusable Relative Time Specification

Unified utility in `frontend/src/lib/relativeTime.ts`:
- `< 60s` $\rightarrow$ `0s ago`, `1s ago`, `12s ago`, `59s ago`
- `60–119s` $\rightarrow$ `1 min ago`
- `120s+` $\rightarrow$ `2 mins ago`, `5 mins ago`, `59 mins ago`
- `60m+` $\rightarrow$ `1 hr ago`
- `120m+` $\rightarrow$ `2 hrs ago`, `23 hrs ago`
- `24h+` $\rightarrow$ `1 day ago`
- `48h+` $\rightarrow$ `2 days ago`
- Invalid / Missing $\rightarrow$ `--`
- Auto-refresh: Local 5000ms ticker with ZERO network calls.
