"""
Feature Importance, Ablation & Signal Quality Research API Endpoints.

Provides read-only access to Phase 4 diagnostic and empirical research results:
- Feature inventory and T0 timing audit results
- Classical and ML feature importance with fold stability metrics
- Single-feature and candidate filter ablation evaluations
- Redundancy, missingness, and distribution stability reports
- Registered research experiments

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

from src.research.feature_ablation.validator import run_full_phase4_analysis
from src.research.feature_ablation.inventory import build_feature_inventory, audit_feature_timing
from src.research.feature_ablation.registry import get_experiment_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research/feature-ablation", tags=["Feature Importance & Ablation"])


@router.get("/summary", summary="Get Full Phase 4 Forensic Summary")
def get_phase4_summary(symbol: str = Query("BTC/USD", description="Asset symbol (BTC/USD or XAU/USD)")):
    """Return consolidated Phase 4 feature importance and ablation report."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "research_disclaimer": "Research and diagnostic layer only. Zero production decision impact.",
            "data": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating Phase 4 summary for {symbol}: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc), "symbol": symbol}


@router.get("/inventory", summary="Get Repository Feature Inventory & T0 Timing Audit")
def get_inventory():
    """Return complete feature inventory and point-in-time timing audit."""
    try:
        inventory = build_feature_inventory()
        timing = audit_feature_timing()
        return {
            "status": "success",
            "inventory": inventory.to_dict(),
            "timing_audit": timing,
        }
    except Exception as exc:
        logger.error(f"Error loading feature inventory: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/importance", summary="Get Classical & ML Feature Importance")
def get_feature_importance(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return feature importance scores across 4 temporal folds."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "classical_importance": [f.to_dict() for f in report.classical_importance],
            "ml_importance": [m.to_dict() for m in report.ml_importance],
        }
    except Exception as exc:
        logger.error(f"Error loading importance for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/ablation", summary="Get Single-Feature Ablation Results")
def get_ablation_results(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return single-feature ablation deltas on Train, OOS, and Holdout."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "ablations": [a.to_dict() for a in report.feature_ablations],
        }
    except Exception as exc:
        logger.error(f"Error loading ablations for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/filters", summary="Get Candidate Filter Research Results")
def get_filter_research(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return candidate filter research results and metrics."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "filter_research": [flt.to_dict() for flt in report.filter_research],
        }
    except Exception as exc:
        logger.error(f"Error loading filter research for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/stability", summary="Get Feature Stability & Drift Reports")
def get_stability_reports(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return fold stability, missingness, and distribution drift analyses."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "stability": report.stability.to_dict(),
            "missingness": report.missingness.to_dict(),
            "distribution_stability": report.distribution_stability.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading stability for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/redundancy", summary="Get Collinearity & Redundancy Analysis")
def get_redundancy_reports(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return correlation pairs, VIF scores, and redundancy conclusions."""
    try:
        report = run_full_phase4_analysis(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "redundancy": report.redundancy.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading redundancy for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/registry", summary="Get Phase 4 Experiment Registry")
def get_registry():
    """Return the registry of all Phase 4 experiments."""
    try:
        reg = get_experiment_registry()
        return {
            "status": "success",
            "registry": reg.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading experiment registry: {exc}")
        return {"status": "error", "message": str(exc)}
