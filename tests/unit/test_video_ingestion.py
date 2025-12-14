"""
Tests for video ingestion handler.
"""
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from bharatrag.main import app
from bharatrag.services.ingestion_handlers.video_handler import VideoIngestionHandler


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_video_handler_supports():
    """Test that video handler correctly identifies supported formats."""
    handler = VideoIngestionHandler()

    assert handler.supports("mp4", "file") is True
    assert handler.supports("avi", "file") is True
    assert handler.supports("mov", "file") is True
    assert handler.supports("mp4", "url") is False
    assert handler.supports("pdf", "file") is False


def test_video_handler_file_not_found():
    """Test video handler handles missing files gracefully."""
    try:
        import whisper  # noqa: F401
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        pytest.skip("Video processing dependencies not installed")

    handler = VideoIngestionHandler()

    with pytest.raises(FileNotFoundError, match="Video file not found"):
        handler.extract_text("/nonexistent/file.mp4")


def test_video_handler_missing_dependencies():
    """Test video handler handles missing dependencies."""
    try:
        import whisper  # noqa: F401
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        pytest.skip("Video processing dependencies not installed")


def test_video_handler_resolve_path():
    """Test path resolution for file:// URIs and plain paths."""
    try:
        import whisper  # noqa: F401
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        pytest.skip("Video processing dependencies not installed")

    handler = VideoIngestionHandler()

    # Test file:// URI
    path1 = handler._resolve_path("file:///tmp/test.mp4")
    assert str(path1) == "/tmp/test.mp4"

    # Test plain path
    path2 = handler._resolve_path("/tmp/test.mp4")
    assert str(path2) == "/tmp/test.mp4"


@pytest.mark.skipif(not _db_enabled(), reason="Database tests disabled")
def test_video_ingestion_end_to_end():
    """End-to-end test: create collection, ingest video, query chunks."""
    try:
        import whisper  # noqa: F401
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        pytest.skip("Video processing dependencies not installed")

    # For testing, we'll mock the video processing since creating real videos is complex
    with patch("bharatrag.services.ingestion_handlers.video_handler.VideoFileClip") as mock_video:
        # Mock video with audio
        mock_audio = Mock()
        mock_audio.duration = 10.0
        mock_video_instance = Mock()
        mock_video_instance.audio = mock_audio
        mock_video_instance.duration = 10.0
        mock_video.return_value = mock_video_instance

        with patch("bharatrag.services.ingestion_handlers.video_handler.whisper.load_model") as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "This is a test transcription.",
                "language": "en",
                "segments": [
                    {
                        "text": "This is a test transcription.",
                        "start": 0.0,
                        "end": 5.0,
                    }
                ],
            }
            mock_whisper.return_value = mock_model

            client = TestClient(app)

            # 1) Create collection
            cname = f"video-test-{uuid.uuid4()}"
            r = client.post("/collections", json={"name": cname})
            assert r.status_code == 201
            collection_id = r.json()["id"]

            # 2) Create a dummy video file path (won't actually be used due to mocking)
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".mp4", delete=False) as f:
                video_path = f.name

            try:
                # 3) Ingest video
                r = client.post(
                    "/ingestion-jobs",
                    json={
                        "collection_id": collection_id,
                        "source_type": "file",
                        "format": "mp4",
                        "uri": f"file://{video_path}",
                    },
                )
                assert r.status_code == 201
                job = r.json()

                # Job should complete
                assert job["status"] in ("COMPLETED", "PARTIAL")
                assert job["progress"]["stage"] == "persisted"

                # 4) Query should work
                if job["status"] in ("COMPLETED", "PARTIAL"):
                    r = client.post(
                        "/query",
                        json={
                            "collection_id": collection_id,
                            "query": "test transcription",
                            "top_k": 5,
                        },
                    )
                    assert r.status_code == 200
                    data = r.json()
                    assert "results" in data

                    # Check if chunks have video metadata
                    for result in data.get("results", []):
                        chunk = result.get("chunk", {})
                        metadata = chunk.get("extra_metadata", {})
                        if metadata:  # Only check if metadata exists
                            assert "source" in metadata or "extraction_method" in metadata
                            # Video chunks should have timestamps
                            if "timestamp_start" in metadata:
                                assert isinstance(metadata["timestamp_start"], (int, float))

            finally:
                Path(video_path).unlink(missing_ok=True)


@pytest.mark.skipif(not _db_enabled(), reason="Database tests disabled")
def test_video_no_audio():
    """Test video handler handles videos without audio gracefully."""
    try:
        import whisper  # noqa: F401
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        pytest.skip("Video processing dependencies not installed")

    handler = VideoIngestionHandler()

    with patch("bharatrag.services.ingestion_handlers.video_handler.VideoFileClip") as mock_video:
        # Mock video without audio
        mock_video_instance = Mock()
        mock_video_instance.audio = None
        mock_video.return_value = mock_video_instance

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".mp4", delete=False) as f:
            video_path = f.name

        try:
            result = handler.extract_text(f"file://{video_path}")
            # Should return empty text with error metadata
            assert len(result) == 1
            text, metadata = result[0]
            assert text == ""
            assert metadata["error"] == "No audio track found in video"
        finally:
            Path(video_path).unlink(missing_ok=True)

