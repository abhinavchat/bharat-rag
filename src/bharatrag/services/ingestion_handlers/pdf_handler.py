"""
PDF ingestion handler for Weekend 4.

Extracts text from PDF files page-by-page with metadata tracking.
"""
from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError, WrongPasswordError, FileNotDecryptedError

from bharatrag.ports.ingestion_handler import IngestionHandler

logger = logging.getLogger(__name__)


class PdfIngestionHandler(IngestionHandler):
    """
    Handler for PDF file ingestion.
    
    Extracts text page-by-page with page number metadata.
    Handles errors gracefully to support partial success.
    """

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract text from PDF file page-by-page.
        
        Args:
            uri: File path or file:// URI to PDF file
        
        Returns:
            List of (text, metadata) tuples where metadata includes:
            - page_number: 1-indexed page number
            - total_pages: Total number of pages in PDF
            - extraction_method: "pypdf"
        
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If URI is invalid
            PdfEncryptionError: If PDF is encrypted (no password provided)
        """
        # Resolve file path
        file_path = self._resolve_path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        logger.debug("Opening PDF file", extra={"path": str(file_path)})
        
        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)
            
            logger.info(
                "PDF opened successfully",
                extra={"total_pages": total_pages, "path": str(file_path)},
            )
            
            results: list[tuple[str, dict]] = []
            failed_pages: list[int] = []
            
            # Extract text page-by-page
            for page_num in range(total_pages):
                try:
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Clean up text (remove excessive whitespace)
                    text = self._clean_text(text)
                    
                    metadata = {
                        "page_number": page_num + 1,  # 1-indexed
                        "total_pages": total_pages,
                        "extraction_method": "pypdf",
                    }
                    
                    results.append((text, metadata))
                    
                    logger.debug(
                        "Page extracted successfully",
                        extra={
                            "page_number": page_num + 1,
                            "text_length": len(text),
                        },
                    )
                    
                except Exception as e:
                    # Log page-level error but continue processing
                    failed_pages.append(page_num + 1)
                    logger.warning(
                        "Failed to extract page",
                        extra={
                            "page_number": page_num + 1,
                            "error": str(e),
                        },
                    )
                    # Add empty text for failed page to maintain page order
                    results.append(
                        (
                            "",
                            {
                                "page_number": page_num + 1,
                                "total_pages": total_pages,
                                "extraction_method": "pypdf",
                                "extraction_error": str(e),
                            },
                        )
                    )
            
            if failed_pages:
                logger.warning(
                    "PDF extraction completed with page-level errors",
                    extra={
                        "total_pages": total_pages,
                        "failed_pages": failed_pages,
                        "successful_pages": total_pages - len(failed_pages),
                    },
                )
            else:
                logger.info(
                    "PDF extraction completed successfully",
                    extra={"total_pages": total_pages},
                )
            
            return results
            
        except (WrongPasswordError, FileNotDecryptedError) as e:
            logger.error("PDF is encrypted", extra={"path": str(file_path), "error": str(e)})
            raise ValueError(f"PDF is encrypted and password is required: {file_path}") from e
        except PdfReadError as e:
            logger.error("PDF read error", extra={"path": str(file_path), "error": str(e)})
            raise ValueError(f"Failed to read PDF file (may be corrupted): {file_path}") from e
        except Exception as e:
            logger.exception("Unexpected error extracting PDF", extra={"path": str(file_path)})
            raise

    def supports(self, format: str, source_type: str) -> bool:
        """Check if this handler supports PDF format."""
        return format == "pdf" and source_type == "file"

    def _resolve_path(self, uri: str) -> Path:
        """Resolve URI to file path."""
        if uri.startswith("file://"):
            return Path(uri.removeprefix("file://"))
        return Path(uri)

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Removes excessive whitespace while preserving structure.
        """
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        import re
        
        # Preserve newlines but normalize spaces
        lines = text.split("\n")
        cleaned_lines = [re.sub(r"\s+", " ", line.strip()) for line in lines]
        # Remove empty lines
        cleaned_lines = [line for line in cleaned_lines if line]
        
        return "\n".join(cleaned_lines)

