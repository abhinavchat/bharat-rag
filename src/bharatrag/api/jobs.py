from uuid import UUID
from fastapi import APIRouter, HTTPException

from bharatrag.domain.ingestion_job import IngestionJob
from bharatrag.services.repositories.ingestion_job_repository import IngestionJobRepository

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion"])
repo = IngestionJobRepository()


@router.get("/{job_id}", response_model=IngestionJob)
def get_job(job_id: UUID) -> IngestionJob:
    job = repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[IngestionJob])
def list_jobs() -> list[IngestionJob]:
    return repo.list()
