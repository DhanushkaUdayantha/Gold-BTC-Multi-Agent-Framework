"""AI Market Analysis API Routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.ai_analysis import (
    AIAnalysisResponse,
    MultiTimeframeTechnicalInput,
)
from src.services.ai_service import AIMarketAnalysisService, get_ai_service

router = APIRouter(prefix="/analysis/ai", tags=["AI Market Analysis"])


@router.get(
    "",
    response_model=AIAnalysisResponse,
    summary="Get multi-timeframe AI market analysis",
    description=(
        "Retrieves multi-timeframe indicators across 5m, 15m, 1h, and 1d, executes AI analysis, "
        "and returns structured market condition, overall bias, confidence score, and key levels.\n\n"
        "**NOTE**: Strictly analytical and advisory. Does not execute trades or guarantee profits."
    ),
)
def get_ai_analysis(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (default: XAU-USD-SPOT)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Bypass cache and freshly fetch multi-timeframe data from market feeds",
    ),
    service: AIMarketAnalysisService = Depends(get_ai_service),
) -> AIAnalysisResponse:
    try:
        return service.analyze_market(symbol=symbol, force_refresh=force_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate AI market analysis: {str(exc)}",
        )


@router.get(
    "/raw",
    response_model=MultiTimeframeTechnicalInput,
    summary="Get raw multi-timeframe technical input data sent to AI",
    description="Returns the aggregated technical indicator profiles for 5m, 15m, 1h, and 1d timeframes.",
)
def get_raw_technical_input(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (default: XAU-USD-SPOT)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Bypass cache to assemble fresh multi-timeframe profiles",
    ),
    service: AIMarketAnalysisService = Depends(get_ai_service),
) -> MultiTimeframeTechnicalInput:
    try:
        return service.get_raw_technical_input(symbol=symbol, force_refresh=force_refresh)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve raw multi-timeframe technical data: {str(exc)}",
        )


@router.get(
    "/usage",
    summary="Get Gemini request usage statistics",
    description="Returns daily usage counts, safety budget limit, and rate limit cooldown metrics.",
)
def get_gemini_usage(
    service: AIMarketAnalysisService = Depends(get_ai_service),
):
    try:
        return service.request_manager.get_stats()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Gemini request stats: {str(exc)}",
        )

