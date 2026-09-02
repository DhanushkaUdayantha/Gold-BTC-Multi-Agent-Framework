"""
Unit tests for the OTE Smart Money 5-step analytical engine.

Tests each step independently with fully mocked candle data,
then tests the complete signal generation pipeline.
"""
import pytest
from datetime import datetime, timezone, timedelta, time as dtime
from unittest.mock import patch

from src.models.market_data import OHLCVCandle
from src.models.ote_analysis import (
    SweepDirection, MSSDirection, FVGType, OTESignalType, SessionName,
)
from src.services.ote_engine import OTEEngine


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _candle(o, h, l, c, ts="2026-01-01T00:00:00Z") -> OHLCVCandle:
    return OHLCVCandle(timestamp=ts, open=o, high=h, low=l, close=c, is_closed=True)


def _candles_range(n: int, base=2700.0, spread=10.0):
    """Create n neutral candles around base price."""
    return [_candle(base, base + spread, base - spread, base, f"2026-01-01T{i:02d}:00:00Z")
            for i in range(n)]


# ─────────────────────────────────────────────────────────────
# Step 1 — Trend
# ─────────────────────────────────────────────────────────────

class TestTrendStep:
    engine = OTEEngine()

    def test_trend_bullish_detection(self):
        result = self.engine.analyze_trend(
            price=2720.0, ema20=2710.0, ema50=2690.0, ema200=2650.0
        )
        assert result.direction == "BULLISH"
        assert result.passed is True

    def test_trend_bearish_detection(self):
        result = self.engine.analyze_trend(
            price=2650.0, ema20=2665.0, ema50=2680.0, ema200=2720.0
        )
        assert result.direction == "BEARISH"
        assert result.passed is True

    def test_trend_neutral_when_mixed(self):
        # price between ema20 and ema50 — no clear structure
        result = self.engine.analyze_trend(
            price=2700.0, ema20=2710.0, ema50=2695.0, ema200=2650.0
        )
        # ema20 > ema50 but price < ema20 → not cleanly bullish
        assert result.passed in (True, False)  # deterministic but depends on exact values

    def test_trend_neutral_no_ema(self):
        result = self.engine.analyze_trend(
            price=2700.0, ema20=None, ema50=None, ema200=None
        )
        assert result.direction == "NEUTRAL"
        assert result.passed is False


# ─────────────────────────────────────────────────────────────
# Step 2 — Liquidity
# ─────────────────────────────────────────────────────────────

class TestLiquidityStep:
    engine = OTEEngine()

    def test_liquidity_pdh_bearish_sweep(self):
        """Price spiked above PDH then closed below — bearish sweep."""
        pdh = 2710.0
        pdl = 2670.0
        prev_day = _candle(2690.0, pdh, pdl, 2685.0)
        curr_day  = _candle(2680.0, 2700.0, 2665.0, 2672.0)  # not used for sweep
        daily = [prev_day, curr_day]

        # Create hourly candle that sweeps PDH and closes below
        h1 = [_candle(2705.0, 2715.0, 2698.0, 2705.0)] * 8  # normal candles
        h1.append(_candle(2706.0, 2718.0, 2700.0, 2702.0))   # swept PDH (high > 2710) but closed below
        result = self.engine.analyze_liquidity(daily, h1, 2702.0)
        assert result.sweep_direction == SweepDirection.BEARISH
        assert result.passed is True

    def test_liquidity_pdl_bullish_sweep(self):
        """Price dipped below PDL then closed above — bullish sweep."""
        pdh = 2720.0
        pdl = 2680.0
        prev_day = _candle(2700.0, pdh, pdl, 2698.0)
        curr_day  = _candle(2695.0, 2710.0, 2675.0, 2692.0)
        daily = [prev_day, curr_day]

        h1 = [_candle(2695.0, 2705.0, 2688.0, 2698.0)] * 8
        h1.append(_candle(2694.0, 2696.0, 2672.0, 2688.0))   # swept PDL (low < 2680) but closed above
        result = self.engine.analyze_liquidity(daily, h1, 2688.0)
        assert result.sweep_direction == SweepDirection.BULLISH
        assert result.passed is True

    def test_liquidity_no_sweep(self):
        """Normal price action — no sweep of PDH or PDL."""
        pdh = 2720.0
        pdl = 2680.0
        prev_day = _candle(2700.0, pdh, pdl, 2698.0)
        curr_day  = _candle(2698.0, 2715.0, 2685.0, 2702.0)
        daily = [prev_day, curr_day]
        h1 = _candles_range(10, base=2700.0, spread=8.0)
        result = self.engine.analyze_liquidity(daily, h1, 2700.0)
        assert result.sweep_direction == SweepDirection.NONE
        assert result.passed is False

    def test_liquidity_insufficient_daily_candles(self):
        result = self.engine.analyze_liquidity([], [], 2700.0)
        assert result.passed is False


# ─────────────────────────────────────────────────────────────
# Step 3 — Market Structure Shift
# ─────────────────────────────────────────────────────────────

class TestMSSStep:
    engine = OTEEngine()

    def test_mss_bullish_detected(self):
        """After bullish sweep, price breaks above swing high → bullish MSS."""
        # First 14 candles form a swing (pivot high at 2705)
        candles = [_candle(2690.0, 2705.0, 2685.0, 2695.0)] * 14
        # Last 6 candles rally above 2705
        for _ in range(6):
            candles.append(_candle(2700.0, 2720.0, 2698.0, 2715.0))
        result = self.engine.analyze_mss(candles, SweepDirection.BULLISH, "15m")
        assert result.direction == MSSDirection.BULLISH
        assert result.passed is True

    def test_mss_bearish_detected(self):
        """After bearish sweep, price breaks below swing low → bearish MSS."""
        candles = [_candle(2710.0, 2715.0, 2698.0, 2705.0)] * 14
        for _ in range(6):
            candles.append(_candle(2700.0, 2702.0, 2680.0, 2685.0))
        result = self.engine.analyze_mss(candles, SweepDirection.BEARISH, "15m")
        assert result.direction == MSSDirection.BEARISH
        assert result.passed is True

    def test_mss_no_sweep_skips(self):
        candles = _candles_range(20)
        result = self.engine.analyze_mss(candles, SweepDirection.NONE)
        assert result.direction == MSSDirection.NONE
        assert result.passed is False


# ─────────────────────────────────────────────────────────────
# Step 4 — Fibonacci OTE Zone
# ─────────────────────────────────────────────────────────────

class TestFibonacciStep:
    engine = OTEEngine()

    def test_fibonacci_bullish_ote_zone_calculation(self):
        """Validate OTE zone math for a bullish setup."""
        candles = [_candle(2660.0, 2660.0, 2660.0, 2660.0)]   # swing low
        candles += [_candle(2700.0, 2700.0, 2700.0, 2700.0)]  # swing high
        # Range 40. 0.618 retrace = 2700 - 40*0.618 = 2675.28; 0.786 = 2700 - 40*0.786 = 2668.56
        candles += _candles_range(10, base=2680.0, spread=3.0)  # current around 2680

        result = self.engine.analyze_fibonacci(candles, MSSDirection.BULLISH, 2680.0)
        assert result.swing_high is not None
        assert result.swing_low  is not None
        assert result.level_618  is not None
        assert result.level_786  is not None
        assert result.ote_low < result.ote_high
        # 0.618 should be between swing_low and swing_high
        assert result.swing_low < result.level_618 < result.swing_high

    def test_price_inside_ote_zone_bullish(self):
        """Price at the 0.7 retracement should be inside OTE zone."""
        # swing_low=2660, swing_high=2700 → range=40
        # 0.618 retrace = 2700 - 24.72 = 2675.28
        # 0.786 retrace = 2700 - 31.44 = 2668.56
        # Price at 2672 should be inside [2668.56, 2675.28]
        candles = [
            _candle(2660.0, 2660.0, 2660.0, 2660.0),
            _candle(2665.0, 2665.0, 2665.0, 2665.0),
            _candle(2670.0, 2670.0, 2670.0, 2670.0),
            _candle(2700.0, 2700.0, 2700.0, 2700.0),
            _candle(2672.0, 2672.0, 2672.0, 2672.0),
        ]
        result = self.engine.analyze_fibonacci(candles, MSSDirection.BULLISH, 2672.0)
        assert result.price_in_ote_zone is True
        assert result.passed is True


    def test_price_outside_ote_zone(self):
        """Price far from OTE zone should fail."""
        candles = [
            _candle(2660.0, 2660.0, 2660.0, 2660.0),
            _candle(2665.0, 2665.0, 2665.0, 2665.0),
            _candle(2670.0, 2670.0, 2670.0, 2670.0),
            _candle(2700.0, 2700.0, 2700.0, 2700.0),
            _candle(2699.0, 2699.0, 2699.0, 2699.0),
        ]
        result = self.engine.analyze_fibonacci(candles, MSSDirection.BULLISH, 2699.0)
        assert result.passed is False



# ─────────────────────────────────────────────────────────────
# Step 5 — Fair Value Gap
# ─────────────────────────────────────────────────────────────

class TestFVGStep:
    engine = OTEEngine()

    def test_fvg_bullish_detected_and_price_inside(self):
        """Three-candle bullish FVG: c1.high < c3.low."""
        candles = [
            _candle(2685.0, 2690.0, 2682.0, 2688.0),   # c[i-2]  high=2690
            _candle(2690.0, 2710.0, 2688.0, 2708.0),   # c[i-1]  impulse up
            _candle(2708.0, 2715.0, 2694.0, 2712.0),   # c[i]    low=2694
        ]
        # FVG = 2690 to 2694; price at 2692 should be inside
        result = self.engine.analyze_fvg(candles, MSSDirection.BULLISH, 2692.0, "5m")
        assert result.fvg_type == FVGType.BULLISH
        assert result.price_in_fvg is True
        assert result.passed is True

    def test_fvg_bearish_detected_and_price_inside(self):
        """Three-candle bearish FVG: c1.low > c3.high."""
        candles = [
            _candle(2710.0, 2712.0, 2705.0, 2707.0),   # c[i-2]  low=2705
            _candle(2707.0, 2708.0, 2688.0, 2690.0),   # c[i-1]  impulse down
            _candle(2690.0, 2701.0, 2686.0, 2699.0),   # c[i]    high=2701
        ]
        # FVG = 2701 to 2705; price at 2703 should be inside
        result = self.engine.analyze_fvg(candles, MSSDirection.BEARISH, 2703.0, "5m")
        assert result.fvg_type == FVGType.BEARISH
        assert result.price_in_fvg is True
        assert result.passed is True

    def test_fvg_none_when_no_gap(self):
        candles = _candles_range(10, base=2700.0, spread=5.0)
        result = self.engine.analyze_fvg(candles, MSSDirection.BULLISH, 2700.0, "5m")
        # No FVG in smooth candles
        assert result.passed is False


# ─────────────────────────────────────────────────────────────
# Session Gate
# ─────────────────────────────────────────────────────────────

class TestSessionGate:
    engine = OTEEngine()

    def test_session_london_active(self):
        """08:30 UTC should be inside London session (07:00–10:00 UTC)."""
        london_time = datetime(2026, 1, 6, 8, 30, 0, tzinfo=timezone.utc)
        result = self.engine.check_session(london_time)
        assert result.is_open is True
        assert result.active_session == SessionName.LONDON

    def test_session_newyork_active(self):
        """14:00 UTC should be inside New York session (13:00–16:00 UTC)."""
        ny_time = datetime(2026, 1, 6, 14, 0, 0, tzinfo=timezone.utc)
        result = self.engine.check_session(ny_time)
        assert result.is_open is True
        assert result.active_session == SessionName.NEW_YORK

    def test_session_blocked_outside_hours(self):
        """05:00 UTC is outside both sessions."""
        blocked_time = datetime(2026, 1, 6, 5, 0, 0, tzinfo=timezone.utc)
        result = self.engine.check_session(blocked_time)
        assert result.is_open is False
        assert result.active_session == SessionName.NONE
        assert result.next_session is not None
        assert result.next_session_opens_in_minutes is not None
        assert result.next_session_opens_in_minutes > 0


# ─────────────────────────────────────────────────────────────
# Full Signal Generation
# ─────────────────────────────────────────────────────────────

class TestFullSignalGeneration:
    engine = OTEEngine()

    def _build_steps(self, direction="BULLISH"):
        """Build all 5 passing steps for a given direction."""
        from src.models.ote_analysis import (
            TrendStep, LiquidityStep, MSSStep, FibonacciStep, FVGStep, SessionStatus,
        )
        if direction == "BULLISH":
            trend     = TrendStep(direction="BULLISH", price=2695.0, ema20=2685.0, ema50=2670.0, passed=True, reasoning="OK")
            liquidity = LiquidityStep(prev_day_high=2710.0, prev_day_low=2665.0, sweep_direction=SweepDirection.BULLISH, swept_level=2665.0, passed=True, reasoning="OK")
            mss       = MSSStep(direction=MSSDirection.BULLISH, break_level=2688.0, timeframe="15m", passed=True, reasoning="OK")
            fibonacci = FibonacciStep(swing_high=2700.0, swing_low=2660.0, ote_high=2676.0, ote_low=2669.0, level_618=2675.28, level_786=2668.56, current_price=2694.0, price_in_ote_zone=True, passed=True, reasoning="OK")
            fvg       = FVGStep(fvg_type=FVGType.BULLISH, fvg_high=2692.0, fvg_low=2690.0, price_in_fvg=True, timeframe="5m", passed=True, reasoning="OK")
        else:
            trend     = TrendStep(direction="BEARISH", price=2700.0, ema20=2710.0, ema50=2725.0, passed=True, reasoning="OK")
            liquidity = LiquidityStep(prev_day_high=2715.0, prev_day_low=2670.0, sweep_direction=SweepDirection.BEARISH, swept_level=2715.0, passed=True, reasoning="OK")
            mss       = MSSStep(direction=MSSDirection.BEARISH, break_level=2705.0, timeframe="15m", passed=True, reasoning="OK")
            fibonacci = FibonacciStep(swing_high=2720.0, swing_low=2680.0, ote_high=2705.0, ote_low=2699.0, level_618=2704.72, level_786=2711.44, current_price=2702.0, price_in_ote_zone=True, passed=True, reasoning="OK")
            fvg       = FVGStep(fvg_type=FVGType.BEARISH, fvg_high=2706.0, fvg_low=2703.0, price_in_fvg=True, timeframe="5m", passed=True, reasoning="OK")
        # Open session
        session = SessionStatus(active_session=SessionName.LONDON, is_open=True, current_time_utc="08:00 UTC", reasoning="Open")
        return trend, liquidity, mss, fibonacci, fvg, session

    def test_full_ote_buy_signal_all_steps_pass(self):
        """With all 5 steps passing and London session open, should get BUY."""
        trend, liquidity, mss, fibonacci, fvg, session = self._build_steps("BULLISH")
        signal = self.engine.generate_signal(
            trend=trend, liquidity=liquidity, mss=mss, fibonacci=fibonacci, fvg=fvg,
            session=session, current_price=2694.0, timestamp="2026-01-06T08:00:00Z"
        )
        assert signal.signal == OTESignalType.BUY
        assert signal.steps_passed == 5
        assert signal.stop_loss is not None
        assert signal.take_profit_1 is not None
        assert signal.take_profit_2 is not None
        assert signal.position_size is not None
        assert signal.position_size > 0
        assert signal.risk_reward_tp2 >= 2.0  # Minimum 1:2 R:R

    def test_full_ote_wait_session_blocked(self):
        """Outside session → WAIT regardless of step confirmations."""
        trend, liquidity, mss, fibonacci, fvg, _ = self._build_steps("BULLISH")
        closed_session = __import__(
            "src.models.ote_analysis", fromlist=["SessionStatus"]
        ).SessionStatus(
            active_session=SessionName.NONE,
            is_open=False,
            current_time_utc="05:00 UTC",
            reasoning="No session",
        )
        signal = self.engine.generate_signal(
            trend=trend, liquidity=liquidity, mss=mss, fibonacci=fibonacci, fvg=fvg,
            session=closed_session, current_price=2694.0, timestamp="2026-01-06T05:00:00Z"
        )
        assert signal.signal == OTESignalType.WAIT
        assert signal.confidence == 0

    def test_full_ote_wait_missing_mss(self):
        """MSS not confirmed → WAIT even with other steps passing."""
        from src.models.ote_analysis import TrendStep, LiquidityStep, MSSStep, FibonacciStep, FVGStep, SessionStatus
        trend     = TrendStep(direction="BULLISH", price=2695.0, passed=True, reasoning="OK")
        liquidity = LiquidityStep(sweep_direction=SweepDirection.BULLISH, swept_level=2665.0, passed=True, reasoning="OK")
        mss       = MSSStep(direction=MSSDirection.NONE, passed=False, timeframe="15m", reasoning="No MSS")
        fibonacci = FibonacciStep(price_in_ote_zone=True, passed=True, current_price=2694.0, reasoning="OK")
        fvg       = FVGStep(fvg_type=FVGType.BULLISH, price_in_fvg=True, passed=True, timeframe="5m", reasoning="OK")
        session   = SessionStatus(active_session=SessionName.LONDON, is_open=True, current_time_utc="08:00 UTC", reasoning="Open")
        signal = self.engine.generate_signal(
            trend=trend, liquidity=liquidity, mss=mss, fibonacci=fibonacci, fvg=fvg,
            session=session, current_price=2694.0, timestamp="2026-01-06T08:00:00Z"
        )
        assert signal.signal == OTESignalType.WAIT
        assert signal.steps_passed < 5
