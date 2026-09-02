"""GoldPrice.dev API Provider Implementation with 429 rate-limit handling."""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import requests

from src.models.market_data import PriceQuote, OHLCVCandle, CandleHistory, Timeframe
from src.services.base_provider import BaseMarketDataProvider

logger = logging.getLogger(__name__)

# Exponential backoff constants for 429 handling
_429_INITIAL_BACKOFF_SECONDS: float = 60.0
_429_MAX_BACKOFF_SECONDS: float = 900.0


class GoldPriceDevError(Exception):
    """Base exception for GoldPrice.dev API errors."""
    pass


class GoldPriceDevPlanGatedError(GoldPriceDevError):
    """Raised when an interval requires an upgraded Pro subscription plan."""
    pass


class GoldPriceDevRateLimitError(GoldPriceDevError):
    """Raised when GoldPrice.dev returns 429 Too Many Requests."""
    pass


class GoldPriceDevProvider(BaseMarketDataProvider):
    """Market data provider connecting to api.goldprice.dev with 429 backoff."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.goldprice.dev/v1",
        timeout: float = 15.0,
    ):
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # 429 rate-limit state — shared across price + candle calls
        self._rate_limit_until: float = 0.0        # epoch seconds
        self._current_backoff: float = _429_INITIAL_BACKOFF_SECONDS
        self._rate_limit_logged: bool = False       # suppress repeated log spam

    @property
    def provider_name(self) -> str:
        return "GoldPrice.dev"

    def _is_rate_limited(self) -> bool:
        """Return True if we are currently in a 429 backoff window."""
        if time.time() < self._rate_limit_until:
            return True
        # Cooldown expired — reset log-once flag so next 429 is logged again
        if self._rate_limit_logged and time.time() >= self._rate_limit_until:
            self._rate_limit_logged = False
        return False

    def _handle_429(self) -> None:
        """Record a 429 hit, apply exponential backoff, log once."""
        self._rate_limit_until = time.time() + self._current_backoff
        recovery_dt = datetime.fromtimestamp(self._rate_limit_until, tz=timezone.utc).strftime("%H:%M:%S UTC")

        if not self._rate_limit_logged:
            logger.warning(
                f"GoldPrice.dev returned 429 Too Many Requests. "
                f"Activating cooldown for {int(self._current_backoff)}s "
                f"(recovery at {recovery_dt}). Routing to Yahoo Finance fallback."
            )
            self._rate_limit_logged = True

        # Exponential back-off: double the window up to max
        self._current_backoff = min(self._current_backoff * 2, _429_MAX_BACKOFF_SECONDS)

    def _reset_backoff(self) -> None:
        """Reset backoff after a successful call."""
        self._current_backoff = _429_INITIAL_BACKOFF_SECONDS
        self._rate_limit_logged = False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "GoldAITradingApp/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_live_price(self, symbol: str = "XAU-USD-SPOT") -> PriceQuote:
        """Fetch current live price quote from GoldPrice.dev."""
        if self._is_rate_limited():
            remaining = int(self._rate_limit_until - time.time())
            raise GoldPriceDevRateLimitError(
                f"GoldPrice.dev is rate-limited. Cooldown expires in ~{remaining}s."
            )

        url = f"{self.base_url}/prices"
        params = {"symbol": symbol}

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code == 429:
                self._handle_429()
                raise GoldPriceDevRateLimitError("GoldPrice.dev rate limited (429)")

            response.raise_for_status()
            data = response.json()

            symbols_list = data.get("symbols", [])
            if not symbols_list:
                raise GoldPriceDevError(f"No price data found for symbol: {symbol}")

            item = symbols_list[0]
            price = float(item.get("price", 0.0))
            bid = float(item["bid"]) if item.get("bid") is not None else None
            ask = float(item["ask"]) if item.get("ask") is not None else None
            spread = round(ask - bid, 4) if (ask is not None and bid is not None) else None

            self._reset_backoff()

            return PriceQuote(
                symbol=item.get("symbol", symbol),
                price=price,
                bid=bid,
                ask=ask,
                spread=spread,
                currency=item.get("quote_currency", "USD"),
                unit=item.get("unit", "troy_ounce"),
                timestamp=item.get("computed_at", datetime.now(timezone.utc).isoformat()),
                provider=self.provider_name,
                is_stale=item.get("is_stale", False),
            )

        except GoldPriceDevRateLimitError:
            raise
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "Unknown"
            if status_code == 429:
                self._handle_429()
                raise GoldPriceDevRateLimitError("GoldPrice.dev rate limited (429)") from exc
            logger.error(f"GoldPrice.dev HTTP error ({status_code}): {exc}")
            raise GoldPriceDevError(f"GoldPrice.dev HTTP error {status_code}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"GoldPrice.dev connection error: {exc}")
            raise GoldPriceDevError(f"Failed to connect to GoldPrice.dev: {exc}") from exc

    def get_candles(
        self,
        symbol: str = "XAU-USD-SPOT",
        timeframe: Timeframe = Timeframe.D1,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> CandleHistory:
        """Fetch historical OHLC bars from GoldPrice.dev."""
        if self._is_rate_limited():
            remaining = int(self._rate_limit_until - time.time())
            raise GoldPriceDevRateLimitError(
                f"GoldPrice.dev is rate-limited. Cooldown expires in ~{remaining}s."
            )

        url = f"{self.base_url}/bars"
        now = datetime.now(timezone.utc)

        if not end_date:
            end_date = now.strftime("%Y-%m-%d")
        if not start_date:
            days_back = max(30, limit * 2)
            start_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "symbol": symbol,
            "interval": timeframe.value,
            "from": start_date,
            "to": end_date,
            "limit": limit,
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code == 429:
                self._handle_429()
                raise GoldPriceDevRateLimitError("GoldPrice.dev rate limited (429)")

            if response.status_code == 403:
                error_data = response.json() if response.text else {}
                msg = error_data.get("message", "Interval requires a Pro tier subscription.")
                logger.warning(f"GoldPrice.dev plan gated: {msg}")
                raise GoldPriceDevPlanGatedError(msg)

            response.raise_for_status()
            data = response.json()

            raw_bars = data.get("bars", [])
            candles = []

            for bar in raw_bars:
                candle = OHLCVCandle(
                    timestamp=bar.get("bar_start", ""),
                    open=float(bar.get("open", 0.0)),
                    high=float(bar.get("high", 0.0)),
                    low=float(bar.get("low", 0.0)),
                    close=float(bar.get("close", 0.0)),
                    volume=float(bar["volume"]) if bar.get("volume") is not None else None,
                    is_closed=bar.get("is_closed", True),
                )
                candles.append(candle)

            candles.sort(key=lambda c: c.timestamp)
            self._reset_backoff()

            return CandleHistory(
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles),
                candles=candles,
                provider=self.provider_name,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )

        except (GoldPriceDevRateLimitError, GoldPriceDevPlanGatedError):
            raise
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "Unknown"
            if status_code == 429:
                self._handle_429()
                raise GoldPriceDevRateLimitError("GoldPrice.dev rate limited (429)") from exc
            logger.error(f"GoldPrice.dev candles HTTP error ({status_code}): {exc}")
            raise GoldPriceDevError(f"GoldPrice.dev HTTP error {status_code}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"GoldPrice.dev candles error: {exc}")
            raise GoldPriceDevError(f"Failed to fetch candles from GoldPrice.dev: {exc}") from exc

    def is_healthy(self) -> bool:
        """Verify API connectivity — returns False immediately if rate-limited."""
        if self._is_rate_limited():
            return False
        # Cache health status for 60 seconds to prevent polling overhead
        now = time.time()
        if hasattr(self, "_last_health_check_time") and now - self._last_health_check_time < 60.0:
            return self._last_health_status
        try:
            quote = self.get_live_price("XAU-USD-SPOT")
            self._last_health_status = quote.price > 0
        except Exception:
            self._last_health_status = False
        self._last_health_check_time = now
        return self._last_health_status
