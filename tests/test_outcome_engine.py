"""
Unit tests for unified outcome engine.
"""
import pytest

from src.research.outcome_engine import OutcomeEngine, PerformanceMetrics
from src.research.trade_semantics import (
    AmbiguousCandleResolution,
    AuthoritativeTrade,
    OutcomeStatus,
    SignalDirection,
)


def test_evaluate_trade_outcome_buy_win():
    trade = AuthoritativeTrade(
        trade_id="t1",
        signal_id="s1",
        symbol="XAU-USD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2010.0,
        entry_timestamp="2026-01-01T00:00:00Z",
        initial_risk_r=10.0,
    )
    candles = [
        {"high": 2005.0, "low": 1995.0, "close": 2002.0, "timestamp": "2026-01-01T00:05:00Z"},
        {"high": 2012.0, "low": 1998.0, "close": 2011.0, "timestamp": "2026-01-01T00:10:00Z"},
    ]
    res = OutcomeEngine.evaluate_trade_outcome(trade, candles)
    assert res.outcome == OutcomeStatus.WIN
    assert res.realized_r == 1.0
    assert res.bars_held == 2


def test_evaluate_trade_outcome_sell_loss():
    trade = AuthoritativeTrade(
        trade_id="t2",
        signal_id="s2",
        symbol="BTC-USD",
        direction=SignalDirection.SELL,
        entry_price=50000.0,
        stop_loss=50500.0,
        take_profit=49000.0,
        entry_timestamp="2026-01-01T00:00:00Z",
        initial_risk_r=500.0,
    )
    candles = [
        {"high": 50600.0, "low": 49800.0, "close": 50550.0, "timestamp": "2026-01-01T00:05:00Z"},
    ]
    res = OutcomeEngine.evaluate_trade_outcome(trade, candles)
    assert res.outcome == OutcomeStatus.LOSS
    assert res.realized_r == -1.0
    assert res.bars_held == 1


def test_evaluate_trade_outcome_ambiguous_bar_loss():
    # Single candle touches both TP (2010) and SL (1990)
    trade = AuthoritativeTrade(
        trade_id="t3",
        signal_id="s3",
        symbol="XAU-USD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2010.0,
        entry_timestamp="2026-01-01T00:00:00Z",
        initial_risk_r=10.0,
    )
    candles = [
        {"high": 2015.0, "low": 1985.0, "close": 2000.0, "timestamp": "2026-01-01T00:05:00Z"},
    ]
    res = OutcomeEngine.evaluate_trade_outcome(trade, candles, ambiguous_policy=AmbiguousCandleResolution.WORST_CASE_LOSS)
    assert res.outcome == OutcomeStatus.LOSS
    assert res.realized_r == -1.0


def test_performance_metrics_calculations():
    # 3 wins (+1.0R each), 2 losses (-1.0R each)
    r_list = [1.0, 1.0, -1.0, 1.0, -1.0]
    perf = OutcomeEngine.calculate_performance_metrics(r_list)

    assert perf.executed_trades == 5
    assert perf.wins == 3
    assert perf.losses == 2
    assert perf.win_rate_pct == 60.0
    assert perf.expectancy_r == 0.20
    assert perf.total_realized_r == 1.0
    assert perf.profit_factor == 1.5  # 3.0 / 2.0
    assert perf.max_drawdown_r == 1.0
    assert perf.max_consecutive_wins == 2
    assert perf.max_consecutive_losses == 1


def test_calculate_max_drawdown():
    # Sequence: 1, 2, 1, 0, 3 -> peak 2, trough 0 -> dd = 2.0
    r_series = [1.0, 1.0, -1.0, -1.0, 3.0]
    assert OutcomeEngine.calculate_max_drawdown(r_series) == 2.0
