"""
REST API routes for the Trading Decision Engine.

GET /api/v1/decision         — Full advisory trading decision
GET /api/v1/decision/explain — Detailed score breakdown per component

DISCLAIMER: Outputs are purely advisory analytical signals.
No trades are executed. No broker connections are made.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.models.trading_decision import TradingDecision, DecisionScoreBreakdown
from src.services.decision_service import get_decision_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/decision", tags=["Trading Decision"])


@router.get(
    "",
    response_model=TradingDecision,
    summary="Advisory Trading Decision",
    description=(
        "Returns a complete BUY / SELL / WAIT advisory signal for XAU/USD based on "
        "multi-timeframe technical analysis and Gemini AI market bias. "
        "**This is not financial advice and does not execute any trades.**"
    ),
)
def get_decision(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (e.g. XAU-USD-SPOT, BTC-USD)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Force a fresh analysis ignoring the cache"
    )
):
    """
    Run the full decision pipeline and return a structured advisory signal.

    Decision logic:
    - Weighted scoring across 8 components (1h/15m/5m/1d trends, MACD, RSI, EMA, Gemini bias)
    - ATR-based stop-loss and TP calculations
    - Multiple WAIT override rules (confidence threshold, proximity, R:R, market condition)
    """
    try:
        svc = get_decision_service()
        decision, _ = svc.get_decision(symbol=symbol, force_refresh=force_refresh)
        return decision
    except Exception as exc:
        logger.error(f"Decision endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Decision engine error: {str(exc)}")


@router.get(
    "/explain",
    response_model=DecisionScoreBreakdown,
    summary="Decision Score Breakdown",
    description=(
        "Returns a detailed explanation of how the decision score was calculated, "
        "including per-component weights, raw scores, weighted contributions, "
        "and any WAIT override rules that were triggered."
    ),
)
def explain_decision(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (e.g. XAU-USD-SPOT, BTC-USD)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Force a fresh analysis ignoring the cache"
    )
):
    """
    Return the full scoring breakdown for audit and transparency.

    Useful for understanding exactly why a BUY, SELL, or WAIT was produced.
    """
    try:
        svc = get_decision_service()
        _, breakdown = svc.get_decision(symbol=symbol, force_refresh=force_refresh)
        return breakdown
    except Exception as exc:
        logger.error(f"Decision explain endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Decision explain error: {str(exc)}")


@router.get(
    "/overall-ai",
    response_model=TradingDecision,
    summary="Overall AI Trading Signal with Empirical Historical Evidence",
    description=(
        "Returns the complete evidence-integrated OVERALL AI TRADING SIGNAL combining "
        "live multi-timeframe technical analysis, 17-contributor confluence scoring, "
        "Gemini AI reasoning, and validated empirical historical backtest performance."
    ),
)
def get_overall_ai_decision(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (e.g. XAU-USD-SPOT, BTC-USD)",
    ),
    force_refresh: bool = Query(
        default=False,
        description="Force a fresh analysis ignoring the cache"
    )
):
    """Return the evidence-integrated Overall AI decision with empirical backtest validation."""
    try:
        svc = get_decision_service()
        decision, _ = svc.get_decision(symbol=symbol, force_refresh=force_refresh)
        return decision
    except Exception as exc:
        logger.error(f"Overall AI endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Overall AI decision error: {str(exc)}")


@router.get(
    "/hourly-strong",
    summary="Strongest valid trading opportunity in the current UTC hour",
    description="Returns up to 1 strongest valid setup observed in the current hour window, or WAIT if no setup qualified.",
)
def get_hourly_strong_signal(
    symbol: Optional[str] = Query(
        default=None,
        description="Instrument symbol (e.g. XAU-USD-SPOT, BTC-USD)",
    ),
):
    try:
        svc = get_decision_service()
        return svc.get_hourly_strong_signal(symbol=symbol or "XAU-USD-SPOT")
    except Exception as exc:
        logger.error(f"Hourly strong signal endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hourly signal error: {str(exc)}")


from typing import Optional
from pydantic import BaseModel

class OpenTradeRequest(BaseModel):
    direction: str
    entry_price: float
    stop_loss: Optional[float] = 0.0
    take_profit_1: Optional[float] = 0.0
    take_profit_2: Optional[float] = 0.0
    position_size: Optional[float] = 0.0
    setup_grade: Optional[str] = "MANUAL"

class CloseTradeRequest(BaseModel):
    trade_id: str
    current_price: Optional[float] = 0.0

class UpdateTradeRequest(BaseModel):
    trade_id: str
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None

@router.post(
    "/trade/open",
    summary="Open a manual demo paper trade",
    description="Opens a manual demo paper trade, validating the 1% maximum account risk rule."
)
def open_trade(req: OpenTradeRequest):
    try:
        from src.services.paper_trading_service import PaperTradingService
        from src.services.market_service import get_market_service
        
        entry_price = req.entry_price
        if entry_price <= 0:
            quote = get_market_service().get_live_price(force_refresh=True)
            entry_price = quote.price

        pt = PaperTradingService()
        res = pt.open_manual_trade(
            direction=req.direction,
            entry_price=entry_price,
            stop_loss=req.stop_loss,
            take_profit_1=req.take_profit_1,
            take_profit_2=req.take_profit_2,
            position_size=req.position_size,
            setup_grade=req.setup_grade,
        )
        return {"status": "success", "trade": res}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to open trade: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to open trade: {str(exc)}")

@router.post(
    "/trade/update",
    summary="Update SL and/or TP for an open demo paper trade",
    description="Adjusts the stop loss and take profit for an active demo trade."
)
def update_trade(req: UpdateTradeRequest):
    try:
        from src.services.paper_trading_service import PaperTradingService
        pt = PaperTradingService()
        res = pt.update_trade(
            trade_id=req.trade_id,
            stop_loss=req.stop_loss,
            take_profit_1=req.take_profit_1,
            take_profit_2=req.take_profit_2,
        )
        if not res:
            raise HTTPException(status_code=404, detail="Trade not found or already closed")
        return {"status": "success", "trade": res}
    except HTTPException as he:
        raise he
    except Exception as exc:
        logger.error(f"Failed to update trade: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update trade: {str(exc)}")

@router.post(
    "/trade/close",
    summary="Close an open manual demo paper trade",
    description="Closes an active open paper trade manually, recording the final exit price and P&L."
)
def close_trade(req: CloseTradeRequest):
    try:
        from src.services.paper_trading_service import PaperTradingService
        from src.services.market_service import get_market_service

        current_price = req.current_price
        if not current_price or current_price <= 0:
            quote = get_market_service().get_live_price(force_refresh=True)
            current_price = quote.price

        pt = PaperTradingService()
        res = pt.close_manual_trade(trade_id=req.trade_id, current_price=current_price)
        if not res:
            raise HTTPException(status_code=404, detail="Trade not found or already closed")
        return {"status": "success", "trade": res}
    except HTTPException as he:
        raise he
    except Exception as exc:
        logger.error(f"Failed to close trade: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to close trade: {str(exc)}")


@router.post(
    "/trade/reset",
    summary="Reset demo paper trading account balance and history",
    description="Resets the simulated demo account history and returns to the default $10,000 balance."
)
def reset_trades():
    try:
        from src.services.paper_trading_service import PaperTradingService
        pt = PaperTradingService()
        pt.reset_account()
        return {"status": "success", "message": "Demo paper trading account reset successfully."}
    except Exception as exc:
        logger.error(f"Failed to reset account: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset account: {str(exc)}")


@router.get(
    "/trade/shadow-status",
    summary="Get BTC v2.1 Shadow Runner & Paper Simulation Status",
    description=(
        "Returns the live paper-trading performance metrics of the BTC v2.1 Shadow Runner, "
        "including N resolved trades, win rate, EV in R, profit factor, open shadow positions, "
        "and a side-by-side comparison against the backtest forward-shadow baseline."
    ),
)
def get_shadow_trading_status():
    """Return read-only shadow runner metrics and reference baseline comparison."""
    try:
        from src.services.btc_shadow_runner import get_btc_shadow_runner
        runner = get_btc_shadow_runner()
        return runner.get_shadow_status()
    except Exception as exc:
        logger.error(f"Failed to fetch shadow status: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load shadow status: {str(exc)}")


