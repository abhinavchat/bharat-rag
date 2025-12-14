"""
Text ingestion handler for plain text, markdown, and raw content.

This handler supports text formats that can be read directly as strings.
"""
from __future__ import annotations

import logging
from pathlib import Path

from bharatrag.ports.ingestion_handler import IngestionHandler

logger = logging.getLogger(__name__)


class TextIngestionHandler(IngestionHandler):
    """
    Handler for plain text formats (txt, md, raw strings).
    
    Reads text directly from files or treats URI as raw content.
    """

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract text from file or raw string.
        
        Args:
            uri: File path, file:// URI, or raw text content
        
        Returns:
            List with single (text, metadata) tuple where metadata includes:
            - source: "file" or "raw_text"
            - extraction_method: "text_handler"
        """
        if not uri:
            logger.warning("Empty URI provided, returning empty text")
            return [("", {"source": "raw_text", "extraction_method": "text_handler"})]

        try:
            # Try to resolve as file path
            file_path = self._resolve_path(uri)
            
            if file_path.exists() and file_path.is_file():
                logger.debug("Loading text from file", extra={"path": str(file_path)})
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                metadata = {
                    "source": "file",
                    "extraction_method": "text_handler",
                    "file_path": str(file_path),
                }
                logger.debug("Text loaded from file", extra={"text_length": len(text)})
                return [(text, metadata)]
            
            # Fallback: treat as raw content
            logger.debug("Treating URI as raw text content", extra={"text_length": len(uri)})
            return [
                (
                    uri,
                    {
                        "source": "raw_text",
                        "extraction_method": "text_handler",
                    },
                )
            ]
            
        except Exception as e:
            logger.exception("Failed to load text from URI", extra={"uri_length": len(uri), "error": str(e)})
            raise

    def supports(self, format: str, source_type: str) -> bool:
        """
        Check if this handler supports text formats.
        
        Supports:
        - txt, md formats with file source_type
        - text source_type (raw content)
        """
        if source_type == "text":
            return True  # Raw text content
        if source_type == "file" and format in ("txt", "md"):
            return True
        return False

    def _resolve_path(self, uri: str) -> Path:
        """Resolve URI to file path."""
        if uri.startswith("file://"):
            return Path(uri.removeprefix("file://"))
        return Path(uri)

