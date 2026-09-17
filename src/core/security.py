"""
Security and authentication dependencies.

Provides constant-time token verification, environment-aware admin protection,
and fail-safe checks for privileged operations (e.g. production gating, demo reset).
"""
import logging
import os
import secrets
from typing import Optional
from fastapi import Header, HTTPException, status
from config.settings import get_settings

logger = logging.getLogger(__name__)


def get_expected_admin_token() -> str:
    """Retrieve the expected admin token securely from environment or settings."""
    token = os.environ.get("ADMIN_AUTH_TOKEN", "").strip()
    if not token:
        token = get_settings().ADMIN_AUTH_TOKEN.strip()
    return token


def verify_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> None:
    """
    Verify administrator authentication token securely.
    Fails closed if token is unconfigured or mismatched.
    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    expected = get_expected_admin_token()
    if not expected:
        logger.error("[Security] ADMIN_AUTH_TOKEN is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication token not configured on server",
        )

    if not x_admin_token or not secrets.compare_digest(
        x_admin_token.encode("utf-8"), expected.encode("utf-8")
    ):
        logger.warning("[Security] Unauthorized access attempt: invalid or missing X-Admin-Token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header",
        )


def verify_demo_reset_auth(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> None:
    """
    Authorization guard for POST /api/v1/decision/trade/reset.
    
    - In production (or when RESET_AUTH_REQUIRED=True):
      Requires valid X-Admin-Token header. Missing/invalid token raises 401.
    - In development/testing (default):
      If X-Admin-Token is supplied, validates it (invalid -> 401).
      If omitted, permits reset for local development convenience with an audit log notice.
    """
    settings = get_settings()
    is_prod_or_enforced = (settings.APP_ENV == "production") or settings.RESET_AUTH_REQUIRED

    if is_prod_or_enforced:
        verify_admin_token(x_admin_token)
    else:
        # Development / Testing mode:
        if x_admin_token is not None:
            # If client explicitly provided a token, validate it
            verify_admin_token(x_admin_token)
        else:
            logger.info("[Security] Demo account reset permitted in non-production mode without admin token.")
