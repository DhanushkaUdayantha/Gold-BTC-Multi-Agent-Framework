"""API route routers."""
from src.api.routes.market import router as market_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.ai_analysis import router as ai_router
from src.api.routes.ote import router as ote_router

__all__ = ["market_router", "analysis_router", "ai_router", "ote_router"]
