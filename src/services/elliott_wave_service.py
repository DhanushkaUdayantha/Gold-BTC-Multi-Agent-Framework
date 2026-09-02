from dataclasses import dataclass
from typing import List, Optional, Any
from src.models.market_data import OHLCVCandle


@dataclass
class ElliottWaveResult:
    wave_phase: str
    wave_number: str
    direction: str  # 'BULLISH' | 'BEARISH' | 'NEUTRAL'
    score: float  # -1.0 to +1.0
    confidence: int  # 0 to 100
    wave_high: Optional[float]
    wave_low: Optional[float]
    reasoning: str


class ElliottWaveService:
    """Calculates Elliott Wave patterns from candlestick price series."""

    @staticmethod
    def analyze(
        candles: List[Any],
        current_price: float,
        timeframe: str = "15m",
    ) -> ElliottWaveResult:
        if not candles or len(candles) < 20 or current_price <= 0:
            return ElliottWaveResult(
                wave_phase="CONSOLIDATION",
                wave_number="NONE",
                direction="NEUTRAL",
                score=0.0,
                confidence=50,
                wave_high=None,
                wave_low=None,
                reasoning="Insufficient candle history for Elliott Wave count.",
            )

        highs = [c.get("high", 0.0) if isinstance(c, dict) else getattr(c, "high", 0.0) for c in candles]
        lows = [c.get("low", 0.0) if isinstance(c, dict) else getattr(c, "low", 0.0) for c in candles]
        closes = [c.get("close", 0.0) if isinstance(c, dict) else getattr(c, "close", 0.0) for c in candles]

        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        range_span = recent_high - recent_low

        if range_span <= 0.5:
            return ElliottWaveResult(
                wave_phase="RANGE_CONSOLIDATION",
                wave_number="NONE",
                direction="NEUTRAL",
                score=0.0,
                confidence=50,
                wave_high=recent_high,
                wave_low=recent_low,
                reasoning="Flat market range — no clear Elliott impulse structure.",
            )

        # Identify local swing pivots (fractals)
        swing_highs = []
        swing_lows = []
        for i in range(2, len(candles) - 2):
            if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
                swing_highs.append((i, highs[i]))
            if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
                swing_lows.append((i, lows[i]))

        # Bullish 5-Wave Pattern Detection
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            last_sh = swing_highs[-1][1]
            prev_sh = swing_highs[-2][1]
            last_sl = swing_lows[-1][1]
            prev_sl = swing_lows[-2][1]

            if last_sh > prev_sh and last_sl > prev_sl:
                wave_range = last_sh - last_sl
                if wave_range > 0:
                    retrace_ratio = (last_sh - current_price) / wave_range
                    if 0.35 <= retrace_ratio <= 0.68:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_PULLBACK_WAVE_2_OR_4",
                            wave_number="WAVE_2/4",
                            direction="BULLISH",
                            score=0.80,
                            confidence=82,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bullish Wave pullback ({retrace_ratio:.1%} Fib retracement) holding above swing low . Primed for Wave 3/5 impulse expansion.",
                        )
                    elif current_price >= last_sh * 0.998:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_EXPANSION_WAVE_3",
                            wave_number="WAVE_3",
                            direction="BULLISH",
                            score=0.85,
                            confidence=85,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bullish Wave 3 impulse extension in progress breaking above swing high .",
                        )
                    else:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_ADVANCING_WAVE_1_OR_3",
                            wave_number="WAVE_1/3",
                            direction="BULLISH",
                            score=0.60,
                            confidence=75,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bullish higher-high structure ( > ) with constructive higher lows.",
                        )

            elif last_sh < prev_sh and last_sl < prev_sl:
                wave_range = last_sh - last_sl
                if wave_range > 0:
                    retrace_ratio = (current_price - last_sl) / wave_range
                    if 0.35 <= retrace_ratio <= 0.68:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_PULLBACK_WAVE_2_OR_4",
                            wave_number="WAVE_2/4",
                            direction="BEARISH",
                            score=-0.80,
                            confidence=82,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bearish Wave pullback up ({retrace_ratio:.1%} Fib retracement) capped below swing high . Primed for Wave 3/5 selloff.",
                        )
                    elif current_price <= last_sl * 1.002:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_EXPANSION_WAVE_3",
                            wave_number="WAVE_3",
                            direction="BEARISH",
                            score=-0.85,
                            confidence=85,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bearish Wave 3 breakdown accelerating beneath swing low .",
                        )
                    else:
                        return ElliottWaveResult(
                            wave_phase="IMPULSE_DECLINING_WAVE_1_OR_3",
                            wave_number="WAVE_1/3",
                            direction="BEARISH",
                            score=-0.60,
                            confidence=75,
                            wave_high=last_sh,
                            wave_low=last_sl,
                            reasoning=f"Bearish lower-low structure ( < ) with descending swing resistance.",
                        )

        momentum = closes[-1] - closes[0]
        if momentum > range_span * 0.4:
            return ElliottWaveResult(
                wave_phase="IMPULSE_BULLISH",
                wave_number="WAVE_3",
                direction="BULLISH",
                score=0.50,
                confidence=65,
                wave_high=recent_high,
                wave_low=recent_low,
                reasoning=f"Upward trend momentum (+) suggesting developing impulse wave.",
            )
        elif momentum < -range_span * 0.4:
            return ElliottWaveResult(
                wave_phase="IMPULSE_BEARISH",
                wave_number="WAVE_3",
                direction="BEARISH",
                score=-0.50,
                confidence=65,
                wave_high=recent_high,
                wave_low=recent_low,
                reasoning=f"Downward trend momentum (-) suggesting developing impulse wave.",
            )

        return ElliottWaveResult(
            wave_phase="CORRECTIVE_CONSOLIDATION",
            wave_number="WAVE_B",
            direction="NEUTRAL",
            score=0.0,
            confidence=50,
            wave_high=recent_high,
            wave_low=recent_low,
            reasoning="Corrective overlapping price action within established boundary.",
        )
