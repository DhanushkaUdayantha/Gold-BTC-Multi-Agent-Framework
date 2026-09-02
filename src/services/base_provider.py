"""Base abstract class for market data providers."""
from abc import ABC, abstractmethod
from typing import Optional
from src.models.market_data import PriceQuote, CandleHistory, Timeframe


class BaseMarketDataProvider(ABC):
    """Abstract interface for all Gold market data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider display name."""
        pass

    @abstractmethod
    def get_live_price(self, symbol: str = "XAU-USD-SPOT") -> PriceQuote:
        """Fetch current live price quote.

        Args:
            symbol: Trading symbol identifier (default: XAU-USD-SPOT)

        Returns:
            PriceQuote containing live bid, ask, spot price and metadata.
        """
        pass

    @abstractmethod
    def get_candles(
        self,
        symbol: str = "XAU-USD-SPOT",
        timeframe: Timeframe = Timeframe.M15,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> CandleHistory:
        """Fetch historical OHLCV candlestick bars.

        Args:
            symbol: Trading symbol identifier
            timeframe: Timeframe interval (1m, 5m, 15m, 1h, 1d)
            limit: Maximum number of candles to return
            start_date: Optional start date string (YYYY-MM-DD)
            end_date: Optional end date string (YYYY-MM-DD)

        Returns:
            CandleHistory containing list of OHLCVCandle bars.
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if provider API is currently reachable."""
        pass
