"""
Image ingestion handler for Weekend 5.

Extracts text from image files using OCR with metadata tracking.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import easyocr
    from PIL import Image
except ImportError:
    easyocr = None  # type: ignore
    Image = None  # type: ignore

from bharatrag.ports.ingestion_handler import IngestionHandler

logger = logging.getLogger(__name__)


class ImageIngestionHandler(IngestionHandler):
    """
    Handler for image file ingestion.
    
    Extracts text using OCR with image metadata.
    Handles errors gracefully to support partial success.
    """

    def __init__(self):
        """Initialize OCR reader (lazy-loaded on first use)."""
        self._reader: Any = None
        self._reader_initialized = False

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract text from image file using OCR.
        
        Args:
            uri: File path or file:// URI to image file
            
        Returns:
            List of (text, metadata) tuples where metadata includes:
            - filename: Image filename
            - format: Image format (png, jpg, etc.)
            - width: Image width in pixels
            - height: Image height in pixels
            - extraction_method: "easyocr"
            - language: Detected language (if available)
        
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If URI is invalid or OCR library not available
        """
        if easyocr is None or Image is None:
            raise ValueError(
                "OCR dependencies not installed. Install easyocr and Pillow: "
                "pip install easyocr Pillow"
            )

        # Resolve file path
        file_path = self._resolve_path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        logger.debug("Loading image file", extra={"path": str(file_path)})
        
        try:
            # Load image to get metadata
            img = Image.open(str(file_path))
            width, height = img.size
            format_name = img.format or file_path.suffix[1:].lower() if file_path.suffix else "unknown"
            
            logger.info(
                "Image loaded successfully",
                extra={
                    "path": str(file_path),
                    "width": width,
                    "height": height,
                    "format": format_name,
                },
            )
            
            # Initialize OCR reader (lazy load)
            if not self._reader_initialized:
                logger.debug("Initializing OCR reader")
                # Use English and Hindi for better Indian language support
                self._reader = easyocr.Reader(['en', 'hi'], gpu=False)
                self._reader_initialized = True
                logger.info("OCR reader initialized")
            
            # Perform OCR
            logger.debug("Performing OCR on image")
            ocr_results = self._reader.readtext(str(file_path))
            
            # Extract text from OCR results
            # OCR results are list of (bbox, text, confidence) tuples
            ocr_text_parts = []
            for bbox, text, confidence in ocr_results:
                if text.strip():
                    ocr_text_parts.append(text.strip())
                    logger.debug(
                        "OCR result",
                        extra={
                            "text_preview": text[:50],
                            "confidence": confidence,
                        },
                    )
            
            # Combine all OCR text
            full_text = "\n".join(ocr_text_parts)
            
            if not full_text.strip():
                logger.warning("No text extracted from image", extra={"path": str(file_path)})
                full_text = ""  # Return empty text if no OCR results
            
            metadata: dict[str, Any] = {
                "source": "image",
                "filename": file_path.name,
                "format": format_name,
                "width": width,
                "height": height,
                "extraction_method": "easyocr",
                "ocr_results_count": len(ocr_results),
            }
            
            # Add language if detected (easyocr doesn't directly provide this, but we can infer)
            # For now, we'll note the languages we're using
            metadata["ocr_languages"] = ["en", "hi"]
            
            logger.info(
                "Image OCR completed",
                extra={
                    "path": str(file_path),
                    "text_length": len(full_text),
                    "ocr_results": len(ocr_results),
                },
            )
            
            return [(full_text, metadata)]
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.exception("Failed to extract text from image", extra={"path": str(file_path)})
            raise ValueError(f"Failed to extract text from image: {e}") from e

    def supports(self, format: str, source_type: str) -> bool:
        """Check if this handler supports image formats."""
        return format in ("png", "jpg", "jpeg") and source_type == "file"

    def _resolve_path(self, uri: str) -> Path:
        """Resolve URI to file path."""
        if uri.startswith("file://"):
            return Path(uri.removeprefix("file://"))
        return Path(uri)

