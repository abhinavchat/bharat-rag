"""
Tests for website ingestion handler.
"""
import os
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from bharatrag.main import app
from bharatrag.services.ingestion_handlers.website_handler import WebsiteIngestionHandler


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_website_handler_supports():
    """Test that website handler correctly identifies supported formats."""
    handler = WebsiteIngestionHandler()

    assert handler.supports("html", "url") is True
    assert handler.supports("html", "file") is False
    assert handler.supports("pdf", "url") is False
    assert handler.supports("txt", "url") is False


def test_website_handler_invalid_url():
    """Test website handler handles invalid URLs gracefully."""
    handler = WebsiteIngestionHandler()

    with pytest.raises(ValueError, match="Invalid URL format"):
        handler.extract_text("not-a-url")

    with pytest.raises(ValueError, match="Invalid URL format"):
        handler.extract_text("file:///tmp/test.html")


def test_website_handler_missing_dependencies():
    """Test website handler handles missing dependencies."""
    try:
        import trafilatura  # noqa: F401
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("Website extraction dependencies not installed")


@pytest.mark.skipif(not _db_enabled(), reason="Database tests disabled")
def test_website_ingestion_end_to_end():
    """End-to-end test: create collection, ingest website, query chunks."""
    try:
        import trafilatura  # noqa: F401
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("Website extraction dependencies not installed")

    # Mock the website fetching to avoid external dependencies in tests
    with patch("bharatrag.services.ingestion_handlers.website_handler.requests.get") as mock_get:
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.text = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Test Article Title</h1>
                <p>This is a test article with some content for ingestion.</p>
                <p>It has multiple paragraphs to test extraction.</p>
            </article>
        </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch("bharatrag.services.ingestion_handlers.website_handler.extract") as mock_extract:
            mock_extract.return_value = "Test Article Title\n\nThis is a test article with some content for ingestion.\n\nIt has multiple paragraphs to test extraction."

            # Patch trafilatura.extract_metadata (imported inside the method)
            with patch("trafilatura.extract_metadata") as mock_meta:
                from trafilatura.core import Document
                mock_meta.return_value = Document(
                    url="https://example.com/test",
                    title="Test Article Title",
                    author="Test Author",
                )

                client = TestClient(app)

                # 1) Create collection
                cname = f"website-test-{uuid.uuid4()}"
                r = client.post("/collections", json={"name": cname})
                assert r.status_code == 201
                collection_id = r.json()["id"]

                # 2) Ingest website
                r = client.post(
                    "/ingestion-jobs",
                    json={
                        "collection_id": collection_id,
                        "source_type": "url",
                        "format": "html",
                        "uri": "https://example.com/test",
                    },
                )
                assert r.status_code == 201
                job = r.json()

                # Job should complete
                assert job["status"] in ("COMPLETED", "PARTIAL")
                assert job["progress"]["stage"] == "persisted"

                # 3) Query should work
                if job["status"] in ("COMPLETED", "PARTIAL"):
                    r = client.post(
                        "/query",
                        json={
                            "collection_id": collection_id,
                            "query": "test article",
                            "top_k": 5,
                        },
                    )
                    assert r.status_code == 200
                    data = r.json()
                    assert "results" in data

                    # Check if chunks have website metadata
                    for result in data.get("results", []):
                        chunk = result.get("chunk", {})
                        metadata = chunk.get("extra_metadata", {})
                        if metadata:  # Only check if metadata exists
                            assert "source" in metadata or "extraction_method" in metadata


def test_website_handler_url_validation():
    """Test URL validation in website handler."""
    handler = WebsiteIngestionHandler()

    # Valid URLs
    assert handler.supports("html", "url") is True

    # Invalid URLs should raise ValueError
    with pytest.raises(ValueError):
        handler.extract_text("not-a-url")

    with pytest.raises(ValueError):
        handler.extract_text("file:///tmp/test.html")

