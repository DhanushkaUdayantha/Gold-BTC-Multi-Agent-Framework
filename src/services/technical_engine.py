"""Pure Technical Analysis Indicator Engine.

Implements standard financial indicator formulas and explainable rule-based algorithms
for EMA, RSI, MACD, ATR, Support/Resistance swing detection, and Trend classification.
"""
from typing import List, Optional, Tuple, Dict
import numpy as np

from src.models.market_data import OHLCVCandle
from src.models.technical_analysis import (
    RSIResult,
    RSICondition,
    MACDResult,
    MACDState,
    ATRResult,
    EMASet,
    TrendAnalysis,
    TrendDirection,
    DataQualityReport,
)


class TechnicalEngine:
    """Mathematical engine for calculating technical indicators on candlestick sequences."""

    @staticmethod
    def calculate_ema_series(prices: List[float], period: int) -> List[Optional[float]]:
        """Calculate full series of Exponential Moving Average values.

        Returns list of same length as prices, with None for indices < period - 1.
        """
        n = len(prices)
        if n < period or period <= 0:
            return [None] * n

        result: List[Optional[float]] = [None] * (period - 1)
        # Initial SMA for first window
        initial_sma = float(np.mean(prices[:period]))
        result.append(round(initial_sma, 4))

        multiplier = 2.0 / (period + 1.0)
        current_ema = initial_sma

        for i in range(period, n):
            current_ema = (prices[i] * multiplier) + (current_ema * (1.0 - multiplier))
            result.append(round(current_ema, 4))

        return result

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate single latest EMA value for the given period."""
        series = TechnicalEngine.calculate_ema_series(prices, period)
        if not series or series[-1] is None:
            return None
        return series[-1]

    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> Optional[RSIResult]:
        """Calculate Relative Strength Index (RSI) using Wilder's Smoothing.

        Args:
            closes: List of close prices chronologically ordered.
            period: Lookback period (default: 14).

        Returns:
            RSIResult with value and OVERBOUGHT / OVERSOLD / NEUTRAL condition.
        """
        n = len(closes)
        if n <= period:
            return None

        # Price changes
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Initial averages
        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        # Wilder's smoothing for subsequent periods
        for i in range(period, len(deltas)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

        if avg_loss == 0.0:
            rsi_value = 100.0
        elif avg_gain == 0.0:
            rsi_value = 0.0
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100.0 - (100.0 / (1.0 + rs))

        rsi_val_rounded = round(float(rsi_value), 2)

        if rsi_val_rounded > 70.0:
            condition = RSICondition.OVERBOUGHT
        elif rsi_val_rounded < 30.0:
            condition = RSICondition.OVERSOLD
        else:
            condition = RSICondition.NEUTRAL

        return RSIResult(
            value=rsi_val_rounded,
            period=period,
            condition=condition,
        )

    @staticmethod
    def calculate_macd(
        closes: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Optional[MACDResult]:
        """Calculate Moving Average Convergence Divergence (MACD).

        Args:
            closes: Close prices in chronological order.
            fast: Fast EMA period (default: 12).
            slow: Slow EMA period (default: 26).
            signal: Signal line EMA period (default: 9).

        Returns:
            MACDResult with MACD line, signal line, histogram, and bullish/bearish state.
        """
        min_required = slow + signal
        if len(closes) < min_required:
            return None

        fast_ema_series = TechnicalEngine.calculate_ema_series(closes, fast)
        slow_ema_series = TechnicalEngine.calculate_ema_series(closes, slow)

        # Calculate MACD line series: fast_ema - slow_ema
        macd_series: List[float] = []
        for f, s in zip(fast_ema_series, slow_ema_series):
            if f is not None and s is not None:
                macd_series.append(f - s)

        if len(macd_series) < signal:
            return None

        # Signal line: 9-period EMA of MACD line
        signal_series = TechnicalEngine.calculate_ema_series(macd_series, signal)
        latest_signal = signal_series[-1]
        latest_macd = macd_series[-1]

        if latest_signal is None:
            return None

        histogram = latest_macd - latest_signal

        if histogram > 0.0001:
            state = MACDState.BULLISH
        elif histogram < -0.0001:
            state = MACDState.BEARISH
        elif latest_macd > 0:
            state = MACDState.BULLISH
        elif latest_macd < 0:
            state = MACDState.BEARISH
        else:
            state = MACDState.NEUTRAL

        return MACDResult(
            macd_line=round(latest_macd, 4),
            signal_line=round(latest_signal, 4),
            histogram=round(histogram, 4),
            state=state,
        )

    @staticmethod
    def calculate_atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Optional[ATRResult]:
        """Calculate Average True Range (ATR) for volatility measurement.

        Args:
            highs: List of high prices.
            lows: List of low prices.
            closes: List of close prices.
            period: Lookback window (default: 14).

        Returns:
            ATRResult with ATR in USD and volatility percentage.
        """
        n = len(closes)
        if n <= period or len(highs) != n or len(lows) != n:
            return None

        # True Range calculation
        tr_list: List[float] = [highs[0] - lows[0]]
        for i in range(1, n):
            h = highs[i]
            l = lows[i]
            prev_c = closes[i - 1]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

        # Initial SMA of TR
        current_atr = float(np.mean(tr_list[:period]))

        # Wilder's smoothing for remaining bars
        for i in range(period, n):
            current_atr = ((current_atr * (period - 1)) + tr_list[i]) / period

        current_price = closes[-1]
        volatility_pct = (current_atr / current_price * 100.0) if current_price > 0 else 0.0

        return ATRResult(
            value=round(current_atr, 3),
            period=period,
            volatility_pct=round(volatility_pct, 3),
        )

    @staticmethod
    def find_support_resistance(
        candles: List[OHLCVCandle],
        current_price: float,
        window: int = 4,
        max_levels: int = 3,
    ) -> Tuple[List[float], List[float]]:
        """Identify key rule-based Support and Resistance levels from recent swing points.

        Uses fractal extrema detection and price proximity clustering.
        """
        n = len(candles)
        if n < (window * 2 + 1):
            return [], []

        swing_highs: List[float] = []
        swing_lows: List[float] = []

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        for i in range(window, n - window):
            current_h = highs[i]
            current_l = lows[i]

            # Swing High: Highest in +/- window
            if all(current_h >= highs[j] for j in range(i - window, i + window + 1) if j != i):
                swing_highs.append(round(current_h, 2))

            # Swing Low: Lowest in +/- window
            if all(current_l <= lows[j] for j in range(i - window, i + window + 1) if j != i):
                swing_lows.append(round(current_l, 2))

        # Filter: Resistances above current price, Supports below current price
        res_candidates = [h for h in swing_highs if h > current_price]
        sup_candidates = [l for l in swing_lows if l < current_price]

        # Helper to cluster nearby levels within 0.15% threshold
        def cluster_levels(levels: List[float], ascending: bool) -> List[float]:
            if not levels:
                return []
            sorted_levels = sorted(levels, reverse=not ascending)
            clustered: List[float] = []

            for level in sorted_levels:
                if not clustered:
                    clustered.append(level)
                    continue
                # If within 0.20% of previous cluster, skip or merge
                if any(abs(level - c) / level < 0.002 for c in clustered):
                    continue
                clustered.append(level)
                if len(clustered) >= max_levels:
                    break

            return clustered

        # Resistance: closest levels above price (ascending order)
        resistance_levels = sorted(cluster_levels(res_candidates, ascending=True))[:max_levels]
        # Support: closest levels below price (descending order)
        support_levels = sorted(cluster_levels(sup_candidates, ascending=False), reverse=True)[:max_levels]

        return support_levels, resistance_levels

    @staticmethod
    def detect_market_trend(
        current_price: float,
        ema20: Optional[float],
        ema50: Optional[float],
        ema200: Optional[float],
        rsi: Optional[RSIResult],
        macd: Optional[MACDResult],
        candles: List[OHLCVCandle],
    ) -> TrendAnalysis:
        """Classify market trend as BULLISH, BEARISH, or SIDEWAYS using multi-factor confirmation."""
        score = 0.0
        confirmations: List[str] = []

        # 1. EMA Analysis (Weight: up to 0.45)
        if ema20 is not None and ema50 is not None:
            if current_price > ema20 and ema20 > ema50:
                if ema200 is not None and ema50 > ema200:
                    score += 0.45
                    confirmations.append("Full Bullish EMA Stack (Price > EMA20 > EMA50 > EMA200)")
                else:
                    score += 0.30
                    confirmations.append("Short-term Bullish EMA (Price > EMA20 > EMA50)")
            elif current_price < ema20 and ema20 < ema50:
                if ema200 is not None and ema50 < ema200:
                    score -= 0.45
                    confirmations.append("Full Bearish EMA Stack (Price < EMA20 < EMA50 < EMA200)")
                else:
                    score -= 0.30
                    confirmations.append("Short-term Bearish EMA (Price < EMA20 < EMA50)")
            else:
                confirmations.append("EMAs are intertwined / transitioning")

        # 2. MACD Analysis (Weight: up to 0.30)
        if macd is not None and macd.macd_line is not None and macd.signal_line is not None:
            if macd.state == MACDState.BULLISH:
                score += 0.30
                confirmations.append(f"Bullish MACD Momentum (MACD={macd.macd_line} > Signal={macd.signal_line})")
            elif macd.state == MACDState.BEARISH:
                score -= 0.30
                confirmations.append(f"Bearish MACD Momentum (MACD={macd.macd_line} < Signal={macd.signal_line})")
            else:
                confirmations.append("Neutral MACD Convergence")

        # 3. RSI Analysis (Weight: up to 0.20)
        if rsi is not None and rsi.value is not None:
            if 50.0 <= rsi.value <= 70.0:
                score += 0.20
                confirmations.append(f"Healthy Bullish RSI ({rsi.value:.1f} in 50-70 range)")
            elif 30.0 <= rsi.value < 50.0:
                score -= 0.20
                confirmations.append(f"Bearish RSI Bias ({rsi.value:.1f} in 30-50 range)")
            elif rsi.value > 70.0:
                score += 0.10
                confirmations.append(f"Overbought RSI ({rsi.value:.1f} > 70) - Strong upward momentum with pullback risk")
            elif rsi.value < 30.0:
                score -= 0.10
                confirmations.append(f"Oversold RSI ({rsi.value:.1f} < 30) - Strong downward momentum with bounce risk")

        # 4. Recent Price Action / Micro Structure (Weight: 0.05)
        if len(candles) >= 5:
            last5 = candles[-5:]
            if last5[-1].close > last5[0].open:
                score += 0.05
                confirmations.append("5-bar price direction is positive")
            else:
                score -= 0.05
                confirmations.append("5-bar price direction is negative")

        # Thresholds
        normalized_score = round(max(-1.0, min(1.0, score)), 2)

        if normalized_score >= 0.25:
            direction = TrendDirection.BULLISH
        elif normalized_score <= -0.25:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.SIDEWAYS

        abs_score = abs(normalized_score)
        if abs_score >= 0.65:
            strength = "STRONG"
        elif abs_score >= 0.35:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        return TrendAnalysis(
            direction=direction,
            score=normalized_score,
            strength=strength,
            confirmations=confirmations,
        )
