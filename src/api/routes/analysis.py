"""Technical Analysis API Routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from src.models.market_data import Timeframe
from src.models.technical_analysis import TechnicalAnalysisResponse
from src.services.technical_service import TechnicalAnalysisService, get_technical_service

router = APIRouter(prefix="/analysis", tags=["Technical Analysis"])


@router.get(
    "/technical",
    response_model=TechnicalAnalysisResponse,
    summary="Get multi-timeframe technical indicator analysis",
    description=(
        "Calculates EMA (20, 50, 200), RSI (14), MACD (12, 26, 9), ATR (14), "
        "Support & Resistance levels, and multi-confirmation Market Trend (BULLISH, BEARISH, SIDEWAYS) "
        "for the specified timeframe."
    ),
)
def get_technical_analysis(
    timeframe: Timeframe = Query(
        default=Timeframe.M15,
        description="Candlestick timeframe interval: 1m, 5m, 15m, 1h, 1d",
    ),
    symbol: Optional[str] = Query(
        default=None,
        description="Trading symbol (default: XAU-USD-SPOT)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Bypass cached candle data to recalculate on freshly fetched market feeds",
    ),
    include_series: bool = Query(
        default=False,
        description="Include full EMA20/50/200 series for chart overlay (same backend formulas)",
    ),
    service: TechnicalAnalysisService = Depends(get_technical_service),
) -> TechnicalAnalysisResponse:
    try:
        return service.analyze(
            symbol=symbol,
            timeframe=timeframe,
            force_refresh=force_refresh,
            include_series=include_series,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to execute technical analysis: {str(exc)}",
        )
