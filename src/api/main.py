"""FastAPI Backend Application for Gold AI Trading Analysis."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from src.api.routes.market import router as market_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.ai_analysis import router as ai_router
from src.api.routes.decision import router as decision_router
from src.api.routes.ote import router as ote_router
from src.api.routes.performance import router as performance_router
from src.api.routes.backtest import router as backtest_router
from src.api.routes.ml_shadow import router as ml_shadow_router
from src.api.routes.research_validation import router as research_validation_router
from src.api.routes.failure_analysis import router as failure_analysis_router
from src.api.routes.feature_ablation import router as feature_ablation_router
from src.api.routes.phase5_research import router as phase5_research_router
from src.api.routes.governance import router as governance_router
from src.api.routes.admin_gating import router as admin_gating_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


import threading
from src.services.historical_data_service import HistoricalDataService
from src.services.live_candle_ingestion_service import LiveCandleIngestionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    logger.info(f"Market Data Provider: {settings.MARKET_DATA_PROVIDER}")
    logger.info(f"AI Provider Mode: {settings.AI_PROVIDER} (Model: {settings.AI_MODEL})")
    
    # Initialize / verify default historical datasets for BTC/USD and XAU/USD in background
    def _init_historical_data():
        try:
            HistoricalDataService.get_instance().ensure_default_datasets()
        except Exception as e:
            logger.warning(f"Initial historical data check warning: {e}")

    threading.Thread(target=_init_historical_data, daemon=True, name="HistDataInit").start()

    # Start the live 5m candle ingestion daemon
    # Catches up any missed candles since last shutdown, then polls every 5 minutes.
    try:
        LiveCandleIngestionService.get_instance().start()
    except Exception as e:
        logger.warning(f"LiveCandleIngestion startup warning: {e}")

    yield
    # Graceful shutdown: signal the ingestion daemon to stop
    try:
        LiveCandleIngestionService.get_instance().stop()
    except Exception:
        pass
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend REST API for Gold (XAU/USD) Market Analysis and AI Signals.\n\n"
        "**NOTE**: This system is strictly an analytical advisory engine. "
        "It does not execute real trades or connect to broker accounts."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for the Next.js dashboard (any local dev port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
app.include_router(market_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(decision_router, prefix="/api/v1")
app.include_router(ote_router, prefix="/api/v1")
app.include_router(performance_router, prefix="/api/v1")
app.include_router(backtest_router)
app.include_router(ml_shadow_router)
app.include_router(research_validation_router)
app.include_router(failure_analysis_router)
app.include_router(feature_ablation_router)
app.include_router(phase5_research_router)
app.include_router(governance_router)
app.include_router(admin_gating_router)


@app.get("/", tags=["Root"])
async def root():
    """Service metadata and navigation."""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "live_price": "/api/v1/market/price",
            "historical_candles": "/api/v1/market/candles",
            "feed_status": "/api/v1/market/status",
            "technical_analysis": "/api/v1/analysis/technical",
            "ai_market_analysis": "/api/v1/analysis/ai",
            "raw_ai_input": "/api/v1/analysis/ai/raw",
            "trading_decision": "/api/v1/decision",
            "decision_explain": "/api/v1/decision/explain",
            "ote_signal": "/api/v1/ote",
            "ote_status": "/api/v1/ote/status",
        },
    }


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Health check endpoint returning API, market feed, and Gemini status."""
    gemini_key_set = bool(settings.GEMINI_API_KEY)
    gemini_active = gemini_key_set or settings.AI_PROVIDER != "fallback"
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "feed": "online",
        "gemini_active": gemini_active,
        "gemini_configured": gemini_key_set,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.AI_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
