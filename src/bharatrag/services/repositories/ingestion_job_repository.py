import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.ingestion_job import IngestionJobModel
from bharatrag.domain.ingestion_job import IngestionJob, IngestionJobCreate

logger = logging.getLogger(__name__)


class IngestionJobRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create(self, payload: IngestionJobCreate) -> IngestionJob:
        logger.debug(
            "Creating ingestion job",
            extra={
                "collection_id": str(payload.collection_id),
                "source_type": payload.source_type,
                "format": payload.format,
            },
        )
        try:
            with self._session_factory() as session:  # type: Session
                obj = IngestionJobModel(
                    collection_id=payload.collection_id,
                    source_type=payload.source_type,
                    format=payload.format,
                    status="PENDING",
                    progress={},
                )
                session.add(obj)
                session.commit()
                session.refresh(obj)
                job = IngestionJob.model_validate(obj)
                logger.info("Ingestion job created", extra={"job_id": str(job.id)})
                return job
        except Exception as e:
            logger.exception(
                "Ingestion job creation failed",
                extra={
                    "collection_id": str(payload.collection_id),
                    "error": str(e),
                },
            )
            raise

    def get(self, job_id: UUID) -> IngestionJob | None:
        logger.debug("Getting ingestion job", extra={"job_id": str(job_id)})
        try:
            with self._session_factory() as session:
                obj = session.get(IngestionJobModel, job_id)
                if obj is None:
                    logger.debug("Ingestion job not found", extra={"job_id": str(job_id)})
                    return None
                return IngestionJob.model_validate(obj)
        except Exception as e:
            logger.exception("Get ingestion job failed", extra={"job_id": str(job_id), "error": str(e)})
            raise

    def update_status(
        self,
        job_id: UUID,
        status: str,
        *,
        progress: dict | None = None,
        error_summary: str | None = None,
    ) -> IngestionJob:
        logger.debug(
            "Updating ingestion job status",
            extra={
                "job_id": str(job_id),
                "status": status,
                "has_progress": progress is not None,
                "has_error": error_summary is not None,
            },
        )
        try:
            with self._session_factory() as session:
                obj = session.get(IngestionJobModel, job_id)
                if obj is None:
                    logger.error("Ingestion job not found for status update", extra={"job_id": str(job_id)})
                    raise ValueError("Ingestion job not found")

                obj.status = status

                if status == "RUNNING":
                    obj.started_at = datetime.now(timezone.utc)
                if status in ("COMPLETED", "FAILED", "CANCELED"):
                    obj.completed_at = datetime.now(timezone.utc)

                if progress is not None:
                    obj.progress = progress
                if error_summary:
                    obj.error_summary = error_summary

                session.commit()
                session.refresh(obj)
                job = IngestionJob.model_validate(obj)
                logger.info(
                    "Ingestion job status updated",
                    extra={
                        "job_id": str(job_id),
                        "status": status,
                        "stage": progress.get("stage") if progress else None,
                    },
                )
                return job
        except Exception as e:
            logger.exception(
                "Update ingestion job status failed",
                extra={"job_id": str(job_id), "status": status, "error": str(e)},
            )
            raise

    def list(self, collection_id: UUID | None = None) -> list[IngestionJob]:
        logger.debug("Listing ingestion jobs", extra={"collection_id": str(collection_id) if collection_id else None})
        try:
            with self._session_factory() as session:
                q = session.query(IngestionJobModel)
                if collection_id:
                    q = q.filter(IngestionJobModel.collection_id == collection_id)
                rows = q.order_by(IngestionJobModel.created_at.desc()).all()
                jobs = [IngestionJob.model_validate(r) for r in rows]
                logger.debug("Ingestion jobs listed", extra={"count": len(jobs)})
                return jobs
        except Exception as e:
            logger.exception("List ingestion jobs failed", extra={"error": str(e)})
            raise
