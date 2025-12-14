from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.ingestion_job import IngestionJobModel
from bharatrag.domain.ingestion_job import IngestionJob, IngestionJobCreate


class IngestionJobRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create(self, payload: IngestionJobCreate) -> IngestionJob:
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
            return IngestionJob.model_validate(obj)

    def get(self, job_id: UUID) -> IngestionJob | None:
        with self._session_factory() as session:
            obj = session.get(IngestionJobModel, job_id)
            return IngestionJob.model_validate(obj) if obj else None

    def update_status(
        self,
        job_id: UUID,
        status: str,
        *,
        progress: dict | None = None,
        error_summary: str | None = None,
    ) -> IngestionJob:
        with self._session_factory() as session:
            obj = session.get(IngestionJobModel, job_id)
            if obj is None:
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
            return IngestionJob.model_validate(obj)

    def list(self, collection_id: UUID | None = None) -> list[IngestionJob]:
        with self._session_factory() as session:
            q = session.query(IngestionJobModel)
            if collection_id:
                q = q.filter(IngestionJobModel.collection_id == collection_id)
            rows = q.order_by(IngestionJobModel.created_at.desc()).all()
            return [IngestionJob.model_validate(r) for r in rows]
