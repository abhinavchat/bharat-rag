"""
Semantic embedding service using sentence-transformers.

Provides semantic embeddings that capture meaning and similarity,
unlike hash-based embeddings which are deterministic but not semantic.
"""
from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer
from bharatrag.ports.embedding import Embedder

logger = logging.getLogger(__name__)


class EmbeddingService(Embedder):
    """
    Semantic embedding service using sentence-transformers.
    
    Uses 'all-MiniLM-L6-v2' model which produces 384-dimensional vectors.
    This matches the database schema and provides semantic similarity.
    """
    dim = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: Hugging Face model identifier (default: all-MiniLM-L6-v2)
        """
        logger.info(
            "Initializing semantic embedding service",
            extra={"model_name": model_name, "dim": self.dim},
        )
        self.model = SentenceTransformer(model_name)
        logger.info("Semantic embedding service initialized")
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate semantic embeddings for texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        logger.debug(
            "Generating semantic embeddings",
            extra={"text_count": len(texts), "dim": self.dim},
        )
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            result = embeddings.tolist()
            
            logger.debug(
                "Semantic embeddings generated",
                extra={
                    "text_count": len(texts),
                    "embedding_count": len(result),
                    "dim": self.dim,
                },
            )
            
            return result
        except Exception as e:
            logger.exception(
                "Failed to generate semantic embeddings",
                extra={"text_count": len(texts), "error": str(e)},
            )
            raise
