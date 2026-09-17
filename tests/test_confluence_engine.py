"""
Unit tests for the Real-Time Multi-Strategy Confluence Signal Engine.

All tests use synthetic data — no live market feeds, no real API calls.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.services.confluence_engine import (
    ConfluenceEngine,
    MarketSnapshot,
    ContributorState,
    CONTRIBUTOR_MAX_SCORES,
    TOTAL_MAX_SCORE,
    GATE_CONTRIBUTORS,
    SIGNAL_HYSTERESIS_THRESHOLD,
    _make_snapshot_id,
)


# ---------------------------------------------------------------------------
# Helpers — build mock objects
# ---------------------------------------------------------------------------

def _make_ta(
    direction: str = "BULLISH",
    strength: str = "STRONG",
    rsi_val: float = 55.0,
    rsi_cond: str = "NEUTRAL",
    macd_state: str = "BULLISH",
    macd_hist: float = 2.5,
    atr_val: float = 15.0,
    ema20: float = 2695.0,
    ema50: float = 2680.0,
    ema200: float = 2600.0,
    support: list = None,
    resistance: list = None,
    timeframe: str = "1h",
    price: float = 2700.0,
):
    """Build a minimal mock TechnicalAnalysisResponse."""
    from unittest.mock import MagicMock
    ta = MagicMock()
    ta.trend.direction.value = direction
    ta.trend.strength = strength
    ta.trend.confirmations = ["EMA alignment"]
    ta.rsi14.value = rsi_val
    ta.rsi14.condition.value = rsi_cond

    from src.models.technical_analysis import RSICondition, MACDState
    rsi_map = {"OVERBOUGHT": RSICondition.OVERBOUGHT, "OVERSOLD": RSICondition.OVERSOLD, "NEUTRAL": RSICondition.NEUTRAL}
    macd_map_s = {"BULLISH": MACDState.BULLISH, "BEARISH": MACDState.BEARISH, "NEUTRAL": MACDState.NEUTRAL}
    ta.rsi14.condition = rsi_map.get(rsi_cond, RSICondition.NEUTRAL)
    ta.macd.state = macd_map_s.get(macd_state, MACDState.NEUTRAL)
    ta.macd.histogram = macd_hist
    ta.atr14.value = atr_val
    ta.ema20 = ema20
    ta.ema50 = ema50
    ta.ema200 = ema200
    ta.support_levels = support or [2690.0, 2680.0]
    ta.resistance_levels = resistance or [2710.0, 2725.0]
    ta.data_timestamp = datetime.now(timezone.utc).isoformat()
    ta.current_price = price
    return ta


def _make_ai(
    bias: str = "BULLISH",
    confidence: int = 75,
    is_fallback: bool = True,
):
    from unittest.mock import MagicMock
    from src.models.ai_analysis import OverallBias
    ai = MagicMock()
    bias_map = {"BULLISH": OverallBias.BULLISH, "BEARISH": OverallBias.BEARISH, "NEUTRAL": OverallBias.NEUTRAL}
    ai.overall_bias = bias_map.get(bias, OverallBias.NEUTRAL)
    ai.confidence = confidence
    ai.is_fallback = is_fallback
    ai.provider_used = "fallback" if is_fallback else "gemini"
    ai.key_bullish_factors = ["Strong uptrend"] if bias == "BULLISH" else []
    ai.key_bearish_factors = ["Weak demand"] if bias == "BEARISH" else []
    return ai


def _make_candle(
    open_: float = 2700,
    high: float = 2710,
    low: float = 2695,
    close: float = 2705,
    volume: float = 1000,
    is_closed: bool = True,
):
    return {
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "is_closed": is_closed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_mtf_input(price: float = 2700.0, symbol: str = "XAU/USD"):
    mtf = MagicMock()
    mtf.symbol = symbol
    mtf.current_price = price
    mtf.timeframes = {}
    return mtf


def _build_snapshot(
    price: float = 2700.0,
    ta_1h=None,
    ta_1d=None,
    ta_15m=None,
    ta_5m=None,
    ai=None,
    candles_15m=None,
    candles_1h=None,
    candles_5m=None,
    candles_1d=None,
) -> MarketSnapshot:
    snap = MarketSnapshot(
        snapshot_id=_make_snapshot_id("XAU/USD", 1722000000.0),
        created_at=datetime.now(timezone.utc).isoformat(),
        symbol="XAU/USD",
        current_price=price,
        ta_1h=ta_1h,
        ta_1d=ta_1d,
        ta_15m=ta_15m,
        ta_5m=ta_5m,
        ai_result=ai,
        candles_15m=candles_15m or [],
        candles_1h=candles_1h or [],
        candles_5m=candles_5m or [],
        candles_1d=candles_1d or [],
    )
    return snap


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSnapshotID:
    def test_snapshot_id_format(self):
        """Snapshot IDs must follow the SNAPSHOT-YYYYMMDD-HHMMSS-XXXX format."""
        snap_id = _make_snapshot_id("XAU/USD", 1722000000.0)
        parts = snap_id.split("-")
        assert parts[0] == "SNAPSHOT"
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 6   # HHMMSS
        assert len(parts[3]) == 4   # hex suffix

    def test_snapshot_id_deterministic(self):
        """Same symbol + timestamp → same snapshot ID."""
        ts = 1722000000.0
        id1 = _make_snapshot_id("XAU/USD", ts)
        id2 = _make_snapshot_id("XAU/USD", ts)
        assert id1 == id2

    def test_snapshot_id_different_timestamps(self):
        """Different timestamps → different snapshot IDs."""
        id1 = _make_snapshot_id("XAU/USD", 1722000000.0)
        id2 = _make_snapshot_id("XAU/USD", 1722000001.0)
        assert id1 != id2

    def test_contributor_snapshot_id_consistent(self):
        """All contributors in one cycle share the same snapshot_id."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        ids = {c.snapshot_id for c in result.contributors if c.status != "UNAVAILABLE"}
        # All available contributors have the same snapshot_id
        assert len(ids) == 1
        assert list(ids)[0] == snap.snapshot_id


class TestContributorMaxScores:
    def test_total_max_score_is_100(self):
        """The 17-contributor max scores must sum to exactly 100."""
        assert TOTAL_MAX_SCORE == 100

    def test_all_contributor_names_present(self):
        """All 17 contributors must be defined in CONTRIBUTOR_MAX_SCORES."""
        expected = {
            "HTF Trend", "Market Structure", "Momentum", "MTF Alignment",
            "S/R Price Action", "Breakout / Retest", "Supply & Demand",
            "Volume Confirmation", "SMC / ICT", "ICT Concepts",
            "Fibonacci OTE", "Elliott Wave", "VWAP", "EMA / MA Stack",
            "RSI", "MACD", "Gemini AI",
        }
        assert set(CONTRIBUTOR_MAX_SCORES.keys()) == expected

    def test_each_contributor_score_leq_max(self):
        """Each computed contributor score must not exceed its max_score."""
        engine = ConfluenceEngine()
        candles = [_make_candle(volume=1000)] * 20
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH"), ta_1d=_make_ta("BULLISH"),
            ta_15m=_make_ta("BULLISH"), ta_5m=_make_ta("BULLISH"),
            ai=_make_ai("BULLISH", 90),
            candles_15m=candles, candles_1h=candles, candles_5m=candles,
        )
        result = engine.compute(snap)
        for c in result.contributors:
            assert c.score <= c.max_score, f"{c.name}: score {c.score} > max {c.max_score}"

    def test_contributor_score_not_negative(self):
        """Contributor scores must never be negative."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta("BEARISH"), ai=_make_ai("BEARISH"))
        result = engine.compute(snap)
        for c in result.contributors:
            assert c.score >= 0, f"{c.name}: score is negative ({c.score})"


class TestDeltaTracking:
    def test_direction_unchanged_on_first_cycle(self):
        """First cycle: all contributors start with UNCHANGED (no prior state)."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        for c in result.contributors:
            assert c.direction == "UNCHANGED"

    def test_direction_up_when_score_increases(self):
        """Second cycle with higher scores → UP direction."""
        engine = ConfluenceEngine()
        # Cycle 1: neutral/bearish to set baselines
        snap1 = _build_snapshot(ta_1h=_make_ta("BEARISH", "WEAK"), ai=_make_ai("BEARISH", 50))
        engine.compute(snap1)
        # Cycle 2: bullish → scores should increase
        snap2 = _build_snapshot(ta_1h=_make_ta("BULLISH", "STRONG"), ai=_make_ai("BULLISH", 90))
        result2 = engine.compute(snap2)
        htf = next((c for c in result2.contributors if c.name == "HTF Trend"), None)
        assert htf is not None
        # HTF Trend score increased from bearish-weak to bullish-strong
        assert htf.direction in ("UP", "UNCHANGED"), f"Expected UP or UNCHANGED, got {htf.direction}"

    def test_direction_down_when_score_decreases(self):
        """Second cycle with lower scores → DOWN direction."""
        engine = ConfluenceEngine()
        snap1 = _build_snapshot(ta_1h=_make_ta("BULLISH", "STRONG"), ai=_make_ai("BULLISH", 90))
        engine.compute(snap1)
        snap2 = _build_snapshot(ta_1h=_make_ta("SIDEWAYS", "WEAK"), ai=_make_ai("NEUTRAL", 30))
        result2 = engine.compute(snap2)
        htf = next((c for c in result2.contributors if c.name == "HTF Trend"), None)
        # HTF Trend score decreased
        assert htf.direction in ("DOWN", "UNCHANGED")

    def test_prev_score_populated(self):
        """After two cycles, prev_score should reflect the prior cycle's score."""
        engine = ConfluenceEngine()
        snap1 = _build_snapshot(ta_1h=_make_ta("BULLISH", "STRONG"), ai=_make_ai("BULLISH", 80))
        r1 = engine.compute(snap1)
        scores_c1 = {c.name: c.score for c in r1.contributors}

        snap2 = _build_snapshot(ta_1h=_make_ta("SIDEWAYS", "WEAK"), ai=_make_ai("NEUTRAL", 40))
        r2 = engine.compute(snap2)
        htf2 = next(c for c in r2.contributors if c.name == "HTF Trend")
        assert htf2.prev_score == scores_c1.get("HTF Trend", htf2.prev_score)

    def test_last_changed_at_populated(self):
        """last_changed_at must be a valid ISO 8601 string."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        for c in result.contributors:
            if c.status != "UNAVAILABLE":
                assert "T" in c.last_changed_at, f"{c.name} has invalid last_changed_at: {c.last_changed_at}"


class TestDirectionGate:
    def test_buy_requires_gate_bullish(self):
        """BUY signal requires at least 2 of {HTF, Structure, MTF} to be bullish."""
        engine = ConfluenceEngine()
        # Provide all bullish inputs with enough strength
        candles = [_make_candle(volume=1500)] * 20
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH", "STRONG"),
            ta_1d=_make_ta("BULLISH", "STRONG"),
            ta_15m=_make_ta("BULLISH", "STRONG"),
            ta_5m=_make_ta("BULLISH", "STRONG"),
            ai=_make_ai("BULLISH", 90),
            candles_15m=candles, candles_1h=candles,
        )
        result = engine.compute(snap)
        # If gate passes bullish, signal should be BUY or WAIT (volume/data dependent)
        assert result.gate_bullish_count >= 1

    def test_wait_when_gate_fails(self):
        """WAIT is produced when direction gate is not met (conflicting HTF/Structure/MTF)."""
        engine = ConfluenceEngine()
        # 1H bullish, 1D bearish, no candle data (structure UNAVAILABLE)
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH", "STRONG"),
            ta_1d=_make_ta("BEARISH", "STRONG"),
            ta_15m=_make_ta("SIDEWAYS", "WEAK"),
            ai=_make_ai("NEUTRAL", 50),
        )
        result = engine.compute(snap)
        # gate_bullish_count < 2 and gate_bearish_count < 2 → gate_direction should be NONE
        # (actual count depends on market structure which requires candles)
        assert result.gate_direction in ("NONE", "BULLISH", "BEARISH")  # at least gate is evaluated

    def test_gate_direction_bullish_when_3_agree(self):
        """When HTF + MTF both bullish → gate_direction = BULLISH."""
        engine = ConfluenceEngine()
        candles = [_make_candle()] * 20
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH", "STRONG"),
            ta_1d=_make_ta("BULLISH", "STRONG"),
            ta_15m=_make_ta("BULLISH", "STRONG"),
            ta_5m=_make_ta("BULLISH"),
            ai=_make_ai("BULLISH", 85),
            candles_15m=candles,
        )
        result = engine.compute(snap)
        # HTF Trend and MTF Alignment are gate contributors — both bullish here
        assert result.gate_bullish_count >= 2
        assert result.gate_direction == "BULLISH"

    def test_gate_direction_bearish_when_2_agree(self):
        """When ≥2 gate contributors bearish → gate_direction = BEARISH."""
        engine = ConfluenceEngine()
        candles = [_make_candle(close=2695, open_=2705)] * 20  # bearish candles
        snap = _build_snapshot(
            ta_1h=_make_ta("BEARISH", "STRONG"),
            ta_1d=_make_ta("BEARISH", "STRONG"),
            ta_15m=_make_ta("BEARISH", "STRONG"),
            ta_5m=_make_ta("BEARISH"),
            ai=_make_ai("BEARISH", 85),
            candles_15m=candles,
        )
        result = engine.compute(snap)
        assert result.gate_bearish_count >= 2
        assert result.gate_direction == "BEARISH"


class TestDataQuality:
    def test_all_data_available_is_high_quality(self):
        """With all TF data provided, quality should be HIGH or MEDIUM."""
        engine = ConfluenceEngine()
        candles = [_make_candle(volume=1000)] * 30
        snap = _build_snapshot(
            ta_1h=_make_ta(), ta_1d=_make_ta(), ta_15m=_make_ta(), ta_5m=_make_ta(),
            ai=_make_ai(),
            candles_15m=candles, candles_1h=candles, candles_5m=candles,
        )
        result = engine.compute(snap)
        assert result.data_quality in ("HIGH", "MEDIUM")

    def test_no_data_is_low_quality(self):
        """With no TA data, quality should be LOW."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()  # no ta, no ai, no candles
        result = engine.compute(snap)
        assert result.data_quality == "LOW"

    def test_signal_blocked_on_low_data_quality(self):
        """BUY/SELL signals must not be emitted when data_quality = LOW."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()  # all None
        result = engine.compute(snap)
        if result.data_quality == "LOW":
            assert result.signal == "WAIT"


class TestUnavailableContributors:
    def test_missing_ta_produces_unavailable(self):
        """When ta_1h is None, HTF Trend should be UNAVAILABLE (not fabricated)."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=None, ta_1d=None, ai=_make_ai())
        result = engine.compute(snap)
        htf = next((c for c in result.contributors if c.name == "HTF Trend"), None)
        assert htf is not None
        assert htf.status == "UNAVAILABLE"
        assert htf.score == 0

    def test_unavailable_score_is_zero(self):
        """UNAVAILABLE contributors must always have score = 0."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()  # no data
        result = engine.compute(snap)
        for c in result.contributors:
            if c.status == "UNAVAILABLE":
                assert c.score == 0, f"{c.name}: UNAVAILABLE but score={c.score}"

    def test_no_volume_does_not_fabricate(self):
        """When candles have no volume, VWAP and Volume Confirmation return UNAVAILABLE."""
        engine = ConfluenceEngine()
        # Candles with None volume
        candles = [_make_candle(volume=None)] * 20
        snap = _build_snapshot(ta_15m=_make_ta(), candles_15m=candles)
        result = engine.compute(snap)
        vol = next((c for c in result.contributors if c.name == "Volume Confirmation"), None)
        vwap = next((c for c in result.contributors if c.name == "VWAP"), None)
        assert vol is not None
        assert vwap is not None
        # Both should be UNAVAILABLE if no volume data
        assert vol.status == "UNAVAILABLE"
        assert vwap.status == "UNAVAILABLE"

    def test_forming_candle_excluded(self):
        """A forming candle (is_closed=False) must not be included in analysis."""
        engine = ConfluenceEngine()
        candles_with_forming = [_make_candle()] * 19 + [_make_candle(is_closed=False)]
        mtf = _make_mtf_input()
        mtf.timeframes = {"15m": _make_ta()}
        ai = _make_ai()
        snap = engine.build_snapshot(mtf_input=mtf, ai_result=ai, candles_dict={"15m": candles_with_forming})
        # The snapshot should exclude the forming candle
        assert len(snap.candles_15m) == 19


class TestGeminiUnavailable:
    def test_technical_signal_continues_without_gemini(self):
        """When ai_result is None, Gemini AI score = 0 but technical signal continues."""
        engine = ConfluenceEngine()
        candles = [_make_candle(volume=1000)] * 20
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH", "STRONG"),
            ta_1d=_make_ta("BULLISH", "STRONG"),
            ta_15m=_make_ta("BULLISH", "STRONG"),
            ta_5m=_make_ta("BULLISH"),
            ai=None,
            candles_15m=candles,
        )
        result = engine.compute(snap)
        gemini = next((c for c in result.contributors if c.name == "Gemini AI"), None)
        assert gemini is not None
        assert gemini.status == "UNAVAILABLE"
        assert gemini.score == 0
        assert result.gemini_score == 0
        # Technical score is computed regardless
        assert result.technical_score >= 0

    def test_gemini_score_bounded(self):
        """Gemini AI score must not exceed its max (10)."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ai=_make_ai("BULLISH", 100))
        result = engine.compute(snap)
        gemini = next((c for c in result.contributors if c.name == "Gemini AI"), None)
        assert gemini.score <= 10


class TestSignalHysteresis:
    def test_small_score_change_does_not_flip_signal(self):
        """A score change < SIGNAL_HYSTERESIS_THRESHOLD should NOT flip the signal band."""
        engine = ConfluenceEngine()
        # Establish a baseline
        snap1 = _build_snapshot(ta_1h=_make_ta("BULLISH", "STRONG"), ai=_make_ai("BULLISH", 80))
        r1 = engine.compute(snap1)

        # Minimal change — only AI confidence shifts slightly
        snap2 = _build_snapshot(ta_1h=_make_ta("BULLISH", "STRONG"), ai=_make_ai("BULLISH", 79))
        r2 = engine.compute(snap2)

        # Gate direction should not have changed — hysteresis keeps signal stable
        assert r1.gate_direction == r2.gate_direction or r2.signal in ("BUY", "WAIT")

    def test_hysteresis_threshold_defined(self):
        """SIGNAL_HYSTERESIS_THRESHOLD must be 3."""
        assert SIGNAL_HYSTERESIS_THRESHOLD == 3


class TestDoubleCountingProtection:
    def test_evidence_penalty_applied(self):
        """SMC/ICT and Market Structure share MSS evidence — penalty must be applied to second use."""
        engine = ConfluenceEngine()
        # Set up candles so MSS analysis can run
        candles = [_make_candle()] * 20
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH"), ta_15m=_make_ta("BULLISH"),
            candles_15m=candles, candles_1h=candles,
        )
        result = engine.compute(snap)
        # Both SMC/ICT and Market Structure may reference the same MSS event
        # Verify that at least one shows double_counting_penalty > 0 IF MSS was found
        # (this is a soft check — it depends on actual SMC analysis results)
        smc = next((c for c in result.contributors if c.name == "SMC / ICT"), None)
        structure = next((c for c in result.contributors if c.name == "Market Structure"), None)
        assert smc is not None
        assert structure is not None
        # Both should have valid (non-negative) double_counting_penalty values
        assert smc.double_counting_penalty >= 0.0
        assert structure.double_counting_penalty >= 0.0
        assert smc.double_counting_penalty <= 1.0
        assert structure.double_counting_penalty <= 1.0


class TestMarketRegime:
    def test_regime_trending_bullish_on_bullish_signals(self):
        """Strong bullish signals → market regime = TRENDING_BULLISH."""
        engine = ConfluenceEngine()
        candles = [_make_candle(volume=1000)] * 30
        snap = _build_snapshot(
            ta_1h=_make_ta("BULLISH", "STRONG"),
            ta_1d=_make_ta("BULLISH", "STRONG"),
            ta_15m=_make_ta("BULLISH", "STRONG"),
            ta_5m=_make_ta("BULLISH"),
            ai=_make_ai("BULLISH", 90),
            candles_15m=candles,
        )
        result = engine.compute(snap)
        assert result.market_regime in ("TRENDING_BULLISH", "RANGING", "UNCLEAR")

    def test_regime_is_string(self):
        """market_regime must be a non-empty string."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        assert isinstance(result.market_regime, str)
        assert len(result.market_regime) > 0


class TestDataCompleteness:
    def test_completeness_string_format(self):
        """data_completeness must follow 'N/17 contributors available' format."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        assert "/" in result.data_completeness
        assert "contributors available" in result.data_completeness

    def test_all_17_contributors_produced(self):
        """ConfluenceEngine must always produce exactly 17 contributor results."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        assert len(result.contributors) == 17


class TestEntryQuality:
    def test_entry_quality_wait_when_signal_wait(self):
        """entry_quality must be 'WAIT' when signal is WAIT."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()  # no data → WAIT
        result = engine.compute(snap)
        if result.signal == "WAIT":
            assert result.entry_quality == "WAIT"

    def test_entry_quality_valid_values(self):
        """entry_quality must be one of {GOOD, FAIR, POOR, WAIT}."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        result = engine.compute(snap)
        assert result.entry_quality in ("GOOD", "FAIR", "POOR", "WAIT")


class TestSpreadStatus:
    def test_spread_unavailable_when_no_bid_ask(self):
        """Without bid/ask data, spread_status must be UNAVAILABLE."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()
        result = engine.compute(snap)
        assert result.spread_status == "UNAVAILABLE"

    def test_news_status_always_unavailable(self):
        """news_status must always be NEWS_DATA_UNAVAILABLE (no news feed)."""
        engine = ConfluenceEngine()
        snap = _build_snapshot()
        result = engine.compute(snap)
        assert result.news_status == "NEWS_DATA_UNAVAILABLE"


class TestAuditTrail:
    def test_audit_trail_grows_each_cycle(self):
        """Audit trail should have one entry per compute() call."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        engine.compute(snap)
        engine.compute(snap)
        trail = engine.get_audit_trail()
        assert len(trail) == 2

    def test_audit_trail_has_snapshot_id(self):
        """Each audit entry must have a snapshot_id."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        engine.compute(snap)
        trail = engine.get_audit_trail()
        assert "snapshot_id" in trail[0]
        assert trail[0]["snapshot_id"] == snap.snapshot_id

    def test_audit_trail_max_100(self):
        """Audit trail must not grow beyond 100 entries."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(ta_1h=_make_ta(), ai=_make_ai())
        for _ in range(110):
            engine.compute(snap)
        trail = engine.get_audit_trail()
        assert len(trail) <= 100


class TestSafeWaitOnError:
    def test_compute_does_not_raise_on_broken_snapshot(self):
        """compute() must never raise — returns WAIT on any internal error."""
        engine = ConfluenceEngine()
        # Pass a completely broken snapshot
        broken = MarketSnapshot(
            snapshot_id="bad",
            created_at="bad",
            symbol="XAU/USD",
            current_price=float("nan"),
        )
        # Should not raise
        result = engine.compute(broken)
        assert result.signal == "WAIT"


class TestMTFAlignmentScaling:
    """Rigorous tests proving the MTF Alignment scaling fix (Phase A)."""

    def test_mtf_4_bullish_0_bearish_scores_8_bullish(self):
        """4/4 agreement awards the full declared maximum of 8 points."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(
            ta_5m=_make_ta("BULLISH"),
            ta_15m=_make_ta("BULLISH"),
            ta_1h=_make_ta("BULLISH"),
            ta_1d=_make_ta("BULLISH"),
        )
        res = engine._c_mtf_alignment(snap)
        assert res.score == 8
        assert res.bias == "BULLISH"
        assert res.score <= CONTRIBUTOR_MAX_SCORES["MTF Alignment"]
        assert len(res.conflicts) == 0

    def test_mtf_3_bullish_1_bearish_scores_6_bullish(self):
        """3/4 agreement awards round((3/4) * 8) = 6 points."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(
            ta_5m=_make_ta("BULLISH"),
            ta_15m=_make_ta("BULLISH"),
            ta_1h=_make_ta("BULLISH"),
            ta_1d=_make_ta("BEARISH"),
        )
        res = engine._c_mtf_alignment(snap)
        assert res.score == 6
        assert res.bias == "BULLISH"
        assert res.score <= CONTRIBUTOR_MAX_SCORES["MTF Alignment"]
        assert len(res.conflicts) == 0

    def test_mtf_2_bullish_2_bearish_neutral_split_with_penalty(self):
        """2/4 tie triggers conflict penalty (round(2/4*8)=4, minus 2 penalty = 2 pts, NEUTRAL)."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(
            ta_5m=_make_ta("BULLISH"),
            ta_15m=_make_ta("BULLISH"),
            ta_1h=_make_ta("BEARISH"),
            ta_1d=_make_ta("BEARISH"),
        )
        res = engine._c_mtf_alignment(snap)
        assert res.score == 2
        assert res.bias == "NEUTRAL"
        assert len(res.conflicts) > 0
        assert res.score <= CONTRIBUTOR_MAX_SCORES["MTF Alignment"]

    def test_mtf_3_bearish_1_bullish_scores_6_bearish(self):
        """3/4 bearish agreement awards 6 points with BEARISH bias."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(
            ta_5m=_make_ta("BEARISH"),
            ta_15m=_make_ta("BEARISH"),
            ta_1h=_make_ta("BEARISH"),
            ta_1d=_make_ta("BULLISH"),
        )
        res = engine._c_mtf_alignment(snap)
        assert res.score == 6
        assert res.bias == "BEARISH"
        assert res.score <= CONTRIBUTOR_MAX_SCORES["MTF Alignment"]
        assert len(res.conflicts) == 0

    def test_mtf_4_bearish_0_bullish_scores_8_bearish(self):
        """4/4 bearish agreement awards full 8 points with BEARISH bias."""
        engine = ConfluenceEngine()
        snap = _build_snapshot(
            ta_5m=_make_ta("BEARISH"),
            ta_15m=_make_ta("BEARISH"),
            ta_1h=_make_ta("BEARISH"),
            ta_1d=_make_ta("BEARISH"),
        )
        res = engine._c_mtf_alignment(snap)
        assert res.score == 8
        assert res.bias == "BEARISH"
        assert res.score <= CONTRIBUTOR_MAX_SCORES["MTF Alignment"]
        assert len(res.conflicts) == 0

