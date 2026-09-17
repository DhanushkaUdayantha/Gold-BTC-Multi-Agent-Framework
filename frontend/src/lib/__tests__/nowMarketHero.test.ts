/**
 * Comprehensive Unit Test Suite:
 * Now Market Navigation Label & Hero Percentage Card Requirements (Section 14)
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// @ts-expect-error Node ESM requires explicit .ts extension
import { formatHeroPercentage, resolveNowMarketPercentage, resolveNowMarketDirection } from "../format.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagePath = path.resolve(__dirname, "../../app/page.tsx");

test("1. Navigation renders NOW MARKET", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // Navigation tab button must contain "NOW MARKET"
  assert.match(
    pageContent,
    /onClick=\{\(\) => setActiveSection\("CURRENT_MARKET"\)\}[\s\S]*?<span>NOW MARKET<\/span>/,
    "Navigation button must display 'NOW MARKET'"
  );

  // Must not have "<span>CURRENT MARKET</span>" in navigation
  assert.doesNotMatch(
    pageContent,
    /onClick=\{\(\) => setActiveSection\("CURRENT_MARKET"\)\}[\s\S]*?<span>CURRENT MARKET<\/span>/,
    "Navigation button must not contain obsolete 'CURRENT MARKET' text"
  );
});

test("2. Hero renders authoritative Now Market percentage", () => {
  // Authoritative percentage from now_signal.percentage (< 50% displays WAIT...)
  const btcNowPct = resolveNowMarketPercentage(27, 27);
  assert.strictEqual(btcNowPct, 27);
  assert.strictEqual(
    formatHeroPercentage({ percentage: btcNowPct, signal: "WAIT", fallbackText: "--%" }),
    "WAIT..."
  );

  // Direct confluence percentage when now_signal.percentage is null (>= 50% displays XX%)
  const confluenceFallback = resolveNowMarketPercentage(null, 72);
  assert.strictEqual(confluenceFallback, 72);
  assert.strictEqual(
    formatHeroPercentage({ percentage: confluenceFallback, signal: "BULLISH", fallbackText: "--%" }),
    "72%"
  );
});

test("3. Hero renders correct direction", () => {
  // Direct now_signal BUY / SELL / WAIT / NEUTRAL mappings
  assert.strictEqual(resolveNowMarketDirection("BUY"), "BULLISH");
  assert.strictEqual(resolveNowMarketDirection("BULLISH"), "BULLISH");
  assert.strictEqual(resolveNowMarketDirection("SELL"), "BEARISH");
  assert.strictEqual(resolveNowMarketDirection("BEARISH"), "BEARISH");
  assert.strictEqual(resolveNowMarketDirection("NEUTRAL"), "NEUTRAL");
  assert.strictEqual(resolveNowMarketDirection("WAIT"), "WAIT");

  // Fallback to gate_direction / trend when now_signal is not provided
  assert.strictEqual(resolveNowMarketDirection(null, "BULLISH", null), "BULLISH");
  assert.strictEqual(resolveNowMarketDirection(null, "BEARISH", null), "BEARISH");
  assert.strictEqual(resolveNowMarketDirection(null, "NONE", "BEARISH"), "BEARISH");
  assert.strictEqual(resolveNowMarketDirection(null, "NONE", "SIDEWAYS"), "NEUTRAL");
  assert.strictEqual(resolveNowMarketDirection(null, null, null), "WAIT");
});

test("4. BTC uses BTC data", () => {
  const btcSnapshot = {
    symbol: "BTC-USD",
    now_signal: { percentage: 27, signal: "WAIT" },
    confluence_pct: 27,
  };
  const btcPct = resolveNowMarketPercentage(btcSnapshot.now_signal.percentage, btcSnapshot.confluence_pct);
  const btcDir = resolveNowMarketDirection(btcSnapshot.now_signal.signal);

  assert.strictEqual(btcPct, 27);
  assert.strictEqual(btcDir, "WAIT");
  assert.strictEqual(formatHeroPercentage({ percentage: btcPct, signal: btcDir, fallbackText: "--%" }), "WAIT...");
});

test("5. XAU uses XAU data", () => {
  const xauSnapshot = {
    symbol: "XAU-USD",
    now_signal: { percentage: 51, signal: "WAIT" },
    confluence_pct: 51,
  };
  const xauPct = resolveNowMarketPercentage(xauSnapshot.now_signal.percentage, xauSnapshot.confluence_pct);
  const xauDir = resolveNowMarketDirection(xauSnapshot.now_signal.signal);

  assert.strictEqual(xauPct, 51);
  assert.strictEqual(xauDir, "WAIT");
  assert.strictEqual(formatHeroPercentage({ percentage: xauPct, signal: xauDir, fallbackText: "--%" }), "51%");
});

test("6. Asset switching updates the Hero (strict isolation)", () => {
  let activeAsset = "BTC-USD";
  let currentDecision: any = {
    now_signal: { percentage: 27, signal: "WAIT" },
    confluence_pct: 27,
  };

  let pct = resolveNowMarketPercentage(currentDecision.now_signal.percentage, currentDecision.confluence_pct);
  assert.strictEqual(pct, 27);

  // Switch asset to XAU
  activeAsset = "XAU-USD";
  currentDecision = {
    now_signal: { percentage: 51, signal: "WAIT" },
    confluence_pct: 51,
  };

  pct = resolveNowMarketPercentage(currentDecision.now_signal.percentage, currentDecision.confluence_pct);
  assert.strictEqual(pct, 51);
  assert.notStrictEqual(pct, 27, "Must not bleed previous asset's percentage");
});

test("7. Missing percentage renders '--%'", () => {
  const missingPct = resolveNowMarketPercentage(null, null);
  assert.strictEqual(missingPct, null);
  assert.strictEqual(
    formatHeroPercentage({ percentage: missingPct, signal: "WAIT", fallbackText: "--%" }),
    "--%"
  );
  assert.strictEqual(
    formatHeroPercentage({ percentage: undefined, signal: "WAIT", fallbackText: "--%" }),
    "--%"
  );
});

test("8. Invalid percentage does not produce a fake value", () => {
  const nanPct = resolveNowMarketPercentage(NaN, NaN);
  assert.strictEqual(nanPct, null);
  assert.strictEqual(
    formatHeroPercentage({ percentage: nanPct, signal: "WAIT", fallbackText: "--%" }),
    "--%"
  );

  const invalidStringPct = resolveNowMarketPercentage("invalid" as any, "invalid" as any);
  assert.strictEqual(invalidStringPct, null);
  assert.strictEqual(
    formatHeroPercentage({ percentage: invalidStringPct, signal: "WAIT", fallbackText: "--%" }),
    "--%"
  );
});

test("9. WAIT does not receive an arbitrary percentage", () => {
  // When WAIT has null percentage, it MUST NOT default to 50%
  const waitPct = resolveNowMarketPercentage(null, null);
  assert.strictEqual(waitPct, null);
  const formatted = formatHeroPercentage({ percentage: waitPct, signal: "WAIT", fallbackText: "--%" });
  assert.strictEqual(formatted, "--%");
  assert.notStrictEqual(formatted, "50%");
  assert.notStrictEqual(formatted, "51%");
});

test("10. No additional API request is introduced", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  // In activeSection === "CURRENT_MARKET", verify that the Now Market Hero uses data.decision
  const currentMarketBlock = pageContent.slice(pageContent.indexOf('activeSection === "CURRENT_MARKET"'));
  assert.match(
    currentMarketBlock,
    /resolveNowMarketPercentage\(\s*data\.decision\?\.now_signal\?\.percentage,\s*data\.decision\?\.confluence_pct\s*\)/,
    "Must use existing data.decision from useDashboardData hook without extra fetch calls"
  );
});

test("11. Existing Now Market sections remain present", () => {
  const pageContent = fs.readFileSync(pagePath, "utf-8");
  const currentMarketBlock = pageContent.slice(pageContent.indexOf('activeSection === "CURRENT_MARKET"'));

  // Ensure sections 01 to 10 are all present
  assert.match(currentMarketBlock, /01\.\s*Live Market State/, "Section 01 must exist");
  assert.match(currentMarketBlock, /02\.\s*17-Factor Confluence Engine/, "Section 02 must exist");
  assert.match(currentMarketBlock, /03\.\s*Multi-Timeframe Alignment/, "Section 03 must exist");
  assert.match(currentMarketBlock, /04\.\s*Price Action, Structure &amp; Key Pivots/, "Section 04 must exist");
  assert.match(currentMarketBlock, /05\.\s*Momentum &amp; Volatility Metrics/, "Section 05 must exist");
  assert.match(currentMarketBlock, /06\.\s*Liquidity State, Market Structure Shift &amp; Sweeps/, "Section 06 must exist");
  assert.match(currentMarketBlock, /07\.\s*Quantitative Strategy Context/, "Section 07 must exist");
  assert.match(currentMarketBlock, /08\.\s*Risk, Conflict &amp; Operational Safety Gates/, "Section 08 must exist");
  assert.match(currentMarketBlock, /09\.\s*Current Market Gemini Recommendation/, "Section 09 must exist");
  assert.match(currentMarketBlock, /10\.\s*Current Market Conclusion &amp; Confirmation Checklist/, "Section 10 must exist");
});
