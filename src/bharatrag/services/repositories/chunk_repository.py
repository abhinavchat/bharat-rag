from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text, bindparam
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector

from bharatrag.db.session import SessionLocal
from bharatrag.db.models.chunk import ChunkModel
from bharatrag.domain.chunk import Chunk, ChunkCreate, ChunkSearchResult

logger = logging.getLogger(__name__)


class ChunkRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def bulk_create(self, rows: list[ChunkCreate]) -> int:
        logger.debug(
            "Bulk creating chunks",
            extra={
                "chunk_count": len(rows),
                "document_id": str(rows[0].document_id) if rows else None,
                "collection_id": str(rows[0].collection_id) if rows else None,
            },
        )
        
        try:
            with self._session_factory() as session:  # type: Session
                models = [
                    ChunkModel(
                        document_id=r.document_id,
                        collection_id=r.collection_id,
                        chunk_index=r.chunk_index,
                        text=r.text,
                        embedding=r.embedding,
                        extra_metadata=r.extra_metadata,
                    )
                    for r in rows
                ]
                session.add_all(models)
                session.commit()
                
                logger.info(
                    "Chunks bulk created successfully",
                    extra={
                        "chunk_count": len(models),
                        "document_id": str(rows[0].document_id) if rows else None,
                        "collection_id": str(rows[0].collection_id) if rows else None,
                    },
                )
                
                return len(models)
        except Exception as e:
            logger.exception(
                "Bulk create chunks failed",
                extra={
                    "chunk_count": len(rows),
                    "error": str(e),
                },
            )
            raise

    def search_similar(
        self,
        *,
        collection_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[ChunkSearchResult]:
        """
        Uses pgvector cosine distance: smaller distance => closer.
        We'll return score = 1 - distance to get "higher is better".
        """
        top_k = max(1, min(top_k, 50))
        
        logger.debug(
            "Searching similar chunks",
            extra={
                "collection_id": str(collection_id),
                "embedding_dim": len(query_embedding),
                "top_k": top_k,
            },
        )

        try:
            sql = sql_text(
                """
                SELECT
                  id,
                  document_id,
                  collection_id,
                  chunk_index,
                  text,
                  metadata,
                  created_at,
                  (1 - (embedding <=> :qvec)) AS score
                FROM chunks
                WHERE collection_id = :cid
                ORDER BY embedding <=> :qvec
                LIMIT :k
                """
            )

            # Use bindparam with Vector type for proper pgvector handling
            sql = sql.bindparams(
                bindparam("qvec", type_=Vector(384)),
                bindparam("cid", type_=PG_UUID(as_uuid=True)),
            )

            with self._session_factory() as session:
                rows = session.execute(
                    sql,
                    {
                        "cid": collection_id,
                        "qvec": query_embedding,
                        "k": top_k,
                    },
                ).mappings().all()

                out: list[ChunkSearchResult] = []
                for r in rows:
                    chunk = Chunk(
                        id=r["id"],
                        document_id=r["document_id"],
                        collection_id=r["collection_id"],
                        chunk_index=r["chunk_index"],
                        text=r["text"],
                        metadata=r["metadata"] or {},
                        created_at=r["created_at"],
                    )
                    out.append(ChunkSearchResult(chunk=chunk, score=float(r["score"])))
                
                logger.info(
                    "Similar chunks found",
                    extra={
                        "collection_id": str(collection_id),
                        "result_count": len(out),
                        "top_k": top_k,
                    },
                )
                
                return out
        except Exception as e:
            logger.exception(
                "Search similar chunks failed",
                extra={
                    "collection_id": str(collection_id),
                    "error": str(e),
                },
            )
            raise
