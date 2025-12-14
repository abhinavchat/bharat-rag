import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from fastapi import FastAPI

from bharatrag.api.health import router as health_router
from bharatrag.api.collections import router as collections_router
from bharatrag.api.jobs import router as jobs_router
from bharatrag.api.ingest import router as ingest_router
from bharatrag.api.answer import router as answer_router
from bharatrag.api.query import router as query_router
from bharatrag.core.config import get_settings
from bharatrag.core.logging_config import setup_logging
from bharatrag.core.context import set_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and inject request_id into context for logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        
        # Add request_id to response headers for client correlation
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


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
    
    # Add request ID middleware (should be first)
    app.add_middleware(RequestIDMiddleware)
    
    app.include_router(health_router)
    app.include_router(collections_router)
    app.include_router(jobs_router)
    app.include_router(ingest_router)
    app.include_router(answer_router)
    app.include_router(query_router)
    logging.getLogger(__name__).info("Application started")
    return app

app = create_app()
