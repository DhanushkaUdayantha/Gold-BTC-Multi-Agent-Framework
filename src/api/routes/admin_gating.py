"""
Admin Production Gating Control API Endpoints.

Provides authenticated, human-triggered endpoints for managing BTC production gating:
- POST /api/v1/admin/gating/btc         — Enable BTC gating (requires admin auth & confirmation)
- POST /api/v1/admin/gating/btc/disable — Kill switch (requires admin auth, friction-free)
- GET  /api/v1/admin/gating/status      — View gating status and invariants

SECURITY:
- Requires X-Admin-Token header verified with secrets.compare_digest against ADMIN_AUTH_TOKEN.
- Token is NEVER logged, hardcoded, or exposed in API errors.
- Every state change appends to an immutable audit trail.
- XAU gating is hardcoded DISABLED and cannot be modified.

DISCLAIMER: Advisory system control layer only. Zero real broker execution.
"""
import logging
import os
import secrets
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.core.gating_control import get_gating_control

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/gating", tags=["Admin Production Gating"])

_EXPECTED_CONFIRMATION = "CONFIRM_MANUAL_BTC_GATING"


class EnableBTCGatingRequest(BaseModel):
    actor: str = Field(..., description="Identity of the administrator making the change")
    rationale: str = Field(..., description="Business / statistical rationale for enabling gating")
    confirmation: str = Field(..., description=f"Must exactly match '{_EXPECTED_CONFIRMATION}'")


class DisableBTCGatingRequest(BaseModel):
    actor: str = Field(..., description="Identity of the administrator triggering the kill switch")
    rationale: str = Field(..., description="Reason for disabling gating")


def _verify_admin_token(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")) -> None:
    """Verify administrator authentication token securely."""
    expected_token = os.environ.get("ADMIN_AUTH_TOKEN", "").strip()
    if not expected_token:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            expected_token = os.environ.get("ADMIN_AUTH_TOKEN", "").strip()
        except Exception:
            pass

    if not expected_token:
        logger.error("[Admin Gating] ADMIN_AUTH_TOKEN is not configured in the environment or .env.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication token not configured on server",
        )

    if not x_admin_token or not secrets.compare_digest(
        x_admin_token.encode("utf-8"), expected_token.encode("utf-8")
    ):
        logger.warning("[Admin Gating] Unauthorized access attempt to admin gating endpoint.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header",
        )


@router.get("/status", summary="Get Production Gating Status & Invariants")
def get_gating_status():
    """Return the current production gating state and safety invariants."""
    mgr = get_gating_control()
    return {
        "status": "success",
        "gating_status": mgr.get_status(),
    }


@router.post("/btc", summary="Enable BTC Production Gating (Authenticated, Manual-Only)")
def enable_btc_gating(
    req: EnableBTCGatingRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    """
    Manually enable Policy B (Calibrated Prob >= 50%) production gating for BTC/USD.
    Requires valid X-Admin-Token and exact confirmation token.
    """
    _verify_admin_token(x_admin_token)

    if req.confirmation != _EXPECTED_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid confirmation string. Must exactly match '{_EXPECTED_CONFIRMATION}'",
        )

    mgr = get_gating_control()
    audit_entry = mgr.set_btc_gating(
        enable=True,
        actor=req.actor,
        rationale=req.rationale,
    )

    return {
        "status": "success",
        "message": "BTC Production Gating successfully ENABLED",
        "audit_entry": audit_entry.to_dict(),
    }


@router.post("/btc/disable", summary="Emergency Kill-Switch: Disable BTC Production Gating")
def disable_btc_gating(
    req: DisableBTCGatingRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    """
    Emergency kill-switch: immediately disable BTC production gating.
    Requires valid X-Admin-Token (friction-free, no confirmation token needed).
    """
    _verify_admin_token(x_admin_token)

    mgr = get_gating_control()
    audit_entry = mgr.set_btc_gating(
        enable=False,
        actor=req.actor,
        rationale=req.rationale,
    )

    return {
        "status": "success",
        "message": "BTC Production Gating successfully DISABLED",
        "audit_entry": audit_entry.to_dict(),
    }
