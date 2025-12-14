import logging
from pathlib import Path
from uuid import UUID

from bharatrag.domain.ingestion_job import IngestionJob, IngestionJobCreate
from bharatrag.domain.document import DocumentCreate
from bharatrag.domain.chunk import ChunkCreate

from bharatrag.services.repositories.ingestion_job_repository import IngestionJobRepository
from bharatrag.services.repositories.document_repository import DocumentRepository
from bharatrag.services.repositories.chunk_repository import ChunkRepository
from bharatrag.services.repositories.collection_repository import CollectionRepository

from bharatrag.services.chunking.simple_chunker import SimpleChunker
from bharatrag.services.embeddings.simple_hash_embedder import SimpleHashEmbedder
from bharatrag.core.context import set_job_id, set_collection_id, set_document_id

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        repo: IngestionJobRepository | None = None,
        document_repo: DocumentRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
        collection_repo: CollectionRepository | None = None,
    ):
        self.repo = repo or IngestionJobRepository()
        self.document_repo = document_repo or DocumentRepository()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.collection_repo = collection_repo or CollectionRepository()

        self.chunker = SimpleChunker()
        self.embedder = SimpleHashEmbedder()

    def ingest(self, payload: IngestionJobCreate) -> IngestionJob:
        # Request validation BEFORE job creation
        self._validate_request(payload)
            
        # Validate collection exists -> if not, return clean error (no 500)
        if self.collection_repo.get(payload.collection_id) is None:
            raise ValueError(f"collection_id not found: {payload.collection_id}")

        job = self.repo.create(payload)
        # Set context for logging
        set_job_id(job.id)
        set_collection_id(payload.collection_id)
        logger.info("Ingestion job created")

        try:
            job = self.repo.update_status(job.id, "RUNNING")
            # self._validate(payload)
            self._store_raw(payload, job.id)
            job = self.repo.update_status(job.id, "COMPLETED", progress={"stage": "persisted"})
            logger.info("Ingestion job completed")
            return job
        except Exception as exc:
            logger.exception("Ingestion job failed")
            return self.repo.update_status(job.id, "FAILED", error_summary=str(exc))

    def _validate_request(self, payload: IngestionJobCreate) -> None:
        logger.debug("Validating ingestion request", extra={"collection_id": str(payload.collection_id)})
        
        if self.collection_repo.get(payload.collection_id) is None:
            logger.error("Collection not found for ingestion", extra={"collection_id": str(payload.collection_id)})
            raise ValueError(f"collection_id not found: {payload.collection_id}")
    
        if not payload.source_type or not payload.format:
            logger.error("Invalid ingestion payload: missing source_type or format")
            raise ValueError("Invalid ingestion payload")
    
        # if you're going uri-based, enforce it as required for now
        if not payload.uri:
            logger.error("Invalid ingestion payload: missing uri")
            raise ValueError("uri is required for ingestion in current implementation")
        
        logger.debug("Ingestion request validation passed")
    
    def _validate(self, payload: IngestionJobCreate) -> None:
        if not payload.source_type or not payload.format:
            raise ValueError("Invalid ingestion payload")

    def _store_raw(self, payload: IngestionJobCreate, job_id: UUID) -> None:
        # 1) Create document row first
        document = self.document_repo.create(
            DocumentCreate(
                collection_id=payload.collection_id,
                source_type=payload.source_type,
                format=payload.format,
                uri=payload.uri,
                extra_metadata={},
            )
        )
        set_document_id(document.id)
        self.repo.update_status(job_id, "RUNNING", progress={"stage": "document_created"})
        logger.info("Document created")

        # 2) Load text (Weekend-3 stub)
        text = self._load_text(payload.uri)

        # 3) Chunk
        chunks = self.chunker.chunk(text)
        chunk_texts = [c[1] for c in chunks if c[1]]
        if not chunk_texts:
            chunk_texts = [""]  # ensure embed is called at least once

        self.repo.update_status(
            job_id, "RUNNING", progress={"stage": "chunked", "chunks": len(chunk_texts)}
        )
        logger.info("Text chunked", extra={"chunk_count": len(chunk_texts)})

        # 4) Embed
        embeddings = self.embedder.embed(chunk_texts)
        self.repo.update_status(job_id, "RUNNING", progress={"stage": "embedded"})
        logger.info("Chunks embedded", extra={"embedding_count": len(embeddings)})

        # 5) Persist chunks
        rows: list[ChunkCreate] = []
        emb_i = 0
        for i, (_, chunk) in enumerate(chunks):
            if not chunk:
                continue
            rows.append(
                ChunkCreate(
                    document_id=document.id,
                    collection_id=document.collection_id,
                    chunk_index=i,
                    text=chunk,
                    embedding=embeddings[emb_i],
                    extra_metadata={},
                )
            )
            emb_i += 1

        if rows:
            self.chunk_repo.bulk_create(rows)
            logger.info("Chunks persisted", extra={"chunk_count": len(rows)})

    def _load_text(self, uri: str | None) -> str:
        logger.debug("Loading text from URI", extra={"uri_length": len(uri) if uri else 0})
        
        # Temp stub: handle file:// + plain paths + raw string
        if not uri:
            logger.warning("Empty URI provided, returning empty text")
            return ""

        try:
            if uri.startswith("file://"):
                path = Path(uri.removeprefix("file://"))
                logger.debug("Loading from file:// URI", extra={"path": str(path)})
                text = path.read_text(encoding="utf-8", errors="ignore")
                logger.debug("Text loaded from file", extra={"text_length": len(text)})
                return text

            p = Path(uri)
            if p.exists() and p.is_file():
                logger.debug("Loading from file path", extra={"path": str(p)})
                text = p.read_text(encoding="utf-8", errors="ignore")
                logger.debug("Text loaded from file", extra={"text_length": len(text)})
                return text

            # fallback: treat as raw content (dev-friendly)
            logger.debug("Treating URI as raw text content", extra={"text_length": len(uri)})
            return uri
        except Exception as e:
            logger.exception("Failed to load text from URI", extra={"uri_length": len(uri) if uri else 0, "error": str(e)})
            raise
