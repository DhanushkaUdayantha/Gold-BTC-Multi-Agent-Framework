"""Unit tests for TechnicalEngine indicator calculations."""
import pytest
from src.models.market_data import OHLCVCandle
from src.models.technical_analysis import (
    RSICondition,
    MACDState,
    TrendDirection,
)
from src.services.technical_engine import TechnicalEngine


def test_ema_calculation():
    """Verify EMA calculation and handling of insufficient data."""
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
    
    # 5-period EMA
    ema5 = TechnicalEngine.calculate_ema(prices, 5)
    assert ema5 is not None
    assert isinstance(ema5, float)
    assert 10.0 < ema5 < 19.0

    # 20-period EMA with only 10 prices should return None (never fake values)
    ema20 = TechnicalEngine.calculate_ema(prices, 20)
    assert ema20 is None


def test_rsi_overbought_oversold():
    """Verify RSI calculation detects rising (overbought), falling (oversold), and flat markets."""
    # Strongly rising prices
    rising_prices = [100.0 + i * 2.0 for i in range(25)]
    rsi_rising = TechnicalEngine.calculate_rsi(rising_prices, period=14)
    assert rsi_rising is not None
    assert rsi_rising.value is not None
    assert rsi_rising.value > 70.0
    assert rsi_rising.condition == RSICondition.OVERBOUGHT

    # Strongly falling prices
    falling_prices = [200.0 - i * 2.0 for i in range(25)]
    rsi_falling = TechnicalEngine.calculate_rsi(falling_prices, period=14)
    assert rsi_falling is not None
    assert rsi_falling.value is not None
    assert rsi_falling.value < 30.0
    assert rsi_falling.condition == RSICondition.OVERSOLD

    # Oscillating / sideways prices
    oscillating_prices = [100.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(30)]
    rsi_neutral = TechnicalEngine.calculate_rsi(oscillating_prices, period=14)
    assert rsi_neutral is not None
    assert rsi_neutral.value is not None
    assert 40.0 <= rsi_neutral.value <= 60.0
    assert rsi_neutral.condition == RSICondition.NEUTRAL


def test_macd_momentum_states():
    """Verify MACD fast-slow EMA differences, histogram, and bullish/bearish crossover flags."""
    # Strong accelerating uptrend -> Fast EMA > Slow EMA -> Positive Histogram
    uptrend_closes = [2000.0 + (i ** 1.3) for i in range(60)]
    macd_bullish = TechnicalEngine.calculate_macd(uptrend_closes, fast=12, slow=26, signal=9)
    assert macd_bullish is not None
    assert macd_bullish.macd_line is not None
    assert macd_bullish.macd_line > 0
    assert macd_bullish.histogram is not None
    assert macd_bullish.state == MACDState.BULLISH

    # Strong accelerating downtrend -> Fast EMA < Slow EMA -> Negative Histogram
    downtrend_closes = [3000.0 - (i ** 1.3) for i in range(60)]
    macd_bearish = TechnicalEngine.calculate_macd(downtrend_closes, fast=12, slow=26, signal=9)
    assert macd_bearish is not None
    assert macd_bearish.macd_line is not None
    assert macd_bearish.macd_line < 0
    assert macd_bearish.histogram is not None
    assert macd_bearish.state == MACDState.BEARISH


def test_atr_volatility():
    """Verify Average True Range calculation correctly measures price volatility."""
    n = 30
    highs = [2000.0 + i + 5.0 for i in range(n)]
    lows = [2000.0 + i - 5.0 for i in range(n)]
    closes = [2000.0 + i for i in range(n)]

    atr = TechnicalEngine.calculate_atr(highs, lows, closes, period=14)
    assert atr is not None
    assert atr.value is not None
    # True range per candle is at least 10.0 (high - low)
    assert atr.value >= 10.0
    assert atr.volatility_pct is not None
    assert atr.volatility_pct > 0.0


def test_support_and_resistance_fractals():
    """Verify swing high and swing low level detection and proper above/below classification."""
    candles = []
    # Construct synthetic candles with an obvious peak at index 10 and trough at index 20
    for i in range(35):
        if i == 10:
            h, l, c, o = 2100.0, 2070.0, 2090.0, 2075.0
        elif i == 20:
            h, l, c, o = 2020.0, 1950.0, 1960.0, 2010.0
        else:
            h, l, c, o = 2050.0, 2030.0, 2040.0, 2035.0
        candles.append(OHLCVCandle(timestamp=f"2026-08-28T{i:02d}:00:00Z", open=o, high=h, low=l, close=c))

    current_price = 2040.0
    supports, resistances = TechnicalEngine.find_support_resistance(
        candles,
        current_price=current_price,
        window=3,
        max_levels=3,
    )

    # Resistances must be strictly above current price
    for r in resistances:
        assert r > current_price

    # Supports must be strictly below current price
    for s in supports:
        assert s < current_price


def test_trend_detection_scoring():
    """Verify multi-confirmation trend classifier for BULLISH, BEARISH, and SIDEWAYS regimes."""
    dummy_candles = [
        OHLCVCandle(timestamp=f"2026-08-28T{i:02d}:00:00Z", open=2000.0 + i, high=2005.0 + i, low=1995.0 + i, close=2002.0 + i)
        for i in range(10)
    ]

    # 1. Bullish scenario: Price > EMA20 > EMA50 > EMA200, MACD Bullish, RSI 60
    bullish_trend = TechnicalEngine.detect_market_trend(
        current_price=2100.0,
        ema20=2080.0,
        ema50=2050.0,
        ema200=2000.0,
        rsi=TechnicalEngine.calculate_rsi([100.0 + i * 0.5 for i in range(25)], 14),
        macd=TechnicalEngine.calculate_macd([2000.0 + i * 2.0 for i in range(50)], 12, 26, 9),
        candles=dummy_candles,
    )
    assert bullish_trend.direction == TrendDirection.BULLISH
    assert bullish_trend.score > 0.3
    assert len(bullish_trend.confirmations) > 0

    # 2. Bearish scenario: Price < EMA20 < EMA50 < EMA200, MACD Bearish
    bearish_trend = TechnicalEngine.detect_market_trend(
        current_price=1900.0,
        ema20=1920.0,
        ema50=1950.0,
        ema200=2000.0,
        rsi=TechnicalEngine.calculate_rsi([200.0 - i * 0.5 for i in range(25)], 14),
        macd=TechnicalEngine.calculate_macd([2500.0 - i * 2.0 for i in range(50)], 12, 26, 9),
        candles=dummy_candles,
    )
    assert bearish_trend.direction == TrendDirection.BEARISH
    assert bearish_trend.score < -0.3

    # 3. Sideways / Indecisive scenario: Mixed EMAs, neutral momentum
    sideways_trend = TechnicalEngine.detect_market_trend(
        current_price=2000.0,
        ema20=2000.0,
        ema50=2000.0,
        ema200=2000.0,
        rsi=None,
        macd=None,
        candles=[],
    )
    assert sideways_trend.direction == TrendDirection.SIDEWAYS
