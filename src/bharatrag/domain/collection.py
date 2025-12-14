from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class Collection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
