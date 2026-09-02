"""
Phase 6 -> Phase 33 Governance & Research Platform API Endpoints.

Provides read-only access to master governance decisions and research validation outputs:
- Phase 6 -> Phase 33 Master Roadmap Matrix
- Forward Shadow & Outcome Forensics
- Strategy Qualification & Shadow Gating Evaluations
- Execution Stress & Multi-Dimensional Robustness Reports
- Drift, Degradation & Multiple Testing Audits

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

from src.research.governance.engine import run_full_phase6_to_33_governance, build_phase_roadmap_matrix
from src.research.governance.forward_shadow import get_forward_shadow_engine
from src.research.governance.filters_and_strategies import evaluate_research_strategies, evaluate_shadow_gating_policies
from src.research.governance.stress_and_robustness import (
    run_execution_stress_tests,
    run_multidimensional_robustness,
    run_coverage_analysis,
)
from src.research.governance.drift_and_bias import (
    run_drift_and_degradation_audit,
    run_overfitting_and_significance_audit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research/governance", tags=["Phase 6-33 Governance & Research"])


@router.get("/summary", summary="Get Master Governance Decision")
def get_governance_summary(symbol: str = Query("BTC/USD", description="Asset symbol (BTC/USD or XAU/USD)")):
    """Return consolidated governance decision and roadmap status."""
    try:
        decision, roadmap = run_full_phase6_to_33_governance(symbol=symbol)
        return {
            "status": "success",
            "research_disclaimer": "Research and diagnostic layer only. Zero production decision impact.",
            "decision": decision.to_dict(),
            "roadmap": [r.to_dict() for r in roadmap],
        }
    except Exception as exc:
        logger.error(f"Error generating governance summary for {symbol}: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc), "symbol": symbol}


@router.get("/roadmap", summary="Get Phase 6-33 Roadmap Matrix")
def get_roadmap():
    """Return the master phase table from Phase 6 to Phase 33."""
    try:
        matrix = build_phase_roadmap_matrix()
        return {
            "status": "success",
            "total_phases": len(matrix),
            "phases": [p.to_dict() for p in matrix],
        }
    except Exception as exc:
        logger.error(f"Error loading roadmap: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/forward-shadow", summary="Get Forward Shadow Summary")
def get_forward_shadow(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return forward shadow tracking metrics."""
    try:
        engine = get_forward_shadow_engine()
        summary = engine.get_forward_summary(symbol=symbol)
        return {
            "status": "success",
            "forward_shadow": summary.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading forward shadow for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/strategies", summary="Get Strategy Qualification & Shadow Gating")
def get_strategies(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return strategy qualification reports and candidate shadow gating policies."""
    try:
        qual = evaluate_research_strategies(symbol=symbol)
        gating = evaluate_shadow_gating_policies(symbol=symbol)
        return {
            "status": "success",
            "qualification_report": qual.to_dict(),
            "shadow_gating_policies": [g.to_dict() for g in gating],
        }
    except Exception as exc:
        logger.error(f"Error loading strategies for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/stress-test", summary="Get Execution Stress Test Report")
def get_stress_test(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return execution slippage and delay stress test results."""
    try:
        report = run_execution_stress_tests(symbol=symbol)
        return {
            "status": "success",
            "stress_test": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading stress test for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/robustness", summary="Get Multi-Dimensional Robustness Report")
def get_robustness(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return robustness across regimes, sessions, and directions."""
    try:
        report = run_multidimensional_robustness(symbol=symbol)
        return {
            "status": "success",
            "robustness": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading robustness for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/coverage", summary="Get Opportunity & Coverage Analysis")
def get_coverage(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return signal frequency, spacing, and qualification coverage metrics."""
    try:
        report = run_coverage_analysis(symbol=symbol)
        return {
            "status": "success",
            "coverage": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading coverage for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/drift", summary="Get Drift & Degradation Monitoring")
def get_drift(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return distribution drift and rolling performance degradation status."""
    try:
        drift, deg = run_drift_and_degradation_audit(symbol=symbol)
        overfit, mult_test = run_overfitting_and_significance_audit(symbol=symbol)
        return {
            "status": "success",
            "drift_report": drift.to_dict(),
            "degradation_report": deg.to_dict(),
            "overfitting_report": overfit.to_dict(),
            "multiple_testing_report": mult_test.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error loading drift for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get(
    "/btc-shadow-comparison",
    summary="Get BTC Shadow-Mode vs Backtest Comparison Gate Report",
    description=(
        "Returns the pre-registered comparison report evaluating live BTC shadow paper trades "
        "against the baseline backtest forward-shadow metrics (N>=50, Days>=14, EV & WR in 95% CI, LOW_DRIFT). "
        "Strictly read-only for human review. Zero write access to production gating flags."
    ),
)
def get_btc_shadow_comparison():
    """Return pre-registered comparison gate report for human review."""
    try:
        from src.research.governance.shadow_comparison import get_btc_shadow_comparison_gate
        gate = get_btc_shadow_comparison_gate()
        report = gate.evaluate_shadow_confirmation()
        return {
            "status": "success",
            "disclaimer": "Diagnostic comparison for human review only. No automatic flag mutation.",
            "report": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error evaluating BTC shadow comparison: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}


@router.get(
    "/xau-shadow-comparison",
    summary="Get XAU Shadow-Mode vs Backtest Comparison Gate Report",
    description=(
        "Returns the pre-registered comparison report evaluating live XAU shadow paper trades "
        "against the baseline backtest forward-shadow metrics, preserving the N>=50 holdout validation milestone. "
        "Strictly read-only for human review. Zero write access to production gating flags."
    ),
)
def get_xau_shadow_comparison():
    """Return pre-registered XAU comparison gate report for human review."""
    try:
        from src.research.governance.shadow_comparison import get_xau_shadow_comparison_gate
        gate = get_xau_shadow_comparison_gate()
        report = gate.evaluate_shadow_confirmation()
        return {
            "status": "success",
            "disclaimer": "Diagnostic comparison for human review only. No automatic flag mutation.",
            "report": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error evaluating XAU shadow comparison: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}


