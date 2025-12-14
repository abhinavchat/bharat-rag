from __future__ import annotations

import logging
import hashlib
from bharatrag.ports.embedding import Embedder

logger = logging.getLogger(__name__)


class SimpleHashEmbedder(Embedder):
    """
    Deterministic "fake" embedder.
    Produces dim=384 vectors based on sha256.
    Not semantically meaningful, but great for plumbing + tests.
    """
    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        logger.debug("Embedding texts", extra={"text_count": len(texts), "dim": self.dim})
        
        try:
            out: list[list[float]] = []
            for t in texts:
                h = hashlib.sha256(t.encode("utf-8")).digest()
                # Expand bytes into dim floats
                vec = []
                i = 0
                while len(vec) < self.dim:
                    b = h[i % len(h)]
                    vec.append((b / 255.0) * 2.0 - 1.0)
                    i += 1
                out.append(vec)
            
            logger.debug(
                "Texts embedded successfully",
                extra={
                    "text_count": len(texts),
                    "embedding_count": len(out),
                    "dim": self.dim,
                },
            )
            
            return out
        except Exception as e:
            logger.exception("Embedding failed", extra={"text_count": len(texts), "error": str(e)})
            raise
