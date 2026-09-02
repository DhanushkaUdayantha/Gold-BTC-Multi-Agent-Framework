"""OpenAI-compatible AI Provider for Market Analysis."""
import logging
import json
from typing import Optional, Dict, Any
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


class OpenAIAIError(Exception):
    """Base exception for OpenAI provider errors."""
    pass


class OpenAIAIProvider(BaseAIProvider):
    """AI analysis provider connecting to OpenAI or compatible API endpoints."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 25.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return f"OpenAI ({self.model_name})"

    def generate_analysis(self, input_data: MultiTimeframeTechnicalInput) -> AIAnalysisResponse:
        """Call OpenAI Chat Completions API with JSON mode."""
        if not self.api_key:
            raise OpenAIAIError("OpenAI API key is not configured.")

        system_prompt = AIAggregator.build_system_prompt()
        user_prompt = AIAggregator.build_user_prompt(input_data)

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            res_data = response.json()

            choices = res_data.get("choices", [])
            if not choices:
                raise OpenAIAIError("No response choices returned by OpenAI.")

            content_text = choices[0].get("message", {}).get("content", "")
            if not content_text:
                raise OpenAIAIError("Empty text payload from OpenAI.")

            parsed_json = json.loads(content_text)

            market_cond = MarketCondition(parsed_json.get("market_condition", "UNCLEAR").upper())
            overall_bias = OverallBias(parsed_json.get("overall_bias", "NEUTRAL").upper())
            risk_level = RiskLevel(parsed_json.get("risk_level", "MEDIUM").upper())
            confidence = int(parsed_json.get("confidence", 50))
            confidence = max(0, min(100, confidence))

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
                provider_used=self.provider_name,
                is_fallback=False,
                config_warning=None,
            )

        except requests.exceptions.Timeout as exc:
            logger.error(f"OpenAI request timed out: {exc}")
            raise OpenAIAIError(f"OpenAI API timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"OpenAI network error: {exc}")
            raise OpenAIAIError(f"OpenAI network error: {exc}") from exc
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.error(f"OpenAI response parsing error: {exc}")
            raise OpenAIAIError(f"Invalid JSON from OpenAI: {exc}") from exc
