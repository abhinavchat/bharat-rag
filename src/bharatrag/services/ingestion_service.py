import logging
from pathlib import Path
from uuid import UUID

from bharatrag.domain.ingestion_job import IngestionJob, IngestionJobCreate
from bharatrag.domain.document import Document, DocumentCreate
from bharatrag.domain.chunk import ChunkCreate

from bharatrag.services.repositories.ingestion_job_repository import IngestionJobRepository
from bharatrag.services.repositories.document_repository import DocumentRepository
from bharatrag.services.repositories.chunk_repository import ChunkRepository
from bharatrag.services.repositories.collection_repository import CollectionRepository

from bharatrag.services.chunking.simple_chunker import SimpleChunker
from bharatrag.services.embeddings.simple_hash_embedder import SimpleHashEmbedder
from bharatrag.core.context import set_job_id, set_collection_id, set_document_id
from bharatrag.ports.ingestion_handler import IngestionHandler
from bharatrag.services.ingestion_handlers.image_handler import ImageIngestionHandler
from bharatrag.services.ingestion_handlers.pdf_handler import PdfIngestionHandler
from bharatrag.services.ingestion_handlers.text_handler import TextIngestionHandler
from bharatrag.services.ingestion_handlers.video_handler import VideoIngestionHandler
from bharatrag.services.ingestion_handlers.website_handler import WebsiteIngestionHandler

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        repo: IngestionJobRepository | None = None,
        document_repo: DocumentRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
        collection_repo: CollectionRepository | None = None,
        handlers: list[IngestionHandler] | None = None,
    ):
        self.repo = repo or IngestionJobRepository()
        self.document_repo = document_repo or DocumentRepository()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.collection_repo = collection_repo or CollectionRepository()

        self.chunker = SimpleChunker()
        self.embedder = SimpleHashEmbedder()
        
        # Register format handlers
        self.handlers: list[IngestionHandler] = handlers or [
            PdfIngestionHandler(),
            TextIngestionHandler(),
            ImageIngestionHandler(),
            VideoIngestionHandler(),
            WebsiteIngestionHandler(),
        ]

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
            result = self._store_raw(payload, job.id)
            
            # Determine final status based on result
            if result.get("status") == "PARTIAL":
                job = self.repo.update_status(
                    job.id,
                    "PARTIAL",
                    progress={"stage": "persisted", **result.get("progress", {})},
                    error_summary=result.get("error_summary"),
                )
                logger.warning("Ingestion job completed with partial success", extra={"failed_pages": result.get("failed_pages", [])})
            else:
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

    def _store_raw(self, payload: IngestionJobCreate, job_id: UUID) -> dict:
        """
        Store raw content using appropriate handler.
        
        Returns:
            dict with status information:
            - status: "COMPLETED" or "PARTIAL"
            - progress: Additional progress info
            - error_summary: Error details if partial
            - failed_pages: List of failed page numbers (for PDFs)
        """
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

        # 2) Get appropriate handler
        handler = self._get_handler(payload.format, payload.source_type)
        
        if handler:
            logger.debug(
                "Using handler for extraction",
                extra={"format": payload.format, "source_type": payload.source_type},
            )
            return self._process_with_handler(handler, payload, document, job_id)
        else:
            # Fallback to legacy text loading
            logger.debug("No handler found, using legacy text loading")
            return self._process_legacy_text(payload, document, job_id)

    def _get_handler(self, format: str, source_type: str) -> IngestionHandler | None:
        """Find handler that supports the given format and source_type."""
        for handler in self.handlers:
            if handler.supports(format, source_type):
                return handler
        return None

    def _process_with_handler(
        self,
        handler: IngestionHandler,
        payload: IngestionJobCreate,
        document: Document,
        job_id: UUID,
    ) -> dict:
        """Process ingestion using a format-specific handler."""
        # Extract text and metadata from handler
        extracted_pages = handler.extract_text(payload.uri)
        
        total_pages = len(extracted_pages)
        failed_pages: list[int] = []
        successful_chunks = 0
        
        logger.info(
            "Content extracted by handler",
            extra={
                "format": payload.format,
                "total_pages": total_pages,
            },
        )
        
        # Process each extracted page/text segment
        all_chunks: list[tuple[str, dict]] = []
        
        for page_idx, (text, page_metadata) in enumerate(extracted_pages):
            # Update progress for PDFs
            if payload.format == "pdf" and "page_number" in page_metadata:
                page_num = page_metadata.get("page_number", page_idx + 1)
                self.repo.update_status(
                    job_id,
                    "RUNNING",
                    progress={
                        "stage": "extracting",
                        "current_page": page_num,
                        "total_pages": page_metadata.get("total_pages", total_pages),
                        "pages_processed": page_idx + 1,
                    },
                )
                logger.debug(
                    "Processing PDF page",
                    extra={
                        "page_number": page_num,
                        "text_length": len(text),
                    },
                )
            
            # Track failed pages (empty text with error metadata)
            if not text and page_metadata.get("extraction_error"):
                failed_pages.append(page_metadata.get("page_number", page_idx + 1))
                logger.warning(
                    "Skipping failed page",
                    extra={
                        "page_number": page_metadata.get("page_number"),
                        "error": page_metadata.get("extraction_error"),
                    },
                )
                continue
            
            # Chunk this page's text
            chunks = self.chunker.chunk(text)
            for chunk_idx, (_, chunk_text) in enumerate(chunks):
                if chunk_text:
                    # Merge page metadata with chunk info
                    chunk_metadata = {
                        **page_metadata,
                        "chunk_index_in_page": chunk_idx,
                    }
                    all_chunks.append((chunk_text, chunk_metadata))
        
        if not all_chunks:
            # No valid chunks extracted
            if failed_pages:
                return {
                    "status": "PARTIAL",
                    "progress": {"failed_pages": failed_pages, "total_pages": total_pages},
                    "error_summary": f"All pages failed extraction. Failed pages: {failed_pages}",
                    "failed_pages": failed_pages,
                }
            else:
                return {
                    "status": "COMPLETED",
                    "progress": {},
                    "error_summary": None,
                    "failed_pages": [],
                }
        
        # Update progress
        self.repo.update_status(
            job_id, "RUNNING", progress={"stage": "chunked", "chunks": len(all_chunks)}
        )
        logger.info("Content chunked", extra={"chunk_count": len(all_chunks)})

        # 4) Embed all chunks
        chunk_texts = [chunk for chunk, _ in all_chunks]
        embeddings = self.embedder.embed(chunk_texts)
        self.repo.update_status(job_id, "RUNNING", progress={"stage": "embedded"})
        logger.info("Chunks embedded", extra={"embedding_count": len(embeddings)})

        # 5) Persist chunks with metadata
        rows: list[ChunkCreate] = []
        for chunk_idx, ((chunk_text, chunk_metadata), embedding) in enumerate(zip(all_chunks, embeddings)):
            rows.append(
                ChunkCreate(
                    document_id=document.id,
                    collection_id=document.collection_id,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    embedding=embedding,
                    extra_metadata=chunk_metadata,
                )
            )
            successful_chunks += 1

        if rows:
            self.chunk_repo.bulk_create(rows)
            logger.info("Chunks persisted", extra={"chunk_count": len(rows)})
        
        # Determine status
        result: dict = {
            "status": "COMPLETED",
            "progress": {},
            "error_summary": None,
            "failed_pages": [],
        }
        
        if failed_pages and successful_chunks > 0:
            # Partial success: some pages failed but we have chunks
            result["status"] = "PARTIAL"
            result["progress"] = {
                "failed_pages": failed_pages,
                "total_pages": total_pages,
                "successful_chunks": successful_chunks,
            }
            result["error_summary"] = f"Some pages failed extraction. Failed pages: {failed_pages}"
            result["failed_pages"] = failed_pages
        
        return result

    def _process_legacy_text(
        self,
        payload: IngestionJobCreate,
        document: Document,
        job_id: UUID,
    ) -> dict:
        """Legacy text processing for formats without handlers."""
        # 2) Load text (Weekend-3 fallback)
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
        
        return {
            "status": "COMPLETED",
            "progress": {},
            "error_summary": None,
            "failed_pages": [],
        }

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
