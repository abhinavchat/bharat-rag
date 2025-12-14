import logging

from fastapi import FastAPI

from bharatrag.api.health import router as health_router
from bharatrag.api.collections import router as collections_router
from bharatrag.core.config import get_settings
from bharatrag.core.logging_config import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    
    app = FastAPI(
        title="Bharat-RAG Reference Server",
        version="0.0.1-prealpha",
        description=(
            "Reference implementation for the Bharat-RAG Protocol (BRP)."
            "This is an early pre-alpha API skeleton."
        ),
    )
    app.include_router(health_router)
    app.include_router(collections_router)
    logging.getLogger(__name__).info("Application started")
    return app

app = create_app()
