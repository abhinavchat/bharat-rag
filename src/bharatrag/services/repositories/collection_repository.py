from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.collection import CollectionModel
from bharatrag.domain.collection import CollectionCreate, Collection

logger = logging.getLogger(__name__)


class CollectionRepository:
    """
    Persistence adapter for collections.
    Keeps domain (Pydantic) separate from DB (SQLAlchemy).
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create(self, payload: CollectionCreate) -> Collection:
        logger.debug("Creating collection", extra={"collection_name": payload.name})
        try:
            with self._session_factory() as session:  # type: Session
                obj = CollectionModel(name=payload.name)
                session.add(obj)
                session.commit()
                session.refresh(obj)
                collection = Collection.model_validate(obj)
                logger.info(
                    "Collection created",
                    extra={"collection_id": str(collection.id), "collection_name": payload.name},
                )
                return collection
        except Exception as e:
            logger.exception("Collection creation failed", extra={"collection_name": payload.name, "error": str(e)})
            raise

    def get(self, collection_id: UUID) -> Collection | None:
        logger.debug("Getting collection", extra={"collection_id": str(collection_id)})
        try:
            with self._session_factory() as session:
                obj = session.get(CollectionModel, collection_id)
                if obj is None:
                    logger.debug("Collection not found", extra={"collection_id": str(collection_id)})
                    return None
                return Collection.model_validate(obj)
        except Exception as e:
            logger.exception(
                "Get collection failed",
                extra={"collection_id": str(collection_id), "error": str(e)},
            )
            raise
    
    def get_by_id(self, collection_id: UUID) -> CollectionModel | None:
        logger.debug("Getting collection by ID", extra={"collection_id": str(collection_id)})
        try:
            with self._session_factory() as session:
                return session.get(CollectionModel, collection_id)
        except Exception as e:
            logger.exception(
                "Get collection by ID failed",
                extra={"collection_id": str(collection_id), "error": str(e)},
            )
            raise

    def list(self, limit: int = 50, offset: int = 0) -> list[Collection]:
        logger.debug("Listing collections", extra={"limit": limit, "offset": offset})
        try:
            with self._session_factory() as session:
                rows = (
                    session.query(CollectionModel)
                    .order_by(CollectionModel.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )
                collections = [Collection.model_validate(r) for r in rows]
                logger.debug(
                    "Collections listed",
                    extra={"count": len(collections), "limit": limit, "offset": offset},
                )
                return collections
        except Exception as e:
            logger.exception("List collections failed", extra={"error": str(e)})
            raise
