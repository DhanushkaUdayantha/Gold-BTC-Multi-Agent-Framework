"""
Performance API Routes — Empirical Backtesting & Probability Calibration.

Endpoints:
  GET /api/v1/performance                     → PerformanceReport
  GET /api/v1/performance/signals             → paginated list of SignalRecord
  GET /api/v1/performance/calibration         → CalibrationResult only
  GET /api/v1/performance/signal/{signal_id}  → single SignalRecord

All routes are read-only. No signal records are created or modified here.
Signal recording happens automatically via DecisionService.

DISCLAIMER: Advisory analytical signals only. No real trades.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.services.signal_repository import get_signal_repository
from src.services.performance_engine import get_performance_engine
from src.services.probability_calibrator import get_probability_calibrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance", tags=["Performance"])


def _filter_records_by_symbol(records: List[Any], symbol: Optional[str]) -> List[Any]:
    if not symbol:
        return records
    sym_u = symbol.upper()
    is_btc = "BTC" in sym_u
    is_xau = "XAU" in sym_u or "GOLD" in sym_u
    if is_btc:
        return [r for r in records if "BTC" in str(getattr(r, "symbol", "")).upper()]
    elif is_xau:
        return [r for r in records if "XAU" in str(getattr(r, "symbol", "")).upper() or "GOLD" in str(getattr(r, "symbol", "")).upper()]
    return [r for r in records if str(getattr(r, "symbol", "")).upper() == sym_u]


# ---------------------------------------------------------------------------
# Full performance report
# ---------------------------------------------------------------------------

@router.get("", summary="Full empirical performance report")
def get_performance_report(
    current_score: Optional[int] = Query(
        default=None,
        ge=0, le=100,
        description="Optional current confluence score (0–100) for calibrated probability lookup",
    ),
    symbol: Optional[str] = Query(
        default=None,
        description="Optional asset symbol filter (e.g. BTC-USD, XAU-USD-SPOT)",
    ),
) -> Dict[str, Any]:
    """
    Returns the full empirical performance report including:
    - Overall win rate, expectancy, profit factor (from completed signals only)
    - Per confluence-score-band statistics
    - Per-strategy/contributor statistics
    - Gemini AI performance analysis and ablation
    - Probability calibration result

    IMPORTANT: Confluence score and calibrated probability are always shown separately.
    Calibrated probability is N/A when fewer than 50 completed signals exist.
    """
    try:
        repo = get_signal_repository()
        engine = get_performance_engine()
        calibrator = get_probability_calibrator()

        all_records = _filter_records_by_symbol(repo.get_all(), symbol)
        completed = _filter_records_by_symbol(repo.get_all_completed(), symbol)

        # Compute calibration first (so it can feed into report)
        calibration = calibrator.calibrate(completed, current_score=current_score)

        report = engine.compute_report(all_records, calibration_result=calibration)

        return {
            "status": "ok",
            "report": report.model_dump(),
        }
    except Exception as exc:
        logger.error(f"Performance report error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Performance report error: {str(exc)}")


# ---------------------------------------------------------------------------
# Signal list (paginated)
# ---------------------------------------------------------------------------

@router.get("/signals", summary="List recorded signals (paginated)")
def list_signals(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Signals per page"),
    symbol: Optional[str] = Query(default=None, description="Filter by asset symbol"),
    direction: Optional[str] = Query(default=None, description="Filter by BUY or SELL"),
    outcome: Optional[str] = Query(
        default=None,
        description="Filter by outcome: WIN | LOSS | BREAKEVEN | EXPIRED | INVALID | OPEN",
    ),
    score_band: Optional[str] = Query(
        default=None,
        description="Filter by score band: 0-49 | 50-59 | 60-69 | 70-79 | 80-89 | 90-100",
    ),
) -> Dict[str, Any]:
    """
    Returns a paginated list of signal records with optional filters.
    Records are returned most-recent first.
    """
    try:
        repo = get_signal_repository()
        all_records = _filter_records_by_symbol(repo.get_all(), symbol)

        # Sort newest first
        all_records.sort(key=lambda r: r.signal_timestamp or "", reverse=True)

        # Apply filters
        if direction:
            direction = direction.upper()
            all_records = [r for r in all_records if r.direction == direction]

        if outcome:
            outcome = outcome.upper()
            all_records = [
                r for r in all_records
                if r.outcome and r.outcome.outcome == outcome
            ]

        if score_band:
            all_records = [r for r in all_records if r.score_band == score_band]

        # Pagination
        total = len(all_records)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = all_records[start:end]

        # Summary counts
        all_all = repo.get_all()
        summary = {
            "total": len(all_all),
            "OPEN": sum(1 for r in all_all if r.outcome is None or r.outcome.outcome == "OPEN"),
            "WIN": sum(1 for r in all_all if r.outcome and r.outcome.outcome == "WIN"),
            "LOSS": sum(1 for r in all_all if r.outcome and r.outcome.outcome == "LOSS"),
            "BREAKEVEN": sum(1 for r in all_all if r.outcome and r.outcome.outcome == "BREAKEVEN"),
            "EXPIRED": sum(1 for r in all_all if r.outcome and r.outcome.outcome == "EXPIRED"),
            "INVALID": sum(1 for r in all_all if r.outcome and r.outcome.outcome == "INVALID"),
        }

        return {
            "status": "ok",
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "summary": summary,
            "signals": [r.model_dump() for r in page_records],
        }
    except Exception as exc:
        logger.error(f"Signal list error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Calibration only
# ---------------------------------------------------------------------------

@router.get("/calibration", summary="Get calibrated probability for a score")
def get_calibration(
    current_score: Optional[int] = Query(
        default=None,
        ge=0, le=100,
        description="Current confluence score (0–100) to look up calibrated probability",
    ),
    symbol: Optional[str] = Query(
        default=None,
        description="Optional asset symbol filter",
    ),
) -> Dict[str, Any]:
    """
    Returns the calibration result for the given confluence score.

    The calibrated probability is ALWAYS displayed separately from the confluence score.
    Never converts confluence score directly to a percentage.

    Response includes calibration_status, sample_size, brier_score, and — only when
    status is EXPLORATORY or better — the calibrated_probability.
    """
    try:
        repo = get_signal_repository()
        calibrator = get_probability_calibrator()

        completed = repo.get_all_completed()
        result = calibrator.calibrate(completed, current_score=current_score)

        response: Dict[str, Any] = {
            "status": "ok",
            "confluence_score": current_score,
            "calibration": result.model_dump(),
        }

        # Explicit display formatting for the UI
        if result.calibrated_probability is not None:
            response["display"] = {
                "confluence_score": f"{current_score} / 100" if current_score is not None else "N/A",
                "calibrated_win_probability": f"{result.calibrated_probability:.1f}%",
                "sample_size": result.sample_size,
                "validation_sample_size": result.validation_size,
                "calibration_status": result.calibration_status,
                "brier_score": result.brier_score,
                "method": result.method_used,
                "note": result.reliability_note,
                "disclaimer": result.disclaimer,
            }
        else:
            response["display"] = {
                "confluence_score": f"{current_score} / 100" if current_score is not None else "N/A",
                "calibrated_win_probability": "N/A",
                "reason": "INSUFFICIENT HISTORICAL DATA",
                "sample_size": result.sample_size,
                "minimum_required": 50,
                "calibration_status": result.calibration_status,
                "disclaimer": result.disclaimer,
            }

        return response
    except Exception as exc:
        logger.error(f"Calibration error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Single signal lookup
# ---------------------------------------------------------------------------

@router.get("/signal/{signal_id}", summary="Get a single signal record by ID")
def get_signal(signal_id: str) -> Dict[str, Any]:
    """
    Returns a single signal record including its outcome (if resolved).
    Useful for tracing individual signal history and outcome attribution.
    """
    try:
        repo = get_signal_repository()
        record = repo.get_by_id(signal_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found")
        return {"status": "ok", "signal": record.model_dump()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Signal lookup error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Phase 5 Live Signal Outcome Validation Endpoints
# ---------------------------------------------------------------------------

@router.get("/live-validation", summary="Complete Phase 5 live signal validation report")
def get_live_validation(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol (BTC-USD or XAU-USD-SPOT)"),
) -> Dict[str, Any]:
    """
    Returns the complete Phase 5 Live Signal Validation Report for the requested asset:
    - Time window performance (Today, 7D, 30D, All-Time)
    - Directional performance (BUY vs SELL)
    - 10-Bucket probability calibration & Brier/ECE scores
    - Root-cause failure & success catalyst decompositions
    - Asset isolation verification
    """
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        engine = get_live_validation_engine()
        summary = engine.generate_asset_live_validation_summary(symbol or "XAU-USD-SPOT")
        return {
            "status": "ok",
            "symbol": symbol,
            "validation": asdict(summary),
        }
    except Exception as exc:
        logger.error(f"Live validation endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/daily", summary="Live daily performance for active asset")
def get_daily_performance(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
    date: Optional[str] = Query(default=None, description="Optional YYYY-MM-DD date"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metrics = get_live_validation_engine().compute_period_metrics(
            records=records,
            period_name="TODAY",
            asset_name=symbol or "XAU-USD-SPOT",
            target_date=target_date,
        )
        return {"status": "ok", "symbol": symbol, "daily": asdict(metrics)}
    except Exception as exc:
        logger.error(f"Daily performance error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/weekly", summary="Live weekly (7-day) performance for active asset")
def get_weekly_performance(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        metrics = get_live_validation_engine().compute_period_metrics(
            records=records,
            period_name="7_DAYS",
            asset_name=symbol or "XAU-USD-SPOT",
            days_window=7,
        )
        return {"status": "ok", "symbol": symbol, "weekly": asdict(metrics)}
    except Exception as exc:
        logger.error(f"Weekly performance error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/monthly", summary="Live monthly (30-day) performance for active asset")
def get_monthly_performance(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        metrics = get_live_validation_engine().compute_period_metrics(
            records=records,
            period_name="30_DAYS",
            asset_name=symbol or "XAU-USD-SPOT",
            days_window=30,
        )
        return {"status": "ok", "symbol": symbol, "monthly": asdict(metrics)}
    except Exception as exc:
        logger.error(f"Monthly performance error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/all-time", summary="Live all-time performance for active asset")
def get_all_time_performance(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        metrics = get_live_validation_engine().compute_period_metrics(
            records=records,
            period_name="ALL_TIME",
            asset_name=symbol or "XAU-USD-SPOT",
        )
        return {"status": "ok", "symbol": symbol, "all_time": asdict(metrics)}
    except Exception as exc:
        logger.error(f"All-time performance error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/failures/live", summary="Decomposed live failure root causes")
def get_live_failures(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        failures = get_live_validation_engine().extract_failure_analysis(records)
        return {"status": "ok", "symbol": symbol, "failures": [asdict(f) for f in failures]}
    except Exception as exc:
        logger.error(f"Live failures error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/success/live", summary="Decomposed live winning pattern catalysts")
def get_live_successes(
    symbol: Optional[str] = Query(default="XAU-USD-SPOT", description="Asset symbol"),
) -> Dict[str, Any]:
    from dataclasses import asdict
    from src.services.live_validation_engine import get_live_validation_engine

    try:
        repo = get_signal_repository()
        records = _filter_records_by_symbol(repo.get_all(), symbol)
        successes = get_live_validation_engine().extract_success_analysis(records)
        return {"status": "ok", "symbol": symbol, "successes": [asdict(s) for s in successes]}
    except Exception as exc:
        logger.error(f"Live successes error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
