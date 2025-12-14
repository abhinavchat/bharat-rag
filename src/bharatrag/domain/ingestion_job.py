from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


JobStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "PARTIAL", "CANCELED"]

# v0.1 protocol-friendly vocab (expand later)
SourceType = Literal["file", "text", "url"]
DocFormat = Literal[
    "txt", "md", "pdf",
    "docx",
    "png", "jpg", "jpeg",
    "html",
    "mp4"
]


class IngestionJobCreate(BaseModel):
    collection_id: UUID = Field(
            ...,
            description="Target collection for this ingestion job. Create one via POST /collections first.",
            examples=["11111111-1111-1111-1111-111111111111"],
        )
    
    source_type: SourceType = Field(
        ...,
        description="Where the content comes from.",
        examples=["file"],
    )
    
    format: DocFormat = Field(
        ...,
        description="Content format (used to pick the right ingestor).",
        examples=["txt"],
    )

    uri: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Optional URI for the source (file://, https://, s3:// etc).",
        examples=["file://notes.txt"],
    )


class IngestionJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    document_id: Optional[UUID] = None
    source_type: SourceType
    format: DocFormat
    status: JobStatus
    progress: Dict[str, Any] = Field(default_factory=dict)
    error_summary: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
