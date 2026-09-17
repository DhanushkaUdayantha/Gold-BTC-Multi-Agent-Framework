"""
Lightweight in-memory rate limiter for FastAPI endpoints.

Provides deterministic sliding-window rate limiting per client identifier (IP address)
with standard HTTP 429 Too Many Requests and Retry-After headers.
Configurable via settings.RATE_LIMITING_ENABLED.
"""
import logging
import time
import threading
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status
from config.settings import get_settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, default_limit: int = 120, window_seconds: int = 60) -> None:
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> Tuple[bool, int]:
        """
        Check if request under key is allowed.
        Returns (is_allowed, retry_after_seconds).
        """
        max_limit = limit if limit is not None else self.default_limit
        win = window if window is not None else self.window_seconds
        now = time.time()
        cutoff = now - win

        with self._lock:
            timestamps = self._requests.get(key, [])
            # Prune expired timestamps
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_limit:
                # Oldest timestamp determines when a slot frees up
                retry_after = max(1, int(valid_timestamps[0] + win - now))
                self._requests[key] = valid_timestamps
                return False, retry_after

            valid_timestamps.append(now)
            self._requests[key] = valid_timestamps
            return True, 0

    def reset(self) -> None:
        """Clear all rate limit state (useful for tests)."""
        with self._lock:
            self._requests.clear()


_global_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = InMemoryRateLimiter()
    return _global_rate_limiter


def check_rate_limit(
    request: Request,
    limit: int = 120,
    window_seconds: int = 60,
    scope: str = "default",
) -> None:
    """
    FastAPI dependency function to enforce rate limits.
    Raises HTTP 429 if rate limit is exceeded.
    """
    settings = get_settings()
    if not settings.RATE_LIMITING_ENABLED:
        return

    # Extract client identifier (X-Forwarded-For or client.host)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"

    key = f"{scope}:{client_ip}"
    allowed, retry_after = get_rate_limiter().is_allowed(
        key=key, limit=limit, window=window_seconds
    )

    if not allowed:
        logger.warning(
            f"[RateLimit] Client {client_ip} exceeded limit ({limit}/{window_seconds}s) on {request.url.path}."
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
