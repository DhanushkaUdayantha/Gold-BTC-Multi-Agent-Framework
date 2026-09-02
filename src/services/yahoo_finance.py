"""Yahoo Finance Market Data Provider (Gold Spot & Futures).

Provides intraday (1m, 5m, 15m, 1h) and daily (1d) OHLCV candles without requiring paid API keys.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import requests

from src.models.market_data import PriceQuote, OHLCVCandle, CandleHistory, Timeframe
from src.services.base_provider import BaseMarketDataProvider

logger = logging.getLogger(__name__)


class YahooFinanceError(Exception):
    """Base exception for Yahoo Finance provider errors."""
    pass


class YahooFinanceProvider(BaseMarketDataProvider):
    """Provider querying Yahoo Finance chart endpoints for Gold (GC=F / XAUUSD=X)."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"

    def _resolve_symbol(self, symbol: str) -> str:
        """Map standard symbol identifiers to Yahoo Finance tickers."""
        clean = symbol.upper().replace("-", "").replace("/", "")
        if "BTC" in clean or "BITCOIN" in clean:
            return "BTC-USD"
        if "XAU" in clean or "GOLD" in clean:
            # GC=F (COMEX Gold Futures) has the deepest intraday liquidity and OHLC volume
            return "GC=F"
        return symbol

    def _get_range_for_timeframe(self, timeframe: Timeframe, limit: int) -> str:
        """Calculate appropriate data range parameter for Yahoo Finance."""
        if timeframe == Timeframe.M1:
            return "1d" if limit <= 100 else "5d"
        elif timeframe in (Timeframe.M5, Timeframe.M15):
            return "5d" if limit <= 100 else "1mo"
        elif timeframe == Timeframe.H1:
            return "1mo" if limit <= 100 else "3mo"
        else:  # Timeframe.D1
            return "3mo" if limit <= 60 else "1y"

    def get_live_price(self, symbol: str = "XAU-USD-SPOT") -> PriceQuote:
        """Fetch real-time Gold / BTC quote from Yahoo Finance."""
        ticker = self._resolve_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"interval": "1m", "range": "1d"}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            results = data.get("chart", {}).get("result", [])
            if not results:
                raise YahooFinanceError(f"No chart data returned for {ticker}")

            meta = results[0].get("meta", {})
            regular_price = float(meta.get("regularMarketPrice", 0.0))
            previous_close = float(meta.get("previousClose", regular_price))

            # Calculate 24h change & percent
            chg_24h = round(regular_price - previous_close, 2) if previous_close else None
            chg_24h_pct = round((chg_24h / previous_close) * 100, 2) if (chg_24h is not None and previous_close and previous_close != 0) else None

            # Yahoo doesn't always provide bid/ask for futures; approximate spread if missing
            bid = float(meta.get("bid", regular_price)) if meta.get("bid") else None
            ask = float(meta.get("ask", regular_price)) if meta.get("ask") else None
            spread = round(ask - bid, 4) if (ask is not None and bid is not None) else None

            # Record the actual real-time retrieval timestamp
            ts = datetime.now(timezone.utc).isoformat()
            is_btc = "BTC" in symbol.upper()

            return PriceQuote(
                symbol=symbol,
                price=regular_price,
                bid=bid,
                ask=ask,
                spread=spread,
                change_24h=chg_24h,
                change_24h_pct=chg_24h_pct,
                prev_close_24h=round(previous_close, 2) if previous_close else None,
                currency=meta.get("currency", "USD"),
                unit="coin" if is_btc else "troy_ounce",
                timestamp=ts,
                provider=self.provider_name,
                is_stale=False,
            )

        except requests.exceptions.RequestException as exc:
            logger.error(f"Yahoo Finance price request error: {exc}")
            raise YahooFinanceError(f"Failed to fetch price from Yahoo Finance: {exc}") from exc

    def get_candles(
        self,
        symbol: str = "XAU-USD-SPOT",
        timeframe: Timeframe = Timeframe.M15,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> CandleHistory:
        """Fetch intraday or daily historical OHLCV candle bars."""
        ticker = self._resolve_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

        # Yahoo interval parameter formatting (1m, 5m, 15m, 1h, 1d)
        interval_str = "60m" if timeframe == Timeframe.H1 else timeframe.value
        range_str = self._get_range_for_timeframe(timeframe, limit)

        params = {
            "interval": interval_str,
            "range": range_str,
            "includePrePost": "false",
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            results = data.get("chart", {}).get("result", [])
            if not results:
                raise YahooFinanceError(f"No candlestick data returned for {ticker}")

            result = results[0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]

            opens = indicators.get("open", [])
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            closes = indicators.get("close", [])
            volumes = indicators.get("volume", [])

            candles: List[OHLCVCandle] = []

            for i, ts in enumerate(timestamps):
                # Filter out null / incomplete bars
                o = opens[i] if i < len(opens) else None
                h = highs[i] if i < len(highs) else None
                l = lows[i] if i < len(lows) else None
                c = closes[i] if i < len(closes) else None
                v = volumes[i] if i < len(volumes) else None

                if None in (o, h, l, c):
                    continue

                iso_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                candles.append(
                    OHLCVCandle(
                        timestamp=iso_time,
                        open=round(float(o), 3),
                        high=round(float(h), 3),
                        low=round(float(l), 3),
                        close=round(float(c), 3),
                        volume=float(v) if v is not None else None,
                        is_closed=True,
                    )
                )

            # Limit to requested number of most recent candles
            if limit and len(candles) > limit:
                candles = candles[-limit:]

            return CandleHistory(
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles),
                candles=candles,
                provider=self.provider_name,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )

        except requests.exceptions.RequestException as exc:
            logger.error(f"Yahoo Finance candle request error: {exc}")
            raise YahooFinanceError(f"Failed to fetch candles from Yahoo Finance: {exc}") from exc

    def is_healthy(self) -> bool:
        """Verify API connectivity."""
        # Cache health status for 60 seconds to prevent polling overhead
        now = time.time()
        if hasattr(self, "_last_health_check_time") and now - self._last_health_check_time < 60.0:
            return self._last_health_status
        try:
            quote = self.get_live_price("XAU-USD-SPOT")
            self._last_health_status = quote.price > 0
        except Exception:
            self._last_health_status = False
        self._last_health_check_time = now
        return self._last_health_status
