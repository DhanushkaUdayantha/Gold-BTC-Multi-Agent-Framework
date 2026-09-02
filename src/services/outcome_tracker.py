"""
Outcome Tracker — labels the empirical result of recorded signals.

KEY INVARIANT (no look-ahead bias):
  signal_timestamp is the information barrier.
  Only price observations AFTER signal_timestamp are used to label outcomes.
  Future price data is NEVER used during signal generation.

Outcome logic:
  - WIN:       current_price hits take_profit_1 (for BUY: price >= TP1, for SELL: price <= TP1)
  - LOSS:      current_price hits stop_loss
  - BREAKEVEN: exit within 0.05% of entry without SL/TP hit
  - EXPIRED:   signal older than OUTCOME_EXPIRY_HOURS without resolution
  - INVALID:   signal missing required fields for evaluation
  - OPEN:      still waiting for outcome

MFE/MAE are tracked continuously on each price observation.
For BUY:  MFE = max(price - entry),  MAE = max(entry - price)
For SELL: MFE = max(entry - price),  MAE = max(price - entry)

DISCLAIMER: Advisory tracking only. No real trades.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from src.models.signal_record import SignalRecord, SignalOutcome
from src.services.signal_repository import get_signal_repository

logger = logging.getLogger(__name__)

# Configurable via environment — default 72 hours
_OUTCOME_EXPIRY_HOURS = int(os.environ.get("OUTCOME_EXPIRY_HOURS", "72"))

# Breakeven tolerance: within this % of entry → BREAKEVEN (not WIN/LOSS)
_BREAKEVEN_TOLERANCE_PCT = 0.0005   # 0.05%

# Minimum time after signal before outcome can be labeled (avoids same-tick false hits)
_MIN_OBSERVATION_MINUTES = 1


class OutcomeTracker:
    """
    Passively labels open signal outcomes from incoming price observations.
    Called by DecisionService on every decision cycle (non-blocking, best-effort).
    """

    def __init__(self) -> None:
        self._repo = get_signal_repository()

    def label_outcomes(
        self,
        current_price: float,
        current_timestamp: Optional[datetime] = None,
        candles_history: Optional[List[Dict[str, Any]]] = None,
        symbol: Optional[str] = None,
    ) -> int:
        """
        Check OPEN signals for the given symbol (or all if None) and label any that have resolved.
        Returns the number of signals newly labeled.
        """
        if not current_price or current_price <= 0:
            return 0

        now = current_timestamp or datetime.now(timezone.utc)
        pending = self._repo.get_pending_outcome_signals(symbol=symbol)
        labeled_count = 0

        for signal in pending:
            try:
                newly_labeled = self._evaluate_signal(signal, current_price, now, candles_history)
                if newly_labeled:
                    labeled_count += 1
            except Exception as exc:
                logger.warning(
                    f"OutcomeTracker: error evaluating signal {signal.signal_id[:8]}: {exc}"
                )

        return labeled_count

    # ------------------------------------------------------------------
    # Signal evaluation
    # ------------------------------------------------------------------

    def _evaluate_signal(
        self,
        signal: SignalRecord,
        current_price: float,
        now: datetime,
        candles_history: Optional[List[Dict[str, Any]]],
    ) -> bool:
        """Evaluate one signal. Returns True if outcome was set."""

        # Parse signal timestamp (the look-ahead barrier)
        try:
            sig_ts = datetime.fromisoformat(
                signal.signal_timestamp.replace("Z", "+00:00")
            )
        except Exception:
            self._label(signal, "INVALID", current_price, now, exit_reason="INVALID", note="Malformed signal_timestamp")
            return True

        # Enforce minimum observation window (avoid same-tick labeling)
        age_minutes = (now - sig_ts).total_seconds() / 60.0
        if age_minutes < _MIN_OBSERVATION_MINUTES:
            return False

        # Check EXPIRED
        if age_minutes > _OUTCOME_EXPIRY_HOURS * 60:
            self._label(
                signal, "EXPIRED", current_price, now,
                exit_reason="EXPIRED",
                note=f"Expired after {_OUTCOME_EXPIRY_HOURS}h without SL/TP hit",
            )
            return True

        # INVALID: missing SL (required for R calculation)
        if signal.stop_loss is None:
            self._label(signal, "INVALID", current_price, now, exit_reason="INVALID", note="No stop_loss recorded")
            return True

        entry = signal.entry_price
        sl = signal.stop_loss
        tp1 = signal.take_profit_1
        direction = signal.direction

        # ---- Update running MFE/MAE ----
        mfe = self._compute_mfe(direction, entry, current_price, signal.current_mfe)
        mae = self._compute_mae(direction, entry, current_price, signal.current_mae)
        self._repo.update_running_excursions(signal.signal_id, mfe, mae)

        # ---- Check outcome conditions ----
        if direction == "BUY":
            hit_sl = current_price <= sl
            hit_tp = (tp1 is not None) and (current_price >= tp1)
        else:  # SELL
            hit_sl = current_price >= sl
            hit_tp = (tp1 is not None) and (current_price <= tp1)

        # ---- Also scan candle highs/lows for intra-bar hits ----
        if candles_history and not hit_sl and not hit_tp:
            hit_sl, hit_tp = self._scan_candles(
                direction, sl, tp1, candles_history, sig_ts
            )

        # Ambiguity check: if both TP and SL were breached in same scan window without order resolution
        if hit_sl and hit_tp:
            # Conservative rule: prioritize SL or mark LOSS
            hit_tp = False

        if hit_tp and tp1 is not None:
            initial_risk = abs(entry - sl)
            r = (abs(tp1 - entry) / initial_risk) if initial_risk > 0 else 1.5
            success_reason = "HTF_TREND_ALIGNMENT" if signal.confluence_score >= 65 else "STRUCTURE_CONFLUENCE_SUPPORT"
            self._label(
                signal, "WIN", tp1, now,
                realized_r=r,
                mfe=mfe, mae=mae, max_r=r,
                exit_reason="TP1_HIT",
                success_reason=success_reason,
                note=f"TP1 hit @ {tp1:.2f}",
            )
            return True

        if hit_sl:
            initial_risk = abs(entry - sl)
            r = -1.0
            # Attribute failure reason
            if signal.market_regime in ("HIGH_VOLATILITY", "VOLATILE"):
                failure_reason = "VOLATILITY_SHOCK"
            elif signal.conflicts and len(signal.conflicts) > 0:
                failure_reason = "HTF_CONFLICT"
            elif mae and mae > (initial_risk * 1.2):
                failure_reason = "TREND_REVERSAL"
            else:
                failure_reason = "FALSE_BREAKOUT"

            self._label(
                signal, "LOSS", sl, now,
                realized_r=r,
                mfe=mfe, mae=mae, max_r=(mfe / initial_risk if initial_risk > 0 else None),
                exit_reason="SL_HIT",
                failure_reason=failure_reason,
                failure_category=failure_reason,
                note=f"SL hit @ {sl:.2f}",
            )
            return True

        # ---- BREAKEVEN (no TP defined, price close to entry, some time elapsed) ----
        if tp1 is None and age_minutes > 30:
            diff_pct = abs(current_price - entry) / entry
            if diff_pct <= _BREAKEVEN_TOLERANCE_PCT:
                self._label(
                    signal, "BREAKEVEN", current_price, now,
                    realized_r=0.0, mfe=mfe, mae=mae,
                    exit_reason="BREAKEVEN",
                    note="No TP defined; price returned near entry",
                )
                return True

        return False  # Still OPEN

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _label(
        self,
        signal: SignalRecord,
        outcome_str: str,
        exit_price: float,
        outcome_ts: datetime,
        realized_r: Optional[float] = None,
        mfe: Optional[float] = None,
        mae: Optional[float] = None,
        max_r: Optional[float] = None,
        exit_reason: Optional[str] = None,
        success_reason: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_category: Optional[str] = None,
        note: str = "",
    ) -> None:
        """Write the outcome to the repository."""
        try:
            sig_ts = datetime.fromisoformat(
                signal.signal_timestamp.replace("Z", "+00:00")
            )
            minutes = int((outcome_ts - sig_ts).total_seconds() / 60)
            bars = max(1, minutes // 15)
        except Exception:
            minutes = None
            bars = None

        outcome = SignalOutcome(
            outcome=outcome_str,
            outcome_timestamp=outcome_ts.isoformat(),
            exit_price=round(exit_price, 4) if exit_price else None,
            realized_r=round(realized_r, 4) if realized_r is not None else None,
            mfe=round(mfe, 4) if mfe is not None else None,
            mae=round(mae, 4) if mae is not None else None,
            max_r=round(max_r, 4) if max_r is not None else None,
            time_to_outcome_minutes=minutes,
            bars_to_resolution=bars,
            exit_reason=exit_reason or outcome_str,
            success_reason=success_reason,
            failure_reason=failure_reason,
            failure_category=failure_category,
            transaction_cost_included=False,
            spread_at_entry=signal.outcome.spread_at_entry if signal.outcome else None,
            note=note,
        )
        self._repo.update_outcome(signal.signal_id, outcome)
        logger.info(
            f"OutcomeTracker: {outcome_str} signal #{signal.signal_id[:8]} "
            f"({signal.symbol}) entry={signal.entry_price:.2f} R={realized_r}"
        )

    @staticmethod
    def _compute_mfe(
        direction: str, entry: float, current_price: float,
        prev_mfe: Optional[float],
    ) -> float:
        """Maximum Favorable Excursion (price units, always positive)."""
        if direction == "BUY":
            current = max(0.0, current_price - entry)
        else:
            current = max(0.0, entry - current_price)
        return max(current, prev_mfe or 0.0)

    @staticmethod
    def _compute_mae(
        direction: str, entry: float, current_price: float,
        prev_mae: Optional[float],
    ) -> float:
        """Maximum Adverse Excursion (price units, always positive)."""
        if direction == "BUY":
            current = max(0.0, entry - current_price)
        else:
            current = max(0.0, current_price - entry)
        return max(current, prev_mae or 0.0)

    @staticmethod
    def _scan_candles(
        direction: str,
        sl: float,
        tp1: Optional[float],
        candles: List[Dict[str, Any]],
        after_ts: datetime,
    ) -> tuple:
        """
        Scan closed candle highs/lows for intra-bar SL or TP hits.
        Only considers candles AFTER the signal timestamp (no look-ahead).
        Returns (hit_sl, hit_tp).
        """
        hit_sl = False
        hit_tp = False

        for c in candles:
            # Enforce look-ahead barrier
            c_ts_str = c.get("timestamp", "")
            if c_ts_str:
                try:
                    c_ts = datetime.fromisoformat(
                        str(c_ts_str).replace("Z", "+00:00")
                    )
                    if c_ts <= after_ts:
                        continue   # This candle is before/at signal — skip
                except Exception:
                    pass  # If can't parse, include it (conservative)

            high = float(c.get("high", 0) or 0)
            low = float(c.get("low", 0) or 0)

            if direction == "BUY":
                if low <= sl:
                    hit_sl = True
                if tp1 is not None and high >= tp1:
                    hit_tp = True
            else:
                if high >= sl:
                    hit_sl = True
                if tp1 is not None and low <= tp1:
                    hit_tp = True

        return hit_sl, hit_tp


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_tracker_instance: Optional[OutcomeTracker] = None


def get_outcome_tracker() -> OutcomeTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = OutcomeTracker()
    return _tracker_instance
