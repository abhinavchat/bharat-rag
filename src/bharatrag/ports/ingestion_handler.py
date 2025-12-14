"""
Protocol for format-specific ingestion handlers.

Each handler is responsible for extracting text and metadata from a specific
file format (PDF, DOCX, images, etc.).
"""
from __future__ import annotations

from typing import Protocol


class IngestionHandler(Protocol):
    """
    Protocol for format-specific ingestion handlers.
    
    Handlers extract text and format-specific metadata from source URIs.
    """

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract text and metadata from source.
        
        Args:
            uri: Source URI (file:// path, URL, etc.)
        
        Returns:
            List of (text, metadata) tuples where:
            - text: Extracted text content
            - metadata: Format-specific metadata (e.g., page_number for PDFs)
        
        Raises:
            ValueError: If URI is invalid or unsupported
            FileNotFoundError: If file doesn't exist
            Exception: Format-specific errors (e.g., encrypted PDF)
        """
        ...

    def supports(self, format: str, source_type: str) -> bool:
        """
        Check if this handler supports the given format and source_type.
        
        Args:
            format: Document format (e.g., "pdf", "txt", "docx")
            source_type: Source type (e.g., "file", "text", "url")
        
        Returns:
            True if this handler can process the given format/source_type
        """
        ...

