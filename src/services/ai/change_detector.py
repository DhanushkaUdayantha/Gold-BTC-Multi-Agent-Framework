"""
Meaningful-Change Detector for AI Analysis Refresh Gate.

Determines whether a new Gemini AI call is warranted by comparing the
current technical/signal state against the last analysis snapshot.

RULE: Gemini must only be called when something materially changed.
      Frontend polling, chart refresh, price tick, and countdown ticks
      must NEVER trigger a Gemini call.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Configurable thresholds
PRICE_MOVE_PCT_THRESHOLD: float = 0.40      # 0.40% price move triggers refresh
SIGNAL_STRENGTH_DELTA_THRESHOLD: int = 10   # 10 point strength delta triggers refresh
STALE_ANALYSIS_MAX_AGE_SECONDS: float = 900 # 15 min always refresh if this old


@dataclass
class AnalysisSnapshot:
    """Snapshot of market state at the time of the last AI analysis."""
    signal_direction: str = "WAIT"
    signal_strength: int = 0
    price_at_analysis: float = 0.0
    m5_trend: str = "SIDEWAYS"
    m15_trend: str = "SIDEWAYS"
    h1_trend: str = "SIDEWAYS"
    d1_trend: str = "SIDEWAYS"
    rsi_condition: str = "NEUTRAL"
    macd_state: str = "NEUTRAL"
    candle_timestamp: str = ""
    analysis_timestamp: float = 0.0
    request_reason: str = "initial"


class MeaningfulChangeDetector:
    """
    Gates Gemini AI calls by comparing current market state against the
    last analysis snapshot.

    Returns (should_refresh: bool, reason: str).
    Consult BEFORE the cooldown/budget check in the request manager.
    If this returns False, skip the request manager and serve cache.
    """

    def __init__(self):
        self._snapshots: dict[str, AnalysisSnapshot] = {}

    def should_refresh(
        self,
        *,
        symbol: str = "XAU-USD-SPOT",
        current_signal: str,
        current_strength: int,
        current_price: float,
        m5_trend: str,
        m15_trend: str,
        h1_trend: str,
        d1_trend: str,
        rsi_condition: str,
        macd_state: str,
        candle_timestamp: str,
    ) -> Tuple[bool, str]:
        """Evaluate whether conditions changed enough to justify a Gemini call."""
        now = time.time()
        sym_key = symbol.upper()
        snap = self._snapshots.get(sym_key)

        if snap is None:
            reason = f"initial_analysis_{sym_key} — no prior snapshot exists"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        age = now - snap.analysis_timestamp
        if age >= STALE_ANALYSIS_MAX_AGE_SECONDS:
            reason = f"stale_analysis — last AI call was {int(age)}s ago (max {int(STALE_ANALYSIS_MAX_AGE_SECONDS)}s)"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        if current_signal != snap.signal_direction:
            reason = (
                f"signal_direction_changed — {snap.signal_direction} -> {current_signal} "
                f"(strength: {snap.signal_strength} -> {current_strength})"
            )
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        strength_delta = abs(current_strength - snap.signal_strength)
        if strength_delta >= SIGNAL_STRENGTH_DELTA_THRESHOLD:
            reason = (
                f"signal_strength_delta — {snap.signal_strength} -> {current_strength} "
                f"(delta={strength_delta} >= threshold={SIGNAL_STRENGTH_DELTA_THRESHOLD})"
            )
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        if snap.price_at_analysis > 0:
            price_move_pct = abs(current_price - snap.price_at_analysis) / snap.price_at_analysis * 100
            if price_move_pct >= PRICE_MOVE_PCT_THRESHOLD:
                price_delta = current_price - snap.price_at_analysis
                reason = (
                    f"price_moved — {snap.price_at_analysis:.2f} -> {current_price:.2f} "
                    f"({price_delta:+.2f}, {price_move_pct:.2f}% >= threshold={PRICE_MOVE_PCT_THRESHOLD}%)"
                )
                logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
                return True, reason

        if h1_trend != snap.h1_trend:
            reason = f"h1_trend_changed — {snap.h1_trend} -> {h1_trend}"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        prev_macd = snap.macd_state
        if (
            macd_state != prev_macd
            and (
                (prev_macd == "BULLISH" and macd_state == "BEARISH")
                or (prev_macd == "BEARISH" and macd_state == "BULLISH")
            )
        ):
            reason = f"macd_flip — {prev_macd} -> {macd_state}"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        prev_rsi = snap.rsi_condition
        rsi_cross = (
            (prev_rsi == "NEUTRAL" and rsi_condition in ("OVERSOLD", "OVERBOUGHT"))
            or (prev_rsi in ("OVERSOLD", "OVERBOUGHT") and rsi_condition == "NEUTRAL")
        )
        if rsi_cross:
            reason = f"rsi_boundary_cross — {prev_rsi} -> {rsi_condition}"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        if candle_timestamp and candle_timestamp != snap.candle_timestamp:
            age_since_last = now - snap.analysis_timestamp
            if age_since_last >= 120.0:
                reason = (
                    f"new_candle_closed — prev={snap.candle_timestamp!r} -> "
                    f"new={candle_timestamp!r} (age_since_analysis={int(age_since_last)}s)"
                )
                logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
                return True, reason

        if d1_trend != snap.d1_trend:
            reason = f"d1_trend_changed — {snap.d1_trend} -> {d1_trend}"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        if m15_trend != snap.m15_trend:
            reason = f"m15_trend_changed — {snap.m15_trend} -> {m15_trend}"
            logger.info(f"AI refresh gate ({sym_key}): ALLOWED — {reason}")
            return True, reason

        reason = (
            f"no_meaningful_change — signal={current_signal}({current_strength}%), "
            f"price={current_price:.2f} (moved {abs(current_price - snap.price_at_analysis):.2f}), "
            f"age={int(age)}s"
        )
        logger.debug(f"AI refresh gate ({sym_key}): BLOCKED — {reason}")
        return False, reason

    def record_analysis(
        self,
        *,
        symbol: str = "XAU-USD-SPOT",
        signal_direction: str,
        signal_strength: int,
        price_at_analysis: float,
        m5_trend: str,
        m15_trend: str,
        h1_trend: str,
        d1_trend: str,
        rsi_condition: str,
        macd_state: str,
        candle_timestamp: str,
        request_reason: str,
    ) -> None:
        """Store snapshot after a successful Gemini analysis. Must always be called."""
        sym_key = symbol.upper()
        self._snapshots[sym_key] = AnalysisSnapshot(
            signal_direction=signal_direction,
            signal_strength=signal_strength,
            price_at_analysis=price_at_analysis,
            m5_trend=m5_trend,
            m15_trend=m15_trend,
            h1_trend=h1_trend,
            d1_trend=d1_trend,
            rsi_condition=rsi_condition,
            macd_state=macd_state,
            candle_timestamp=candle_timestamp,
            analysis_timestamp=time.time(),
            request_reason=request_reason,
        )

    @property
    def _last_snapshot(self) -> Optional[AnalysisSnapshot]:
        return self._snapshots.get("XAU-USD-SPOT") or next(iter(self._snapshots.values()), None)

    @_last_snapshot.setter
    def _last_snapshot(self, val: Optional[AnalysisSnapshot]) -> None:
        if val is not None:
            self._snapshots["XAU-USD-SPOT"] = val

    def get_snapshot(self, symbol: str = "XAU-USD-SPOT") -> Optional[AnalysisSnapshot]:
        """Return the current snapshot (None if no analysis yet)."""
        sym_key = symbol.upper()
        return self._snapshots.get(sym_key) or self._last_snapshot
