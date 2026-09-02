"""
Phase 5 Probability Calibration & No-Trade Research API Endpoints.

Provides read-only access to Phase 5 empirical findings:
- Probability sources inventory & T0 timing audit
- Raw vs Platt vs Isotonic calibration metrics on Train, OOS, and Holdout
- Reliability buckets with Wilson confidence intervals
- Expected Value & Monotonicity reports by probability band
- No-trade / WAIT policy opportunity cost evaluations
- Chronological walk-forward, frozen holdout, bootstrap, and Monte Carlo results

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

from src.research.phase5.audit import audit_probability_sources
from src.research.phase5.calibration import evaluate_probability_calibration
from src.research.phase5.expected_value import evaluate_expected_value_bands
from src.research.phase5.no_trade import evaluate_no_trade_policies
from src.research.phase5.validation import run_phase5_validations
from src.research.phase5.orchestrator import run_full_phase5_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research/phase5", tags=["Phase 5 Probability & No-Trade Research"])


@router.get("/summary", summary="Get Full Phase 5 Research Summary")
def get_phase5_summary(symbol: str = Query("BTC/USD", description="Asset symbol (BTC/USD or XAU/USD)")):
    """Return consolidated Phase 5 calibration and expected value report."""
    try:
        report = run_full_phase5_research(symbol=symbol)
        return {
            "status": "success",
            "research_disclaimer": "Research and diagnostic layer only. Zero production decision impact.",
            "data": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating Phase 5 summary for {symbol}: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc), "symbol": symbol}


@router.get("/audit", summary="Get Probability Sources Audit")
def get_audit():
    """Return inventory and T0 timing audit of all probability sources."""
    try:
        audit = audit_probability_sources()
        return {
            "status": "success",
            "audit": audit.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading probability sources audit: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/calibration", summary="Get Probability Calibration & Reliability Buckets")
def get_calibration(
    symbol: str = Query("BTC/USD", description="Asset symbol"),
    method: str = Query("PLATT_SCALING", description="Calibration method (RAW, PLATT_SCALING, ISOTONIC_REGRESSION)"),
    split: str = Query("OOS", description="Dataset split (TRAIN, OOS, HOLDOUT)"),
):
    """Return calibration metrics and reliability buckets."""
    try:
        metrics = evaluate_probability_calibration(symbol=symbol, method=method, split=split)
        return {
            "status": "success",
            "calibration": metrics.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error evaluating calibration: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/expected-value", summary="Get Expected Value by Probability Band")
def get_expected_value(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return EV, win rate, and profit factor per probability band."""
    try:
        ev_report = evaluate_expected_value_bands(symbol=symbol)
        return {
            "status": "success",
            "expected_value": ev_report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error evaluating EV bands for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/no-trade", summary="Get No-Trade / WAIT Policy Results")
def get_no_trade_policies(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return opportunity cost analysis of candidate no-trade policies."""
    try:
        policies = evaluate_no_trade_policies(symbol=symbol)
        return {
            "status": "success",
            "symbol": symbol,
            "policies": [p.to_dict() for p in policies],
        }
    except Exception as exc:
        logger.error(f"Error evaluating no-trade policies for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/validations", summary="Get Walk-Forward, Holdout, Bootstrap & Monte Carlo")
def get_validations(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return all statistical validation experiments."""
    try:
        vals = run_phase5_validations(symbol=symbol)
        return {
            "status": "success",
            "validations": vals,
        }
    except Exception as exc:
        logger.error(f"Error loading validations for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}
