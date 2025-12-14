from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class DocumentCreate(BaseModel):
    collection_id: UUID
    source_type: str = Field(min_length=1, max_length=32)  # file|url|text
    format: str = Field(min_length=1, max_length=32)       # pdf|md|docx|image|video|website|3d|...
    title: Optional[str] = Field(default=None, max_length=512)
    uri: Optional[str] = Field(default=None, max_length=2048)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    source_type: str
    format: str
    title: Optional[str]
    uri: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
