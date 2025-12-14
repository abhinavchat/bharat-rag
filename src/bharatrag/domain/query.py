from __future__ import annotations

from typing import Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field

from bharatrag.domain.chunk import ChunkSearchResult


class QueryRequest(BaseModel):
    collection_id: UUID
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    results: list[ChunkSearchResult]
    debug: Dict[str, Any] = Field(default_factory=dict)
