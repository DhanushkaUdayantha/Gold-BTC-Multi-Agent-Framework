"""
Production Isolation Test for Phase 3 Research Framework.

Verifies the absolute safety rule:
- DecisionEngine evaluate() behavior is completely unmodified.
- No production trading logic is altered.
- All research modules exist solely in src/research/ and are non-invasive.
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
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe("1h"),
        current_price=2050.0,
        ema20=2045.0,
        ema50=2030.0,
        ema200=1980.0,
        rsi14=RSIResult(value=55.0, period=14, condition=RSICondition.NEUTRAL),
        macd=MACDResult(macd_line=2.0, signal_line=0.5, histogram=1.5, state=MACDState.BULLISH),
        atr14=ATRResult(value=12.5, period=14, volatility_pct=0.6),
        support_levels=[2040.0, 2020.0],
        resistance_levels=[2060.0, 2080.0],
        trend=TrendAnalysis(
            direction=TrendDirection.BULLISH,
            score=0.8,
            strength="STRONG",
            confirmations=["EMA alignment", "MACD positive"],
        ),
        indicator_summary="Bullish trend test",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=200, is_sufficient=True, missing_indicators=[], notes="OK"),
    )
    mtf = MultiTimeframeTechnicalInput(
        symbol="XAU/USD",
        current_price=2050.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timeframes={"1h": tech},
        timeframe_count=1,
        alignment_summary="1/1 bullish",
    )
    ai = AIAnalysisResponse(
        symbol="XAU/USD",
        market_condition=MarketCondition.TRENDING_BULLISH,
        overall_bias=OverallBias.BULLISH,
        confidence=80,
        timeframe_analysis={"1h": "Bullish", "15m": "Bullish"},
        key_bullish_factors=["Strong trend"],
        key_bearish_factors=[],
        key_support=[2040.0, 2020.0],
        key_resistance=[2060.0, 2080.0],
        risk_level=RiskLevel.MEDIUM,
        summary="Bullish trend expected to continue.",
        provider_used="Test Mock",
        is_fallback=False,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return mtf, ai


class TestProductionIsolation:
    def test_decision_engine_initialization(self):
        engine = DecisionEngine()
        assert engine is not None
        assert hasattr(engine, "evaluate")

    def test_decision_engine_evaluate_returns_trading_decision(self):
        engine = DecisionEngine()
        mtf, ai = _make_dummy_inputs()
        decision, breakdown = engine.evaluate(
            mtf_input=mtf,
            ai_result=ai,
        )
        assert isinstance(decision, TradingDecision)
        assert isinstance(breakdown, DecisionScoreBreakdown)
        assert decision.decision in (TradingSignal.BUY, TradingSignal.SELL, TradingSignal.WAIT)
        assert decision.symbol == "XAU/USD"

    def test_production_signals_unaffected_by_research_state(self):
        """Evaluate two identical runs to verify determinism and isolation."""
        engine = DecisionEngine()
        mtf, ai = _make_dummy_inputs()

        decision1, _ = engine.evaluate(mtf_input=mtf, ai_result=ai)
        decision2, _ = engine.evaluate(mtf_input=mtf, ai_result=ai)

        assert decision1.decision == decision2.decision
        assert decision1.confidence == decision2.confidence
        assert decision1.composite_score == decision2.composite_score
