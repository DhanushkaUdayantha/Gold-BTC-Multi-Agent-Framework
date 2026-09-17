"""Google Gemini AI Provider for Market Analysis."""
import logging
import json
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import requests

from src.models.ai_analysis import (
    MultiTimeframeTechnicalInput,
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    RiskLevel,
)
from src.services.ai.base_provider import BaseAIProvider
from src.services.ai.ai_aggregator import AIAggregator

logger = logging.getLogger(__name__)


class GeminiAIError(Exception):
    """Base exception for Gemini provider errors."""
    pass


class GeminiAIProvider(BaseAIProvider):
    """AI analysis provider powered by Google Gemini API."""

    CANDIDATE_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite-preview",
        "gemma-4-31b-it",
        "gemma-4-26b-a4b-it",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
    ]

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-flash-lite",
        timeout: float = 45.0,
    ):
        self.api_key = api_key
        clean_model = model_name.replace("models/", "")
        self.model_name = clean_model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model_name})"

    def _extract_json_text(self, text: str) -> str:
        """Strip markdown code blocks or whitespace from JSON output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def generate_analysis(self, input_data: MultiTimeframeTechnicalInput) -> AIAnalysisResponse:
        """Call Gemini API with structured JSON output and validate against response schema."""
        if not self.api_key:
            raise GeminiAIError("Gemini API key is not configured.")

        system_prompt = AIAggregator.build_system_prompt()
        user_prompt = AIAggregator.build_user_prompt(input_data)

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "topP": 0.95,
            }
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        # Build model attempt list starting with user-configured model
        models_to_try = [self.model_name] + [m for m in self.CANDIDATE_MODELS if m != self.model_name]
        last_exception: Optional[Exception] = None

        for model in models_to_try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                logger.debug(f"Attempting Gemini generation with model: {model}")
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if not response.ok:
                    err_msg = f"HTTP {response.status_code}: {response.text[:300]}"
                    if response.status_code in (404, 503, 429) and model != models_to_try[-1]:
                        logger.warning(f"Gemini model '{model}' failed ({err_msg}). Trying next candidate...")
                        last_exception = GeminiAIError(f"Model '{model}' {err_msg}")
                        continue
                    else:
                        logger.error(f"Gemini API request failed for '{model}' ({err_msg})")
                        response.raise_for_status()

                res_data = response.json()

                candidates = res_data.get("candidates", [])
                if not candidates:
                    raise GeminiAIError(f"No response candidates returned by Gemini ({res_data}).")

                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not content_text:
                    raise GeminiAIError(f"Empty text payload in Gemini candidate response ({candidates[0]}).")

                cleaned_json_text = self._extract_json_text(content_text)
                parsed_json = json.loads(cleaned_json_text)

                # Validate enums and required fields
                market_cond = MarketCondition(parsed_json.get("market_condition", "UNCLEAR").upper())
                overall_bias = OverallBias(parsed_json.get("overall_bias", "NEUTRAL").upper())
                risk_level = RiskLevel(parsed_json.get("risk_level", "MEDIUM").upper())
                confidence = int(parsed_json.get("confidence", 50))
                confidence = max(0, min(100, confidence))

                # Update active model name if fallback succeeded
                self.model_name = model

                return AIAnalysisResponse(
                    symbol=parsed_json.get("symbol", input_data.symbol),
                    analysis_timestamp=datetime.now(timezone.utc).isoformat(),
                    market_condition=market_cond,
                    overall_bias=overall_bias,
                    confidence=confidence,
                    timeframe_analysis=parsed_json.get("timeframe_analysis", {}),
                    key_bullish_factors=parsed_json.get("key_bullish_factors", []),
                    key_bearish_factors=parsed_json.get("key_bearish_factors", []),
                    key_support=[float(s) for s in parsed_json.get("key_support", [])],
                    key_resistance=[float(r) for r in parsed_json.get("key_resistance", [])],
                    risk_level=risk_level,
                    summary=parsed_json.get("summary", "Analysis completed."),
                    provider_used=f"Google Gemini ({model})",
                    is_fallback=False,
                    config_warning=None,
                )

            except requests.exceptions.Timeout as exc:
                logger.warning(f"Gemini model '{model}' timed out after {self.timeout}s.")
                last_exception = exc
                continue
            except requests.exceptions.RequestException as exc:
                err_text = ""
                if hasattr(exc, "response") and exc.response is not None:
                    err_text = f" - Response: {exc.response.text[:300]}"
                logger.warning(f"Gemini model '{model}' request error: {exc}{err_text}")
                last_exception = exc
                continue
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                logger.error(f"Gemini response parsing error on model '{model}': {exc}")
                raise GeminiAIError(f"Invalid structured JSON response from Gemini: {exc}") from exc

        raise GeminiAIError(f"All Gemini model attempts failed: {last_exception}")
