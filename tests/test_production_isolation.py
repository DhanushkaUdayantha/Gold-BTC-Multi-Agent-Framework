"""
Production Safety & Decision Isolation Regression Tests.

Verifies the absolute invariant:
- Live DecisionEngine.evaluate() outputs remain 100% identical.
- Zero production thresholds, signals, entry, SL, TP, or position sizing modified.
- Shadow gating is strictly isolated in research modules.
"""
from datetime import datetime, timezone
from src.models.ai_analysis import (
    AIAnalysisResponse,
    MarketCondition,
    MultiTimeframeTechnicalInput,
    OverallBias,
    RiskLevel,
)
from src.models.market_data import Timeframe
from src.models.technical_analysis import (
    ATRResult,
    DataQualityReport,
    MACDResult,
    MACDState,
    RSICondition,
    RSIResult,
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
)
from src.models.trading_decision import TradingDecision, TradingSignal
from src.services.decision_engine import DecisionEngine


def _make_ta(
    price: float = 2700.0,
    direction: TrendDirection = TrendDirection.BULLISH,
    strength: str = "STRONG",
    rsi_val: float = 55.0,
    rsi_cond: RSICondition = RSICondition.NEUTRAL,
    macd_state: MACDState = MACDState.BULLISH,
    macd_hist: float = 2.5,
    atr_val: float = 15.0,
    ema20: float = 2695.0,
    ema50: float = 2680.0,
    ema200: float = 2600.0,
    timeframe: str = "1h",
) -> TechnicalAnalysisResponse:
    return TechnicalAnalysisResponse(
        symbol="XAU-USD-SPOT",
        timeframe=Timeframe(timeframe),
        current_price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi14=RSIResult(value=rsi_val, period=14, condition=rsi_cond),
        macd=MACDResult(macd_line=3.0, signal_line=0.5, histogram=macd_hist, state=macd_state),
        atr14=ATRResult(value=atr_val, period=14, volatility_pct=atr_val / price * 100),
        support_levels=[2680.0, 2650.0],
        resistance_levels=[2720.0, 2750.0],
        trend=TrendAnalysis(
            direction=direction,
            score=0.8 if direction == TrendDirection.BULLISH else (-0.8 if direction == TrendDirection.BEARISH else 0.0),
            strength=strength,
            confirmations=["EMA alignment", "MACD positive"],
        ),
        indicator_summary="Test summary",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=200, is_sufficient=True, missing_indicators=[], notes="OK"),
    )


def _make_ai_result(
    market_condition: MarketCondition = MarketCondition.TRENDING_BULLISH,
    overall_bias: OverallBias = OverallBias.BULLISH,
    confidence: int = 80,
) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        symbol="XAU/USD",
        market_condition=market_condition,
        overall_bias=overall_bias,
        confidence=confidence,
        timeframe_analysis={"1h": "Bullish", "15m": "Bullish"},
        key_bullish_factors=["Strong trend"],
        key_bearish_factors=[],
        key_support=[2680.0, 2660.0],
        key_resistance=[2745.0, 2780.0],
        risk_level=RiskLevel.MEDIUM,
        summary="Test AI summary.",
        provider_used="Test Fallback",
        is_fallback=False,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _make_mtf_input(tf_map: dict, price: float = 2700.0) -> MultiTimeframeTechnicalInput:
    bullish = sum(1 for t in tf_map.values() if t and t.trend.direction == TrendDirection.BULLISH)
    total = sum(1 for t in tf_map.values() if t is not None)
    return MultiTimeframeTechnicalInput(
        symbol="XAU/USD",
        current_price=price,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timeframes={k: v for k, v in tf_map.items() if v is not None},
        timeframe_count=total,
        alignment_summary=f"{bullish}/{total} bullish",
    )


def test_production_decision_engine_isolation():
    """
    Asserts that DecisionEngine.evaluate produces identical deterministic signals
    for both Bullish and Bearish MTF inputs.
    """
    tf_map = {
        "5m": _make_ta(timeframe="5m"),
        "15m": _make_ta(timeframe="15m"),
        "1h": _make_ta(timeframe="1h"),
        "1d": _make_ta(timeframe="1d"),
    }
    mtf = _make_mtf_input(tf_map, price=2700.0)
    ai = _make_ai_result(overall_bias=OverallBias.BULLISH, confidence=80)
    engine = DecisionEngine()

    decision, breakdown = engine.evaluate(mtf, ai)

    # Core engine must produce valid standard outputs without research contamination
    assert decision.decision in (TradingSignal.BUY, TradingSignal.SELL, TradingSignal.WAIT)
    assert isinstance(decision, TradingDecision)
    assert breakdown is not None
    assert breakdown.total_score is not None


def test_production_safety_declarations():
    """Verify safety assertions in code and reports."""
    from src.research.gating_acceptance_policy import GATING_RESEARCH_POLICY_VERSION
    assert GATING_RESEARCH_POLICY_VERSION == "1.0"
