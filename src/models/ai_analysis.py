"""Data models for AI Market Analysis."""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from src.models.technical_analysis import TechnicalAnalysisResponse


class MarketCondition(str, Enum):
    """Overall market structural condition."""
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    RANGE = "RANGE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNCLEAR = "UNCLEAR"


class OverallBias(str, Enum):
    """Consolidated market directional bias."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskLevel(str, Enum):
    """Estimated market environmental risk."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MultiTimeframeTechnicalInput(BaseModel):
    """Raw structured multi-timeframe technical input data compiled for AI consumption."""
    symbol: str = Field(default="XAU/USD")
    current_price: float
    timestamp: str
    timeframes: Dict[str, TechnicalAnalysisResponse] = Field(
        description="Technical analysis profiles keyed by interval: '5m', '15m', '1h', '1d'"
    )
    timeframe_count: int
    alignment_summary: str = Field(description="Summary of trend agreement across timeframes")
    historical_evidence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Factual empirical backtest evidence for LLM prompt context"
    )


class AIAnalysisResponse(BaseModel):
    """Standardized AI multi-timeframe market analysis output."""
    symbol: str = Field(default="XAU/USD", description="Market symbol analyzed")
    analysis_timestamp: str = Field(description="ISO timestamp when analysis was conducted")
    market_condition: MarketCondition = Field(description="Market structure classification")
    overall_bias: OverallBias = Field(description="Consolidated directional bias: BULLISH, BEARISH, or NEUTRAL")
    confidence: int = Field(ge=0, le=100, description="Confidence score from 0 to 100")
    timeframe_analysis: Dict[str, str] = Field(
        description="Concise analytical reasoning breakdown for each timeframe ('5m', '15m', '1h', '1d')"
    )
    key_bullish_factors: List[str] = Field(default_factory=list, description="Primary bullish drivers and technical supports")
    key_bearish_factors: List[str] = Field(default_factory=list, description="Primary bearish drivers and technical resistances")
    key_support: List[float] = Field(default_factory=list, description="Aggregated key support price levels")
    key_resistance: List[float] = Field(default_factory=list, description="Aggregated key resistance price levels")
    risk_level: RiskLevel = Field(description="Environmental risk rating (LOW, MEDIUM, HIGH)")
    summary: str = Field(description="Comprehensive executive market assessment summary")
    provider_used: str = Field(default="fallback", description="Name of the AI provider/model that produced this analysis")
    is_fallback: bool = Field(default=False, description="Whether this analysis was produced by the fallback rule engine")
    config_warning: Optional[str] = Field(default=None, description="Configuration warning or guidance if API key is omitted")
    generation_duration_ms: Optional[int] = Field(default=None, description="Time taken to generate the analysis in milliseconds")

