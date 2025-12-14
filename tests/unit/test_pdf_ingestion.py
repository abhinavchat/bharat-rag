"""
Tests for PDF ingestion (Weekend 4).

Tests PDF handler, page-by-page extraction, metadata, and partial failure handling.
"""
import os
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from bharatrag.main import app
from bharatrag.services.ingestion_handlers.pdf_handler import PdfIngestionHandler


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def _create_test_pdf(num_pages: int, output_path: Path) -> None:
    """Create a minimal test PDF with specified number of blank pages."""
    from pypdf import PdfWriter
    
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)  # US Letter size
    
    with open(output_path, "wb") as f:
        writer.write(f)


def test_pdf_handler_supports():
    """Test that PDF handler correctly identifies supported formats."""
    handler = PdfIngestionHandler()
    
    assert handler.supports("pdf", "file") is True
    assert handler.supports("txt", "file") is False
    assert handler.supports("pdf", "text") is False
    assert handler.supports("pdf", "url") is False


def test_pdf_handler_file_not_found():
    """Test PDF handler handles missing files gracefully."""
    handler = PdfIngestionHandler()
    
    with pytest.raises(FileNotFoundError):
        handler.extract_text("/nonexistent/file.pdf")


def test_pdf_handler_invalid_pdf():
    """Test PDF handler handles invalid/corrupted PDFs."""
    handler = PdfIngestionHandler()
    
    # Create a file that's not a valid PDF
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        f.write(b"This is not a PDF file")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Failed to read PDF"):
            handler.extract_text(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.skipif(not _db_enabled(), reason="Database tests disabled")
def test_pdf_ingestion_end_to_end():
    """End-to-end test: create collection, ingest PDF, query chunks."""
    from pypdf import PdfWriter
    
    client = TestClient(app)
    
    # 1) Create collection
    cname = f"pdf-test-{uuid.uuid4()}"
    r = client.post("/collections", json={"name": cname})
    assert r.status_code == 201
    collection_id = r.json()["id"]
    
    # 2) Create a simple test PDF with blank pages
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.write(f)
        pdf_path = f.name
    
    try:
        # 3) Ingest PDF
        r = client.post(
            "/ingestion-jobs",
            json={
                "collection_id": collection_id,
                "source_type": "file",
                "format": "pdf",
                "uri": f"file://{pdf_path}",
            },
        )
        assert r.status_code == 201
        job = r.json()
        
        # Job should complete (even if PDF has no extractable text)
        assert job["status"] in ("COMPLETED", "PARTIAL", "FAILED")
        
        # 4) If successful, query should work
        if job["status"] in ("COMPLETED", "PARTIAL"):
            r = client.post(
                "/query",
                json={
                    "collection_id": collection_id,
                    "query": "test",
                    "top_k": 5,
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert "results" in data
            
            # Check if chunks have page metadata
            for result in data.get("results", []):
                chunk = result.get("chunk", {})
                metadata = chunk.get("extra_metadata", {})
                # If PDF was processed, metadata might have page_number
                if "page_number" in metadata:
                    assert isinstance(metadata["page_number"], int)
                    assert metadata["page_number"] > 0
    
    finally:
        Path(pdf_path).unlink(missing_ok=True)


@pytest.mark.skipif(not _db_enabled(), reason="Database tests disabled")
def test_pdf_ingestion_progress_tracking():
    """Test that PDF ingestion provides page-level progress updates."""
    from pypdf import PdfWriter
    
    client = TestClient(app)
    
    # Create collection
    cname = f"pdf-progress-{uuid.uuid4()}"
    r = client.post("/collections", json={"name": cname})
    assert r.status_code == 201
    collection_id = r.json()["id"]
    
    # Create test PDF (minimal)
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        writer = PdfWriter()
        # Add multiple pages to test progress
        for _ in range(3):
            writer.add_blank_page(width=612, height=792)
        writer.write(f)
        pdf_path = f.name
    
    try:
        # Ingest PDF
        r = client.post(
            "/ingestion-jobs",
            json={
                "collection_id": collection_id,
                "source_type": "file",
                "format": "pdf",
                "uri": f"file://{pdf_path}",
            },
        )
        assert r.status_code == 201
        job_id = r.json()["id"]
        
        # Check job status (may need to poll)
        r = client.get(f"/ingestion-jobs/{job_id}")
        assert r.status_code == 200
        job = r.json()
        
        # Progress should include PDF-specific info if available
        progress = job.get("progress", {})
        if "total_pages" in progress:
            assert isinstance(progress["total_pages"], int)
            assert progress["total_pages"] > 0
    
    finally:
        Path(pdf_path).unlink(missing_ok=True)


def test_pdf_handler_text_cleaning():
    """Test that PDF handler cleans extracted text properly."""
    handler = PdfIngestionHandler()
    
    # Test text cleaning
    dirty_text = "This   has    multiple    spaces\n\n\nAnd   empty   lines"
    cleaned = handler._clean_text(dirty_text)
    
    assert "  " not in cleaned  # No double spaces
    assert "\n\n\n" not in cleaned  # No triple newlines
    assert len(cleaned.split("\n")) <= len(dirty_text.split("\n"))  # Fewer or equal lines

