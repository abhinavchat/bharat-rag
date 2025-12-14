"""
Video ingestion handler for Weekend 5.

Extracts audio from video and transcribes using Whisper with timestamp metadata.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

try:
    import whisper
    from moviepy import VideoFileClip
except ImportError:
    whisper = None  # type: ignore
    VideoFileClip = None  # type: ignore

from bharatrag.ports.ingestion_handler import IngestionHandler

logger = logging.getLogger(__name__)


class VideoIngestionHandler(IngestionHandler):
    """
    Handler for video file ingestion.
    
    Extracts audio, transcribes with Whisper, and provides timestamp metadata.
    Handles errors gracefully.
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize video handler.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       Default: "base" for balance of speed and accuracy
        """
        self.model_size = model_size
        self._model: Any = None
        self._model_loaded = False

    def extract_text(self, uri: str) -> list[tuple[str, dict]]:
        """
        Extract audio from video and transcribe using Whisper.
        
        Args:
            uri: File path or file:// URI to video file
            
        Returns:
            List of (text, metadata) tuples where metadata includes:
            - filename: Video filename
            - format: Video format (mp4, etc.)
            - timestamp_start: Start time in seconds
            - timestamp_end: End time in seconds
            - segment_index: Segment number (0-indexed)
            - extraction_method: "whisper"
            - language: Detected language code
        
        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If URI is invalid or transcription fails
        """
        if whisper is None or VideoFileClip is None:
            raise ValueError(
                "Video processing dependencies not installed. "
                "Install openai-whisper and moviepy: pip install openai-whisper moviepy"
            )
        
        # Check if ffmpeg is available (required by moviepy)
        import shutil
        if shutil.which("ffmpeg") is None:
            raise ValueError(
                "ffmpeg is not installed. MoviePy requires ffmpeg to extract audio from videos. "
                "Install ffmpeg:\n"
                "  macOS: brew install ffmpeg\n"
                "  Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "  Windows: Download from https://ffmpeg.org/download.html"
            )

        # Resolve file path
        file_path = self._resolve_path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        logger.debug("Loading video file", extra={"path": str(file_path)})
        
        audio_path: Path | None = None
        
        try:
            # Load video to extract audio
            logger.debug("Extracting audio from video")
            video = VideoFileClip(str(file_path))
            
            if video.audio is None:
                logger.warning("Video has no audio track", extra={"path": str(file_path)})
                video.close()
                # Return empty transcript with metadata
                return [(
                    "",
                    {
                        "source": "video",
                        "filename": file_path.name,
                        "format": file_path.suffix[1:].lower() if file_path.suffix else "unknown",
                        "extraction_method": "whisper",
                        "error": "No audio track found in video",
                    },
                )]
            
            duration = video.duration
            logger.info(
                "Video loaded successfully",
                extra={
                    "path": str(file_path),
                    "duration": duration,
                },
            )
            
            # Extract audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                audio_path = Path(tmp_audio.name)
                logger.debug("Extracting audio to temporary file", extra={"audio_path": str(audio_path)})
                # moviepy 2.x doesn't support verbose/logger parameters
                video.audio.write_audiofile(str(audio_path))
            
            video.close()
            logger.debug("Audio extracted successfully")
            
            # Load Whisper model (lazy load)
            if not self._model_loaded:
                logger.info(f"Loading Whisper model: {self.model_size}")
                self._model = whisper.load_model(self.model_size)
                self._model_loaded = True
                logger.info("Whisper model loaded")
            
            # Transcribe audio
            logger.debug("Transcribing audio with Whisper")
            result = self._model.transcribe(
                str(audio_path),
                verbose=False,
            )
            
            # Extract segments with timestamps
            segments = result.get("segments", [])
            language = result.get("language", "unknown")
            
            logger.info(
                "Transcription completed",
                extra={
                    "path": str(file_path),
                    "segments_count": len(segments),
                    "language": language,
                    "duration": duration,
                },
            )
            
            # Convert segments to (text, metadata) tuples
            results: list[tuple[str, dict]] = []
            
            for i, segment in enumerate(segments):
                text = segment.get("text", "").strip()
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                
                if not text:
                    continue
                
                metadata: dict[str, Any] = {
                    "source": "video",
                    "filename": file_path.name,
                    "format": file_path.suffix[1:].lower() if file_path.suffix else "unknown",
                    "timestamp_start": start_time,
                    "timestamp_end": end_time,
                    "segment_index": i,
                    "extraction_method": "whisper",
                    "language": language,
                }
                
                results.append((text, metadata))
                
                logger.debug(
                    "Transcription segment",
                    extra={
                        "segment_index": i,
                        "start": start_time,
                        "end": end_time,
                        "text_preview": text[:50],
                    },
                )
            
            # If no segments, return full transcript as single chunk
            if not results:
                full_text = result.get("text", "").strip()
                if full_text:
                    results.append((
                        full_text,
                        {
                            "source": "video",
                            "filename": file_path.name,
                            "format": file_path.suffix[1:].lower() if file_path.suffix else "unknown",
                            "timestamp_start": 0.0,
                            "timestamp_end": duration,
                            "segment_index": 0,
                            "extraction_method": "whisper",
                            "language": language,
                        },
                    ))
            
            return results
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.exception("Failed to extract text from video", extra={"path": str(file_path)})
            raise ValueError(f"Failed to extract text from video: {e}") from e
        finally:
            # Clean up temporary audio file
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    logger.debug("Cleaned up temporary audio file")
                except Exception as cleanup_error:
                    logger.warning(
                        "Failed to clean up temporary audio file",
                        extra={"path": str(audio_path), "error": str(cleanup_error)},
                    )

    def supports(self, format: str, source_type: str) -> bool:
        """Check if this handler supports video formats."""
        return format in ("mp4", "avi", "mov") and source_type == "file"

    def _resolve_path(self, uri: str) -> Path:
        """Resolve URI to file path."""
        if uri.startswith("file://"):
            return Path(uri.removeprefix("file://"))
        return Path(uri)

