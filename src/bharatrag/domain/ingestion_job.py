from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


JobStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "PARTIAL", "CANCELED"]


class IngestionJobCreate(BaseModel):
    collection_id: UUID
    source_type: str = Field(min_length=1, max_length=32)
    format: str = Field(min_length=1, max_length=32)
    # Optional: if you create Document upfront; otherwise set later
    document_id: Optional[UUID] = None


class IngestionJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    document_id: Optional[UUID]
    source_type: str
    format: str
    status: JobStatus
    progress: Dict[str, Any]
    error_summary: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
