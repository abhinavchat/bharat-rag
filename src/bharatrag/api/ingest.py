import logging

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from bharatrag.domain.ingestion_job import IngestionJobCreate, IngestionJob
from bharatrag.services.ingestion_service import IngestionService
from bharatrag.core.context import set_collection_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion"])
service = IngestionService()


@router.post("", response_model=IngestionJob, status_code=status.HTTP_201_CREATED)
def create_ingestion_job(payload: IngestionJobCreate) -> IngestionJob:
    set_collection_id(payload.collection_id)
    logger.info(
        "Ingestion job creation requested",
        extra={
            "collection_id": str(payload.collection_id),
            "source_type": payload.source_type,
            "format": payload.format,
            "uri_length": len(payload.uri) if payload.uri else 0,
        },
    )
    
    try:
        job = service.ingest(payload)
        logger.info(
            "Ingestion job created successfully",
            extra={
                "job_id": str(job.id),
                "collection_id": str(payload.collection_id),
                "status": job.status,
            },
        )
        return job
    except ValueError as e:
        logger.warning(
            "Ingestion job creation failed: validation error",
            extra={
                "collection_id": str(payload.collection_id),
                "error": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(
            "Ingestion job creation failed: unexpected error",
            extra={
                "collection_id": str(payload.collection_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during ingestion",
        )
