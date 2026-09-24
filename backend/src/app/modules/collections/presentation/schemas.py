from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.collections.domain import Collection


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)


class CollectionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, collection: Collection) -> "CollectionResponse":
        return cls(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )
