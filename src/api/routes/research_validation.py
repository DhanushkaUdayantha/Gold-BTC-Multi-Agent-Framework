"""
Research Validation API Endpoints.

Provides read-only statistical validation and empirical research metrics:
- Bootstrap confidence intervals (10,000 resamples)
- Execution stress & slippage/latency degradation
- Probability calibration & reliability buckets
- Monte Carlo downside risk boundaries
- Holdout sample sufficiency milestones

DISCLAIMER: Research and analytical metrics only. Zero influence on production trading decisions.
"""
import logging
from dataclasses import asdict
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

from src.research.statistical_validation.validator import run_full_statistical_validation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research/validation", tags=["Research Validation"])


@router.get("/summary", summary="Get Full Statistical Validation Summary")
def get_validation_summary(symbol: str = Query("BTC/USD", description="Asset symbol (BTC/USD or XAU/USD)")):
    """Return consolidated statistical validation report for the requested asset."""
    try:
        report = run_full_statistical_validation(symbol=symbol)
        return {
            "status": "success",
            "research_disclaimer": "Research and observation layer only. Zero production decision impact.",
            "data": report.to_dict(),
        }
    except Exception as exc:
        logger.error(f"Error generating validation summary for {symbol}: {exc}", exc_info=True)
        return {
            "status": "error",
            "message": str(exc),
            "symbol": symbol,
        }


@router.get("/bootstrap", summary="Get 10,000 Bootstrap Confidence Intervals")
def get_bootstrap_metrics(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return 10,000 bootstrap resample confidence intervals for Expectancy, Total R, and Win Rate."""
    try:
        report = run_full_statistical_validation(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "real_n": report.bootstrap.real_n,
            "bootstrap_resamples": report.bootstrap.bootstrap_resamples,
            "seed": report.bootstrap.seed,
            "expectancy_r": report.bootstrap.expectancy_r,
            "total_r": report.bootstrap.total_r,
            "win_rate_pct": report.bootstrap.win_rate_pct,
            "validation_status": report.bootstrap.status,
        }
    except Exception as exc:
        logger.error(f"Error generating bootstrap metrics for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/stress", summary="Get Execution Stress & Slippage Matrix")
def get_execution_stress(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return slippage (0.00R - 0.20R) and latency (0-2 bar) stress testing matrix."""
    try:
        report = run_full_statistical_validation(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "real_n": report.stress.real_n,
            "baseline": {
                "expectancy_r": report.stress.baseline_expectancy_r,
                "profit_factor": report.stress.baseline_profit_factor,
                "total_r": report.stress.baseline_total_r,
                "win_rate_pct": report.stress.baseline_win_rate_pct,
                "max_drawdown_r": report.stress.baseline_max_drawdown_r,
            },
            "slippage_scenarios": [asdict(s) if hasattr(s, "__dataclass_fields__") else s for s in report.stress.slippage_scenarios],
            "latency_scenarios": [asdict(l) if hasattr(l, "__dataclass_fields__") else l for l in report.stress.latency_scenarios],
            "classification": report.stress.classification,
            "rationale": report.stress.rationale,
        }
    except Exception as exc:
        logger.error(f"Error generating stress metrics for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}


@router.get("/calibration", summary="Get Probability Calibration & Reliability Buckets")
def get_calibration_metrics(symbol: str = Query("BTC/USD", description="Asset symbol")):
    """Return Brier scores, ECE, MCE, and reliability bucket distributions."""
    try:
        report = run_full_statistical_validation(symbol=symbol)
        return {
            "status": "success",
            "symbol": report.symbol,
            "sample_size": report.calibration.sample_size,
            "raw_brier_score": report.calibration.raw_brier_score,
            "calibrated_brier_score": report.calibration.calibrated_brier_score,
            "raw_ece_pct": report.calibration.raw_ece_pct,
            "calibrated_ece_pct": report.calibration.calibrated_ece_pct,
            "max_calibration_error_pct": report.calibration.max_calibration_error_pct,
            "buckets": report.calibration.buckets,
            "calibration_status": report.calibration.calibration_status,
            "assessment_notes": report.calibration.assessment_notes,
        }
    except Exception as exc:
        logger.error(f"Error generating calibration metrics for {symbol}: {exc}")
        return {"status": "error", "message": str(exc)}
