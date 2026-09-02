"""
Unified Research Outcome Engine.

Authoritative engine for evaluating trades, outcomes, realized R, and portfolio performance metrics.
ALL research modules MUST use this engine to guarantee consistent, unbiased metrics.

Features:
- Deterministic candle-by-candle outcome simulation
- Strict non-favorable ambiguous candle resolution (Loss if ambiguous)
- Comprehensive risk metrics: Expectancy, Profit Factor, Max Drawdown, Win Rate, Streaks, Rolling Metrics
- Zero lookahead bias: evaluates forward from entry timestamp only

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from src.research.trade_semantics import (
    AmbiguousCandleResolution,
    AuthoritativeSignal,
    AuthoritativeTrade,
    OutcomeStatus,
    SignalDirection,
    TradeOutcomeRecord,
    calculate_initial_risk_distance,
    resolve_realized_r,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PerformanceMetrics:
    """Comprehensive performance metrics summary."""
    total_signals: int
    executed_trades: int
    buy_trades: int
    sell_trades: int
    wait_signals: int
    wins: int
    losses: int
    breakevens: int
    expired: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    total_realized_r: float
    max_drawdown_r: float
    avg_win_r: float
    avg_loss_r: float
    win_loss_ratio: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    realized_r_series: List[float]


class OutcomeEngine:
    """
    Unified, deterministic outcome evaluator for research experiments.
    """

    @staticmethod
    def evaluate_trade_outcome(
        trade: AuthoritativeTrade,
        future_candles: Sequence[Dict[str, Any]],  # Expects list of candles after trade entry: {"open", "high", "low", "close", "timestamp"}
        max_bars: int = 100,
        ambiguous_policy: AmbiguousCandleResolution = AmbiguousCandleResolution.WORST_CASE_LOSS,
    ) -> TradeOutcomeRecord:
        """
        Evaluate outcome forward from entry candle.
        Strict rule: If a single candle touches BOTH TP and SL, enforce conservative policy (Loss).
        """
        direction = trade.direction
        entry = trade.entry_price
        sl = trade.stop_loss
        tp = trade.take_profit
        risk_dist = trade.initial_risk_r

        max_favorable_excursion = 0.0
        max_adverse_excursion = 0.0

        for idx, candle in enumerate(future_candles[:max_bars]):
            high = float(candle.get("high", candle.get("h", 0.0)))
            low = float(candle.get("low", candle.get("l", 0.0)))
            close = float(candle.get("close", candle.get("c", 0.0)))
            ts = str(candle.get("timestamp", candle.get("t", "")))

            # Track MFE / MAE
            if direction == SignalDirection.BUY:
                mfe_curr = (high - entry) / risk_dist
                mae_curr = (entry - low) / risk_dist
                max_favorable_excursion = max(max_favorable_excursion, mfe_curr)
                max_adverse_excursion = max(max_adverse_excursion, mae_curr)

                hit_tp = high >= tp
                hit_sl = low <= sl
            else:  # SELL
                mfe_curr = (entry - low) / risk_dist
                mae_curr = (high - entry) / risk_dist
                max_favorable_excursion = max(max_favorable_excursion, mfe_curr)
                max_adverse_excursion = max(max_adverse_excursion, mae_curr)

                hit_tp = low <= tp
                hit_sl = high >= sl

            # Ambiguous candle handling (both hit in same bar)
            if hit_tp and hit_sl:
                if ambiguous_policy == AmbiguousCandleResolution.WORST_CASE_LOSS:
                    return TradeOutcomeRecord(
                        trade_id=trade.trade_id,
                        symbol=trade.symbol,
                        direction=direction,
                        outcome=OutcomeStatus.LOSS,
                        realized_r=-1.0,
                        mfe_r=round(max_favorable_excursion, 3),
                        mae_r=round(max_adverse_excursion, 3),
                        exit_price=sl,
                        exit_timestamp=ts,
                        bars_held=idx + 1,
                        ambiguous_resolution=ambiguous_policy,
                        notes="Ambiguous bar touched both TP and SL. Resolved conservatively as LOSS.",
                    )
                elif ambiguous_policy == AmbiguousCandleResolution.HALF_R_PENALTY:
                    return TradeOutcomeRecord(
                        trade_id=trade.trade_id,
                        symbol=trade.symbol,
                        direction=direction,
                        outcome=OutcomeStatus.LOSS,
                        realized_r=-0.5,
                        mfe_r=round(max_favorable_excursion, 3),
                        mae_r=round(max_adverse_excursion, 3),
                        exit_price=(sl + entry) / 2.0,
                        exit_timestamp=ts,
                        bars_held=idx + 1,
                        ambiguous_resolution=ambiguous_policy,
                        notes="Ambiguous bar touched both TP and SL. Resolved with -0.5R penalty.",
                    )

            # Clear single hits
            if hit_tp:
                r_val = resolve_realized_r(direction, entry, sl, tp, OutcomeStatus.WIN)
                return TradeOutcomeRecord(
                    trade_id=trade.trade_id,
                    symbol=trade.symbol,
                    direction=direction,
                    outcome=OutcomeStatus.WIN,
                    realized_r=r_val,
                    mfe_r=round(max_favorable_excursion, 3),
                    mae_r=round(max_adverse_excursion, 3),
                    exit_price=tp,
                    exit_timestamp=ts,
                    bars_held=idx + 1,
                    notes="Take profit reached.",
                )

            if hit_sl:
                r_val = resolve_realized_r(direction, entry, sl, sl, OutcomeStatus.LOSS)
                return TradeOutcomeRecord(
                    trade_id=trade.trade_id,
                    symbol=trade.symbol,
                    direction=direction,
                    outcome=OutcomeStatus.LOSS,
                    realized_r=r_val,
                    mfe_r=round(max_favorable_excursion, 3),
                    mae_r=round(max_adverse_excursion, 3),
                    exit_price=sl,
                    exit_timestamp=ts,
                    bars_held=idx + 1,
                    notes="Stop loss hit.",
                )

        # Expiry if max_bars exceeded
        last_candle = future_candles[-1] if future_candles else {}
        exit_p = float(last_candle.get("close", entry))
        exit_ts = str(last_candle.get("timestamp", ""))
        r_val = resolve_realized_r(direction, entry, sl, exit_p, OutcomeStatus.EXPIRED)

        return TradeOutcomeRecord(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            direction=direction,
            outcome=OutcomeStatus.EXPIRED,
            realized_r=r_val,
            mfe_r=round(max_favorable_excursion, 3),
            mae_r=round(max_adverse_excursion, 3),
            exit_price=exit_p,
            exit_timestamp=exit_ts,
            bars_held=len(future_candles),
            notes="Trade expired after max holding period.",
        )

    @classmethod
    def calculate_performance_metrics(
        cls,
        realized_r_list: Sequence[float],
        total_signals_count: Optional[int] = None,
        buy_count: Optional[int] = None,
        sell_count: Optional[int] = None,
        wait_count: Optional[int] = None,
    ) -> PerformanceMetrics:
        """
        Calculate complete performance metrics from an array of realized R values.
        """
        r_arr = np.array(realized_r_list, dtype=float)
        n_trades = len(r_arr)
        total_sig = total_signals_count if total_signals_count is not None else n_trades
        n_wait = wait_count if wait_count is not None else max(0, total_sig - n_trades)

        if n_trades == 0:
            return PerformanceMetrics(
                total_signals=total_sig,
                executed_trades=0,
                buy_trades=buy_count or 0,
                sell_trades=sell_count or 0,
                wait_signals=n_wait,
                wins=0,
                losses=0,
                breakevens=0,
                expired=0,
                win_rate_pct=0.0,
                expectancy_r=0.0,
                profit_factor=1.0,
                total_realized_r=0.0,
                max_drawdown_r=0.0,
                avg_win_r=0.0,
                avg_loss_r=0.0,
                win_loss_ratio=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                realized_r_series=[],
            )

        wins = int(np.sum(r_arr > 0.0))
        losses = int(np.sum(r_arr < 0.0))
        breakevens = int(np.sum(r_arr == 0.0))

        win_rate = round((wins / n_trades) * 100.0, 2)
        exp_r = round(float(np.mean(r_arr)), 4)
        tot_r = round(float(np.sum(r_arr)), 2)

        pos_sum = float(np.sum(r_arr[r_arr > 0.0])) if wins > 0 else 0.0
        neg_sum = float(np.sum(np.abs(r_arr[r_arr < 0.0]))) if losses > 0 else 0.0

        if neg_sum > 0:
            pf = round(pos_sum / neg_sum, 3)
        elif pos_sum > 0:
            pf = 99.0  # Infinite/No loss cap
        else:
            pf = 1.0

        avg_win = round(float(np.mean(r_arr[r_arr > 0.0])), 3) if wins > 0 else 0.0
        avg_loss = round(float(np.mean(r_arr[r_arr < 0.0])), 3) if losses > 0 else 0.0
        wl_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0.0

        # Drawdown calculation
        max_dd = cls.calculate_max_drawdown(r_arr)

        # Streaks
        max_win_streak, max_loss_streak = cls.calculate_streaks(r_arr)

        return PerformanceMetrics(
            total_signals=total_sig,
            executed_trades=n_trades,
            buy_trades=buy_count if buy_count is not None else 0,
            sell_trades=sell_count if sell_count is not None else 0,
            wait_signals=n_wait,
            wins=wins,
            losses=losses,
            breakevens=breakevens,
            expired=0,
            win_rate_pct=win_rate,
            expectancy_r=exp_r,
            profit_factor=pf,
            total_realized_r=tot_r,
            max_drawdown_r=round(max_dd, 2),
            avg_win_r=avg_win,
            avg_loss_r=avg_loss,
            win_loss_ratio=wl_ratio,
            max_consecutive_wins=max_win_streak,
            max_consecutive_losses=max_loss_streak,
            realized_r_series=r_arr.tolist(),
        )

    @staticmethod
    def calculate_max_drawdown(r_series: Sequence[float]) -> float:
        """
        Peak-to-trough maximum drawdown in R units.
        Returns positive value representing peak - trough.
        """
        if len(r_series) == 0:
            return 0.0
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in r_series:
            cum += float(r)
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 4)

    @staticmethod
    def calculate_streaks(r_series: Sequence[float]) -> Tuple[int, int]:
        """Returns (max_consecutive_wins, max_consecutive_losses)."""
        max_w = 0
        max_l = 0
        curr_w = 0
        curr_l = 0

        for r in r_series:
            if r > 0:
                curr_w += 1
                curr_l = 0
                max_w = max(max_w, curr_w)
            elif r < 0:
                curr_l += 1
                curr_w = 0
                max_l = max(max_l, curr_l)
            else:
                curr_w = 0
                curr_l = 0

        return max_w, max_l

    @staticmethod
    def calculate_rolling_expectancy(r_series: Sequence[float], window: int = 50) -> List[float]:
        """Calculates rolling mean expectancy over a sliding window."""
        if len(r_series) < window:
            return [float(np.mean(r_series))] if len(r_series) > 0 else []
        rolling = []
        for i in range(len(r_series) - window + 1):
            sub = r_series[i : i + window]
            rolling.append(round(float(np.mean(sub)), 4))
        return rolling
