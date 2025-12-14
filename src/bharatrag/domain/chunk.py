from __future__ import annotations
from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class ChunkCreate(BaseModel):
    document_id: UUID
    text: str = Field(min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    text: str
    metadata: Dict[str, Any]
    created_at: datetime
