import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json

from src.models.market_data import Timeframe
from src.models.technical_analysis import TechnicalAnalysisResponse, TrendDirection
from src.models.ai_analysis import MultiTimeframeTechnicalInput
from src.services.technical_service import TechnicalAnalysisService, get_technical_service

logger = logging.getLogger(__name__)


class AIAggregator:
    """Collects multi-timeframe technical profiles and prepares inputs for AI models."""

    TARGET_TIMEFRAMES = [
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.D1,
    ]

    def __init__(self, technical_service: Optional[TechnicalAnalysisService] = None):
        self.technical_service = technical_service or get_technical_service()

    def collect_multi_timeframe_data(
        self,
        symbol: Optional[str] = None,
        force_refresh: bool = False,
    ) -> MultiTimeframeTechnicalInput:
        """Gather technical analysis profiles across 5m, 15m, 1h, and 1d timeframes concurrently."""
        timeframes_data: Dict[str, TechnicalAnalysisResponse] = {}
        latest_price = 0.0

        def _fetch_tf(tf: Timeframe) -> Tuple[str, Optional[TechnicalAnalysisResponse]]:
            try:
                analysis = self.technical_service.analyze(
                    symbol=symbol,
                    timeframe=tf,
                    force_refresh=force_refresh,
                )
                return tf.value, analysis
            except Exception as exc:
                logger.warning(f"Failed to gather {tf.value} technical data for AI analysis: {exc}")
                return tf.value, None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_fetch_tf, tf) for tf in self.TARGET_TIMEFRAMES]
            for fut in as_completed(futures):
                tf_val, analysis = fut.result()
                if analysis is not None:
                    timeframes_data[tf_val] = analysis
                    if analysis.current_price > 0:
                        latest_price = analysis.current_price

        if not timeframes_data:
            raise ValueError(f"Unable to retrieve technical data for any timeframe for {symbol or 'XAU/USD'}.")

        # Assess alignment across gathered timeframes
        bullish_count = sum(1 for a in timeframes_data.values() if a.trend.direction == TrendDirection.BULLISH)
        bearish_count = sum(1 for a in timeframes_data.values() if a.trend.direction == TrendDirection.BEARISH)
        sideways_count = sum(1 for a in timeframes_data.values() if a.trend.direction == TrendDirection.SIDEWAYS)
        total = len(timeframes_data)

        if bullish_count == total:
            alignment = f"Full Bullish Alignment ({bullish_count}/{total} timeframes bullish)"
        elif bearish_count == total:
            alignment = f"Full Bearish Alignment ({bearish_count}/{total} timeframes bearish)"
        elif bullish_count > bearish_count and bullish_count >= 2:
            alignment = f"Bullish Skew with Counter-Trend Noise ({bullish_count} bullish, {bearish_count} bearish, {sideways_count} sideways)"
        elif bearish_count > bullish_count and bearish_count >= 2:
            alignment = f"Bearish Skew with Counter-Trend Noise ({bearish_count} bearish, {bullish_count} bullish, {sideways_count} sideways)"
        else:
            alignment = f"Conflicting / Mixed Timeframes ({bullish_count} bullish, {bearish_count} bearish, {sideways_count} sideways)"

        return MultiTimeframeTechnicalInput(
            symbol=symbol or "XAU-USD-SPOT",
            current_price=latest_price,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timeframes=timeframes_data,
            timeframe_count=len(timeframes_data),
            alignment_summary=alignment,
        )

    @staticmethod
    def build_system_prompt() -> str:
        """Construct system instructions enforcing rigorous AI market analysis constraints."""
        return (
            "You are an expert Institutional Market Structure & Quantitative Technical Analyst for XAU/USD (Gold).\n"
            "Your task is to analyze multi-timeframe technical indicator data and produce a structured market assessment.\n\n"
            "CRITICAL OPERATING RULES:\n"
            "1. NO TRADE EXECUTION: You are strictly an analytical advisory model. Do NOT provide entry, stop-loss, or take-profit targets.\n"
            "2. NO PROFIT GUARANTEES: Never claim certainty or guaranteed direction. Markets are probabilistic.\n"
            "3. ZERO FABRICATION: You must strictly base your analysis ONLY on the supplied numerical indicators and candle data.\n"
            "4. CONFLICT DETECTION: Actively compare higher timeframes (1d, 1h) with lower timeframes (15m, 5m). If lower timeframes contradict higher timeframes (e.g. 5m pullback in a 1d uptrend), highlight the conflict and REDUCE the confidence score.\n"
            "5. CONFIDENCE SCORING:\n"
            "   - High (75-90): Strong multi-timeframe confluence (EMAs, MACD, RSI aligned across 1d, 1h, 15m).\n"
            "   - Moderate (55-74): Macro trend clear, but lower timeframes show counter-trend pullback or consolidation.\n"
            "   - Low / Unclear (30-54): Timeframes strongly disagree or indicators are mixed/flat (return overall_bias='NEUTRAL').\n"
            "6. MARKET CONDITIONS:\n"
            "   Must be one of: 'TRENDING_BULLISH', 'TRENDING_BEARISH', 'RANGE', 'HIGH_VOLATILITY', 'UNCLEAR'.\n"
            "7. OVERALL BIAS:\n"
            "   Must be one of: 'BULLISH', 'BEARISH', 'NEUTRAL'.\n"
            "8. RISK LEVEL:\n"
            "   Must be one of: 'LOW', 'MEDIUM', 'HIGH'.\n"
            "9. SUMMARY FORMAT: Keep the 'summary' section extremely SHORT and concise. List only the major points using concise bullet points followed by one short overall conclusion sentence. Do not exceed 80 words total in the summary.\n"
            "10. OUTPUT FORMAT: Respond with valid JSON matching the exact required schema."
        )


    @staticmethod
    def build_user_prompt(input_data: MultiTimeframeTechnicalInput) -> str:
        """Format raw technical indicator data into an analytical prompt for LLM consumption."""
        data_summary = {
            "symbol": input_data.symbol,
            "current_price": input_data.current_price,
            "timestamp": input_data.timestamp,
            "alignment_overview": input_data.alignment_summary,
            "timeframe_profiles": {},
        }

        for tf_key, tf_val in input_data.timeframes.items():
            data_summary["timeframe_profiles"][tf_key] = {
                "price": tf_val.current_price,
                "ema20": tf_val.ema20,
                "ema50": tf_val.ema50,
                "ema200": tf_val.ema200,
                "rsi14": {
                    "value": tf_val.rsi14.value if tf_val.rsi14 else None,
                    "condition": tf_val.rsi14.condition.value if tf_val.rsi14 else None,
                },
                "macd": {
                    "macd_line": tf_val.macd.macd_line if tf_val.macd else None,
                    "signal_line": tf_val.macd.signal_line if tf_val.macd else None,
                    "histogram": tf_val.macd.histogram if tf_val.macd else None,
                    "state": tf_val.macd.state.value if tf_val.macd else None,
                },
                "atr14": {
                    "value": tf_val.atr14.value if tf_val.atr14 else None,
                    "volatility_pct": tf_val.atr14.volatility_pct if tf_val.atr14 else None,
                },
                "support_levels": tf_val.support_levels,
                "resistance_levels": tf_val.resistance_levels,
                "trend_direction": tf_val.trend.direction.value,
                "trend_strength": tf_val.trend.strength,
                "trend_score": tf_val.trend.score,
                "confirmations": tf_val.trend.confirmations,
                "data_quality": tf_val.data_quality.notes,
            }

        if input_data.historical_evidence:
            data_summary["historical_empirical_evidence"] = input_data.historical_evidence

        sym_display = input_data.symbol or "XAU/USD"
        return (
            f"Analyze the following multi-timeframe market data for {sym_display} and produce a structured JSON response:\n"
            "NOTE: If 'historical_empirical_evidence' is provided, treat it as factual validated backtest context. "
            "Never invent or hallucinate historical statistics.\n\n"
            f"```json\n{json.dumps(data_summary, indent=2)}\n```\n\n"
            "Required JSON Schema:\n"
            "{\n"
            f'  "symbol": "{sym_display}",\n'
            '  "analysis_timestamp": "<ISO timestamp>",\n'
            '  "market_condition": "TRENDING_BULLISH | TRENDING_BEARISH | RANGE | HIGH_VOLATILITY | UNCLEAR",\n'
            '  "overall_bias": "BULLISH | BEARISH | NEUTRAL",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "timeframe_analysis": {\n'
            '    "5m": "<analysis of 5m trend, EMA, RSI, MACD>",\n'
            '    "15m": "<analysis of 15m trend, EMA, RSI, MACD>",\n'
            '    "1h": "<analysis of 1h trend, EMA, RSI, MACD>",\n'
            '    "1d": "<analysis of 1d macro trend, EMA, RSI, MACD>"\n'
            '  },\n'
            '  "key_bullish_factors": ["<bullish factor 1>", "<bullish factor 2>"],\n'
            '  "key_bearish_factors": ["<bearish factor 1>", "<bearish factor 2>"],\n'
            '  "key_support": [<float>, <float>],\n'
            '  "key_resistance": [<float>, <float>],\n'
            '  "risk_level": "LOW | MEDIUM | HIGH",\n'
            '  "summary": "<comprehensive analytical summary of market state>"\n'
            "}"
        )
