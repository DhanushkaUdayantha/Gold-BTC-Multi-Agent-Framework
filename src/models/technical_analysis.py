"""Data models for Technical Analysis calculations and indicators."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from src.models.market_data import Timeframe


class TrendDirection(str, Enum):
    """Market trend classification."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class RSICondition(str, Enum):
    """RSI threshold state."""
    OVERBOUGHT = "OVERBOUGHT"
    OVERSOLD = "OVERSOLD"
    NEUTRAL = "NEUTRAL"


class MACDState(str, Enum):
    """MACD signal crossover state."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RSIResult(BaseModel):
    """RSI calculation output."""
    value: Optional[float] = Field(default=None, description="Current RSI value (0-100)")
    period: int = Field(default=14, description="RSI calculation period")
    condition: RSICondition = Field(default=RSICondition.NEUTRAL, description="Market condition based on RSI")


class MACDResult(BaseModel):
    """MACD calculation output."""
    macd_line: Optional[float] = Field(default=None, description="MACD fast-slow difference line")
    signal_line: Optional[float] = Field(default=None, description="MACD signal line (9 EMA of MACD line)")
    histogram: Optional[float] = Field(default=None, description="Histogram (MACD line - Signal line)")
    state: MACDState = Field(default=MACDState.NEUTRAL, description="Bullish or Bearish MACD momentum state")


class ATRResult(BaseModel):
    """Average True Range calculation output."""
    value: Optional[float] = Field(default=None, description="ATR volatility measurement in USD")
    period: int = Field(default=14, description="ATR period")
    volatility_pct: Optional[float] = Field(default=None, description="ATR as percentage of current price")


class EMASet(BaseModel):
    """Exponential Moving Averages set."""
    ema20: Optional[float] = Field(default=None, description="20-period Exponential Moving Average")
    ema50: Optional[float] = Field(default=None, description="50-period Exponential Moving Average")
    ema200: Optional[float] = Field(default=None, description="200-period Exponential Moving Average")
    alignment: str = Field(default="MIXED", description="Description of EMA stacking alignment")


class TrendAnalysis(BaseModel):
    """Multi-confirmation market trend classification."""
    direction: TrendDirection = Field(description="Trend direction: BULLISH, BEARISH, or SIDEWAYS")
    score: float = Field(description="Composite trend score between -1.0 (very bearish) and +1.0 (very bullish)")
    strength: str = Field(description="Trend strength: STRONG, MODERATE, or WEAK")
    confirmations: List[str] = Field(default_factory=list, description="List of technical confirmations used")


class DataQualityReport(BaseModel):
    """Data quality and history depth metrics."""
    candle_count: int = Field(description="Number of candles evaluated")
    is_sufficient: bool = Field(description="Whether candle depth meets standard indicator requirements")
    missing_indicators: List[str] = Field(default_factory=list, description="Indicators skipped due to insufficient data")
    notes: str = Field(description="Explanatory notes regarding data completeness")


class TechnicalAnalysisResponse(BaseModel):
    """Standardized technical analysis output payload."""
    symbol: str = Field(description="Trading symbol (e.g. XAU-USD-SPOT)")
    timeframe: Timeframe = Field(description="Timeframe analyzed")
    current_price: float = Field(description="Latest spot or close price")
    ema20: Optional[float] = Field(default=None, description="EMA 20 value")
    ema50: Optional[float] = Field(default=None, description="EMA 50 value")
    ema200: Optional[float] = Field(default=None, description="EMA 200 value (null if <200 bars)")
    ema20_series: Optional[List[Optional[float]]] = Field(
        default=None,
        description="Optional full EMA20 series aligned to analyzed candles (chart overlay)",
    )
    ema50_series: Optional[List[Optional[float]]] = Field(
        default=None,
        description="Optional full EMA50 series aligned to analyzed candles (chart overlay)",
    )
    ema200_series: Optional[List[Optional[float]]] = Field(
        default=None,
        description="Optional full EMA200 series aligned to analyzed candles (chart overlay)",
    )
    rsi14: Optional[RSIResult] = Field(default=None, description="RSI 14 result")
    macd: Optional[MACDResult] = Field(default=None, description="MACD (12, 26, 9) result")
    atr14: Optional[ATRResult] = Field(default=None, description="ATR 14 volatility result")
    support_levels: List[float] = Field(default_factory=list, description="Key support price levels")
    resistance_levels: List[float] = Field(default_factory=list, description="Key resistance price levels")
    trend: TrendAnalysis = Field(description="Comprehensive trend analysis")
    indicator_summary: str = Field(description="Concise human-readable technical summary")
    data_timestamp: str = Field(description="Timestamp of the latest candle analyzed")
    data_quality: DataQualityReport = Field(description="Quality assessment of historical data feed")
