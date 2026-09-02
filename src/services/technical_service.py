"""Technical Analysis Service.

Orchestrates market candle data retrieval, executes indicator calculations via TechnicalEngine,
evaluates data quality, and generates comprehensive technical reports.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from functools import lru_cache

from src.models.market_data import Timeframe, CandleHistory
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
    DataQualityReport,
    RSIResult,
    MACDResult,
    ATRResult,
)
from src.services.market_service import MarketDataService, get_market_service
from src.services.technical_engine import TechnicalEngine

logger = logging.getLogger(__name__)


class TechnicalAnalysisService:
    """Service responsible for technical analysis computations on market data."""

    def __init__(self, market_service: Optional[MarketDataService] = None):
        self.market_service = market_service or get_market_service()
        self.engine = TechnicalEngine()

    def analyze(
        self,
        symbol: Optional[str] = None,
        timeframe: Timeframe = Timeframe.M15,
        force_refresh: bool = False,
        include_series: bool = False,
    ) -> TechnicalAnalysisResponse:
        """Execute full technical indicator suite and trend classification for a given timeframe.

        Args:
            symbol: Trading instrument (default from settings)
            timeframe: Candle interval (1m, 5m, 15m, 1h, 1d)
            force_refresh: Whether to bypass market data cache

        Returns:
            TechnicalAnalysisResponse containing all indicators, levels, and trend analysis.
        """
        # Request up to 250 candles to allow 200 EMA computation
        candle_limit = 250
        history: CandleHistory = self.market_service.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=candle_limit,
            force_refresh=force_refresh,
        )

        candles = history.candles
        n_candles = len(candles)

        if n_candles == 0:
            raise ValueError(f"No candle data available for {symbol or 'XAU/USD'} on {timeframe.value} timeframe.")

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        latest_candle = candles[-1]
        current_price = latest_candle.close

        # Track missing indicators for data quality reporting
        missing_indicators: List[str] = []

        # 1. EMA Calculations
        ema20 = self.engine.calculate_ema(closes, 20)
        if ema20 is None:
            missing_indicators.append("EMA20 (requires >= 20 bars)")

        ema50 = self.engine.calculate_ema(closes, 50)
        if ema50 is None:
            missing_indicators.append("EMA50 (requires >= 50 bars)")

        ema200 = self.engine.calculate_ema(closes, 200)
        if ema200 is None:
            missing_indicators.append("EMA200 (requires >= 200 bars)")

        ema20_series = self.engine.calculate_ema_series(closes, 20) if include_series else None
        ema50_series = self.engine.calculate_ema_series(closes, 50) if include_series else None
        ema200_series = self.engine.calculate_ema_series(closes, 200) if include_series else None

        # 2. RSI 14
        rsi14 = self.engine.calculate_rsi(closes, period=14)
        if rsi14 is None:
            missing_indicators.append("RSI14 (requires >= 15 bars)")

        # 3. MACD (12, 26, 9)
        macd = self.engine.calculate_macd(closes, fast=12, slow=26, signal=9)
        if macd is None:
            missing_indicators.append("MACD (requires >= 35 bars)")

        # 4. ATR 14
        atr14 = self.engine.calculate_atr(highs, lows, closes, period=14)
        if atr14 is None:
            missing_indicators.append("ATR14 (requires >= 15 bars)")

        # 5. Support and Resistance Levels
        support_levels, resistance_levels = self.engine.find_support_resistance(
            candles,
            current_price=current_price,
            window=4,
            max_levels=3,
        )

        # 6. Trend Detection
        trend = self.engine.detect_market_trend(
            current_price=current_price,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            rsi=rsi14,
            macd=macd,
            candles=candles,
        )

        # 7. Data Quality Assessment
        is_sufficient = n_candles >= 50
        quality_notes = (
            f"Evaluated {n_candles} bars from {history.provider}."
            if not missing_indicators
            else f"Evaluated {n_candles} bars. Skipped: {', '.join(missing_indicators)}."
        )

        data_quality = DataQualityReport(
            candle_count=n_candles,
            is_sufficient=is_sufficient,
            missing_indicators=missing_indicators,
            notes=quality_notes,
        )

        # 8. Human-Readable Indicator Summary
        summary_parts = [
            f"Market Trend: {trend.direction.value} ({trend.strength}, score: {trend.score:+0.2f}).",
            f"Price: ${current_price:,.2f}.",
        ]

        if rsi14 and rsi14.value is not None:
            summary_parts.append(f"RSI(14): {rsi14.value:.1f} ({rsi14.condition.value}).")

        if macd and macd.histogram is not None:
            summary_parts.append(f"MACD Histogram: {macd.histogram:+0.2f} ({macd.state.value}).")

        if atr14 and atr14.value is not None:
            summary_parts.append(f"ATR(14): ${atr14.value:.2f} ({atr14.volatility_pct:.2f}%).")

        if support_levels:
            summary_parts.append(f"Nearest Support: ${support_levels[0]:,.2f}.")
        if resistance_levels:
            summary_parts.append(f"Nearest Resistance: ${resistance_levels[0]:,.2f}.")

        indicator_summary = " ".join(summary_parts)

        return TechnicalAnalysisResponse(
            symbol=history.symbol,
            timeframe=timeframe,
            current_price=current_price,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            ema20_series=ema20_series,
            ema50_series=ema50_series,
            ema200_series=ema200_series,
            rsi14=rsi14,
            macd=macd,
            atr14=atr14,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            trend=trend,
            indicator_summary=indicator_summary,
            data_timestamp=latest_candle.timestamp,
            data_quality=data_quality,
        )


@lru_cache()
def get_technical_service() -> TechnicalAnalysisService:
    """Return singleton instance of TechnicalAnalysisService."""
    return TechnicalAnalysisService()
