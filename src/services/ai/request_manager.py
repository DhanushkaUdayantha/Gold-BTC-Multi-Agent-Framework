"""Centralized request manager for tracking and restricting Gemini API consumption."""
import os
import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# File path for storing state, next to paper_trading.json
_USAGE_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
    "gemini_usage.json"
)

DAILY_LIMIT = 1500
SAFETY_RESERVE = 100
USABLE_BUDGET = DAILY_LIMIT - SAFETY_RESERVE  # 1400

class GeminiRequestManager:
    """Intelligently tracks and budgets daily Gemini API calls.

    Args:
        testing_mode: When True, all requests are unconditionally allowed and
                      no file I/O is performed.  Pass True in unit tests that
                      instantiate Settings directly (without APP_ENV='testing').
    """

    def __init__(self, testing_mode: bool = False):
        self._testing_mode = testing_mode
        if not testing_mode:
            self._load_usage()
        else:
            self.state = {}


    def _load_usage(self):
        """Load usage state from disk or initialize fresh if date changed."""
        now_date = datetime.now(timezone.utc).date().isoformat()
        
        default_state = {
            "date": now_date,
            "requests_used_today": 0,
            "requests_remaining_today": USABLE_BUDGET,
            "last_ai_request_time": 0.0,
            "next_allowed_ai_request_time": 0.0,
        }

        if not os.path.exists(_USAGE_FILE_PATH):
            self.state = default_state
            self._save_usage()
            return

        try:
            with open(_USAGE_FILE_PATH, "r") as f:
                data = json.load(f)
            
            # Check calendar day transition
            if data.get("date") != now_date:
                logger.info("Calendar day changed. Resetting Gemini request counter.")
                self.state = default_state
                self._save_usage()
            else:
                self.state = data
                # Keep remaining requests synchronized
                self.state["requests_remaining_today"] = max(
                    0, USABLE_BUDGET - self.state.get("requests_used_today", 0)
                )
        except Exception as exc:
            logger.error(f"Failed to read gemini_usage.json: {exc}")
            self.state = default_state

    def _save_usage(self):
        """Persist current usage state to disk."""
        try:
            with open(_USAGE_FILE_PATH, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to write gemini_usage.json: {exc}")

    def get_adaptive_cooldown(self) -> float:
        """Calculate minimum request interval based on budget remaining."""
        remaining = self.state.get("requests_remaining_today", USABLE_BUDGET)
        
        # Adaptive cooldown scaling optimized for responsive live dashboard
        if remaining > 1000:
            return 25.0  # 25 seconds
        elif remaining > 500:
            return 45.0  # 45 seconds
        elif remaining > 100:
            return 90.0  # 1.5 minutes
        elif remaining > 0:
            return 180.0  # 3 minutes
        else:
            return 86400.0  # 24 hours (blocked)

    def is_request_allowed(
        self, is_important_event: bool = False, force_refresh: bool = False
    ) -> tuple[bool, str]:
        """
        Check if we can request Gemini under rate limiting, cooldowns, and daily budget.
        Returns (is_allowed, reason_code).
        """
        # Instance-level testing bypass (no file I/O, always allowed)
        if self._testing_mode:
            return True, "ALLOWED_TESTING"

        # Global APP_ENV bypass for the main application singleton
        from config.settings import get_settings
        if get_settings().APP_ENV == "testing":
            return True, "ALLOWED_TESTING"

        # Reload state to ensure multi-process concurrency safety
        self._load_usage()

        remaining = self.state.get("requests_remaining_today", 0)
        if remaining <= 0:
            return False, "LIMIT_EXCEEDED"

        now = time.time()
        last_time = self.state.get("last_ai_request_time", 0.0)
        elapsed = now - last_time

        # Force refresh (user clicked REFRESH button) — allow immediately with 1s anti-spam guard
        if force_refresh:
            if elapsed >= 1.0 or last_time == 0.0:
                return True, "ALLOWED_FORCE_REFRESH"
            else:
                return False, "SAFETY_COOLDOWN"

        # Important events override standard cooldowns, but keep a 10s safety guard
        if is_important_event:
            if elapsed >= 10.0:
                return True, "ALLOWED_IMPORTANT"
            else:
                return False, "SAFETY_COOLDOWN"

        # Check standard adaptive cooldown
        cooldown = self.get_adaptive_cooldown()
        if elapsed >= cooldown:
            return True, "ALLOWED_NORMAL"

        return False, "COOLDOWN_ACTIVE"

    def record_request(self, reason: str = "unspecified"):
        """Increment count, update timestamps, record reason, and save state."""
        if self._testing_mode:
            return  # no-op in testing

        self._load_usage()  # load fresh first
        self.state["requests_used_today"] += 1
        self.state["requests_remaining_today"] = max(
            0, USABLE_BUDGET - self.state["requests_used_today"]
        )
        now = time.time()
        self.state["last_ai_request_time"] = now
        self.state["last_request_reason"] = reason

        # Next allowed is based on the updated cooldown
        cooldown = self.get_adaptive_cooldown()
        self.state["next_allowed_ai_request_time"] = now + cooldown

        self._save_usage()
        logger.info(
            f"Gemini API request recorded. Reason: '{reason}'. "
            f"Used today: {self.state['requests_used_today']}, "
            f"Remaining today: {self.state['requests_remaining_today']}."
        )

    def get_stats(self) -> dict:
        """Return usage stats dict for the frontend/API endpoints."""
        self._load_usage()
        return {
            "requests_used_today": self.state.get("requests_used_today", 0),
            "requests_remaining_today": self.state.get("requests_remaining_today", USABLE_BUDGET),
            "last_ai_request_time": self.state.get("last_ai_request_time", 0.0),
            "next_allowed_ai_request_time": self.state.get("next_allowed_ai_request_time", 0.0),
            "last_request_reason": self.state.get("last_request_reason", "none"),
            "daily_limit": DAILY_LIMIT,
            "usable_daily_budget": USABLE_BUDGET,
        }

