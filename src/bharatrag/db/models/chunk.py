# db/models/chunk.py
import uuid
from sqlalchemy import DateTime, func, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from bharatrag.db.base import Base


class ChunkModel(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # embedding dimension chosen for MiniLM / sentence-transformers compatibility
    embedding: Mapped[list[float]] = mapped_column(
        Vector(384),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
