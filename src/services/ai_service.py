"""High-level AI Market Analysis Service.

Orchestrates multi-timeframe indicator aggregation, resolves the active AI provider,
implements short-term caching, tracks request budgets, runs the meaningful-change
gate, and handles graceful fallbacks.

GEMINI CALL POLICY
==================
A Gemini API call is only made when ALL of the following are true:
  1. MeaningfulChangeDetector says the market state materially changed.
  2. GeminiRequestManager says the daily budget and cooldown allow it.
  3. The resolved provider is NOT FallbackAIProvider.

Frontend polling, chart refresh, price ticks, countdown ticks, and page
load do NOT cause Gemini calls.
"""
import logging
import threading
import time
from typing import Optional, Dict, Tuple
from functools import lru_cache

from config.settings import Settings, get_settings
from src.models.ai_analysis import (
    MultiTimeframeTechnicalInput,
    AIAnalysisResponse,
)
from src.services.technical_service import TechnicalAnalysisService, get_technical_service
from src.services.ai.ai_aggregator import AIAggregator
from src.services.ai.base_provider import BaseAIProvider
from src.services.ai.fallback_provider import FallbackAIProvider
from src.services.ai.gemini_provider import GeminiAIProvider, GeminiAIError
from src.services.ai.openai_provider import OpenAIAIProvider, OpenAIAIError
from src.services.ai.request_manager import GeminiRequestManager
from src.services.ai.change_detector import MeaningfulChangeDetector

logger = logging.getLogger(__name__)


class AIMarketAnalysisService:
    """Core service for generating multi-timeframe AI market analysis."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        technical_service: Optional[TechnicalAnalysisService] = None,
    ):
        self.settings = settings or get_settings()
        self.technical_service = technical_service or get_technical_service()
        self.aggregator = AIAggregator(technical_service=self.technical_service)
        self.fallback_provider = FallbackAIProvider()
        self.request_manager = GeminiRequestManager(
            testing_mode=(self.settings.APP_ENV == "testing")
        )
        self.change_detector = MeaningfulChangeDetector()
        self._lock = threading.Lock()


        # Cache: market_context_key -> (timestamp, AIAnalysisResponse)
        self._analysis_cache: Dict[str, Tuple[float, AIAnalysisResponse]] = {}
        # General fallback if context cache is empty
        self._last_successful_analysis: Optional[AIAnalysisResponse] = None
        self._cached_provider: Optional[BaseAIProvider] = None

    def _resolve_provider(self) -> BaseAIProvider:
        """Resolve the active AI provider based on settings and available API keys."""
        if self._cached_provider is not None:
            return self._cached_provider

        mode = self.settings.AI_PROVIDER.lower()
        provider = None

        if mode == "gemini":
            if self.settings.GEMINI_API_KEY:
                provider = GeminiAIProvider(
                    api_key=self.settings.GEMINI_API_KEY,
                    model_name=self.settings.AI_MODEL,
                    timeout=self.settings.AI_REQUEST_TIMEOUT_SECONDS,
                )
            else:
                logger.warning("Gemini provider selected but GEMINI_API_KEY is empty. Routing to Fallback provider.")
                provider = self.fallback_provider

        elif mode == "openai":
            if self.settings.OPENAI_API_KEY:
                provider = OpenAIAIProvider(
                    api_key=self.settings.OPENAI_API_KEY,
                    model_name="gpt-4o-mini",
                    timeout=self.settings.AI_REQUEST_TIMEOUT_SECONDS,
                )
            else:
                logger.warning("OpenAI provider selected but OPENAI_API_KEY is empty. Routing to Fallback provider.")
                provider = self.fallback_provider

        elif mode == "fallback":
            provider = self.fallback_provider

        else:  # "auto"
            if self.settings.GEMINI_API_KEY:
                provider = GeminiAIProvider(
                    api_key=self.settings.GEMINI_API_KEY,
                    model_name=self.settings.AI_MODEL,
                    timeout=self.settings.AI_REQUEST_TIMEOUT_SECONDS,
                )
            elif self.settings.OPENAI_API_KEY:
                provider = OpenAIAIProvider(
                    api_key=self.settings.OPENAI_API_KEY,
                    model_name="gpt-4o-mini",
                    timeout=self.settings.AI_REQUEST_TIMEOUT_SECONDS,
                )
            else:
                provider = self.fallback_provider

        self._cached_provider = provider
        return provider

    def get_raw_technical_input(
        self,
        symbol: Optional[str] = None,
        force_refresh: bool = False,
    ) -> MultiTimeframeTechnicalInput:
        """Collect and return raw multi-timeframe technical input data."""
        symbol = symbol or self.settings.DEFAULT_SYMBOL
        return self.aggregator.collect_multi_timeframe_data(symbol=symbol, force_refresh=force_refresh)

    def analyze_market(
        self,
        symbol: Optional[str] = None,
        force_refresh: bool = False,
        # Optional: caller can supply current decision signal to feed change detector
        current_signal: str = "WAIT",
        current_strength: int = 50,
        raw_input: Optional[MultiTimeframeTechnicalInput] = None,
    ) -> AIAnalysisResponse:
        """Conduct complete multi-timeframe AI market analysis.

        Gate order (two layers):
          Layer 1 — MeaningfulChangeDetector: Has anything materially changed?
                    If NO -> return cached analysis immediately (zero budget cost).
          Layer 2 — GeminiRequestManager: Is the daily budget and cooldown OK?
                    If NO -> return cached/fallback analysis.
          Layer 3 — Execute live Gemini call, record reason, update snapshot.
        """
        with self._lock:
            symbol = symbol or self.settings.DEFAULT_SYMBOL
            now = time.time()

            # 1. Collect multi-timeframe data first if not passed in
            if raw_input is None:
                try:
                    raw_input = self.get_raw_technical_input(symbol=symbol, force_refresh=force_refresh)
                except Exception as exc:
                    logger.error(f"Failed to retrieve technical input for AI service: {exc}")
                    return self.fallback_provider.generate_analysis(
                        MultiTimeframeTechnicalInput(
                            symbol=symbol, current_price=2700.0, timestamp="",
                            timeframes={}, timeframe_count=0, alignment_summary="Error"
                        )
                    )

            # 2. Extract state for change detection
            m5_ta   = raw_input.timeframes.get("5m")
            m15_ta  = raw_input.timeframes.get("15m")
            h1_ta   = raw_input.timeframes.get("1h")
            d1_ta   = raw_input.timeframes.get("1d")

            m5_trend  = m5_ta.trend.direction.value  if m5_ta  else "SIDEWAYS"
            m15_trend = m15_ta.trend.direction.value if m15_ta else "SIDEWAYS"
            h1_trend  = h1_ta.trend.direction.value  if h1_ta  else "SIDEWAYS"
            d1_trend  = d1_ta.trend.direction.value  if d1_ta  else "SIDEWAYS"

            h1_rsi_cond  = (h1_ta.rsi14.condition.value if (h1_ta and h1_ta.rsi14) else "NEUTRAL")
            h1_macd_state = (h1_ta.macd.state.value     if (h1_ta and h1_ta.macd)  else "NEUTRAL")

            # Latest candle timestamp on the 15m timeframe (primary entry TF)
            candle_ts = ""
            if m15_ta:
                # current_price field tracks last candle data_timestamp
                candle_ts = getattr(m15_ta, "data_timestamp", "") or ""

            # Build context-aware cache key (same logic as before)
            market_context = f"{symbol}:{m5_trend}:{m15_trend}:{h1_trend}:{d1_trend}:{h1_rsi_cond}:{h1_macd_state}"
            cached_item = self._analysis_cache.get(market_context)

            # 3. Short-circuit: if AI-level cache is still fresh, serve directly
            # For force_refresh, reuse cache if generated in the last 10s (concurrent refresh burst)
            if cached_item:
                cached_time, cached_res = cached_item
                max_cache_age = 10.0 if force_refresh else self.settings.AI_CACHE_TTL_SECONDS
                if now - cached_time < max_cache_age:
                    logger.debug(f"Serving fresh AI cache (age={int(now-cached_time)}s) for context: {market_context}")
                    return cached_res

            # 4. Resolve provider early — fallback provider skips all gates
            provider = self._resolve_provider()
            if isinstance(provider, FallbackAIProvider):
                analysis = provider.generate_analysis(raw_input)
                analysis.generation_duration_ms = 0
                self._analysis_cache[market_context] = (now, analysis)
                self._last_successful_analysis = analysis
                return analysis

            # 5. LAYER 1: MeaningfulChangeDetector gate
            if not force_refresh and self.settings.APP_ENV != "testing":
                should_call, change_reason = self.change_detector.should_refresh(
                    symbol=symbol,
                    current_signal=current_signal,
                    current_strength=current_strength,
                    current_price=raw_input.current_price,
                    m5_trend=m5_trend,
                    m15_trend=m15_trend,
                    h1_trend=h1_trend,
                    d1_trend=d1_trend,
                    rsi_condition=h1_rsi_cond,
                    macd_state=h1_macd_state,
                    candle_timestamp=candle_ts,
                )
                if not should_call:
                    # Nothing materially changed — serve cached or last-known result
                    if cached_item:
                        return cached_item[1]
                    if self._last_successful_analysis:
                        return self._last_successful_analysis
                    # Edge case: no cache at all, fall through to live call anyway

            else:
                change_reason = "force_refresh" if force_refresh else "testing_bypass"

            # 6. LAYER 2: GeminiRequestManager budget + cooldown gate
            # Also check if PDH/PDL has been swept (important market event)
            is_important_event = False
            if h1_ta and hasattr(h1_ta, "prev_day_high") and h1_ta.prev_day_high:
                pdh = h1_ta.prev_day_high
                pdl = getattr(h1_ta, "prev_day_low", None)
                if pdl and (raw_input.current_price < pdl * 1.0005 or raw_input.current_price > pdh * 0.9995):
                    is_important_event = True

            if self.settings.APP_ENV == "testing":
                budget_allowed, budget_reason = True, "ALLOWED_TESTING"
            else:
                budget_allowed, budget_reason = self.request_manager.is_request_allowed(
                    is_important_event=is_important_event,
                    force_refresh=force_refresh,
                )

            if not budget_allowed:
                logger.warning(
                    f"Gemini request blocked by budget manager. Budget reason: {budget_reason}. "
                    f"Change reason was: {change_reason}. Serving cached analysis."
                )
                fallback_res = cached_item[1] if cached_item else self._last_successful_analysis
                if fallback_res is None:
                    fallback_res = self.fallback_provider.generate_analysis(raw_input)

                if budget_reason == "LIMIT_EXCEEDED":
                    fallback_res.config_warning = "AI: DAILY LIMIT REACHED"
                    fallback_res.provider_used = "AI: LIMIT REACHED"
                else:
                    fallback_res.config_warning = f"AI Refresh Cooldown Active ({budget_reason.replace('_', ' ')})"
                return fallback_res

            # 7. Execute live Gemini call
            full_reason = f"{change_reason} | budget={budget_reason}"
            logger.info(f"Gemini API call EXECUTING — reason: {full_reason} | price={raw_input.current_price:.2f}")

            start_t = time.perf_counter()
            try:
                analysis = provider.generate_analysis(raw_input)
                duration_ms = int((time.perf_counter() - start_t) * 1000)
                analysis.generation_duration_ms = duration_ms

                # Record the request with the precise reason
                self.request_manager.record_request(reason=full_reason)

                # Update the change detector snapshot
                self.change_detector.record_analysis(
                    symbol=symbol,
                    signal_direction=current_signal,
                    signal_strength=current_strength,
                    price_at_analysis=raw_input.current_price,
                    m5_trend=m5_trend,
                    m15_trend=m15_trend,
                    h1_trend=h1_trend,
                    d1_trend=d1_trend,
                    rsi_condition=h1_rsi_cond,
                    macd_state=h1_macd_state,
                    candle_timestamp=candle_ts,
                    request_reason=full_reason,
                )

                # Cache results
                self._analysis_cache[market_context] = (now, analysis)
                self._last_successful_analysis = analysis
                return analysis

            except Exception as exc:
                logger.error(f"AI provider '{provider.provider_name}' call failed: {exc}")

                # Graceful fallback: return cached or local rule-based fallback
                if cached_item:
                    fallback_res = cached_item[1]
                elif self._last_successful_analysis:
                    fallback_res = self._last_successful_analysis
                else:
                    fallback_res = self.fallback_provider.generate_analysis(raw_input)

                fallback_res.config_warning = (
                    f"AI Provider '{provider.provider_name}' failed ({exc}). "
                    "Analysis generated by built-in fallback engine."
                )
                fallback_res.provider_used = "AI: FALLBACK"
                fallback_res.is_fallback = True
                return fallback_res


@lru_cache()
def get_ai_service() -> AIMarketAnalysisService:
    """Return singleton instance of AIMarketAnalysisService."""
    return AIMarketAnalysisService()
