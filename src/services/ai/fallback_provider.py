"""Deterministic Fallback AI Provider.

Provides robust rule-based multi-timeframe synthesis when no external LLM API key is configured.
Ensures zero runtime crashes and guarantees complete schema-compliant analysis with configuration notices.
"""
import logging
from typing import Dict, List
from datetime import datetime, timezone

from src.models.technical_analysis import TrendDirection, RSICondition, MACDState
from src.models.ai_analysis import (
    MultiTimeframeTechnicalInput,
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    RiskLevel,
)
from src.services.ai.base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class FallbackAIProvider(BaseAIProvider):
    """Rule-based multi-timeframe reasoning engine used as deterministic fallback."""

    @property
    def provider_name(self) -> str:
        return "Deterministic Fallback Engine"

    def generate_analysis(self, input_data: MultiTimeframeTechnicalInput) -> AIAnalysisResponse:
        """Evaluate multi-timeframe metrics and generate explainable structured market assessment."""
        tf_data = input_data.timeframes
        current_price = input_data.current_price
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract timeframe objects if present
        d1 = tf_data.get("1d")
        h1 = tf_data.get("1h")
        m15 = tf_data.get("15m")
        m5 = tf_data.get("5m")

        bullish_factors: List[str] = []
        bearish_factors: List[str] = []
        timeframe_analysis: Dict[str, str] = {}

        # 1. Evaluate individual timeframes
        bullish_votes = 0
        bearish_votes = 0
        neutral_votes = 0

        for tf_label, analysis in tf_data.items():
            trend_dir = analysis.trend.direction
            rsi_val = analysis.rsi14.value if analysis.rsi14 else None
            macd_state = analysis.macd.state if analysis.macd else None
            atr_val = analysis.atr14.value if analysis.atr14 else None

            desc_parts = [f"{trend_dir.value} ({analysis.trend.strength}, score: {analysis.trend.score:+0.2f})."]
            if analysis.ema20 and analysis.ema50:
                desc_parts.append(f"EMA20 (${analysis.ema20:,.1f}) vs EMA50 (${analysis.ema50:,.1f}).")
            if rsi_val:
                desc_parts.append(f"RSI: {rsi_val:.1f} ({analysis.rsi14.condition.value}).")
            if macd_state:
                desc_parts.append(f"MACD: {macd_state.value}.")
            if atr_val:
                desc_parts.append(f"ATR: ${atr_val:.2f}.")

            timeframe_analysis[tf_label] = " ".join(desc_parts)

            # Scoring factors
            if trend_dir == TrendDirection.BULLISH:
                bullish_votes += (2 if tf_label in ("1d", "1h") else 1)
                bullish_factors.append(f"[{tf_label.upper()}] Bullish trend structure with positive momentum")
            elif trend_dir == TrendDirection.BEARISH:
                bearish_votes += (2 if tf_label in ("1d", "1h") else 1)
                bearish_factors.append(f"[{tf_label.upper()}] Bearish trend structure with negative momentum")
            else:
                neutral_votes += 1

        # Check macro vs micro alignment
        macro_bullish = bool(d1 and d1.trend.direction == TrendDirection.BULLISH) or bool(h1 and h1.trend.direction == TrendDirection.BULLISH)
        macro_bearish = bool(d1 and d1.trend.direction == TrendDirection.BEARISH) or bool(h1 and h1.trend.direction == TrendDirection.BEARISH)
        micro_bullish = bool(m15 and m15.trend.direction == TrendDirection.BULLISH) or bool(m5 and m5.trend.direction == TrendDirection.BULLISH)
        micro_bearish = bool(m15 and m15.trend.direction == TrendDirection.BEARISH) or bool(m5 and m5.trend.direction == TrendDirection.BEARISH)

        # 2. Determine Market Condition & Bias
        if macro_bullish and micro_bullish and bullish_votes >= 4:
            market_condition = MarketCondition.TRENDING_BULLISH
            overall_bias = OverallBias.BULLISH
            confidence = min(88, 70 + (bullish_votes * 3))
            risk_level = RiskLevel.LOW
        elif macro_bearish and micro_bearish and bearish_votes >= 4:
            market_condition = MarketCondition.TRENDING_BEARISH
            overall_bias = OverallBias.BEARISH
            confidence = min(88, 70 + (bearish_votes * 3))
            risk_level = RiskLevel.LOW
        elif (macro_bullish and micro_bearish) or (macro_bearish and micro_bullish):
            # Counter-trend divergence
            market_condition = MarketCondition.RANGE
            overall_bias = OverallBias.BULLISH if macro_bullish else OverallBias.BEARISH
            confidence = 58  # Reduced confidence on conflicting timeframes
            risk_level = RiskLevel.MEDIUM
            if macro_bullish and micro_bearish:
                bearish_factors.append("Intraday pullbacks (5m/15m) conflicting with higher timeframe bullish trend")
            else:
                bullish_factors.append("Intraday bounces (5m/15m) conflicting with higher timeframe bearish trend")
        elif (d1 and d1.atr14 and d1.atr14.volatility_pct and d1.atr14.volatility_pct > 1.2):
            market_condition = MarketCondition.HIGH_VOLATILITY
            overall_bias = OverallBias.NEUTRAL
            confidence = 50
            risk_level = RiskLevel.HIGH
        else:
            market_condition = MarketCondition.UNCLEAR
            overall_bias = OverallBias.NEUTRAL
            confidence = 45
            risk_level = RiskLevel.MEDIUM

        # Check for RSI overbought / oversold cautions
        for tf_label, a in tf_data.items():
            if a.rsi14 and a.rsi14.condition == RSICondition.OVERBOUGHT:
                bearish_factors.append(f"[{tf_label.upper()}] RSI is Overbought ({a.rsi14.value:.1f}) - risk of temporary exhaustion")
                if overall_bias == OverallBias.BULLISH:
                    confidence = max(35, confidence - 8)
            elif a.rsi14 and a.rsi14.condition == RSICondition.OVERSOLD:
                bullish_factors.append(f"[{tf_label.upper()}] RSI is Oversold ({a.rsi14.value:.1f}) - potential mean-reversion bounce zone")
                if overall_bias == OverallBias.BEARISH:
                    confidence = max(35, confidence - 8)

        # 3. Aggregate Supports and Resistances across timeframes
        all_supports: List[float] = []
        all_resistances: List[float] = []

        for a in tf_data.values():
            all_supports.extend(a.support_levels)
            all_resistances.extend(a.resistance_levels)

        # De-duplicate and cluster key levels
        def deduplicate_levels(levels: List[float], ascending: bool) -> List[float]:
            unique: List[float] = []
            for lvl in sorted(levels, reverse=not ascending):
                if not unique or not any(abs(lvl - u) / lvl < 0.0015 for u in unique):
                    unique.append(lvl)
            return sorted(unique, reverse=not ascending)[:3]

        key_support = sorted(deduplicate_levels(all_supports, ascending=False), reverse=True)
        key_resistance = sorted(deduplicate_levels(all_resistances, ascending=True))

        # 4. Generate Comprehensive Executive Summary
        summary_lines = [
            f"XAU/USD is currently trading at ${current_price:,.2f}.",
            f"Overall market condition is classified as {market_condition.value} with a {overall_bias.value} directional bias (Confidence: {confidence}%).",
            f"Trend Alignment: {input_data.alignment_summary}.",
        ]

        if key_support:
            summary_lines.append(f"Primary Support Zone: ${key_support[0]:,.2f}.")
        if key_resistance:
            summary_lines.append(f"Primary Resistance Zone: ${key_resistance[0]:,.2f}.")

        if overall_bias == OverallBias.NEUTRAL:
            summary_lines.append("Market conditions are mixed or in consolidation. Recommended posture is WAIT / NO TRADE.")
        else:
            summary_lines.append(f"Market exhibits {overall_bias.value.lower()} momentum; monitor key levels and risk parameters.")

        summary_text = " ".join(summary_lines)

        return AIAnalysisResponse(
            symbol=input_data.symbol,
            analysis_timestamp=timestamp,
            market_condition=market_condition,
            overall_bias=overall_bias,
            confidence=confidence,
            timeframe_analysis=timeframe_analysis,
            key_bullish_factors=bullish_factors[:5],
            key_bearish_factors=bearish_factors[:5],
            key_support=key_support,
            key_resistance=key_resistance,
            risk_level=risk_level,
            summary=summary_text,
            provider_used=self.provider_name,
            is_fallback=True,
            config_warning=(
                "AI API Key not configured in .env. Running on built-in deterministic heuristic engine. "
                "Set GEMINI_API_KEY in .env to activate Google Gemini AI analysis."
            ),
        )
