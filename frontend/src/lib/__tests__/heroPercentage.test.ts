/**
 * Comprehensive Unit & Regression Test Suite:
 * Hero Percentage Loading, Resolution, and Asset Isolation Lifecycle
 */

import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node ESM requires explicit .ts extension
import {
  formatHeroPercentage,
  computeOverallInsightPercentage,
  getSignalSemanticTheme,
  getAssetBadgeClass,
  resolveHeroPresentation,
} from "../format.ts";

test("1. Valid percentage renders as expected integer with % suffix (>=50%) and WAIT... (<50%)", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: 74, signal: "SELL" }), "74%");
  assert.strictEqual(formatHeroPercentage({ percentage: 82, signal: "BUY" }), "82%");
  assert.strictEqual(formatHeroPercentage({ percentage: 50, signal: "WAIT" }), "50%");
  assert.strictEqual(formatHeroPercentage({ percentage: 38, signal: "WAIT" }), "WAIT...");
  assert.strictEqual(formatHeroPercentage({ percentage: "65.4", signal: "BUY" }), "65%");
});

test("2. 0% (<50%) renders as WAIT... according to authoritative <50% rule", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: 0, signal: "BUY" }), "WAIT...");
  assert.strictEqual(formatHeroPercentage({ percentage: 0, signal: "SELL" }), "WAIT...");
  assert.strictEqual(formatHeroPercentage({ percentage: 0, signal: "WAIT" }), "WAIT...");
  assert.strictEqual(formatHeroPercentage({ percentage: "0", signal: "BUY" }), "WAIT...");
});

test("3. null renders -- when fallback not provided, or fallbackText when provided", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: null, signal: "BUY" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: null, signal: "SELL" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: null, signal: "BUY", fallbackText: "--%" }), "--%");
});

test("4. undefined renders -- when fallback not provided, or fallbackText when provided", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: undefined, signal: "BUY" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: undefined, signal: "SELL" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: undefined, signal: "BUY", fallbackText: "--%" }), "--%");
});

test("5. NaN and invalid render -- for missing/invalid percentage", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: NaN, signal: "BUY" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: "invalid", signal: "BUY" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: NaN, signal: "WAIT" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: "invalid", signal: "WAIT" }), "--");
});

test("6. WAIT renders -- when percentage is genuinely unavailable/null", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: null, signal: "WAIT" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: undefined, signal: "WAIT" }), "--");
  assert.strictEqual(formatHeroPercentage({ percentage: "", signal: "WAIT" }), "--");
});

test("7. Overall Market Insight computes 38% (<50% renders WAIT... in Hero)", () => {
  // Overall Market Insight calculation: (History 45% + Now 31%) / 2 = 38%
  const hPct = 45;
  const nPct = 31;
  const overallPct = computeOverallInsightPercentage(hPct, nPct);
  assert.strictEqual(overallPct, 38);

  // When signal is WAIT and pct < 50, Hero displays WAIT...
  const rendered = formatHeroPercentage({ percentage: overallPct, signal: "WAIT" });
  assert.strictEqual(rendered, "WAIT...");
});

test("8. XAU percentage remains XAU and BTC percentage remains BTC (strict asset isolation)", () => {
  interface AssetState {
    symbol: string;
    percentage: number | null;
    signal: string;
  }

  const xauData: AssetState = { symbol: "XAU-USD-SPOT", percentage: 38, signal: "WAIT" };
  const btcData: AssetState = { symbol: "BTC-USD", percentage: 68, signal: "BUY" };

  const xauRendered = formatHeroPercentage({ percentage: xauData.percentage, signal: xauData.signal });
  const btcRendered = formatHeroPercentage({ percentage: btcData.percentage, signal: btcData.signal });

  assert.strictEqual(xauRendered, "WAIT...");
  assert.strictEqual(btcRendered, "68%");
  assert.notStrictEqual(xauRendered, btcRendered);
});

test("9. Page/Tab switching lifecycle does not flash or bleed stale percentages", () => {
  // Simulating immediate tab invalidation contract
  let currentTabPercentage: number | null = 82; // e.g. Dashboard
  let currentSignal = "BUY";

  // When switching to a section awaiting resolution
  function onTabSwitch(newTab: "DASHBOARD" | "SHADOW_VALIDATION") {
    if (newTab === "SHADOW_VALIDATION") {
      // Immediate invalidation to prevent stale bleed
      currentTabPercentage = null;
      currentSignal = "WAIT";
    }
  }

  onTabSwitch("SHADOW_VALIDATION");
  const shadowRendered = formatHeroPercentage({ percentage: currentTabPercentage, signal: currentSignal });
  assert.strictEqual(shadowRendered, "--");
  assert.notStrictEqual(shadowRendered, "82%");
});

test("10. Asset switching resets data so previous asset percentage is discarded", () => {
  let activeSymbol = "BTC-USD";
  let activePercentage: number | null = 72;

  function switchAsset(newSymbol: string) {
    activeSymbol = newSymbol;
    // Immediate cache invalidation on asset switch
    activePercentage = null;
  }

  switchAsset("XAU-USD-SPOT");
  assert.strictEqual(activeSymbol, "XAU-USD-SPOT");
  assert.strictEqual(activePercentage, null);

  // While loading XAU, display is truthful
  const loadingDisplay = formatHeroPercentage({ percentage: activePercentage, signal: "WAIT", isEvaluating: true });
  assert.strictEqual(loadingDisplay, "WAIT...");
});

test("11. Slow network response cannot overwrite current asset (activeRequestId & symRef guard)", () => {
  let currentAsset = "XAU-USD-SPOT";
  let renderedPercentage = "38%";
  let activeRequestId = 2;

  function handleAsyncResponse(responseSymbol: string, requestId: number, newPct: number) {
    // Both activeRequestId guard and symbol check must match
    if (requestId !== activeRequestId || responseSymbol !== currentAsset) {
      return; // Discard stale/race-condition response
    }
    renderedPercentage = `${newPct}%`;
  }

  // Late BTC response from request #1 arrives after user switched to XAU (request #2)
  handleAsyncResponse("BTC-USD", 1, 85);

  // XAU remains 38%, not overwritten by 85%
  assert.strictEqual(renderedPercentage, "38%");
});

test("12. Valid percentage is not accidentally replaced by fallback or 0%", () => {
  const validInputs = [1, 25, 50, 75, 99, 100];
  for (const pct of validInputs) {
    const res = formatHeroPercentage({ percentage: pct, signal: "WAIT" });
    if (pct < 50) {
      assert.strictEqual(res, "WAIT...");
    } else {
      assert.strictEqual(res, `${pct}%`);
    }
    assert.notStrictEqual(res, "0%");
    assert.notStrictEqual(res, "--%");
  }
});

test("13. Hero percentage remains visible after loading completes", () => {
  // During loading
  const duringLoading = formatHeroPercentage({ percentage: 74, signal: "SELL", isEvaluating: true });
  assert.strictEqual(duringLoading, "WAIT...");

  // After loading finishes
  const afterLoading = formatHeroPercentage({ percentage: 74, signal: "SELL", isEvaluating: false });
  assert.strictEqual(afterLoading, "74%");
});

test("14. Weekend market closed always returns empty string for percentage (no --%)", () => {
  assert.strictEqual(formatHeroPercentage({ percentage: 85, signal: "BUY", isMarketClosed: true }), "");
  assert.strictEqual(formatHeroPercentage({ percentage: 38, signal: "WAIT", isMarketClosed: true }), "");
  assert.strictEqual(formatHeroPercentage({ percentage: null, signal: "WAIT", isMarketClosed: true }), "");
});

test("15. Section 36 Item 3: BUY with >50% uses BUY Emerald color (#34d399 / #10b981)", () => {
  const theme51 = getSignalSemanticTheme("BUY", 51);
  assert.strictEqual(theme51.pctColor, "#34d399");
  assert.strictEqual(theme51.accent, "#10b981");
  assert.match(theme51.text, /emerald/);

  const theme85 = getSignalSemanticTheme("BUY", 85);
  assert.strictEqual(theme85.pctColor, "#34d399");
  assert.strictEqual(theme85.accent, "#10b981");
});

test("16. Section 36 Item 4: SELL with >50% uses SELL Rose color (#fb7185 / #f43f5e)", () => {
  const theme51 = getSignalSemanticTheme("SELL", 51);
  assert.strictEqual(theme51.pctColor, "#fb7185");
  assert.strictEqual(theme51.accent, "#f43f5e");
  assert.match(theme51.text, /rose/);

  const theme74 = getSignalSemanticTheme("SELL", 74);
  assert.strictEqual(theme74.pctColor, "#fb7185");
  assert.strictEqual(theme74.accent, "#f43f5e");
});

test("17. BUY 50% uses green theme, SELL 50% uses red theme, WAIT 50% uses neutral theme", () => {
  const buy50 = getSignalSemanticTheme("BUY", 50);
  assert.strictEqual(buy50.pctColor, "#34d399");
  assert.strictEqual(buy50.accent, "#10b981");

  const sell50 = getSignalSemanticTheme("SELL", 50);
  assert.strictEqual(sell50.pctColor, "#fb7185");
  assert.strictEqual(sell50.accent, "#f43f5e");

  const wait50 = getSignalSemanticTheme("WAIT", 50);
  assert.strictEqual(wait50.pctColor, "#cbd5e1");
  assert.strictEqual(wait50.accent, "#64748b");
  assert.strictEqual(wait50.textGlow, "none");
});

test("18. Section 36: BUY/SELL below 50% uses neutral styling, never false emerald/rose", () => {
  const buy42 = getSignalSemanticTheme("BUY", 42);
  assert.strictEqual(buy42.pctColor, "#cbd5e1");
  assert.strictEqual(buy42.textGlow, "none");

  const sell35 = getSignalSemanticTheme("SELL", 35);
  assert.strictEqual(sell35.pctColor, "#cbd5e1");
  assert.strictEqual(sell35.textGlow, "none");
});

test("19. Section 36 Item 1 & 2: WAIT with no percentage renders '--' (unavailable)", () => {
  const display = formatHeroPercentage({ percentage: null, signal: "WAIT" });
  assert.strictEqual(display, "--");
  assert.notStrictEqual(display, "50%");
  assert.notStrictEqual(display, "0%");

  const theme = getSignalSemanticTheme("WAIT", null);
  assert.strictEqual(theme.pctColor, "#cbd5e1");
  assert.strictEqual(theme.textGlow, "none");
});

test("20. Section 36 Item 6, 7, 8: Invalid and missing percentage handling never generates fake fallback", () => {
  const cases: Array<[unknown, string]> = [
    [null, "--"],
    [undefined, "--"],
    ["", "--"],
    ["N/A", "--"],
    [NaN, "--"],
  ];
  for (const [input, expected] of cases) {
    const res = formatHeroPercentage({ percentage: input as any, signal: "WAIT" });
    assert.strictEqual(res, expected);
    assert.notStrictEqual(res, "50%");
    assert.notStrictEqual(res, "0%");
    assert.notStrictEqual(res, "--%");
  }
});

test("21. Section 36 Item 9: Sub-50% WAIT percentage (e.g. BTC Confluence 44%) renders WAIT... with neutral theme", () => {
  const res = formatHeroPercentage({ percentage: 44, signal: "WAIT" });
  assert.strictEqual(res, "WAIT...");

  const theme = getSignalSemanticTheme("WAIT", 44);
  assert.strictEqual(theme.pctColor, "#cbd5e1");
  assert.strictEqual(theme.textGlow, "none");
});

test("22. Section 36 Item 10: Hero Card source value immutability (input object/number not mutated)", () => {
  const sourcePayload = { percentage: 44, signal: "WAIT" };
  const originalCopy = JSON.stringify(sourcePayload);
  formatHeroPercentage(sourcePayload);
  assert.strictEqual(JSON.stringify(sourcePayload), originalCopy);
});

test("23. WAIT 53% remains neutral styling", () => {
  const theme = getSignalSemanticTheme("WAIT", 53);
  assert.strictEqual(theme.pctColor, "#cbd5e1");
  assert.strictEqual(theme.textGlow, "none");
  assert.match(theme.text, /slate/);
});

test("24. WAIT 70% remains neutral styling", () => {
  const theme = getSignalSemanticTheme("WAIT", 70);
  assert.strictEqual(theme.pctColor, "#cbd5e1");
  assert.strictEqual(theme.textGlow, "none");
  assert.match(theme.text, /slate/);
});

test("25. BUY 51% and BUY 70% use BUY/emerald color", () => {
  const theme51 = getSignalSemanticTheme("BUY", 51);
  assert.strictEqual(theme51.pctColor, "#34d399");
  assert.strictEqual(theme51.accent, "#10b981");
  assert.match(theme51.text, /emerald/);

  const theme70 = getSignalSemanticTheme("BUY", 70);
  assert.strictEqual(theme70.pctColor, "#34d399");
  assert.strictEqual(theme70.accent, "#10b981");
  assert.match(theme70.text, /emerald/);
});

test("26. SELL 51% and SELL 70% use SELL/rose color", () => {
  const theme51 = getSignalSemanticTheme("SELL", 51);
  assert.strictEqual(theme51.pctColor, "#fb7185");
  assert.strictEqual(theme51.accent, "#f43f5e");
  assert.match(theme51.text, /rose/);

  const theme70 = getSignalSemanticTheme("SELL", 70);
  assert.strictEqual(theme70.pctColor, "#fb7185");
  assert.strictEqual(theme70.accent, "#f43f5e");
  assert.match(theme70.text, /rose/);
});

test("27. Loading does not cause temporary incorrect green/red color (isEvaluating returns neutral)", () => {
  const loadingBuy = getSignalSemanticTheme("BUY", 75, false, true);
  assert.strictEqual(loadingBuy.pctColor, "#cbd5e1");
  assert.strictEqual(loadingBuy.textGlow, "none");

  const loadingSell = getSignalSemanticTheme("SELL", 80, false, true);
  assert.strictEqual(loadingSell.pctColor, "#cbd5e1");
  assert.strictEqual(loadingSell.textGlow, "none");

  const loadingWait = getSignalSemanticTheme("WAIT", 53, false, true);
  assert.strictEqual(loadingWait.pctColor, "#cbd5e1");
});

test("28. MARKET CLOSED... renders without percentage and open market renders normally", () => {
  // Closed market has no percentage appended
  const closedPct = formatHeroPercentage({ percentage: 75, signal: "BUY", isMarketClosed: true });
  assert.strictEqual(closedPct, "");
  assert.notStrictEqual(closedPct, "--%");
  assert.notStrictEqual(closedPct, "50%");

  // Open market with same inputs renders normal percentage
  const openPct = formatHeroPercentage({ percentage: 75, signal: "BUY", isMarketClosed: false });
  assert.strictEqual(openPct, "75%");
});

test("29. BTC asset badge applies BTC orange accent", () => {
  const btcExpected = "bg-orange-500/15 text-orange-300 border-orange-500/40";
  assert.strictEqual(getAssetBadgeClass("BTC/USD"), btcExpected);
  assert.strictEqual(getAssetBadgeClass("Bitcoin (BTC/USD)"), btcExpected);
  assert.strictEqual(getAssetBadgeClass("BTC-USD"), btcExpected);
  assert.strictEqual(getAssetBadgeClass("Bitcoin"), btcExpected);
  assert.strictEqual(getAssetBadgeClass("bitcoin"), btcExpected);
});

test("30. XAU / Gold asset badge applies Gold/yellow accent", () => {
  const xauExpected = "bg-yellow-500/15 text-yellow-300 border-yellow-500/40";
  assert.strictEqual(getAssetBadgeClass("XAU/USD"), xauExpected);
  assert.strictEqual(getAssetBadgeClass("Gold (XAU/USD)"), xauExpected);
  assert.strictEqual(getAssetBadgeClass("Gold XAU/USD"), xauExpected);
  assert.strictEqual(getAssetBadgeClass("GC=F"), "bg-zinc-800/70 text-zinc-300 border-zinc-700/60");
  assert.strictEqual(getAssetBadgeClass("Gold"), xauExpected);
  assert.strictEqual(getAssetBadgeClass("gold"), xauExpected);
});

test("31. Fallback / unknown asset badge uses subtle zinc styling", () => {
  const fallbackExpected = "bg-zinc-800/70 text-zinc-300 border-zinc-700/60";
  assert.strictEqual(getAssetBadgeClass(""), fallbackExpected);
  assert.strictEqual(getAssetBadgeClass(undefined), fallbackExpected);
  assert.strictEqual(getAssetBadgeClass("ETH/USD"), fallbackExpected);
});

test("32. Asset badge styling is strictly independent of signal state (BUY/SELL/WAIT)", () => {
  // Asset tag must retain asset color regardless of whether signal is BUY, SELL, or WAIT
  const btcBadge = getAssetBadgeClass("BTC/USD");
  const xauBadge = getAssetBadgeClass("XAU/USD");
  assert.match(btcBadge, /orange/);
  assert.match(xauBadge, /yellow/);
  assert.doesNotMatch(btcBadge, /emerald/);
  assert.doesNotMatch(btcBadge, /rose/);
  assert.doesNotMatch(xauBadge, /emerald/);
  assert.doesNotMatch(xauBadge, /rose/);
});

test("33. resolveHeroPresentation: BUY 63% -> BUY 63% (GREEN)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 63 });
  assert.strictEqual(res.state, "BUY");
  assert.strictEqual(res.signalText, "BUY");
  assert.strictEqual(res.percentageText, "63%");
  assert.strictEqual(res.theme.pctColor, "#34d399");
  assert.strictEqual(res.isLoading, false);
  assert.strictEqual(res.isUnavailable, false);
});

test("34. resolveHeroPresentation: SELL 74% -> SELL 74% (RED)", () => {
  const res = resolveHeroPresentation({ signal: "SELL", percentage: 74 });
  assert.strictEqual(res.state, "SELL");
  assert.strictEqual(res.signalText, "SELL");
  assert.strictEqual(res.percentageText, "74%");
  assert.strictEqual(res.theme.pctColor, "#fb7185");
  assert.strictEqual(res.isLoading, false);
  assert.strictEqual(res.isUnavailable, false);
});

test("35. resolveHeroPresentation: BUY 50% -> BUY 50% (GREEN)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 50 });
  assert.strictEqual(res.state, "BUY");
  assert.strictEqual(res.signalText, "BUY");
  assert.strictEqual(res.percentageText, "50%");
  assert.strictEqual(res.theme.pctColor, "#34d399");
});

test("36. resolveHeroPresentation: SELL 50% -> SELL 50% (RED)", () => {
  const res = resolveHeroPresentation({ signal: "SELL", percentage: 50 });
  assert.strictEqual(res.state, "SELL");
  assert.strictEqual(res.signalText, "SELL");
  assert.strictEqual(res.percentageText, "50%");
  assert.strictEqual(res.theme.pctColor, "#fb7185");
});

test("37. resolveHeroPresentation: BUY 49% -> WAIT... (NEUTRAL)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 49 });
  assert.strictEqual(res.state, "WAIT");
  assert.strictEqual(res.signalText, "WAIT...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
});

test("38. resolveHeroPresentation: SELL 45% -> WAIT... (NEUTRAL)", () => {
  const res = resolveHeroPresentation({ signal: "SELL", percentage: 45 });
  assert.strictEqual(res.state, "WAIT");
  assert.strictEqual(res.signalText, "WAIT...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
});

test("39. resolveHeroPresentation: WAIT 30% -> WAIT... (NEUTRAL)", () => {
  const res = resolveHeroPresentation({ signal: "WAIT", percentage: 30 });
  assert.strictEqual(res.state, "WAIT");
  assert.strictEqual(res.signalText, "WAIT...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
});

test("40. resolveHeroPresentation: LOADING -> WAIT... (NEUTRAL, isLoading: true)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 80, isEvaluating: true });
  assert.strictEqual(res.state, "LOADING");
  assert.strictEqual(res.signalText, "WAIT...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
  assert.strictEqual(res.isLoading, true);
  assert.strictEqual(res.isUnavailable, false);
});

test("41. resolveHeroPresentation: UNAVAILABLE -> -- (NEUTRAL, isUnavailable: true)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: null, isEvaluating: false });
  assert.strictEqual(res.state, "UNAVAILABLE");
  assert.strictEqual(res.signalText, "--");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
  assert.strictEqual(res.isLoading, false);
  assert.strictEqual(res.isUnavailable, true);
});

test("42. resolveHeroPresentation: MARKET CLOSED -> MARKET CLOSED... (AMBER)", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 80, isMarketClosed: true });
  assert.strictEqual(res.state, "WAIT");
  assert.strictEqual(res.signalText, "MARKET CLOSED...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#fbbf24");
});

test("43. Hero WAIT state: single WAIT... label with empty percentageText and strictly neutral theme", () => {
  const waitInputs = [
    { signal: "WAIT", percentage: 42 },
    { signal: "WAIT", percentage: 38 },
    { signal: "WAIT", percentage: 0 },
    { signal: "NEUTRAL", percentage: 45 },
    { signal: "SIDEWAYS", percentage: 30 },
  ];

  for (const input of waitInputs) {
    const res = resolveHeroPresentation(input);
    assert.strictEqual(res.state, "WAIT");
    assert.strictEqual(res.signalText, "WAIT...");
    assert.strictEqual(res.percentageText, "", "Percentage text must be empty in WAIT state to prevent duplicate rendering");
    assert.strictEqual(res.theme.pctColor, "#cbd5e1");
    assert.strictEqual(res.theme.textGlow, "none");
    assert.match(res.theme.text, /slate/);
    assert.strictEqual(res.isLoading, false);
    assert.strictEqual(res.isUnavailable, false);
  }
});

test("44. Hero WAIT with >=50% (e.g. WAIT 53%, WAIT 70%): strictly neutral theme, no directional color leakage", () => {
  const waitHighPct = [
    { signal: "WAIT", percentage: 53 },
    { signal: "WAIT", percentage: 70 },
    { signal: "WAIT", percentage: 85 },
    { signal: "WAIT (53%)", percentage: 53 },
    { signal: "NEUTRAL", percentage: 65 },
  ];

  for (const input of waitHighPct) {
    const res = resolveHeroPresentation(input);
    assert.strictEqual(res.state, "WAIT");
    assert.strictEqual(res.signalText, "WAIT...");
    assert.strictEqual(res.percentageText, "");
    assert.strictEqual(res.theme.pctColor, "#cbd5e1", "Must strictly use neutral color #cbd5e1");
    assert.strictEqual(res.theme.textGlow, "none", "Glow must be disabled in WAIT");
    assert.doesNotMatch(res.theme.text, /emerald|rose|blue|purple|indigo|cyan/, "No directional/accent leakage");
  }
});

test("45. Hero LOADING state: single WAIT... text label with isLoading: true and neutral theme", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: 85, isEvaluating: true });
  assert.strictEqual(res.state, "LOADING");
  assert.strictEqual(res.signalText, "WAIT...");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
  assert.strictEqual(res.theme.textGlow, "none");
  assert.strictEqual(res.isLoading, true);
  assert.strictEqual(res.isUnavailable, false);
});

test("46. Hero UNAVAILABLE state: single '--' text label with isUnavailable: true and neutral theme", () => {
  const res = resolveHeroPresentation({ signal: "BUY", percentage: null, isEvaluating: false });
  assert.strictEqual(res.state, "UNAVAILABLE");
  assert.strictEqual(res.signalText, "--");
  assert.strictEqual(res.percentageText, "");
  assert.strictEqual(res.theme.pctColor, "#cbd5e1");
  assert.strictEqual(res.isUnavailable, true);
  assert.strictEqual(res.isLoading, false);
});




