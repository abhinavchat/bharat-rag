import logging

from fastapi.routing import APIRouter

router = APIRouter()

@router.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    """
    Lightweight health check endpoint.
    
    This will be used by CI/tests and also by Kubernetes/infra in the future.
    """
    logging.getLogger(__name__).info("Health check successful")
    return {"status": "ok"}
