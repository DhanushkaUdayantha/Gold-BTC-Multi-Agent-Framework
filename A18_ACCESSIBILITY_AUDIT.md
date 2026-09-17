# A18 — ACCESSIBILITY FORENSIC AUDIT REPORT

**Audit Date**: September 14, 2026  
**Governance State**: `S2 — EVIDENCE_COLLECTION`  
**Production Gating**: `DISABLED`  
**Live Execution**: `DISABLED`  
**Audit Outcome**: `PASS`

---

## 1. EXECUTIVE SUMMARY

The **A18 Accessibility Forensic Audit** conducted a comprehensive, evidence-based verification of accessibility across all five primary tabs (`OVERALL`, `MARKET INSIGHT`, `NOW MARKET`, `SHADOW`, `ML MODELS`) of the active trading dashboard.

The audit verified adherence to WCAG 2.1 / 2.2 AA standards, keyboard navigation pathways, focus visibility, ARIA role mapping, color contrast against the dark theme, accessible names for controls and icons, table header relationships, dialog modal semantics, and operating system reduced-motion preferences.

---

## 2. DETAILED AUDIT CHECKLIST ACROSS 5 TABS

### Tab 1: OVERALL
- **Tab Navigation & Activation**: Keyboard focus navigates logically (`Tab`), activating tab panel via `Enter` or `Space`. Tab element declares `role="tab"`, `aria-selected="true"`, `aria-controls="section-overall"`, and panel declares `role="tabpanel"` and `aria-labelledby="tab-overall"`.
- **Hero Card & Progress Indicator**: SVG circular progress ring marked with `aria-hidden="true"` as decorative art. Textual signal, percentage, and action levels (Entry, SL, TP1, TP2) are fully readable by screen readers.
- **Chart Controls**: Zoom in, Zoom out, Reset, and Crosshair buttons have explicit `type="button"` and `aria-label` descriptors.
- **Demo Trade History Table**: Declares `aria-label="Closed demo trade history"` and all column headers enforce `scope="col"` for screen reader table navigation. Expand/collapse toggle declares `aria-expanded` and `aria-controls`.

### Tab 2: MARKET INSIGHT
- **Unified Narrative Cards**: Structured using semantic `h2`, `h3`, `h4` headings and `section` wrappers.
- **Directional Grids**: High-contrast text colors (`text-emerald-400`, `text-rose-400`, `text-cyan-300`, `text-zinc-100`) against `#0c1424` card backgrounds ensure compliance with WCAG AA 4.5:1 text contrast.
- **Signal Detail Modal**: Implements `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-signal-record-title"`, explicit close button `aria-label="Close signal record details"`, and keyboard `Escape` dismissal.

### Tab 3: NOW MARKET
- **Live Price & Indicators**: Tab declares `role="tab"`, `aria-selected="true"`, `aria-controls="section-current-market"`.
- **SMC / ICT Status Badges**: Uses readable contrast with paired textual indicators (`SWEEP DETECTED` / `ORDERLY FLOW`, `MSS Confirmed`).
- **Momentum & Level Readouts**: Real numeric values (e.g. RSI, MACD, Support, Resistance) formatted cleanly with tabular numbers.

### Tab 4: SHADOW
- **Shadow Accumulation Monitor**: Section panel declares `role="tabpanel"` and `aria-labelledby="tab-shadow"`.
- **Progress Milestones**: Screen readers receive clean text descriptions of milestone targets (`25`, `50`, `100` trades).
- **Quarantine Isolation Callouts**: Quarantined test signal notices are distinctly styled and labeled.
- **Shadow Validation Table**: Wrapped in `overflow-x-auto` with clear column headers.

### Tab 5: ML MODELS
- **ML Tab Navigation**: Tab declares `role="tab"`, `aria-selected="true"`, `aria-controls="section-ml-models"`.
- **Glossary & Metric Definitions**: Accuracy, Precision, Recall, F1, Brier, and ECE explained in accessible glossary cards.
- **Point-in-Time Observations**: Table toggle uses accessible button with expand/collapse label.
- **Signal Inspector Modal**: Modal dialog implements `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-signal-inspector-title"`, explicit `aria-label="Close signal inspector modal"` on close button, and keyboard `Escape` dismissal.

---

## 3. GLOBAL ACCESSIBILITY ENHANCEMENTS APPLIED

1. **Global Focus Visibility (WCAG 2.4.7 & 2.4.11)**:
   - Added `:focus-visible` in `frontend/src/app/globals.css` with `outline: 2px solid #38bdf8 !important; outline-offset: 2px !important;`.
   - Guarantees keyboard navigators receive an unmistakable focus indicator on every interactive control without disrupting mouse users.
2. **OS Reduced Motion Respect (WCAG 2.2 SC 2.3.3)**:
   - Added `@media (prefers-reduced-motion: reduce)` in `frontend/src/app/globals.css` that reduces animations and transitions to near-zero duration (`0.01ms`), preventing vestibular discomfort.
3. **Semantic Navigation & ARIA Tabs Pattern**:
   - Primary navigation bar in `frontend/src/app/page.tsx` upgraded to `<nav aria-label="Primary Dashboard Sections">` with `role="tablist"` and `role="tab"` on all 5 buttons.
   - All 5 primary tab views mapped to `role="tabpanel"` with matching `id` and `aria-labelledby` connections.
4. **Accessible Icon-Only and Header Controls**:
   - Added `aria-label` to header logo button, subtitle button, and refresh button in `frontend/src/app/page.tsx`.
   - Added `type="button"`, `role="tab"`, `aria-selected`, and `aria-label` to Asset Selector buttons.
   - Added `type="button"` and `aria-label` to chart controls (`ZoomIn`, `ZoomOut`, `Reset`, `Crosshair`) in `frontend/src/components/CandleChart.tsx`.
   - Added `aria-hidden="true"` to decorative circular SVG progress ring in `frontend/src/components/SignalHeroCard.tsx`.
5. **Modal Accessibility & Escape Dismissal**:
   - `EmpiricalPerformancePanel.tsx` modal: Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-signal-record-title"`, `aria-label="Close signal record details"` on close button, and keyboard `Escape` key dismissal.
   - `HistoricalBacktestTab.tsx` modal: Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-signal-inspector-title"`, `aria-label="Close signal inspector modal"` on close button, and keyboard `Escape` key dismissal.
6. **Table Structure**:
   - Added `scope="col"` to column headers and `aria-label="Closed demo trade history"` on table in `frontend/src/app/page.tsx`.

---

## 4. FILES MODIFIED (FRONTEND ONLY)

1. `frontend/src/app/globals.css`: Focus-visible outline and prefers-reduced-motion media query.
2. `frontend/src/app/page.tsx`: Semantic `<nav>`, ARIA tablist/tab/tabpanel roles, accessible names on header buttons, and table `scope="col"`.
3. `frontend/src/components/CandleChart.tsx`: `type="button"` and `aria-label` on chart controls.
4. `frontend/src/components/EmpiricalPerformancePanel.tsx`: Dialog ARIA attributes, close button label, and Escape key dismissal.
5. `frontend/src/components/HistoricalBacktestTab.tsx`: Dialog ARIA attributes, close button label, and Escape key dismissal.
6. `frontend/src/components/SignalHeroCard.tsx`: Decorative SVG `aria-hidden="true"`.

---

## 5. CRYPTOGRAPHIC & DATA INTEGRITY PROOF

### SHA256 Hashes of Protected Artifacts
| File | Baseline SHA256 | Current Post-Audit SHA256 | Status |
|---|---|---|---|
| `signal_records.json` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | `138C0BB9E6B22CAD99F5A5DC6792285000FD17FE5917CF4859F0576EAAD849B5` | **MATCH** |
| `data/historical/historical_market_data.db` | `CA1E2AFCA0DDB99C6FF8704B4A8CD9A1E0D7665BDD09D7797FF561751C12A488` | `CA1E2AFCA0DDB99C6FF8704B4A8CD9A1E0D7665BDD09D7797FF561751C12A488` | **MATCH** |
| `data/governance_forward_state.json` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | `23DB7EC99F7E12687F985B6ED3534924F72F0FD68FDD8595B818B53E53D7BF4B` | **MATCH** |
| `data/shadow_trades.db` | `D593F5500CD413B22BD22983B5CB6BCE77415F3E89AB9310E6E88489F7C8F919` | `D593F5500CD413B22BD22983B5CB6BCE77415F3E89AB9310E6E88489F7C8F919` | **MATCH** |
| `data/gating_state.json` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | `65B356577E053F264FD1C0ED468745506F0F839FE9CE8D0237B95CF066A3D1DF` | **MATCH** |

### Database Row Counts
- `ml_shadow_observations`: **3,828** (Unchanged)
- `forward_shadow_signals`: **479** (Unchanged)
- `shadow_trades`: **5** (Unchanged)

### Verification Suite
- **ESLint**: `0 errors, 0 warnings` (`npm --prefix frontend run lint`)
- **Frontend Unit Tests**: `99 / 99 PASS` (`npm --prefix frontend test`)
- **Backend Targeted Pytest**: `26 / 26 PASS` (4.31s)
- **Next.js Production Build**: `PASS` (4/4 static pages, 0 errors, 0 warnings)
- **Production Gating**: `DISABLED`
- **Live Execution**: `DISABLED`
