"""Main entrypoint exposing FastAPI app for uvicorn (src.main:app)."""
from src.api.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from config.settings import get_settings

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
