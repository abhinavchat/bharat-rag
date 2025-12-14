from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.document import DocumentModel
from bharatrag.domain.document import DocumentCreate, Document

logger = logging.getLogger(__name__)


class DocumentRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create(self, payload: DocumentCreate) -> Document:
        logger.debug(
            "Creating document",
            extra={
                "collection_id": str(payload.collection_id),
                "source_type": payload.source_type,
                "format": payload.format,
            },
        )
        try:
            with self._session_factory() as session:  # type: Session
                obj = DocumentModel(
                    collection_id=payload.collection_id,
                    source_type=payload.source_type,
                    format=payload.format,
                    title=payload.title,
                    uri=payload.uri,
                    extra_metadata=payload.extra_metadata,
                )
                session.add(obj)
                session.commit()
                session.refresh(obj)
                document = Document.model_validate(obj)
                logger.info(
                    "Document created",
                    extra={
                        "document_id": str(document.id),
                        "collection_id": str(payload.collection_id),
                    },
                )
                return document
        except Exception as e:
            logger.exception(
                "Document creation failed",
                extra={
                    "collection_id": str(payload.collection_id),
                    "error": str(e),
                },
            )
            raise

    def get(self, document_id: UUID) -> Document | None:
        logger.debug("Getting document", extra={"document_id": str(document_id)})
        try:
            with self._session_factory() as session:
                obj = session.get(DocumentModel, document_id)
                if obj is None:
                    logger.debug("Document not found", extra={"document_id": str(document_id)})
                    return None
                return Document.model_validate(obj)
        except Exception as e:
            logger.exception(
                "Get document failed",
                extra={"document_id": str(document_id), "error": str(e)},
            )
            raise
