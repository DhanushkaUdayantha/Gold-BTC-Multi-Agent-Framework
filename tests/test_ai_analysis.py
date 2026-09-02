"""Unit tests for AI Market Analysis Engine (mocked tests, no live AI calls)."""
import json
import pytest
from unittest.mock import MagicMock, patch
import requests

from src.models.market_data import Timeframe
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
    DataQualityReport,
    RSIResult,
    RSICondition,
    MACDResult,
    MACDState,
    ATRResult,
)
from src.models.ai_analysis import (
    MultiTimeframeTechnicalInput,
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    RiskLevel,
)
from src.services.ai.ai_aggregator import AIAggregator
from src.services.ai.fallback_provider import FallbackAIProvider
from src.services.ai.gemini_provider import GeminiAIProvider, GeminiAIError
from src.services.ai.openai_provider import OpenAIAIProvider, OpenAIAIError
from src.services.ai_service import AIMarketAnalysisService
from config.settings import Settings


def make_dummy_technical_response(
    timeframe: Timeframe,
    trend_dir: TrendDirection = TrendDirection.BULLISH,
    price: float = 2050.0,
    rsi_val: float = 55.0,
) -> TechnicalAnalysisResponse:
    """Helper to generate mock technical responses."""
    return TechnicalAnalysisResponse(
        symbol="XAU-USD-SPOT",
        timeframe=timeframe,
        current_price=price,
        ema20=price - 5.0,
        ema50=price - 15.0,
        ema200=price - 30.0,
        rsi14=RSIResult(value=rsi_val, period=14, condition=RSICondition.NEUTRAL),
        macd=MACDResult(macd_line=2.5, signal_line=1.2, histogram=1.3, state=MACDState.BULLISH),
        atr14=ATRResult(value=10.0, period=14, volatility_pct=0.5),
        support_levels=[price - 10.0, price - 20.0],
        resistance_levels=[price + 10.0, price + 20.0],
        trend=TrendAnalysis(
            direction=trend_dir,
            score=0.75 if trend_dir == TrendDirection.BULLISH else (-0.75 if trend_dir == TrendDirection.BEARISH else 0.0),
            strength="STRONG",
            confirmations=["Mock confirmation"],
        ),
        indicator_summary=f"Mock summary for {timeframe.value}",
        data_timestamp="2026-08-28T12:00:00Z",
        data_quality=DataQualityReport(
            candle_count=200,
            is_sufficient=True,
            missing_indicators=[],
            notes="Mock data quality",
        ),
    )


def make_multi_timeframe_input(conflict: bool = False) -> MultiTimeframeTechnicalInput:
    """Create a mock MultiTimeframeTechnicalInput dataset."""
    tf_data = {
        "5m": make_dummy_technical_response(Timeframe.M5, TrendDirection.BEARISH if conflict else TrendDirection.BULLISH),
        "15m": make_dummy_technical_response(Timeframe.M15, TrendDirection.BEARISH if conflict else TrendDirection.BULLISH),
        "1h": make_dummy_technical_response(Timeframe.H1, TrendDirection.BULLISH),
        "1d": make_dummy_technical_response(Timeframe.D1, TrendDirection.BULLISH),
    }
    return MultiTimeframeTechnicalInput(
        symbol="XAU/USD",
        current_price=2050.0,
        timestamp="2026-08-28T12:00:00Z",
        timeframes=tf_data,
        timeframe_count=4,
        alignment_summary="Conflicting timeframes" if conflict else "Full Bullish Alignment",
    )


def test_multi_timeframe_data_collection():
    """Verify AIAggregator aggregates all 4 required timeframes."""
    mock_tech_service = MagicMock()
    mock_tech_service.analyze.side_effect = lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)

    aggregator = AIAggregator(technical_service=mock_tech_service)
    result = aggregator.collect_multi_timeframe_data(symbol="XAU-USD-SPOT")

    assert result.timeframe_count == 4
    assert "5m" in result.timeframes
    assert "15m" in result.timeframes
    assert "1h" in result.timeframes
    assert "1d" in result.timeframes
    assert "Full Bullish Alignment" in result.alignment_summary


def test_ai_prompt_builder():
    """Verify system and user prompt generation contains valid JSON and strict instructions."""
    input_data = make_multi_timeframe_input()
    system_prompt = AIAggregator.build_system_prompt()
    user_prompt = AIAggregator.build_user_prompt(input_data)

    assert "NO TRADE EXECUTION" in system_prompt
    assert "ZERO FABRICATION" in system_prompt
    assert "XAU/USD" in user_prompt
    assert "timeframe_profiles" in user_prompt


def test_conflicting_timeframe_signals():
    """Verify fallback engine correctly lowers confidence and identifies conflict when timeframes disagree."""
    conflict_input = make_multi_timeframe_input(conflict=True)
    fallback = FallbackAIProvider()
    response = fallback.generate_analysis(conflict_input)

    assert response.confidence <= 65
    assert response.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    assert any("conflicting" in f.lower() or "pullback" in f.lower() for f in response.key_bearish_factors)


def test_ai_response_schema_validation():
    """Verify valid schema instantiation and enum compliance."""
    response = AIAnalysisResponse(
        symbol="XAU/USD",
        analysis_timestamp="2026-08-28T12:00:00Z",
        market_condition=MarketCondition.TRENDING_BULLISH,
        overall_bias=OverallBias.BULLISH,
        confidence=80,
        timeframe_analysis={"5m": "Up", "15m": "Up", "1h": "Up", "1d": "Up"},
        key_bullish_factors=["Strong EMA", "MACD positive"],
        key_bearish_factors=["None"],
        key_support=[2040.0, 2030.0],
        key_resistance=[2060.0, 2070.0],
        risk_level=RiskLevel.LOW,
        summary="Market is bullish.",
        provider_used="MockProvider",
        is_fallback=False,
    )
    assert response.confidence == 80
    assert response.market_condition == MarketCondition.TRENDING_BULLISH
    assert response.overall_bias == OverallBias.BULLISH


def test_gemini_provider_mocked_success():
    """Verify GeminiAIProvider correctly parses valid structured model responses."""
    mock_payload = {
        "symbol": "XAU/USD",
        "analysis_timestamp": "2026-08-28T12:00:00Z",
        "market_condition": "TRENDING_BULLISH",
        "overall_bias": "BULLISH",
        "confidence": 85,
        "timeframe_analysis": {
            "5m": "5m is moving upward above 20 EMA.",
            "15m": "15m has positive MACD momentum.",
            "1h": "1h is above 50 EMA.",
            "1d": "1d macro trend is strongly bullish."
        },
        "key_bullish_factors": ["MACD bullish crossover", "Price > EMA20 > EMA50"],
        "key_bearish_factors": ["Resistance at 2070"],
        "key_support": [2040.0, 2030.0],
        "key_resistance": [2070.0, 2085.0],
        "risk_level": "LOW",
        "summary": "Gold exhibits robust multi-timeframe bullish momentum."
    }

    mock_gemini_response = MagicMock()
    mock_gemini_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(mock_payload)}]
                }
            }
        ]
    }
    mock_gemini_response.raise_for_status.return_value = None

    provider = GeminiAIProvider(api_key="mock-key", model_name="gemini-2.5-flash")
    with patch("requests.post", return_value=mock_gemini_response):
        input_data = make_multi_timeframe_input()
        result = provider.generate_analysis(input_data)

        assert result.symbol == "XAU/USD"
        assert result.market_condition == MarketCondition.TRENDING_BULLISH
        assert result.confidence == 85
        assert len(result.key_support) == 2


def test_gemini_provider_invalid_json():
    """Verify GeminiAIProvider raises GeminiAIError when candidate text is corrupt/invalid."""
    mock_gemini_response = MagicMock()
    mock_gemini_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "THIS IS NOT JSON"}]}}]
    }
    mock_gemini_response.raise_for_status.return_value = None

    provider = GeminiAIProvider(api_key="mock-key")
    with patch("requests.post", return_value=mock_gemini_response):
        with pytest.raises(GeminiAIError, match="Invalid structured JSON"):
            provider.generate_analysis(make_multi_timeframe_input())


def test_ai_provider_timeout_handling():
    """Verify service handles provider timeout and automatically falls back without crashing."""
    settings = Settings(AI_PROVIDER="gemini", GEMINI_API_KEY="test-key")
    service = AIMarketAnalysisService(settings=settings)

    mock_tech_service = MagicMock()
    mock_tech_service.analyze.side_effect = lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
    service.aggregator.technical_service = mock_tech_service

    with patch.object(service.request_manager, "is_request_allowed", return_value=(True, "allowed")), \
         patch("requests.post", side_effect=requests.exceptions.Timeout("API Timeout")):
        res = service.analyze_market(symbol="XAU-USD-SPOT", force_refresh=True)
        assert res is not None
        assert res.is_fallback is True
        assert "built-in fallback engine" in (res.config_warning or "")


def test_ai_service_no_key_warning():
    """Verify service provides clear configuration notice when no API key is set."""
    settings = Settings(AI_PROVIDER="auto", GEMINI_API_KEY="", OPENAI_API_KEY="")
    service = AIMarketAnalysisService(settings=settings)

    mock_tech_service = MagicMock()
    mock_tech_service.analyze.side_effect = lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
    service.aggregator.technical_service = mock_tech_service

    res = service.analyze_market(symbol="XAU-USD-SPOT")
    assert res.is_fallback is True
    assert "AI API Key not configured" in (res.config_warning or "")
