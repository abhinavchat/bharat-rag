from fastapi import APIRouter, status

from bharatrag.domain.ingestion_job import IngestionJobCreate, IngestionJob
from bharatrag.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion"])
service = IngestionService()


@router.post("", response_model=IngestionJob, status_code=status.HTTP_201_CREATED)
def create_ingestion_job(payload: IngestionJobCreate) -> IngestionJob:
    return service.ingest(payload)
