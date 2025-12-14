import logging

from uuid import UUID
from fastapi import APIRouter, HTTPException

from bharatrag.domain.ingestion_job import IngestionJob
from bharatrag.services.repositories.ingestion_job_repository import IngestionJobRepository
from bharatrag.core.context import set_job_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion"])
repo = IngestionJobRepository()


@router.get("/{job_id}", response_model=IngestionJob)
def get_job(job_id: UUID) -> IngestionJob:
    set_job_id(job_id)
    logger.debug("Job fetch requested", extra={"job_id": str(job_id)})
    job = repo.get(job_id)
    if not job:
        logger.warning("Job not found", extra={"job_id": str(job_id)})
        raise HTTPException(status_code=404, detail="Job not found")
    logger.debug(
        "Job fetched successfully",
        extra={"job_id": str(job_id), "status": job.status},
    )
    return job


@router.get("", response_model=list[IngestionJob])
def list_jobs() -> list[IngestionJob]:
    logger.debug("List jobs requested")
    try:
        jobs = repo.list()
        logger.info("Jobs listed successfully", extra={"count": len(jobs)})
        return jobs
    except Exception as e:
        logger.exception("List jobs failed", extra={"error": str(e)})
        raise
