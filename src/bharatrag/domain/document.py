from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DocumentCreate(BaseModel):
    collection_id: UUID
    source_type: str = Field(min_length=1, max_length=32)
    format: str = Field(min_length=1, max_length=32)

    title: Optional[str] = Field(default=None, max_length=512)
    uri: Optional[str] = Field(default=None, max_length=2048)

    # accept "metadata" from input, store it internally as extra_metadata
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata",
    )

    model_config = ConfigDict(populate_by_name=True)


class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    collection_id: UUID
    source_type: str
    format: str

    title: Optional[str]
    uri: Optional[str]

    # output as "metadata" (but DO NOT use alias="metadata")
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="metadata",
    )

    created_at: datetime
    updated_at: datetime
