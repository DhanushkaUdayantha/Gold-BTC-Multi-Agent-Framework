"""
Failure, Winner, and Drawdown Forensic Analysis API Endpoints.

Provides read-only access to Phase 3 diagnostic and empirical research forensics:
- Winner & Loser deep empirical profiles
- Deterministic failure taxonomy breakdowns
- Missed winner & opportunity cost metrics
- Drawdown decomposition & recovery statistics
- Serial correlation & loss/winner clustering
- Multi-dimensional segmentation across regimes, sessions, directions, and confluence

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

from src.research.failure_analysis.validator import run_full_failure_forensic_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research/failure-analysis", tags=["Failure Analysis"])


@router.get("/summary", summary="Get Full Failure & Winner Forensic Summary")
def get_forensic_summary(symbol: str = Query("BTC/USD", description="Asset symbol (BTC/USD or XAU/USD)")):
    """Return consolidated forensic report for the requested asset."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "research_disclaimer": "Research and diagnostic layer only. Zero production decision impact.",
            "data": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating forensic summary for {symbol}: {exc}", exc_info=True)
        return {
            "status": "error",
            "message": str(exc),
            "symbol": symbol,
        }


@router.get("/winners", summary="Get Winner Forensic Profile")
def get_winner_profile(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return winner empirical profile including MFE/MAE, duration, and success reasons."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "winners": report.winners.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating winner profile for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/losers", summary="Get Loser Forensic Profile")
def get_loser_profile(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return loser empirical profile including MAE/MFE, duration, and failure taxonomy."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "losers": report.losers.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating loser profile for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/missed-winners", summary="Get Missed Opportunity Analysis")
def get_missed_winners(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return missed winner counts, potential R missed, and net opportunity cost."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "missed_winners": report.missed_winners.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating missed winners for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/drawdown", summary="Get Drawdown Decomposition")
def get_drawdown_decomposition(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return peak-to-trough drawdown episodes, recovery durations, and regime/session contributions."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "drawdown": report.drawdown.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating drawdown report for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/clustering", summary="Get Loss & Winner Streak Clustering")
def get_streak_clustering(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return streak distributions, autocorrelation lag-1, and rolling performance decay."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "clustering": report.clustering.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating clustering report for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/segments", summary="Get Multi-Dimensional Segmentation")
def get_segmentation_breakdown(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return performance segmented across regimes, sessions, directions, and confluence."""
    try:
        report = run_full_failure_forensic_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "segments": report.segments.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating segment forensics for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}
