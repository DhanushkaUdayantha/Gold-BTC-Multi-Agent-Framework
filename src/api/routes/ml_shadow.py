"""
API Routes for ML Shadow Validation Layer (Research & Observational Only).

Symbol is REQUIRED on /observations and /metrics — never omitted.
This prevents the API from silently returning an interleaved BTC+XAU
response when a caller forgets to specify an asset.

If a genuinely cross-asset aggregate endpoint is ever needed, it must
be a separately named, clearly-labelled route (e.g. /metrics/combined).
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from src.research.ml_shadow.shadow_service import get_ml_shadow_service
from src.research.ml_shadow.symbol_utils import normalize_ml_symbol

router = APIRouter(prefix="/api/v1/ml/shadow", tags=["ML Shadow Research"])

@router.get("/status")
def get_shadow_status() -> Dict[str, Any]:
    """Returns the operational status of the ML shadow observer models."""
    svc = get_ml_shadow_service()
    btc_avail = svc.is_available("BTC/USD")
    xau_avail = svc.is_available("XAU/USD")
    btc_metrics = svc.get_forward_validation_metrics("BTC/USD")
    xau_metrics = svc.get_forward_validation_metrics("XAU/USD")

    return {
        "status": "OPERATIONAL",
        "mode": "SHADOW_OBSERVER_ONLY",
        "production_influence": "ZERO (Advisory/Observational Only)",
        "models": {
            "BTC/USD": {
                "available": btc_avail,
                "model_name": svc._model_names.get("BTC", "None"),
                "version": "v1.0.0-research",
                "observations_total": btc_metrics["total_observations"],
                "observations_pending": btc_metrics["pending_observations"],
                "trades_resolved": btc_metrics["resolved_trades"],
                "milestone": btc_metrics["milestone_reached"]
            },
            "XAU/USD": {
                "available": xau_avail,
                "model_name": svc._model_names.get("XAU", "None"),
                "version": "v1.0.0-research",
                "observations_total": xau_metrics["total_observations"],
                "observations_pending": xau_metrics["pending_observations"],
                "trades_resolved": xau_metrics["resolved_trades"],
                "milestone": xau_metrics["milestone_reached"]
            }
        }
    }

@router.get("/metrics")
def get_shadow_metrics(
    symbol: str = Query(
        ...,
        description="Required. Asset symbol — 'BTC/USD' or 'XAU/USD'. "
                    "Variants like 'BTC-USD' and 'XAU-USD-SPOT' are also accepted. "
                    "Never omit: a cross-asset aggregate is misleading and unsupported."
    )
) -> Dict[str, Any]:
    """
    Returns forward validation metrics on resolved live observations.

    symbol is REQUIRED — pass 'BTC/USD' or 'XAU/USD'.
    If you omit symbol, FastAPI returns HTTP 422.
    """
    try:
        canonical = normalize_ml_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    svc = get_ml_shadow_service()
    return svc.get_forward_validation_metrics(symbol=canonical)

@router.get("/observations")
def get_shadow_observations(
    symbol: str = Query(
        ...,
        description="Required. Asset symbol — 'BTC/USD' or 'XAU/USD'. "
                    "Variants like 'BTC-USD' and 'XAU-USD-SPOT' are also accepted. "
                    "Never omit: the endpoint must not silently return interleaved BTC+XAU data."
    ),
    limit: int = Query(50, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """
    Returns recent point-in-time shadow observations for a single asset.

    symbol is REQUIRED — pass 'BTC/USD' or 'XAU/USD'.
    If you omit symbol, FastAPI returns HTTP 422.
    """
    try:
        canonical = normalize_ml_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    svc = get_ml_shadow_service()
    all_obs = svc.store.get_all_observations(symbol=canonical)
    return all_obs[-limit:]
