"""
Website ingestion handler for Weekend 5.

Extracts article content from web pages with metadata tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

try:
    import trafilatura
    import requests
    from trafilatura import extract
except ImportError:
    trafilatura = None  # type: ignore
    requests = None  # type: ignore
    extract = None  # type: ignore

from bharatrag.ports.ingestion_handler import IngestionHandler

logger = logging.getLogger(__name__)


class WebsiteIngestionHandler(IngestionHandler):
    """
    Handler for website/URL ingestion.
    
    Extracts article content from web pages with metadata.
    Handles errors gracefully.
    """

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract article text from a web page URL.
        
        Args:
            uri: HTTP/HTTPS URL to web page
            
        Returns:
            List of (text, metadata) tuples where metadata includes:
            - canonical_url: Canonical URL of the page
            - title: Page/article title
            - author: Author name (if available)
            - extraction_method: "trafilatura"
            - fetched_at: ISO timestamp of when page was fetched
        
        Raises:
            ValueError: If URL is invalid or extraction fails
        """
        if trafilatura is None or requests is None:
            raise ValueError(
                "Website extraction dependencies not installed. "
                "Install trafilatura and requests: pip install trafilatura requests"
            )

        # Validate URL
        if not uri.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL format: {uri}. Must start with http:// or https://")
        
        logger.debug("Fetching webpage", extra={"url": uri})
        
        try:
            # Fetch webpage using requests with timeout, then extract with trafilatura
            # trafilatura's fetch_url doesn't support timeout parameter
            response = requests.get(uri, timeout=30, headers={"User-Agent": "Bharat-RAG/0.0.1"})
            response.raise_for_status()
            
            downloaded = response.text
            
            if not downloaded:
                logger.error("Failed to fetch webpage", extra={"url": uri})
                raise ValueError(f"Failed to fetch webpage: {uri}")
            
            logger.debug("Webpage fetched successfully", extra={"url": uri})
            
            # Extract article content
            article = extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
            )
            
            if not article or not article.strip():
                logger.warning("No article content extracted", extra={"url": uri})
                # Try to get at least some text from the raw HTML
                # This is a fallback - trafilatura might have failed to extract
                # but we can still try to get basic text
                article = ""
            
            # Get metadata from trafilatura
            # Note: trafilatura's extract_metadata can provide more info
            canonical_url = uri
            title = ""
            author = ""
            
            try:
                from trafilatura import extract_metadata
                metadata_dict = extract_metadata(downloaded)
                
                if metadata_dict:
                    canonical_url = metadata_dict.url if metadata_dict.url else uri
                    title = metadata_dict.title if metadata_dict.title else ""
                    author = metadata_dict.author if metadata_dict.author else ""
            except Exception as meta_error:
                logger.warning(
                    "Failed to extract metadata",
                    extra={"url": uri, "error": str(meta_error)},
                )
            
            metadata: dict[str, Any] = {
                "source": "website",
                "canonical_url": canonical_url,
                "title": title,
                "author": author if author else None,
                "extraction_method": "trafilatura",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            
            logger.info(
                "Website extraction completed",
                extra={
                    "url": uri,
                    "canonical_url": canonical_url,
                    "title": title[:100] if title else None,
                    "text_length": len(article),
                },
            )
            
            return [(article, metadata)]
            
        except requests.exceptions.RequestException as e:
            logger.error("HTTP error fetching webpage", extra={"url": uri, "error": str(e)})
            raise ValueError(f"Failed to fetch webpage: {e}") from e
        except Exception as e:
            logger.exception("Failed to extract content from webpage", extra={"url": uri})
            raise ValueError(f"Failed to extract content from webpage: {e}") from e

    def supports(self, format: str, source_type: str) -> bool:
        """Check if this handler supports website/URL format."""
        return format == "html" and source_type == "url"

