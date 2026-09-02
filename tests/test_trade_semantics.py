"""
Unit tests for trade and outcome semantics specification.
"""
import pytest

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


def test_initial_risk_distance_calculation():
    # BUY: entry 2000, sl 1980 -> risk 20
    assert calculate_initial_risk_distance(SignalDirection.BUY, 2000.0, 1980.0) == 20.0

    # SELL: entry 2000, sl 2020 -> risk 20
    assert calculate_initial_risk_distance(SignalDirection.SELL, 2000.0, 2020.0) == 20.0

    # Invalid SL
    with pytest.raises(ValueError):
        calculate_initial_risk_distance(SignalDirection.BUY, 2000.0, 2010.0)

    with pytest.raises(ValueError):
        calculate_initial_risk_distance(SignalDirection.SELL, 2000.0, 1990.0)


def test_resolve_realized_r_win_and_loss():
    # BUY Win: 1R
    assert resolve_realized_r(SignalDirection.BUY, 2000.0, 1980.0, 2020.0, OutcomeStatus.WIN) == 1.0

    # BUY Loss: -1R
    assert resolve_realized_r(SignalDirection.BUY, 2000.0, 1980.0, 1980.0, OutcomeStatus.LOSS) == -1.0

    # SELL Win: 1R
    assert resolve_realized_r(SignalDirection.SELL, 2000.0, 2020.0, 1980.0, OutcomeStatus.WIN) == 1.0

    # SELL Loss: -1R
    assert resolve_realized_r(SignalDirection.SELL, 2000.0, 2020.0, 2020.0, OutcomeStatus.LOSS) == -1.0

    # Breakeven: 0R
    assert resolve_realized_r(SignalDirection.BUY, 2000.0, 1980.0, 2000.0, OutcomeStatus.BREAKEVEN) == 0.0

    # Ambiguous candle: conservative loss -1R
    assert resolve_realized_r(SignalDirection.BUY, 2000.0, 1980.0, 2000.0, OutcomeStatus.AMBIGUOUS) == -1.0


def test_authoritative_signal_and_trade():
    sig = AuthoritativeSignal(
        signal_id="sig_1",
        timestamp="2026-01-01T00:00:00Z",
        symbol="BTC-USD",
        direction=SignalDirection.SELL,
        probability=0.45,
        entry_price=50000.0,
        stop_loss=50500.0,
        take_profit_1=49000.0,
    )
    assert sig.is_actionable is True

    trade = AuthoritativeTrade(
        trade_id="tr_1",
        signal_id=sig.signal_id,
        symbol=sig.symbol,
        direction=sig.direction,
        entry_price=sig.entry_price,
        stop_loss=sig.stop_loss,
        take_profit=sig.take_profit_1,
        entry_timestamp=sig.timestamp,
        initial_risk_r=500.0,
    )
    assert trade.direction == SignalDirection.SELL
    assert trade.initial_risk_r == 500.0

    # WAIT cannot be a trade
    with pytest.raises(ValueError):
        AuthoritativeTrade(
            trade_id="tr_2",
            signal_id="sig_2",
            symbol="BTC-USD",
            direction=SignalDirection.WAIT,
            entry_price=50000.0,
            stop_loss=50500.0,
            take_profit=49000.0,
            entry_timestamp="2026-01-01T00:00:00Z",
            initial_risk_r=500.0,
        )
