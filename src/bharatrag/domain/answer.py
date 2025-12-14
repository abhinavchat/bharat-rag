from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    collection_id: UUID
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    """Citation metadata for source attribution."""
    document_id: UUID
    chunk_id: UUID
    chunk_index: int


class AnswerResponse(BaseModel):
    """Response containing synthesized answer with citations and context."""
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)