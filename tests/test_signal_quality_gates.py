"""
Unit tests for the Validated Empirical Signal Quality Gates (BTC & XAU).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.models.ai_analysis import (
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    MultiTimeframeTechnicalInput,
)
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendAnalysis,
    TrendDirection,
    RSIResult,
    RSICondition,
    MACDResult,
    MACDState,
    ATRResult,
    DataQualityReport,
)
from src.models.market_data import Timeframe
from src.models.trading_decision import TradingSignal, TradingDecision
from src.services.decision_engine import DecisionEngine
from src.services.confluence_engine import ContributorState


def _make_mock_ta(
    symbol: str,
    price: float,
    direction: TrendDirection,
    timeframe: str = "15m",
) -> TechnicalAnalysisResponse:
    return TechnicalAnalysisResponse(
        symbol=symbol,
        timeframe=Timeframe(timeframe),
        current_price=price,
        ema20=price * 0.99,
        ema50=price * 0.98,
        ema200=price * 0.95,
        rsi14=RSIResult(value=55.0, period=14, condition=RSICondition.NEUTRAL),
        macd=MACDResult(macd_line=3.0, signal_line=1.0, histogram=2.0, state=MACDState.BULLISH),
        atr14=ATRResult(value=15.0, period=14, volatility_pct=0.5),
        support_levels=[price * 0.98, price * 0.96],
        resistance_levels=[price * 1.02, price * 1.04],
        trend=TrendAnalysis(
            direction=direction,
            score=0.8 if direction == TrendDirection.BULLISH else -0.8,
            strength="STRONG",
            confirmations=["Trend alignment"],
        ),
        indicator_summary="Test",
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        data_quality=DataQualityReport(candle_count=100, is_sufficient=True, missing_indicators=[], notes="OK"),
    )


def _make_mock_mtf(symbol: str, price: float, direction: TrendDirection) -> MultiTimeframeTechnicalInput:
    tf_map = {
        "5m": _make_mock_ta(symbol, price, direction, "5m"),
        "15m": _make_mock_ta(symbol, price, direction, "15m"),
        "1h": _make_mock_ta(symbol, price, direction, "1h"),
        "1d": _make_mock_ta(symbol, price, direction, "1d"),
    }
    return MultiTimeframeTechnicalInput(
        symbol=symbol,
        current_price=price,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timeframes=tf_map,
        timeframe_count=4,
        alignment_summary="Full Alignment",
    )


def _make_mock_ai(bias: OverallBias) -> AIAnalysisResponse:
    from src.models.ai_analysis import RiskLevel
    return AIAnalysisResponse(
        symbol="TEST",
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        market_condition=MarketCondition.TRENDING_BULLISH if bias == OverallBias.BULLISH else MarketCondition.TRENDING_BEARISH,
        overall_bias=bias,
        confidence=80,
        risk_level=RiskLevel.LOW,
        summary="Test AI summary",
        timeframe_analysis={"15m": bias.value, "1h": bias.value},
        key_support=[100.0],
        key_resistance=[200.0],
        provider_used="Mock",
        is_fallback=True,
    )


def _make_contrib(name: str, score: int, bias: str) -> ContributorState:
    return ContributorState(
        name=name,
        max_score=10,
        score=score,
        prev_score=score,
        direction="UNCHANGED",
        bias=bias,
        status="OK",
        evidence=[f"{name} {bias}"],
        conflicts=[],
        timeframe="15m",
        last_changed_at=datetime.now(timezone.utc).isoformat(),
        snapshot_id="test",
        data_freshness="FRESH",
    )


class TestSignalQualityGates:
    """Test the validated signal quality gates for BTC and XAU."""

    def setup_method(self):
        self.engine = DecisionEngine()
        self.engine.bypass_threshold = 50

    def test_btc_confluence_below_58_gates_to_wait(self):
        """BTC signal with confluence score 57 must be gated to WAIT."""
        mtf = _make_mock_mtf("BTC/USD", 65000.0, TrendDirection.BULLISH)
        ai = _make_mock_ai(OverallBias.BULLISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "BUY"
            mock_res.final_score = 57
            mock_res.gate_direction = "BULLISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 8, "BULLISH"),
                _make_contrib("Momentum", 8, "BULLISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 57
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.WAIT
            assert any("BTC Quality Gate: Confluence score (57%)" in w for w in breakdown.wait_overrides_triggered)

    def test_btc_mtf_misalignment_gates_to_wait(self):
        """BTC BUY signal with MTF Alignment BEARISH must be gated to WAIT."""
        mtf = _make_mock_mtf("BTC/USD", 65000.0, TrendDirection.BULLISH)
        ai = _make_mock_ai(OverallBias.BULLISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "BUY"
            mock_res.final_score = 65
            mock_res.gate_direction = "BULLISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 0, "BEARISH"),
                _make_contrib("Momentum", 8, "BULLISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 65
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.WAIT
            assert any("MTF Alignment not aligned" in w for w in breakdown.wait_overrides_triggered)

    def test_btc_valid_sell_preserved(self):
        """Valid BTC SELL with Confluence 65% and MTF Bearish must remain SELL."""
        mtf = _make_mock_mtf("BTC/USD", 65000.0, TrendDirection.BEARISH)
        ai = _make_mock_ai(OverallBias.BEARISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "SELL"
            mock_res.final_score = 65
            mock_res.gate_direction = "BEARISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 8, "BEARISH"),
                _make_contrib("Momentum", 8, "BEARISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 65
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.SELL

    def test_xau_confluence_below_58_gates_to_wait(self):
        """XAU signal with confluence score 57 must be gated to WAIT."""
        mtf = _make_mock_mtf("XAU/USD", 2650.0, TrendDirection.BULLISH)
        ai = _make_mock_ai(OverallBias.BULLISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "BUY"
            mock_res.final_score = 57
            mock_res.gate_direction = "BULLISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 8, "BULLISH"),
                _make_contrib("VWAP", 4, "BULLISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 57
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.WAIT
            assert any("XAU Quality Gate: Confluence score (57%)" in w for w in breakdown.wait_overrides_triggered)

    def test_xau_vwap_misalignment_gates_to_wait(self):
        """XAU BUY signal with VWAP BEARISH must be gated to WAIT."""
        mtf = _make_mock_mtf("XAU/USD", 2650.0, TrendDirection.BULLISH)
        ai = _make_mock_ai(OverallBias.BULLISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "BUY"
            mock_res.final_score = 65
            mock_res.gate_direction = "BULLISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 8, "BULLISH"),
                _make_contrib("VWAP", 0, "BEARISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 65
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.WAIT
            assert any("VWAP position not aligned" in w for w in breakdown.wait_overrides_triggered)

    def test_xau_confluence_58_with_full_alignment_allowed(self):
        """XAU BUY signal with Confluence 65%, MTF Bullish, and VWAP Bullish must be allowed as BUY."""
        mtf = _make_mock_mtf("XAU/USD", 2650.0, TrendDirection.BULLISH)
        ai = _make_mock_ai(OverallBias.BULLISH)

        with patch.object(self.engine.confluence_engine, "compute") as mock_compute:
            mock_res = MagicMock()
            mock_res.signal = "BUY"
            mock_res.final_score = 65
            mock_res.gate_direction = "BULLISH"
            mock_res.gate_passed = True
            mock_res.contributors = [
                _make_contrib("MTF Alignment", 8, "BULLISH"),
                _make_contrib("VWAP", 4, "BULLISH"),
            ]
            mock_res.snapshot_id = "test"
            mock_res.technical_score = 65
            mock_res.gemini_score = 0
            mock_res.data_quality = "HIGH"
            mock_res.data_completeness = "100.0%"
            mock_res.market_regime = "TRENDING"
            mock_res.conflicts = []
            mock_res.top_confirmations = []
            mock_res.entry_quality = "OPTIMAL"
            mock_res.spread_status = "NORMAL"
            mock_res.news_status = "CLEAR"
            mock_compute.return_value = mock_res

            decision, breakdown = self.engine.evaluate(mtf, ai)
            assert decision.decision == TradingSignal.BUY
