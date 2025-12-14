from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class ChunkCreate(BaseModel):
    document_id: UUID
    collection_id: UUID
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    embedding: List[float]
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata")


class Chunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    collection_id: UUID
    chunk_index: int
    text: str
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata")
    created_at: datetime

class ChunkSearchResult(BaseModel):
    chunk: Chunk
    score: float
