"""
REST API routes for the Smart Money / OTE Strategy.

GET /api/v1/ote         — Full 5-step OTE analysis + signal + paper trading stats
GET /api/v1/ote/status  — Lightweight 5-step status check only

DISCLAIMER: All outputs are advisory and paper-trading only.
No real trades are executed. No broker connections are made.
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from src.models.ote_analysis import OTESignal
from src.services.ote_service import get_ote_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ote", tags=["OTE Smart Money Strategy"])


@router.get(
    "",
    response_model=OTESignal,
    summary="Smart Money / OTE Advisory Signal",
    description=(
        "Runs the full 5-step Smart Money / ICT OTE (Optimal Trade Entry) strategy for XAU/USD:\n\n"
        "1. **Trend (1H)** — EMA 20/50/200 structure\n"
        "2. **Liquidity (1D/1H)** — Previous Day High/Low sweep\n"
        "3. **MSS (15m)** — Market Structure Shift after liquidity event\n"
        "4. **Fibonacci (15m)** — 0.618–0.786 OTE retracement zone\n"
        "5. **FVG (5m)** — Fair Value Gap inside OTE zone\n\n"
        "Only generates BUY/SELL during London (07:00–10:00 UTC) or New York (13:00–16:00 UTC) sessions. "
        "**Advisory + paper-trading only. No real orders are placed.**"
    ),
)
def get_ote_signal(
    force_refresh: bool = Query(
        default=False,
        description="Bypass the 60-second cache and run a fresh OTE analysis",
    )
):
    try:
        svc = get_ote_service()
        return svc.get_signal(force_refresh=force_refresh)
    except Exception as exc:
        logger.error(f"OTE signal endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OTE strategy error: {str(exc)}")


@router.get(
    "/status",
    summary="OTE 5-Step Status Check",
    description="Returns only the 5-step execution status and session information (lightweight, no paper trading update).",
)
def get_ote_status():
    """Quick 5-step status without triggering a paper trade check."""
    try:
        svc = get_ote_service()
        signal = svc.get_signal()
        return {
            "signal": signal.signal.value,
            "confidence": signal.confidence,
            "setup_grade": signal.setup_grade,
            "steps_passed": signal.steps_passed,
            "steps_detail": signal.steps_detail,
            "session": {
                "active": signal.session.active_session.value,
                "is_open": signal.session.is_open,
                "next_session": signal.session.next_session.value if signal.session.next_session else None,
                "next_opens_in_minutes": signal.session.next_session_opens_in_minutes,
                "current_time_utc": signal.session.current_time_utc,
            },
            "timestamp": signal.timestamp,
        }
    except Exception as exc:
        logger.error(f"OTE status endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OTE status error: {str(exc)}")
