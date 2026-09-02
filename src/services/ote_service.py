"""
OTE Strategy Top-Level Service Orchestrator.

Coordinates:
  1. Fetch candles for 1d, 1h, 15m, 5m from existing MarketDataService
  2. Fetch technical analysis (EMA20/50/200) from existing TechnicalAnalysisService
  3. Run 5-step OTE analysis via OTEEngine
  4. Optionally call Gemini AI for an OTE-specific assessment
  5. Log new paper trade via OTEPaperTradingService if signal fires
  6. Return complete OTESignal with paper stats + trade history
"""
import logging
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional, Tuple

from config.settings import get_settings
from src.models.market_data import Timeframe
from src.models.ote_analysis import OTESignal, OTESignalType
from src.services.market_service import MarketDataService
from src.services.technical_service import TechnicalAnalysisService, get_technical_service
from src.services.ote_engine import OTEEngine
from src.services.ote_paper_trading import OTEPaperTradingService

logger = logging.getLogger(__name__)


class OTEService:
    """Top-level orchestrator for the Smart Money / OTE execution strategy."""

    def __init__(self):
        self._settings = get_settings()
        self._tech_service: TechnicalAnalysisService = get_technical_service()
        self._market_service: MarketDataService = self._tech_service.market_service
        self._engine = OTEEngine()
        self._paper = OTEPaperTradingService()
        self._cache: Optional[OTESignal] = None
        self._cache_ts: float = 0.0
        self._cache_ttl = 60  # 60 second cache for OTE (session-sensitive)

    def get_signal(self, force_refresh: bool = False) -> OTESignal:
        """
        Return the latest OTE signal.
        Cached for 60 seconds unless force_refresh=True.
        """
        now = time.monotonic()
        if not force_refresh and self._cache and (now - self._cache_ts) < self._cache_ttl:
            logger.debug("Returning cached OTE signal.")
            return self._cache

        try:
            signal = self._build_signal()
        except Exception as exc:
            logger.error(f"OTE pipeline error: {exc}", exc_info=True)
            signal = self._wait_signal(f"OTE pipeline error: {exc}")

        self._cache = signal
        self._cache_ts = now
        return signal

    # ─────────────────────────────────────────────────────────
    # Pipeline
    # ─────────────────────────────────────────────────────────

    def _build_signal(self) -> OTESignal:
        timestamp = datetime.now(timezone.utc).isoformat()

        # ── Step 1: Fetch current price + 1H technical analysis ──
        try:
            ta_1h = self._tech_service.analyze(timeframe=Timeframe.H1)
            current_price = ta_1h.current_price
            ema20  = ta_1h.ema20
            ema50  = ta_1h.ema50
            ema200 = ta_1h.ema200
        except Exception as exc:
            logger.warning(f"Could not fetch 1H technical analysis: {exc}")
            return self._wait_signal("Failed to fetch 1H technical analysis.")

        if current_price <= 0:
            return self._wait_signal("Invalid current price from 1H analysis.")

        # ── Step 2: Fetch 1D candles for PDH/PDL ──
        try:
            d1_history = self._market_service.get_candles(timeframe=Timeframe.D1, limit=5)
            daily_candles = d1_history.candles
        except Exception as exc:
            logger.warning(f"Could not fetch 1D candles: {exc}")
            daily_candles = []

        # ── Step 3: Fetch 1H candles for liquidity sweep ──
        try:
            h1_history = self._market_service.get_candles(timeframe=Timeframe.H1, limit=24)
            h1_candles = h1_history.candles
        except Exception as exc:
            logger.warning(f"Could not fetch 1H candles: {exc}")
            h1_candles = []

        # ── Step 4: Fetch 15m candles for MSS, Fibonacci, FVG ──
        try:
            m15_history = self._market_service.get_candles(timeframe=Timeframe.M15, limit=50)
            m15_candles = m15_history.candles
        except Exception as exc:
            logger.warning(f"Could not fetch 15m candles: {exc}")
            m15_candles = []

        # ── Step 5: Fetch 5m candles for FVG ──
        try:
            m5_history = self._market_service.get_candles(timeframe=Timeframe.M5, limit=30)
            m5_candles = m5_history.candles
        except Exception as exc:
            logger.warning(f"Could not fetch 5m candles: {exc}")
            m5_candles = []

        # ── Run 5-step OTE engine ──
        trend     = self._engine.analyze_trend(current_price, ema20, ema50, ema200)
        liquidity = self._engine.analyze_liquidity(daily_candles, h1_candles, current_price)
        mss       = self._engine.analyze_mss(m15_candles, liquidity.sweep_direction, timeframe="15m")
        fibonacci = self._engine.analyze_fibonacci(m15_candles, mss.direction, current_price)
        # Prefer 5m for FVG, fall back to 15m
        fvg = self._engine.analyze_fvg(
            m5_candles if m5_candles else m15_candles,
            mss.direction,
            current_price,
            timeframe="5m" if m5_candles else "15m",
        )
        session = self._engine.check_session()

        signal = self._engine.generate_signal(
            trend=trend,
            liquidity=liquidity,
            mss=mss,
            fibonacci=fibonacci,
            fvg=fvg,
            session=session,
            current_price=current_price,
            timestamp=timestamp,
        )

        # ── Optional: Gemini AI OTE Assessment ──
        try:
            ai_text, ai_conf = self._ai_assess_ote(signal, current_price)
            signal.ai_assessment = ai_text
            signal.ai_confidence = ai_conf
        except Exception as exc:
            logger.warning(f"Gemini OTE assessment skipped: {exc}")
            signal.ai_assessment = "AI assessment unavailable."
            signal.ai_confidence = None

        # ── Paper Trading ──
        try:
            if (
                signal.signal in (OTESignalType.BUY, OTESignalType.SELL)
                and signal.stop_loss is not None
                and signal.take_profit_1 is not None
                and signal.take_profit_2 is not None
            ):
                self._paper.log_new_signal(
                    direction=signal.signal.value,
                    entry_price=current_price,
                    stop_loss=signal.stop_loss,
                    take_profit_1=signal.take_profit_1,
                    take_profit_2=signal.take_profit_2,
                    position_size=signal.position_size or 0.07,
                    setup_grade=signal.setup_grade,
                )
            stats, history = self._paper.update_and_get_stats(current_price)
            signal.paper_stats   = stats
            signal.trade_history = history
        except Exception as exc:
            logger.warning(f"OTE paper trading update failed: {exc}")

        return signal

    # ─────────────────────────────────────────────────────────
    # Gemini OTE Assessment
    # ─────────────────────────────────────────────────────────

    def _ai_assess_ote(self, signal: OTESignal, price: float) -> Tuple[str, int]:
        """
        Ask Gemini to evaluate the current OTE setup and return (text, confidence).
        Uses direct HTTP requests to avoid extra package dependencies.
        """
        settings = self._settings
        if not settings.GEMINI_API_KEY:
            return "Gemini API key not configured — using rule-based assessment only.", 0

        import requests
        prompt = self._build_ote_prompt(signal, price)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            }
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }

        model = settings.AI_MODEL.replace("models/", "")
        models_to_try = [model, "gemini-3.5-flash", "gemini-3.1-flash-lite"]

        for try_model in models_to_try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{try_model}:generateContent"
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=15.0,
                )
                if response.status_code in (404, 503, 429) and try_model != models_to_try[-1]:
                    continue
                response.raise_for_status()
                res_data = response.json()
                candidates = res_data.get("candidates", [])
                if not candidates:
                    continue
                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if content_text:
                    raw = content_text.strip()
                    conf = self._extract_confidence(raw)
                    return raw[:1000], conf
            except Exception as exc:
                logger.debug(f"Gemini OTE call failed for model {try_model}: {exc}")

        return "Gemini assessment failed to generate response.", 0


    def _build_ote_prompt(self, signal: OTESignal, price: float) -> str:
        steps_summary = "\n".join(signal.steps_detail)
        return f"""You are an expert ICT Smart Money / OTE (Optimal Trade Entry) analyst for Gold (XAU/USD).

Current price: ${price:.2f}
Timestamp: {signal.timestamp}

5-Step Execution Status:
{steps_summary}

Step details:
- Trend (1H): {signal.trend.direction} | EMA20: {signal.trend.ema20} | EMA50: {signal.trend.ema50}
- Liquidity: Sweep={signal.liquidity.sweep_direction.value} | PDH={signal.liquidity.prev_day_high} | PDL={signal.liquidity.prev_day_low}
- MSS: {signal.mss.direction.value} | Break level: {signal.mss.break_level}
- OTE Zone: {signal.fibonacci.ote_low}–{signal.fibonacci.ote_high} | In zone: {signal.fibonacci.price_in_ote_zone}
- FVG: {signal.fvg.fvg_type.value} | {signal.fvg.fvg_low}–{signal.fvg.fvg_high} | In FVG: {signal.fvg.price_in_fvg}
- Session: {signal.session.active_session.value} | Open: {signal.session.is_open}

Current signal: {signal.signal.value} (Confidence: {signal.confidence}%)

Evaluate this setup and provide:
1. Your confidence in this setup (0-100)
2. Whether you agree or disagree with the signal, and why
3. Key risks or confirmations to watch for

Keep your response under 300 words. Start with CONFIDENCE: XX% on the first line."""

    @staticmethod
    def _extract_confidence(text: str) -> int:
        """Extract confidence percentage from Gemini response text."""
        import re
        m = re.search(r"CONFIDENCE:\s*(\d+)%", text, re.IGNORECASE)
        if m:
            return min(100, max(0, int(m.group(1))))
        return 50

    # ─────────────────────────────────────────────────────────
    # Safe WAIT fallback
    # ─────────────────────────────────────────────────────────

    def _wait_signal(self, reason: str) -> OTESignal:
        from src.models.ote_analysis import (
            TrendStep, LiquidityStep, MSSStep, FibonacciStep, FVGStep,
            SessionStatus, SweepDirection, MSSDirection, FVGType,
        )
        now = datetime.now(timezone.utc)
        session = self._engine.check_session(now)
        return OTESignal(
            symbol="XAU/USD",
            timestamp=now.isoformat(),
            trend=TrendStep(direction="NEUTRAL", price=0.0, passed=False, reasoning=reason),
            liquidity=LiquidityStep(passed=False, reasoning=reason),
            mss=MSSStep(direction=MSSDirection.NONE, passed=False, timeframe="15m", reasoning=reason),
            fibonacci=FibonacciStep(current_price=0.0, passed=False, reasoning=reason),
            fvg=FVGStep(fvg_type=FVGType.NONE, passed=False, timeframe="5m", reasoning=reason),
            session=session,
            steps_passed=0,
            steps_detail=[f"❌ All steps SKIPPED — {reason}"],
            signal=OTESignalType.WAIT,
            confidence=0,
            setup_grade="C",
            reasons=[f"WAIT — {reason}"],
            warnings=["OTE pipeline encountered an error. Do not trade on this output."],
        )


@lru_cache()
def get_ote_service() -> OTEService:
    """Return singleton OTE service instance."""
    return OTEService()
