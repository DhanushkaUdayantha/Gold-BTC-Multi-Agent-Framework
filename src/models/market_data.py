"""Data models for Gold market data."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Timeframe(str, Enum):
    """Supported candle intervals."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class PriceQuote(BaseModel):
    """Real-time Gold price quote."""
    symbol: str = Field(description="Trading symbol, e.g. XAU-USD-SPOT")
    price: float = Field(description="Current mid/spot price in USD per unit")
    bid: Optional[float] = Field(default=None, description="Bid price")
    ask: Optional[float] = Field(default=None, description="Ask price")
    spread: Optional[float] = Field(default=None, description="Ask - Bid spread")
    change_24h: Optional[float] = Field(default=None, description="24-hour price change in USD")
    change_24h_pct: Optional[float] = Field(default=None, description="24-hour price change percentage")
    prev_close_24h: Optional[float] = Field(default=None, description="Previous 24-hour close price")
    currency: str = Field(default="USD", description="Quote currency")
    unit: str = Field(default="troy_ounce", description="Unit of measurement")
    timestamp: str = Field(description="ISO 8601 timestamp of the quote")
    provider: str = Field(description="Data provider source name")
    is_stale: bool = Field(default=False, description="Whether the quote is marked stale")


class OHLCVCandle(BaseModel):
    """Single OHLCV candlestick bar."""
    timestamp: str = Field(description="ISO 8601 timestamp or bar start time")
    open: float = Field(description="Open price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Close price")
    volume: Optional[float] = Field(default=None, description="Trade volume if available")
    is_closed: bool = Field(default=True, description="Whether the candle period is closed")


class CandleHistory(BaseModel):
    """Historical collection of OHLCV candles."""
    symbol: str = Field(description="Trading symbol")
    timeframe: Timeframe = Field(description="Candlestick interval")
    count: int = Field(description="Number of candles returned")
    candles: List[OHLCVCandle] = Field(default_factory=list, description="List of OHLCV bars")
    provider: str = Field(description="Data provider source name")
    fetched_at: str = Field(description="Timestamp when data was retrieved")


class MarketStatus(BaseModel):
    """Health and status of market data feeds."""
    status: str = Field(description="Overall status: healthy, degraded, or offline")
    primary_provider: str = Field(description="Active primary provider")
    goldprice_dev_reachable: bool = Field(description="Whether GoldPrice.dev is reachable")
    intraday_supported: bool = Field(description="Whether intraday candles (1m, 5m, 15m, 1h) are available")
    message: str = Field(description="Status description or warning notes")
    timestamp: str = Field(description="Status check timestamp")
