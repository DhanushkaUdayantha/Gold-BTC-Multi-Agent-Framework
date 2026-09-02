"""Unit tests for TechnicalAnalysisService and edge case handling."""
import pytest
from unittest.mock import MagicMock

from src.models.market_data import CandleHistory, OHLCVCandle, Timeframe
from src.models.technical_analysis import TrendDirection
from src.services.technical_service import TechnicalAnalysisService


def create_mock_candles(count: int, start_price: float = 2000.0, step: float = 1.0):
    candles = []
    for i in range(count):
        p = start_price + (i * step)
        candles.append(
            OHLCVCandle(
                timestamp=f"2026-08-28T{i:04d}:00:00Z",
                open=p - 0.5,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=100.0,
                is_closed=True,
            )
        )
    return candles


def test_technical_service_full_data():
    """Verify service calculates all indicators when full history (250 candles) is available."""
    mock_market = MagicMock()
    mock_market.get_candles.return_value = CandleHistory(
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe.M15,
        count=250,
        candles=create_mock_candles(250, start_price=2000.0, step=0.5),
        provider="TestProvider",
        fetched_at="2026-08-28T09:00:00Z",
    )

    service = TechnicalAnalysisService(market_service=mock_market)
    res = service.analyze(symbol="XAU-USD-SPOT", timeframe=Timeframe.M15)

    assert res.symbol == "XAU-USD-SPOT"
    assert res.timeframe == Timeframe.M15
    assert res.ema20 is not None
    assert res.ema50 is not None
    assert res.ema200 is not None
    assert res.rsi14 is not None and res.rsi14.value is not None
    assert res.macd is not None and res.macd.histogram is not None
    assert res.atr14 is not None and res.atr14.value is not None
    assert res.data_quality.is_sufficient is True
    assert len(res.data_quality.missing_indicators) == 0


def test_technical_service_insufficient_history():
    """Verify service gracefully flags missing EMA200 when only 30 candles exist."""
    mock_market = MagicMock()
    mock_market.get_candles.return_value = CandleHistory(
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe.M1,
        count=30,
        candles=create_mock_candles(30, start_price=2000.0, step=0.5),
        provider="TestProvider",
        fetched_at="2026-08-28T09:00:00Z",
    )

    service = TechnicalAnalysisService(market_service=mock_market)
    res = service.analyze(symbol="XAU-USD-SPOT", timeframe=Timeframe.M1)

    assert res.ema20 is not None
    # 30 candles < 50 and < 200 -> ema50 and ema200 must be None
    assert res.ema50 is None
    assert res.ema200 is None
    # Data quality must list the missing items
    assert "EMA50 (requires >= 50 bars)" in res.data_quality.missing_indicators
    assert "EMA200 (requires >= 200 bars)" in res.data_quality.missing_indicators
    assert res.data_quality.is_sufficient is False


def test_technical_service_zero_candles():
    """Verify service raises descriptive error when 0 candles are returned."""
    mock_market = MagicMock()
    mock_market.get_candles.return_value = CandleHistory(
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe.M5,
        count=0,
        candles=[],
        provider="TestProvider",
        fetched_at="2026-08-28T09:00:00Z",
    )

    service = TechnicalAnalysisService(market_service=mock_market)
    with pytest.raises(ValueError, match="No candle data available"):
        service.analyze(symbol="XAU-USD-SPOT", timeframe=Timeframe.M5)
