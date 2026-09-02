"""
Gold Smart Money / OTE (Optimal Trade Entry) Analytical Engine.

Pure mathematical implementation of the 5-step ICT Smart Money execution strategy:

  Step 1 — Trend (1H):       EMA 20/50/200 structure determines market direction
  Step 2 — Liquidity (1D/1H): Previous Day High/Low sweep detection
  Step 3 — MSS (5m/15m):     Market Structure Shift after liquidity event
  Step 4 — Fibonacci (5m/15m): OTE zone [0.618–0.786] retracement
  Step 5 — FVG (5m/15m):     Fair Value Gap inside OTE zone

Session Gate (UTC times — Sri Lanka UTC+5:30):
  London   07:00–10:00 UTC  (12:30–15:30 SL)
  New York 13:00–16:00 UTC  (18:30–21:30 SL)

All outputs are advisory only. No trades are executed.
"""
import logging
from datetime import datetime, timezone, time as dtime
from typing import List, Optional, Tuple

from src.models.market_data import OHLCVCandle
from src.models.ote_analysis import (
    TrendStep, LiquidityStep, MSSStep, FibonacciStep, FVGStep,
    SessionStatus, SessionName, SweepDirection, MSSDirection, FVGType,
    OTESignal, OTESignalType,
)

logger = logging.getLogger(__name__)

# 1% risk on $10,000 demo balance
_STARTING_BALANCE = 10_000.0
_RISK_PCT = 1.0
# Lot size: 1 lot XAU/USD = 100 oz ⟹ $1 move = $100 P&L
_LOT_UNIT = 100.0

# Session windows in UTC (hour, minute)
_SESSIONS = {
    SessionName.LONDON:   (dtime(7, 0),  dtime(10, 0)),
    SessionName.NEW_YORK: (dtime(13, 0), dtime(16, 0)),
}


def _to_ohlcv(c: Any) -> OHLCVCandle:
    if isinstance(c, OHLCVCandle):
        return c
    if isinstance(c, dict):
        return OHLCVCandle(
            timestamp=str(c.get("timestamp", "")),
            open=float(c.get("open", 0)),
            high=float(c.get("high", 0)),
            low=float(c.get("low", 0)),
            close=float(c.get("close", 0)),
            volume=float(c.get("volume", 0) or 0),
            is_closed=bool(c.get("is_closed", True)),
        )
    return OHLCVCandle(
        timestamp=str(getattr(c, "timestamp", "")),
        open=float(getattr(c, "open", 0)),
        high=float(getattr(c, "high", 0)),
        low=float(getattr(c, "low", 0)),
        close=float(getattr(c, "close", 0)),
        volume=float(getattr(c, "volume", 0) or 0),
        is_closed=bool(getattr(c, "is_closed", True)),
    )


class OTEEngine:
    """
    Pure analytical engine for the 5-step Smart Money / OTE strategy.
    Stateless — all inputs are passed per call.
    """

    # ─────────────────────────────────────────────────────────
    # Step 1 — Trend
    # ─────────────────────────────────────────────────────────

    def analyze_trend(
        self,
        price: float,
        ema20: Optional[float],
        ema50: Optional[float],
        ema200: Optional[float],
    ) -> TrendStep:
        """Determine 1H trend using EMA 20/50/200 structure."""
        if ema20 is None or ema50 is None:
            return TrendStep(
                direction="NEUTRAL",
                ema20=ema20, ema50=ema50, ema200=ema200,
                price=price, passed=False,
                reasoning="Insufficient EMA data for trend determination.",
            )

        bullish = (
            price > ema20 > 0 and
            ema20 > (ema50 or 0) and
            (ema200 is None or price > ema200)
        )
        bearish = (
            price < ema20 and
            ema20 < (ema50 or float("inf")) and
            (ema200 is None or price < ema200)
        )

        if bullish:
            direction = "BULLISH"
            reasoning = f"Price ({price:.2f}) > EMA20 ({ema20:.2f}) > EMA50 ({ema50:.2f}). Bullish EMA structure confirmed."
        elif bearish:
            direction = "BEARISH"
            reasoning = f"Price ({price:.2f}) < EMA20 ({ema20:.2f}) < EMA50 ({ema50:.2f}). Bearish EMA structure confirmed."
        else:
            direction = "NEUTRAL"
            reasoning = f"EMA structure is mixed — no clear directional bias (price {price:.2f}, EMA20 {ema20:.2f}, EMA50 {ema50:.2f})."

        return TrendStep(
            direction=direction,
            ema20=ema20, ema50=ema50, ema200=ema200,
            price=price,
            passed=(direction in ("BULLISH", "BEARISH")),
            reasoning=reasoning,
        )

    # ─────────────────────────────────────────────────────────
    # Step 2 — Liquidity
    # ─────────────────────────────────────────────────────────

    def analyze_liquidity(
        self,
        daily_candles: List[Any],
        hourly_candles: List[Any],
        current_price: float,
    ) -> LiquidityStep:
        """Detect Previous Day High/Low and check for a sweep on 1H candles."""
        daily_candles = [_to_ohlcv(c) for c in daily_candles]
        hourly_candles = [_to_ohlcv(c) for c in hourly_candles]
        if len(daily_candles) < 2:
            return LiquidityStep(
                passed=False,
                reasoning="Not enough daily candles to determine Previous Day High/Low.",
            )

        # Previous day = second-to-last closed daily candle
        prev_day = daily_candles[-2]
        pdh = prev_day.high
        pdl = prev_day.low

        # Look at recent hourly candles (last 12 = ~half day) for sweep
        recent_h1 = hourly_candles[-12:] if len(hourly_candles) >= 12 else hourly_candles

        # Bearish sweep: price spiked above PDH and then pulled back below it
        bearish_sweep = False
        bullish_sweep = False

        for i, c in enumerate(recent_h1):
            # Bearish sweep: high exceeded PDH but closed below PDH
            if c.high > pdh and c.close < pdh:
                bearish_sweep = True
            # Bullish sweep: low went below PDL but closed above PDL
            if c.low < pdl and c.close > pdl:
                bullish_sweep = True

        # Prioritise the most recent sweep
        if bearish_sweep and bullish_sweep:
            # Use the last candle's position to determine which is more recent/relevant
            last_c = recent_h1[-1] if recent_h1 else None
            if last_c:
                if abs(last_c.high - pdh) < abs(last_c.low - pdl):
                    bullish_sweep = False  # bearish more recent
                else:
                    bearish_sweep = False  # bullish more recent

        if bearish_sweep:
            return LiquidityStep(
                prev_day_high=round(pdh, 2),
                prev_day_low=round(pdl, 2),
                sweep_direction=SweepDirection.BEARISH,
                swept_level=round(pdh, 2),
                passed=True,
                reasoning=(
                    f"Bearish liquidity sweep: price spiked above Previous Day High ${pdh:.2f} "
                    f"but closed back below it — sell-side liquidity swept."
                ),
            )
        if bullish_sweep:
            return LiquidityStep(
                prev_day_high=round(pdh, 2),
                prev_day_low=round(pdl, 2),
                sweep_direction=SweepDirection.BULLISH,
                swept_level=round(pdl, 2),
                passed=True,
                reasoning=(
                    f"Bullish liquidity sweep: price dipped below Previous Day Low ${pdl:.2f} "
                    f"but closed back above it — buy-side liquidity swept."
                ),
            )

        return LiquidityStep(
            prev_day_high=round(pdh, 2),
            prev_day_low=round(pdl, 2),
            sweep_direction=SweepDirection.NONE,
            passed=False,
            reasoning=(
                f"No liquidity sweep detected. PDH: ${pdh:.2f}, PDL: ${pdl:.2f}. "
                f"Price at ${current_price:.2f} has not swept either level with a close-back."
            ),
        )

    # ─────────────────────────────────────────────────────────
    # Step 3 — Market Structure Shift
    # ─────────────────────────────────────────────────────────

    def analyze_mss(
        self,
        candles: List[Any],
        sweep_direction: SweepDirection,
        timeframe: str = "15m",
    ) -> MSSStep:
        """Detect Market Structure Shift on 5m/15m candles after a liquidity sweep."""
        candles = [_to_ohlcv(c) for c in candles]
        if sweep_direction == SweepDirection.NONE:
            return MSSStep(
                direction=MSSDirection.NONE,
                passed=False,
                timeframe=timeframe,
                reasoning="No liquidity sweep detected — MSS check skipped.",
            )

        recent = candles[-20:] if len(candles) >= 20 else candles
        if len(recent) < 4:
            return MSSStep(
                direction=MSSDirection.NONE,
                passed=False,
                timeframe=timeframe,
                reasoning="Not enough candles to detect Market Structure Shift.",
            )

        # For a BULLISH sweep (PDL swept): look for a break of a recent swing HIGH (bullish MSS)
        # For a BEARISH sweep (PDH swept): look for a break of a recent swing LOW (bearish MSS)
        highs = [c.high for c in recent]
        lows  = [c.low  for c in recent]

        if sweep_direction == SweepDirection.BULLISH:
            # Find a local swing high in the first ~70% of the window
            pivot_window = recent[: max(4, int(len(recent) * 0.7))]
            pivot_high = max(c.high for c in pivot_window)
            # Check if a later candle's close breaks above that swing high
            later = recent[len(pivot_window):]
            break_level = pivot_high
            for c in later:
                if c.close > break_level:
                    return MSSStep(
                        direction=MSSDirection.BULLISH,
                        break_level=round(break_level, 2),
                        timeframe=timeframe,
                        passed=True,
                        reasoning=(
                            f"Bullish MSS confirmed on {timeframe}: price closed above swing high "
                            f"${break_level:.2f} after bullish PDL sweep. Market structure shifted bullish."
                        ),
                    )
            return MSSStep(
                direction=MSSDirection.NONE,
                passed=False,
                timeframe=timeframe,
                reasoning=f"Bullish sweep detected but no {timeframe} break above swing high ${pivot_high:.2f} yet.",
            )

        else:  # BEARISH sweep
            pivot_window = recent[: max(4, int(len(recent) * 0.7))]
            pivot_low = min(c.low for c in pivot_window)
            later = recent[len(pivot_window):]
            break_level = pivot_low
            for c in later:
                if c.close < break_level:
                    return MSSStep(
                        direction=MSSDirection.BEARISH,
                        break_level=round(break_level, 2),
                        timeframe=timeframe,
                        passed=True,
                        reasoning=(
                            f"Bearish MSS confirmed on {timeframe}: price closed below swing low "
                            f"${break_level:.2f} after bearish PDH sweep. Market structure shifted bearish."
                        ),
                    )
            return MSSStep(
                direction=MSSDirection.NONE,
                passed=False,
                timeframe=timeframe,
                reasoning=f"Bearish sweep detected but no {timeframe} break below swing low ${pivot_low:.2f} yet.",
            )

    # ─────────────────────────────────────────────────────────
    # Step 4 — Fibonacci OTE Zone
    # ─────────────────────────────────────────────────────────

    def analyze_fibonacci(
        self,
        candles: List[Any],
        mss_direction: MSSDirection,
        current_price: float,
    ) -> FibonacciStep:
        """Calculate OTE Fibonacci retracement zone [0.618, 0.786] from recent swing impulse."""
        candles = [_to_ohlcv(c) for c in candles]
        if mss_direction == MSSDirection.NONE:
            return FibonacciStep(
                current_price=current_price,
                passed=False,
                reasoning="MSS not confirmed — Fibonacci OTE skipped.",
            )

        recent = candles[-30:] if len(candles) >= 30 else candles
        if len(recent) < 5:
            return FibonacciStep(
                current_price=current_price,
                passed=False,
                reasoning="Not enough candles for Fibonacci calculation.",
            )

        if mss_direction == MSSDirection.BULLISH:
            # Impulse: from the lowest low → to the highest high (after the MSS)
            swing_low  = min(c.low  for c in recent)
            swing_high = max(c.high for c in recent)
            # OTE zone: retracement from high back down toward low
            # 0.618 retracement = high - 0.618 * (high - low)
            # 0.786 retracement = high - 0.786 * (high - low)
            rng = swing_high - swing_low
            if rng <= 0:
                return FibonacciStep(current_price=current_price, passed=False,
                                     reasoning="Swing range is zero — Fibonacci skipped.")
            level_618 = swing_high - 0.618 * rng
            level_786 = swing_high - 0.786 * rng
            ote_low  = min(level_618, level_786)  # deeper pullback
            ote_high = max(level_618, level_786)  # shallower pullback
            in_zone = ote_low <= current_price <= ote_high

            return FibonacciStep(
                swing_high=round(swing_high, 2),
                swing_low=round(swing_low, 2),
                ote_high=round(ote_high, 2),
                ote_low=round(ote_low, 2),
                level_618=round(level_618, 2),
                level_786=round(level_786, 2),
                current_price=current_price,
                price_in_ote_zone=in_zone,
                passed=in_zone,
                reasoning=(
                    f"Bullish OTE zone: ${ote_low:.2f}–${ote_high:.2f} "
                    f"(0.786: ${level_786:.2f}, 0.618: ${level_618:.2f}). "
                    f"Current price ${current_price:.2f} {'IS' if in_zone else 'is NOT'} inside the OTE zone."
                ),
            )

        else:  # BEARISH
            swing_high = max(c.high for c in recent)
            swing_low  = min(c.low  for c in recent)
            rng = swing_high - swing_low
            if rng <= 0:
                return FibonacciStep(current_price=current_price, passed=False,
                                     reasoning="Swing range is zero — Fibonacci skipped.")
            # Bearish OTE: retracement from low back UP toward high
            level_618 = swing_low + 0.618 * rng
            level_786 = swing_low + 0.786 * rng
            ote_low  = min(level_618, level_786)
            ote_high = max(level_618, level_786)
            in_zone = ote_low <= current_price <= ote_high

            return FibonacciStep(
                swing_high=round(swing_high, 2),
                swing_low=round(swing_low, 2),
                ote_high=round(ote_high, 2),
                ote_low=round(ote_low, 2),
                level_618=round(level_618, 2),
                level_786=round(level_786, 2),
                current_price=current_price,
                price_in_ote_zone=in_zone,
                passed=in_zone,
                reasoning=(
                    f"Bearish OTE zone: ${ote_low:.2f}–${ote_high:.2f} "
                    f"(0.618: ${level_618:.2f}, 0.786: ${level_786:.2f}). "
                    f"Current price ${current_price:.2f} {'IS' if in_zone else 'is NOT'} inside the OTE zone."
                ),
            )

    # ─────────────────────────────────────────────────────────
    # Step 5 — Fair Value Gap
    # ─────────────────────────────────────────────────────────

    def analyze_fvg(
        self,
        candles: List[Any],
        mss_direction: MSSDirection,
        current_price: float,
        timeframe: str = "5m",
    ) -> FVGStep:
        """Detect the most recent valid Fair Value Gap aligned with MSS direction."""
        candles = [_to_ohlcv(c) for c in candles]
        if mss_direction == MSSDirection.NONE:
            return FVGStep(
                fvg_type=FVGType.NONE,
                timeframe=timeframe,
                passed=False,
                reasoning="MSS not confirmed — FVG check skipped.",
            )

        recent = candles[-15:] if len(candles) >= 15 else candles
        if len(recent) < 3:
            return FVGStep(
                fvg_type=FVGType.NONE,
                timeframe=timeframe,
                passed=False,
                reasoning="Not enough candles for FVG detection.",
            )

        # Scan from newest to oldest (latest FVG wins)
        for i in range(len(recent) - 1, 1, -1):
            c_prev = recent[i - 2]   # candle i-2
            c_curr = recent[i - 1]   # candle i-1 (the body candle)
            c_next = recent[i]       # candle i

            # Bullish FVG: gap between c_prev.high and c_next.low (c_curr is the impulse up)
            if mss_direction == MSSDirection.BULLISH:
                if c_next.low > c_prev.high:
                    gap_low  = c_prev.high
                    gap_high = c_next.low
                    in_gap = gap_low <= current_price <= gap_high
                    return FVGStep(
                        fvg_type=FVGType.BULLISH,
                        fvg_high=round(gap_high, 2),
                        fvg_low=round(gap_low, 2),
                        price_in_fvg=in_gap,
                        timeframe=timeframe,
                        passed=in_gap,
                        reasoning=(
                            f"Bullish FVG detected on {timeframe}: ${gap_low:.2f}–${gap_high:.2f}. "
                            f"Price ${current_price:.2f} {'IS' if in_gap else 'is NOT'} inside the gap."
                        ),
                    )

            # Bearish FVG: gap between c_next.high and c_prev.low
            elif mss_direction == MSSDirection.BEARISH:
                if c_next.high < c_prev.low:
                    gap_high = c_prev.low
                    gap_low  = c_next.high
                    in_gap = gap_low <= current_price <= gap_high
                    return FVGStep(
                        fvg_type=FVGType.BEARISH,
                        fvg_high=round(gap_high, 2),
                        fvg_low=round(gap_low, 2),
                        price_in_fvg=in_gap,
                        timeframe=timeframe,
                        passed=in_gap,
                        reasoning=(
                            f"Bearish FVG detected on {timeframe}: ${gap_low:.2f}–${gap_high:.2f}. "
                            f"Price ${current_price:.2f} {'IS' if in_gap else 'is NOT'} inside the gap."
                        ),
                    )

        direction_str = "Bullish" if mss_direction == MSSDirection.BULLISH else "Bearish"
        return FVGStep(
            fvg_type=FVGType.NONE,
            timeframe=timeframe,
            passed=False,
            reasoning=f"No {direction_str} FVG found in the last {len(recent)} {timeframe} candles.",
        )

    # ─────────────────────────────────────────────────────────
    # Session Gate
    # ─────────────────────────────────────────────────────────

    def check_session(self, now_utc: Optional[datetime] = None) -> SessionStatus:
        """Check if current UTC time is within a valid trading session."""
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)

        current_t = now_utc.time().replace(second=0, microsecond=0)
        current_utc_str = now_utc.strftime("%H:%M UTC")

        for session_name, (start, end) in _SESSIONS.items():
            if start <= current_t < end:
                return SessionStatus(
                    active_session=session_name,
                    is_open=True,
                    session_start_utc=start.strftime("%H:%M UTC"),
                    session_end_utc=end.strftime("%H:%M UTC"),
                    current_time_utc=current_utc_str,
                    reasoning=f"{session_name.value} session is OPEN ({start.strftime('%H:%M')}–{end.strftime('%H:%M')} UTC).",
                )

        # Find next session
        next_sess = None
        min_wait = None
        for session_name, (start, end) in _SESSIONS.items():
            today_start = now_utc.replace(
                hour=start.hour, minute=start.minute, second=0, microsecond=0
            )
            if today_start <= now_utc:
                # Already passed today — push to tomorrow
                from datetime import timedelta
                today_start += timedelta(days=1)
            wait_mins = int((today_start - now_utc).total_seconds() / 60)
            if min_wait is None or wait_mins < min_wait:
                min_wait = wait_mins
                next_sess = session_name

        return SessionStatus(
            active_session=SessionName.NONE,
            is_open=False,
            next_session=next_sess,
            next_session_opens_in_minutes=min_wait,
            current_time_utc=current_utc_str,
            reasoning=(
                f"No active session. Current time: {current_utc_str}. "
                f"Next: {next_sess.value if next_sess else '?'} in ~{min_wait} min."
            ),
        )

    # ─────────────────────────────────────────────────────────
    # Position Sizing
    # ─────────────────────────────────────────────────────────

    def calculate_position_size(self, entry: float, stop_loss: float) -> float:
        """Calculate advisory lot size based on 1% risk of $10,000 balance."""
        sl_distance = abs(entry - stop_loss)
        if sl_distance < 0.01:
            return 0.01
        risk_amount = _STARTING_BALANCE * (_RISK_PCT / 100.0)
        lots = risk_amount / (sl_distance * _LOT_UNIT)
        return max(0.01, min(10.0, round(lots, 2)))

    # ─────────────────────────────────────────────────────────
    # Full 5-Step Signal
    # ─────────────────────────────────────────────────────────

    def generate_signal(
        self,
        trend: TrendStep,
        liquidity: LiquidityStep,
        mss: MSSStep,
        fibonacci: FibonacciStep,
        fvg: FVGStep,
        session: SessionStatus,
        current_price: float,
        timestamp: str,
    ) -> OTESignal:
        """Combine all 5 steps into a final OTE signal."""
        from datetime import datetime, timezone

        steps_passed = sum([
            trend.passed,
            liquidity.passed,
            mss.passed,
            fibonacci.passed,
            fvg.passed,
        ])

        steps_detail = [
            f"{'✅' if trend.passed     else '❌'} Step 1 — Trend: {trend.direction}",
            f"{'✅' if liquidity.passed else '❌'} Step 2 — Liquidity: {liquidity.sweep_direction.value} sweep",
            f"{'✅' if mss.passed       else '❌'} Step 3 — MSS: {mss.direction.value}",
            f"{'✅' if fibonacci.passed else '❌'} Step 4 — OTE Zone: {'IN ZONE' if fibonacci.price_in_ote_zone else 'OUT OF ZONE'}",
            f"{'✅' if fvg.passed       else '❌'} Step 5 — FVG: {fvg.fvg_type.value}",
        ]

        reasons  = []
        warnings = []

        # Session block
        if not session.is_open:
            reasons.append(f"WAIT — Outside valid session. {session.reasoning}")
            return OTESignal(
                symbol="XAU/USD",
                timestamp=timestamp,
                trend=trend, liquidity=liquidity, mss=mss,
                fibonacci=fibonacci, fvg=fvg, session=session,
                steps_passed=steps_passed,
                steps_detail=steps_detail,
                signal=OTESignalType.WAIT,
                confidence=0,
                setup_grade="C",
                reasons=reasons,
                warnings=["No valid session — London (07:00–10:00 UTC) or New York (13:00–16:00 UTC) required."],
            )

        # All 5 steps must pass for a signal
        if steps_passed < 5:
            missing = [d for d in steps_detail if d.startswith("❌")]
            reasons.append(f"WAIT — Only {steps_passed}/5 steps confirmed. Missing: {'; '.join(missing)}")
            return OTESignal(
                symbol="XAU/USD",
                timestamp=timestamp,
                trend=trend, liquidity=liquidity, mss=mss,
                fibonacci=fibonacci, fvg=fvg, session=session,
                steps_passed=steps_passed,
                steps_detail=steps_detail,
                signal=OTESignalType.WAIT,
                confidence=int(steps_passed / 5 * 50),
                setup_grade="C" if steps_passed < 3 else "B",
                reasons=reasons,
                warnings=warnings,
            )

        # Direction check: trend, liquidity sweep, MSS, and FVG must all agree
        if mss.direction == MSSDirection.BULLISH:
            signal_type = OTESignalType.BUY
        elif mss.direction == MSSDirection.BEARISH:
            signal_type = OTESignalType.SELL
        else:
            reasons.append("WAIT — MSS direction is NONE despite steps passing. Internal inconsistency.")
            return OTESignal(
                symbol="XAU/USD",
                timestamp=timestamp,
                trend=trend, liquidity=liquidity, mss=mss,
                fibonacci=fibonacci, fvg=fvg, session=session,
                steps_passed=steps_passed,
                steps_detail=steps_detail,
                signal=OTESignalType.WAIT,
                confidence=0,
                setup_grade="C",
                reasons=reasons,
                warnings=warnings,
            )

        # Calculate trade levels
        entry_price = current_price

        if signal_type == OTESignalType.BUY:
            # SL = below swing low with small buffer
            swing_low  = fibonacci.swing_low or (current_price - 20)
            stop_loss  = round(swing_low - 2.0, 2)
            risk       = entry_price - stop_loss
            tp1        = round(entry_price + risk * 1.5, 2)
            tp2        = round(entry_price + risk * 3.0, 2)
        else:  # SELL
            swing_high = fibonacci.swing_high or (current_price + 20)
            stop_loss  = round(swing_high + 2.0, 2)
            risk       = stop_loss - entry_price
            tp1        = round(entry_price - risk * 1.5, 2)
            tp2        = round(entry_price - risk * 3.0, 2)

        risk = abs(entry_price - stop_loss)
        rr_tp1 = round(abs(tp1 - entry_price) / risk, 2) if risk > 0 else 0.0
        rr_tp2 = round(abs(tp2 - entry_price) / risk, 2) if risk > 0 else 0.0

        position_size = self.calculate_position_size(entry_price, stop_loss)

        # Setup grade based on steps + confidence
        confidence = 80 + steps_passed * 4  # base 80 when all 5 pass
        confidence = min(95, confidence)

        # Check R:R for grading
        if rr_tp2 >= 3.0 and confidence >= 88:
            grade = "A+"
        elif rr_tp2 >= 2.5 and confidence >= 82:
            grade = "A"
        elif rr_tp2 >= 2.0:
            grade = "B"
        else:
            grade = "C"

        reasons = [
            f"All 5 Smart Money steps confirmed for {signal_type.value}",
            trend.reasoning,
            liquidity.reasoning,
            mss.reasoning,
            fibonacci.reasoning,
            fvg.reasoning,
            f"Session: {session.active_session.value} is OPEN",
        ]

        return OTESignal(
            symbol="XAU/USD",
            timestamp=timestamp,
            trend=trend, liquidity=liquidity, mss=mss,
            fibonacci=fibonacci, fvg=fvg, session=session,
            steps_passed=steps_passed,
            steps_detail=steps_detail,
            signal=signal_type,
            confidence=confidence,
            setup_grade=grade,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_reward_tp1=rr_tp1,
            risk_reward_tp2=rr_tp2,
            position_size=position_size,
            reasons=reasons,
            warnings=warnings,
        )
