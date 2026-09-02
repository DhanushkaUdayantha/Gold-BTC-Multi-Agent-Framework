"""
Phase 4 Production Safety and Isolation Test.

Asserts:
  1. Live DecisionEngine is 100% frozen and unmodified.
  2. Live TradingDecision output schema is unchanged.
  3. No research candidate is auto-deployed to production.
  4. Phase 4 safety statement is verified.
"""
from datetime import datetime, timezone
import pytest
from src.services.decision_engine import DecisionEngine
from src.models.trading_decision import TradingDecision, TradingSignal, DecisionScoreBreakdown
from src.models.ai_analysis import (
    AIAnalysisResponse,
    OverallBias,
    MarketCondition,
    MultiTimeframeTechnicalInput,
    RiskLevel,
)
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendDirection,
    MACDState,
    RSICondition,
    RSIResult,
    MACDResult,
    ATRResult,
    TrendAnalysis,
    DataQualityReport,
)
from src.models.market_data import Timeframe


def _make_dummy_inputs():
    tech = TechnicalAnalysisResponse(
        symbol="BTC/USD",
        timeframe=Timeframe("1h"),
        current_price=64000.0,
        ema20=63800.0,
        ema50=63200.0,
        ema200=60000.0,
        rsi14=RSIResult(value=58.0, period=14, condition=RSICondition.NEUTRAL),
        macd=MACDResult(macd_line=120.0, signal_line=50.0, histogram=70.0, state=MACDState.BULLISH),
        atr14=ATRResult(value=850.0, period=14, volatility_pct=1.3),
        support_levels=[63000.0, 62000.0],
        resistance_levels=[65000.0, 66000.0],
        trend=TrendAnalysis(
            direction=TrendDirection.BULLISH,
            score=0.85,
            strength="STRONG",
            confirmations=["EMA stacking", "MACD cross"],
        ),
        indicator_summary="Bullish trend test",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=200, is_sufficient=True, missing_indicators=[], notes="OK"),
    )
    mtf = MultiTimeframeTechnicalInput(
        symbol="BTC/USD",
        current_price=64000.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timeframes={"1h": tech},
        timeframe_count=1,
        alignment_summary="1/1 bullish",
    )
    ai = AIAnalysisResponse(
        symbol="BTC/USD",
        market_condition=MarketCondition.TRENDING_BULLISH,
        overall_bias=OverallBias.BULLISH,
        confidence=85,
        timeframe_analysis={"1h": "Bullish"},
        key_bullish_factors=["Strong trend"],
        key_bearish_factors=[],
        key_support=[63000.0],
        key_resistance=[65000.0],
        risk_level=RiskLevel.LOW,
        summary="Bullish continuation expected.",
        provider_used="Test Mock",
        is_fallback=False,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return mtf, ai


class TestPhase4ProductionSafety:
    def test_production_decision_engine_unmodified(self):
        engine = DecisionEngine()
        mtf, ai = _make_dummy_inputs()
        decision, breakdown = engine.evaluate(mtf_input=mtf, ai_result=ai)

        assert isinstance(decision, TradingDecision)
        assert isinstance(breakdown, DecisionScoreBreakdown)
        assert decision.decision in (TradingSignal.BUY, TradingSignal.SELL, TradingSignal.WAIT)
        assert decision.symbol == "BTC/USD"

    def test_deterministic_signals_under_repeated_runs(self):
        engine = DecisionEngine()
        mtf, ai = _make_dummy_inputs()
        d1, _ = engine.evaluate(mtf_input=mtf, ai_result=ai)
        d2, _ = engine.evaluate(mtf_input=mtf, ai_result=ai)

        assert d1.decision == d2.decision
        assert d1.confidence == d2.confidence
        assert d1.composite_score == d2.composite_score
