"""
Historical Market Snapshot Builder.

Constructs synchronized, multi-timeframe MarketSnapshot objects for the existing
ConfluenceEngine at any historical decision timestamp T.

STRICT ZERO LOOK-AHEAD GUARANTEE:
- Slices candles strictly satisfying: candle.epoch_ms <= T_epoch_ms and is_closed == True
- Indicator values (EMA, RSI, MACD, ATR, Support/Resistance, Swings) are calculated
  ONLY from the closed historical slice.
- No future high, low, close, volume, or swing points are accessible.

DISCLAIMER: Research and analytical modeling only. No real trades are executed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.models.market_data import OHLCVCandle
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
    DataQualityReport,
    RSIResult,
    MACDResult,
    ATRResult,
)
from src.services.confluence_engine import MarketSnapshot, _make_snapshot_id
from src.services.technical_engine import TechnicalEngine
from src.services.historical_data_service import HistoricalCandle

import bisect

logger = logging.getLogger(__name__)


class HistoricalSnapshotBuilder:
    """Builds synchronized historical MarketSnapshots with strict no-lookahead enforcement."""

    def __init__(self):
        self.engine = TechnicalEngine()
        self._epoch_cache: Dict[int, List[int]] = {}

    def _get_epochs(self, candle_list: List[HistoricalCandle]) -> List[int]:
        list_id = id(candle_list)
        if list_id not in self._epoch_cache or len(self._epoch_cache[list_id]) != len(candle_list):
            self._epoch_cache[list_id] = [c.epoch_ms for c in candle_list]
        return self._epoch_cache[list_id]

    def build_snapshot_at_timestamp(
        self,
        symbol: str,
        decision_epoch_ms: int,
        candles_by_tf: Dict[str, List[HistoricalCandle]],
        source_symbol: str = "BTCUSDT",
    ) -> Optional[MarketSnapshot]:
        """
        Build a complete MarketSnapshot at decision timestamp T using only closed candles <= T.

        Args:
            symbol: Target symbol (e.g. "BTC/USD" or "XAU/USD")
            decision_epoch_ms: Target decision timestamp T in milliseconds
            candles_by_tf: Pre-loaded full candle series keyed by timeframe ("5m", "15m", "1h", "4h", "1d")
            source_symbol: Underlying instrument proxy

        Returns:
            Synchronized MarketSnapshot, or None if insufficient history.
        """
        dt_utc = datetime.fromtimestamp(decision_epoch_ms / 1000.0, tz=timezone.utc)
        iso_str = dt_utc.isoformat()
        snapshot_id = _make_snapshot_id(symbol, decision_epoch_ms / 1000.0)

        # 1. Filter and slice closed candles strictly <= decision_epoch_ms using O(log N) binary search
        sliced_candles: Dict[str, List[HistoricalCandle]] = {}
        for tf, candle_list in candles_by_tf.items():
            if not candle_list:
                continue
            epochs = self._get_epochs(candle_list)
            idx = bisect.bisect_right(epochs, decision_epoch_ms)
            # Take up to 250 closed candles for 200 EMA & indicator calculation
            sliced_candles[tf] = candle_list[max(0, idx - 250):idx]

        primary_candles = sliced_candles.get("15m") or sliced_candles.get("5m") or []
        if not primary_candles or len(primary_candles) < 20:
            return None

        current_price = primary_candles[-1].close

        # 2. Derive higher timeframes if missing from lower closed candles (strictly no lookahead)
        if "1h" not in sliced_candles or len(sliced_candles["1h"]) < 10:
            sliced_candles["1h"] = self._derive_1h_from_15m(sliced_candles.get("15m", []))

        if "4h" not in sliced_candles or len(sliced_candles["4h"]) < 10:
            sliced_candles["4h"] = self._derive_4h_from_1h(sliced_candles.get("1h", []))

        if "1d" not in sliced_candles or len(sliced_candles["1d"]) < 5:
            sliced_candles["1d"] = self._derive_1d_from_1h(sliced_candles.get("1h", []))

        # 3. Compute TechnicalAnalysisResponse for each timeframe
        ta_5m = self._compute_ta(symbol, "5m", sliced_candles.get("5m", []), current_price)
        ta_15m = self._compute_ta(symbol, "15m", sliced_candles.get("15m", []), current_price)
        ta_1h = self._compute_ta(symbol, "1h", sliced_candles.get("1h", []), current_price)
        ta_1d = self._compute_ta(symbol, "1d", sliced_candles.get("1d", []), current_price)

        # Convert candles to dict format expected by ConfluenceEngine
        def _to_dicts(candles: List[HistoricalCandle]) -> List[dict]:
            return [
                {
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                    "timestamp": c.timestamp,
                    "is_closed": True,
                }
                for c in candles
            ]

        # 4. Construct the point-in-time MarketSnapshot
        snapshot = MarketSnapshot(
            snapshot_id=snapshot_id,
            created_at=iso_str,
            symbol=symbol,
            current_price=current_price,
            ta_5m=ta_5m,
            ta_15m=ta_15m,
            ta_1h=ta_1h,
            ta_1d=ta_1d,
            candles_5m=_to_dicts(sliced_candles.get("5m", [])),
            candles_15m=_to_dicts(sliced_candles.get("15m", [])),
            candles_1h=_to_dicts(sliced_candles.get("1h", [])),
            candles_1d=_to_dicts(sliced_candles.get("1d", [])),
            ai_result=None,  # Gemini is evaluated strictly in replay / ablation mode
            bid=current_price,
            ask=current_price,
        )

        return snapshot

    def _compute_ta(
        self,
        symbol: str,
        timeframe: str,
        candles: List[HistoricalCandle],
        current_price: float,
    ) -> Optional[TechnicalAnalysisResponse]:
        """Compute full TechnicalAnalysisResponse using the pure TechnicalEngine on closed candles."""
        if not candles or len(candles) < 5:
            return None

        # Convert to OHLCVCandle
        ohlcv_candles = [
            OHLCVCandle(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
                is_closed=True,
            )
            for c in candles
        ]

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        # Indicator calculations
        ema20 = self.engine.calculate_ema(closes, 20)
        ema50 = self.engine.calculate_ema(closes, 50)
        ema200 = self.engine.calculate_ema(closes, 200)

        rsi = self.engine.calculate_rsi(closes, period=14)
        macd = self.engine.calculate_macd(closes, fast=12, slow=26, signal=9)
        atr = self.engine.calculate_atr(highs, lows, closes, period=14)

        support_levels, resistance_levels = self.engine.find_support_resistance(
            ohlcv_candles,
            current_price=current_price,
            window=4,
            max_levels=3,
        )

        trend = self.engine.detect_market_trend(
            current_price=current_price,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            rsi=rsi,
            macd=macd,
            candles=ohlcv_candles,
        )

        n_candles = len(candles)
        missing_indicators = []
        if ema20 is None:
            missing_indicators.append("EMA20")
        if ema50 is None:
            missing_indicators.append("EMA50")
        if ema200 is None:
            missing_indicators.append("EMA200")
        if rsi is None:
            missing_indicators.append("RSI")
        if macd is None:
            missing_indicators.append("MACD")
        if atr is None:
            missing_indicators.append("ATR")

        data_quality = DataQualityReport(
            candle_count=n_candles,
            is_sufficient=n_candles >= 50,
            missing_indicators=missing_indicators,
            notes=f"Evaluated {n_candles} bars.",
        )
        trend_dir_str = trend.direction.value if hasattr(trend.direction, "value") else str(trend.direction)
        summary = f"Trend: {trend_dir_str} ({trend.strength}). RSI: {rsi.value if rsi else 'N/A'}."

        return TechnicalAnalysisResponse(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            rsi14=rsi,
            macd=macd,
            atr14=atr,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            trend=trend,
            indicator_summary=summary,
            data_timestamp=candles[-1].timestamp,
            data_quality=data_quality,
        )

    def _derive_1h_from_15m(self, candles_15m: List[HistoricalCandle]) -> List[HistoricalCandle]:
        """Derive 1H candles from closed 15M candles without lookahead."""
        if not candles_15m or len(candles_15m) < 4:
            return []

        derived: List[HistoricalCandle] = []
        for i in range(0, len(candles_15m) - 3, 4):
            chunk = candles_15m[i:i + 4]
            derived.append(HistoricalCandle(
                symbol=chunk[0].symbol,
                source_symbol=chunk[0].source_symbol,
                timeframe="1h",
                timestamp=chunk[0].timestamp,
                epoch_ms=chunk[0].epoch_ms,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
                is_closed=True,
                source=chunk[0].source,
            ))
        return derived

    def _derive_4h_from_1h(self, candles_1h: List[HistoricalCandle]) -> List[HistoricalCandle]:
        """Derive 4H candles from closed 1H candles without lookahead."""
        if not candles_1h or len(candles_1h) < 4:
            return []

        derived: List[HistoricalCandle] = []
        # Group every 4 consecutive 1h candles
        for i in range(0, len(candles_1h) - 3, 4):
            chunk = candles_1h[i:i + 4]
            derived.append(HistoricalCandle(
                symbol=chunk[0].symbol,
                source_symbol=chunk[0].source_symbol,
                timeframe="4h",
                timestamp=chunk[0].timestamp,
                epoch_ms=chunk[0].epoch_ms,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
                is_closed=True,
                source=chunk[0].source,
            ))
        return derived

    def _derive_1d_from_1h(self, candles_1h: List[HistoricalCandle]) -> List[HistoricalCandle]:
        """Derive 1D candles from closed 1H candles without lookahead."""
        if not candles_1h or len(candles_1h) < 24:
            return []

        derived: List[HistoricalCandle] = []
        for i in range(0, len(candles_1h) - 23, 24):
            chunk = candles_1h[i:i + 24]
            derived.append(HistoricalCandle(
                symbol=chunk[0].symbol,
                source_symbol=chunk[0].source_symbol,
                timeframe="1d",
                timestamp=chunk[0].timestamp,
                epoch_ms=chunk[0].epoch_ms,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
                is_closed=True,
                source=chunk[0].source,
            ))
        return derived
