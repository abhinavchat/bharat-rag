import logging
from fastapi import HTTPException

from bharatrag.domain.ingestion_job import IngestionJob, IngestionJobCreate
from bharatrag.services.repositories.ingestion_job_repository import IngestionJobRepository
from bharatrag.services.repositories.collection_repository import CollectionRepository

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        repo: IngestionJobRepository | None = None,
        collections: CollectionRepository | None = None,
    ):
        self.repo = repo or IngestionJobRepository()
        self.collections = collections or CollectionRepository()

    def ingest(self, payload: IngestionJobCreate) -> IngestionJob:
        # ✅ Validate payload early
        self._validate(payload)

        # ✅ Ensure collection exists BEFORE creating job (avoid FK 500)
        if self.collections.get(payload.collection_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Collection not found: {payload.collection_id}",
            )

        # ✅ Now it's safe to create the job
        job = self.repo.create(payload)

        logger.info("Ingestion job created", extra={"job_id": str(job.id)})

        try:
            job = self.repo.update_status(job.id, "RUNNING")

            self._store_raw(payload)

            job = self.repo.update_status(
                job.id,
                "COMPLETED",
                progress={"stage": "completed"},
            )

            logger.info("Ingestion job completed", extra={"job_id": str(job.id)})
            return job

        except Exception as exc:
            logger.exception("Ingestion job failed", extra={"job_id": str(job.id)})
            return self.repo.update_status(
                job.id,
                "FAILED",
                error_summary=str(exc),
            )

    def _validate(self, payload: IngestionJobCreate) -> None:
        if payload.source_type == "url" and not payload.uri:
            raise HTTPException(status_code=422, detail="uri is required when source_type is url")

    def _store_raw(self, payload: IngestionJobCreate) -> None:
        # Placeholder for Weekend 3 (file storage)
        return
