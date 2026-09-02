"""Market data endpoints for live price, historical candles, and feed status."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from config.settings import Settings, get_settings
from src.models.market_data import (
    PriceQuote,
    CandleHistory,
    Timeframe,
    MarketStatus,
)
from src.services.market_service import MarketDataService, get_market_service

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get(
    "/price",
    response_model=PriceQuote,
    summary="Get live Gold (XAU/USD) spot price",
    description="Fetches the latest real-time bid, ask, spot price, spread, and timestamp.",
)
def get_price(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (default: XAU-USD-SPOT)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Bypass short-term cache and fetch fresh data from provider",
    ),
    service: MarketDataService = Depends(get_market_service),
) -> PriceQuote:
    try:
        quote = service.get_live_price(symbol=symbol, force_refresh=force_refresh)
        if quote and quote.price > 0:
            try:
                from src.services.paper_trading_service import PaperTradingService
                PaperTradingService().update_and_get_stats(quote.price)
            except Exception:
                pass
        return quote
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch market price: {str(exc)}",
        )


@router.get(
    "/candles",
    response_model=CandleHistory,
    summary="Get historical OHLCV candlestick bars",
    description="Retrieves historical candlestick bars for 1m, 5m, 15m, 1h, or 1d timeframes.",
)
def get_candles(
    timeframe: Timeframe = Query(
        default=Timeframe.M15,
        description="Candle timeframe: 1m, 5m, 15m, 1h, 1d",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Number of candles to return (max: 500)",
    ),
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (default: XAU-USD-SPOT)",
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Optional start date filter (YYYY-MM-DD)",
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="Optional end date filter (YYYY-MM-DD)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Bypass short-term cache and fetch fresh data",
    ),
    service: MarketDataService = Depends(get_market_service),
) -> CandleHistory:
    try:
        return service.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch candlestick history: {str(exc)}",
        )


@router.get(
    "/status",
    response_model=MarketStatus,
    summary="Get market data provider connectivity status",
    description="Checks the health and connectivity of GoldPrice.dev and auxiliary feeds.",
)
def get_status(
    service: MarketDataService = Depends(get_market_service),
) -> MarketStatus:
    return service.get_market_status()
