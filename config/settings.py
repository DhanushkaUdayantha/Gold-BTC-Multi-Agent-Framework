"""Application configuration and settings management.

Loads environment variables from .env file or environment with type validation.
"""
from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # Application settings
    APP_NAME: str = "Gold AI Trading Analysis"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Security & CORS Settings
    ADMIN_AUTH_TOKEN: str = Field(default="", description="Admin authentication token for privileged endpoints")
    ALLOWED_ORIGINS: str = Field(default="", description="Comma-separated allowed CORS origins for production")
    RATE_LIMITING_ENABLED: bool = Field(default=True, description="Enable API rate limiting")
    RESET_AUTH_REQUIRED: bool = Field(default=False, description="Require admin token for demo reset even in dev")

    # Market Data Provider
    # Options: "goldprice_dev", "yahoo_finance", "hybrid"
    MARKET_DATA_PROVIDER: Literal["goldprice_dev", "yahoo_finance", "hybrid"] = "hybrid"

    # API Credentials & URLs for Market Data
    GOLDPRICE_DEV_API_KEY: str = Field(
        default="",
        description="Optional API key for goldprice.dev. Free tier works for spot price and daily bars."
    )
    GOLDPRICE_DEV_BASE_URL: str = "https://api.goldprice.dev/v1"

    # AI Provider Settings
    # Options: "auto" (uses gemini if key present, else fallback), "gemini", "openai", "fallback"
    AI_PROVIDER: Literal["auto", "gemini", "openai", "fallback"] = "auto"
    AI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        description="Google Gemini API Key"
    )
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    AI_REQUEST_TIMEOUT_SECONDS: float = 45.0
    AI_CACHE_TTL_SECONDS: int = 120

    # Default Instrument
    DEFAULT_SYMBOL: str = "XAU-USD-SPOT"

    # Cache Settings
    PRICE_CACHE_TTL_SECONDS: int = 3
    CANDLE_CACHE_TTL_SECONDS: int = 15

    # HTTP Network Timeout
    HTTP_TIMEOUT_SECONDS: float = 15.0

    # -------------------------------------------------------------------------
    # Decision Engine — Scoring Weights (must sum to 1.0)
    # -------------------------------------------------------------------------
    DECISION_WEIGHT_1H_TREND: float = Field(default=0.25, description="Weight for 1h trend direction")
    DECISION_WEIGHT_15M_TREND: float = Field(default=0.20, description="Weight for 15m trend direction")
    DECISION_WEIGHT_5M_MOMENTUM: float = Field(default=0.15, description="Weight for 5m price momentum")
    DECISION_WEIGHT_1D_TREND: float = Field(default=0.15, description="Weight for 1d macro trend")
    DECISION_WEIGHT_MACD: float = Field(default=0.10, description="Weight for MACD signal confirmation")
    DECISION_WEIGHT_RSI: float = Field(default=0.05, description="Weight for RSI condition")
    DECISION_WEIGHT_EMA: float = Field(default=0.05, description="Weight for EMA structure alignment")
    DECISION_WEIGHT_GEMINI: float = Field(default=0.05, description="Weight for Gemini AI bias")

    # Decision Engine — Risk & Signal Parameters
    DECISION_ATR_MULTIPLIER: float = Field(default=1.5, description="ATR multiplier for stop-loss calculation")
    DECISION_MIN_CONFIDENCE: int = Field(default=65, description="Minimum confidence to produce BUY/SELL (below → WAIT)")
    DECISION_MIN_RR_RATIO: float = Field(default=2.0, description="Minimum risk:reward ratio required for BUY/SELL")
    DECISION_RESISTANCE_PROXIMITY_PCT: float = Field(default=0.15, description="% proximity to resistance that forces WAIT on BUY")
    DECISION_SUPPORT_PROXIMITY_PCT: float = Field(default=0.15, description="% proximity to support that forces WAIT on SELL")
    DECISION_CACHE_TTL_SECONDS: int = Field(
        default=120,
        description=(
            "Cache TTL for decision results in seconds. "
            "Must be >= frontend polling interval (45s) to prevent every poll triggering a rebuild. "
            "120s default means at most ~720 rebuilds/day maximum."
        )
    )

    # Historical Empirical Evidence — Canonical Run Pinning
    HISTORICAL_CANONICAL_RUN_BTC: str = Field(
        default="RUN-BTC-USD-20260831-173607",
        description="Canonical backtest run ID for BTC/USD empirical evidence baseline"
    )
    HISTORICAL_CANONICAL_RUN_XAU: str = Field(
        default="RUN-XAU-USD-20260831-174452",
        description="Canonical backtest run ID for XAU/USD empirical evidence baseline"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
