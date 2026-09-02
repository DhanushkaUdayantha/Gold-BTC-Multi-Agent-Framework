"""
API Routes for ML Shadow Validation Layer (Research & Observational Only).
"""
from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
from src.research.ml_shadow.shadow_service import get_ml_shadow_service

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
def get_shadow_metrics(symbol: Optional[str] = Query(None, description="BTC/USD or XAU/USD")) -> Dict[str, Any]:
    """Returns forward validation metrics on resolved live observations."""
    svc = get_ml_shadow_service()
    return svc.get_forward_validation_metrics(symbol=symbol)

@router.get("/observations")
def get_shadow_observations(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """Returns recent point-in-time shadow observations."""
    svc = get_ml_shadow_service()
    all_obs = svc.store.get_all_observations(symbol=symbol)
    return all_obs[-limit:]
