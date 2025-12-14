from __future__ import annotations

import logging

from bharatrag.services.repositories.chunk_repository import ChunkRepository
from bharatrag.services.embedding_service import EmbeddingService
from bharatrag.domain.chunk import ChunkSearchResult

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, chunk_repo: ChunkRepository | None = None):
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.embedder = EmbeddingService()  # Use semantic embeddings instead of hash-based

    def query(self, *, collection_id, query: str, top_k: int = 5) -> list[ChunkSearchResult]:
        logger.debug(
            "Starting retrieval query",
            extra={
                "collection_id": str(collection_id),
                "query_length": len(query),
                "top_k": top_k,
            },
        )
        
        try:
            qvec = self.embedder.embed([query])[0]
            logger.debug(
                "Query embedded successfully",
                extra={
                    "collection_id": str(collection_id),
                    "embedding_dim": len(qvec),
                },
            )
            
            results = self.chunk_repo.search_similar(
                collection_id=collection_id,
                query_embedding=qvec,
                top_k=top_k,
            )
            
            logger.info(
                "Retrieval query completed",
                extra={
                    "collection_id": str(collection_id),
                    "result_count": len(results),
                    "top_k": top_k,
                },
            )
            
            return results
        except Exception as e:
            logger.exception(
                "Retrieval query failed",
                extra={
                    "collection_id": str(collection_id),
                    "error": str(e),
                },
            )
            raise
