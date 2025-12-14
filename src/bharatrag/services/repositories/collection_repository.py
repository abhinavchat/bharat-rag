from __future__ import annotations

from uuid import UUID
from sqlalchemy.orm import Session

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.collection import CollectionModel
from bharatrag.domain.collection import CollectionCreate, Collection


class CollectionRepository:
    """
    Persistence adapter for collections.
    Keeps domain (Pydantic) separate from DB (SQLAlchemy).
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create(self, payload: CollectionCreate) -> Collection:
        with self._session_factory() as session:  # type: Session
            obj = CollectionModel(name=payload.name)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return Collection.model_validate(obj)

    def get(self, collection_id: UUID) -> Collection | None:
        with self._session_factory() as session:
            obj = session.get(CollectionModel, collection_id)
            if obj is None:
                return None
            return Collection.model_validate(obj)
    
    def get_by_id(self, collection_id: UUID) -> CollectionModel | None:
        with self._session_factory() as session:
            return session.get(CollectionModel, collection_id)

    def list(self, limit: int = 50, offset: int = 0) -> list[Collection]:
        with self._session_factory() as session:
            rows = (
                session.query(CollectionModel)
                .order_by(CollectionModel.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [Collection.model_validate(r) for r in rows]
