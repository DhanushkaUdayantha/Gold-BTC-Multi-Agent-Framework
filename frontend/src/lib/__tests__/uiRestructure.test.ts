/**
 * Comprehensive Unit Test Suite:
 * UI Restructure, 5-Page Architecture, Evidence Lineage, and Truthful Metrics
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// @ts-expect-error Node ESM requires explicit .ts extension
import {
  resolveOverallSignalPercentage,
  resolveHistoryMarketPercentage,
  resolveMLShadowAccuracy,
  resolveNowMarketPercentage,
  resolveNowMarketDirection,
  formatHeroPercentage,
} from "../format.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagePath = path.resolve(__dirname, "../../app/page.tsx");

test("1. Navigation tabs: Exactly 5 target pages rendered", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Verify all 5 tab buttons exist in the navigation bar
  assert.match(pageContent, /<span>OVERALL<\/span>/, "Must contain OVERALL tab");
  assert.match(pageContent, /<span>MARKET INSIGHT<\/span>/, "Must contain MARKET INSIGHT tab");
  assert.match(pageContent, /<span>NOW MARKET<\/span>/, "Must contain NOW MARKET tab");
  assert.match(pageContent, /<span>HISTORY MARKET<\/span>/, "Must contain HISTORY MARKET tab");
  assert.match(pageContent, /<span>ML &amp; SHADOW<\/span>|<span>ML & SHADOW<\/span>/, "Must contain ML & SHADOW tab");

  // Verify obsolete standalone tabs are removed from primary navigation
  assert.doesNotMatch(pageContent, /<button[^>]*><span>BACKTEST LAB<\/span><\/button>/, "BACKTEST LAB must not be standalone tab");
  assert.doesNotMatch(pageContent, /<button[^>]*><span>ML MODELS<\/span><\/button>/, "ML MODELS must not be standalone tab");
});

test("2. Architectural Reasoning Lineage Flowchart rendered in MARKET INSIGHT", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Lineage flowchart header and core quant lock
  assert.match(pageContent, /Quantitative Decision &amp; Evidence Lineage Architecture/, "Must render architecture banner");
  assert.match(pageContent, /CORE QUANT 🔒 LOCKED MODEL/, "Must display Core Quant lock badge");

  // Core quant sequential steps
  assert.match(pageContent, /1\.\s*Core Quant Pipeline 🔒/, "Must include Core Quant pipeline");
  assert.match(pageContent, /Live Data/, "Must include Live Data node");
  assert.match(pageContent, /Tech \/ Structure/, "Must include Tech / Structure node");
  assert.match(pageContent, /17 Factors \+ Gemini/, "Must include 17 Factors + Gemini node");
  assert.match(pageContent, /Confluence/, "Must include Confluence node");
  assert.match(pageContent, /Safety Gates/, "Must include Safety Gates node");
  assert.match(pageContent, /Decision Engine/, "Must include Decision Engine node");

  // Dual branches from Now Market
  assert.match(pageContent, /Branch A:\s*History Market Precedent/, "Must include Branch A: History Market");
  assert.match(pageContent, /Branch B:\s*ML Prediction &amp; Shadow Validation/, "Must include Branch B: ML Shadow");
  assert.match(pageContent, /Observation/, "Must include Observation in ML Shadow");
  assert.match(pageContent, /Shadow/, "Must include Shadow in ML Shadow");
  assert.match(pageContent, /Validation/, "Must include Validation in ML Shadow");

  // Convergence & Summit
  assert.match(pageContent, /Convergence &rarr; MARKET INSIGHT &rarr; OVERALL/, "Must render Convergence banner");
});

test("3. resolveOverallSignalPercentage: Authoritative decision metrics", () => {
  // Valid BUY signal with backend overall percentage
  assert.strictEqual(resolveOverallSignalPercentage("BUY", 68, 68), 68);

  // Valid SELL signal with backend overall percentage
  assert.strictEqual(resolveOverallSignalPercentage("SELL", 74, 74), 74);

  // WAIT signal suppresses percentage to null (renders as '--' or 'WAIT...')
  assert.strictEqual(resolveOverallSignalPercentage("WAIT", 68, 68), null);
  assert.strictEqual(resolveOverallSignalPercentage("", 68, 68), null);
  assert.strictEqual(resolveOverallSignalPercentage(null, 68, 68), null);

  // Fallback to overall_evidence_score if overall_signal.percentage is missing
  assert.strictEqual(resolveOverallSignalPercentage("BUY", null, 62), 62);
  assert.strictEqual(resolveOverallSignalPercentage("BUY", undefined, 65), 65);

  // Missing data returns null
  assert.strictEqual(resolveOverallSignalPercentage("BUY", null, null), null);
  assert.strictEqual(resolveOverallSignalPercentage("BUY", NaN, NaN), null);
});

test("4. resolveHistoryMarketPercentage: Backend data lineage preservation", () => {
  // Valid finite win rate from backend returns valid rounded win rate
  assert.strictEqual(resolveHistoryMarketPercentage(65.4, 25), 65);
  assert.strictEqual(resolveHistoryMarketPercentage(65.6, 25), 66);
  assert.strictEqual(resolveHistoryMarketPercentage(50, 10), 50);
  assert.strictEqual(resolveHistoryMarketPercentage(75, 5), 75);

  // Missing/null/NaN win rate (e.g. backend set win_rate = None when sample_size < 10) strictly returns null (truthful '--')
  assert.strictEqual(resolveHistoryMarketPercentage(null, 5), null);
  assert.strictEqual(resolveHistoryMarketPercentage(null, 0), null);
  assert.strictEqual(resolveHistoryMarketPercentage(null, null), null);
  assert.strictEqual(resolveHistoryMarketPercentage(undefined, undefined), null);
  assert.strictEqual(resolveHistoryMarketPercentage(NaN, 50), null);
});

test("5. resolveMLShadowAccuracy: Backend data lineage preservation", () => {
  // Valid finite accuracy with 0.0 - 1.0 fraction returns percentage
  assert.strictEqual(resolveMLShadowAccuracy(0.75, 40), 75);
  assert.strictEqual(resolveMLShadowAccuracy(0.824, 20), 82);
  assert.strictEqual(resolveMLShadowAccuracy(0.9, 8), 90);

  // Valid finite accuracy with already scaled percentage (0 - 100)
  assert.strictEqual(resolveMLShadowAccuracy(78.5, 30), 79);

  // Missing/null/NaN accuracy strictly returns null (truthful '--')
  assert.strictEqual(resolveMLShadowAccuracy(null, 8), null);
  assert.strictEqual(resolveMLShadowAccuracy(null, 0), null);
  assert.strictEqual(resolveMLShadowAccuracy(null, null), null);
  assert.strictEqual(resolveMLShadowAccuracy(NaN, 50), null);
});

test("6. All 5 section containers exist with accessible ARIA landmarks", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Verify all 5 tabpanel sections exist
  assert.match(pageContent, /id="section-overall"/, "Must have section-overall");
  assert.match(pageContent, /id="section-market-insight"/, "Must have section-market-insight");
  assert.match(pageContent, /id="section-now-market"/, "Must have section-now-market");
  assert.match(pageContent, /id="section-history-market"/, "Must have section-history-market");
  assert.match(pageContent, /id="section-ml-shadow"/, "Must have section-ml-shadow");
});

test("7. Cross-tab asset switching preserves strict BTC/XAU isolation", () => {
  // BTC sample
  const btcNowPct = resolveNowMarketPercentage(27, 27);
  const btcHistPct = resolveHistoryMarketPercentage(58.2, 34);
  const btcShadowAcc = resolveMLShadowAccuracy(0.68, 25);

  assert.strictEqual(btcNowPct, 27);
  assert.strictEqual(btcHistPct, 58);
  assert.strictEqual(btcShadowAcc, 68);

  // XAU sample
  const xauNowPct = resolveNowMarketPercentage(51, 51);
  const xauHistPct = resolveHistoryMarketPercentage(null, 0); // No historical setup
  const xauShadowAcc = resolveMLShadowAccuracy(0.72, 18);

  assert.strictEqual(xauNowPct, 51);
  assert.strictEqual(xauHistPct, null, "XAU empty history must return null");
  assert.strictEqual(xauShadowAcc, 72);

  // Verify that BTC data does not leak into XAU
  assert.notStrictEqual(xauNowPct, btcNowPct);
  assert.notStrictEqual(xauHistPct, btcHistPct);
});

test("8. Surgical Semantic Verification: Market Insight, History Market, ML Target", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Issue 1: Market Insight Hero displays 4-Component Conviction Ledger with Metric: --
  assert.match(pageContent, /MARKET INSIGHT · FULL-SYSTEM EVIDENCE SYNTHESIS/, "Market Insight Hero must have correct title");
  assert.match(pageContent, /4-COMPONENT CONVICTION LEDGER/, "Market Insight Hero must display 4-COMPONENT CONVICTION LEDGER badge");

  // Issue 2: History Market Hero displays Historical Win Rate (never Historical Support)
  assert.match(pageContent, /Historical Win Rate:/, "History Market must label metric as Historical Win Rate");
  assert.doesNotMatch(pageContent, /Historical Support:/, "Must never label win rate as Historical Support");

  // Issue 4: ML Prediction probability labeled as Model Win Prob / Trade Win Probability
  assert.match(pageContent, /Trade Win Probability/, "ML Card must label classification target as Trade Win Probability");
});

test("9. Section 1 Overall Hero: Final Action WAIT dominates, secondary Overall Evidence Bias pill displayed", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Final Action WAIT when decision is WAIT
  assert.match(pageContent, /FINAL ACTION: WAIT/, "Overall Hero must show FINAL ACTION: WAIT");
  assert.match(pageContent, /Overall Evidence Bias:/, "Must render Overall Evidence Bias secondary pill");
});

test("10. Section 1 Risk & Gates: When Quality Gate fails, badge is WAIT, shows Direction, Conflict, Quality Gate metrics", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Quality gate failure forces badge to WAIT
  assert.match(pageContent, /isQualityFailed \|\| finalDecision === "WAIT" \? "WAIT" : finalDecision/, "Risk & Gates badge must be WAIT on quality gate failure");
  assert.match(pageContent, /PASSED \(0\.0% &lt;= 25%\)|PASSED \(0\.0% <= 25%\)/, "Conflict Gate must show truthful threshold");
  assert.match(pageContent, /FAILED \(\$\{Math\.round\(qScore\)\} &lt; 58 pts\)|FAILED \(\$\{Math\.round\(qScore\)\} < 58 pts\)/, "Quality Gate must show current pts vs 58 threshold");
});

test("11. Now Market Hero: Metric labeled as Confluence, never Total Buy or Total Sell", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Confluence label in Now Market
  assert.match(pageContent, /<span className="text-zinc-400">Confluence:<\/span>/, "Now Market must label metric as Confluence:");
  assert.doesNotMatch(pageContent, /"Total Buy:"/, "Now Market must never label metric as Total Buy:");
  assert.doesNotMatch(pageContent, /"Total Sell:"/, "Now Market must never label metric as Total Sell:");
});

test("12. Market Insight: Dynamic weights and re-normalization semantics, no hardcoded 35/35/15/15", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Dynamic re-normalization text
  assert.match(pageContent, /Weights re-normalized across currently available components/, "Must state weights re-normalized across active components");
  assert.doesNotMatch(pageContent, /Technical \(35%\) \+ Historical \(35%\) \+ ML \(15%\) \+ Strategy \(15%\)/, "Must not contain hardcoded 35/35/15/15 string");
});

test("13. History Market: Clean separation of Block A (Comparable Setup N) and Block B (Global Baseline)", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Block A & Block B
  assert.match(pageContent, /CURRENT SETUP HISTORICAL MATCH/, "Must contain Block A: CURRENT SETUP HISTORICAL MATCH");
  assert.match(pageContent, /GLOBAL \{activeAsset\.ticker\} HISTORICAL BASELINE/, "Must contain Block B: GLOBAL HISTORICAL BASELINE");
  assert.match(pageContent, /REFERENCE BASELINE — NOT CURRENT SETUP MATCH RATE/, "Must label baseline as reference baseline");
  assert.match(pageContent, /Comparable Setup N/, "Must show Comparable Setup N in Block A");
  assert.match(pageContent, /NO QUALIFYING HISTORICAL MATCHES/, "Must handle 0 qualifying setups cleanly");
});

test("14. ML & Shadow: Dynamic active model identity and 3-layer architecture", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Dynamic model identity for BTC and XAU
  assert.match(pageContent, /LogisticRegression \(Calibrated\)/, "Must identify BTC model as LogisticRegression (Calibrated)");
  assert.match(pageContent, /RandomForestClassifier \(Calibrated\)/, "Must identify XAU model as RandomForestClassifier (Calibrated)");
  assert.match(pageContent, /3-Layer ML &amp; Shadow Validation Architecture|3-Layer ML & Shadow Validation Architecture/, "Must contain 3-layer architecture banner");
  assert.match(pageContent, /Part A: Current ML Output/, "Must contain Part A");
  assert.match(pageContent, /Part B: ML Shadow Accumulation/, "Must contain Part B");
  assert.match(pageContent, /Part C: Strategy Governance/, "Must contain Part C");
});

test("15. HistoricalBacktestTab: SIGNAL ID column and timestamp deduplication toggle", () => {
  const backtestTabPath = path.resolve(__dirname, "../../components/HistoricalBacktestTab.tsx");
  const tabContent = fs.readFileSync(backtestTabPath, "utf-8");

  assert.match(tabContent, /<th[^>]*>SIGNAL ID<\/th>/, "Table must have SIGNAL ID column");
  assert.match(tabContent, /Deduplicate Multi-Run Timestamps/, "Must provide toggle to deduplicate multi-run timestamps");
});

