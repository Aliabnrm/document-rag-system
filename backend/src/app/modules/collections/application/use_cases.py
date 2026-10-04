from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.collections.domain import Collection
from app.platform.errors import NotFoundError


class CollectionRepository(Protocol):
    async def create(
        self,
        *,
        owner_id: UUID,
        name: str,
        description: str | None,
    ) -> Collection: ...

    async def get_owned(self, *, collection_id: UUID, owner_id: UUID) -> Collection | None: ...

    async def list_owned(
        self,
        *,
        owner_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[Collection]: ...

    async def tombstone(self, *, owner_id: UUID, collection_id: UUID) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class CreateCollectionCommand:
    owner_id: UUID
    name: str
    description: str | None


class CreateCollection:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository

    async def execute(self, command: CreateCollectionCommand) -> Collection:
        return await self._repository.create(
            owner_id=command.owner_id,
            name=command.name.strip(),
            description=command.description.strip() if command.description else None,
        )


class GetCollection:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository

    async def execute(self, *, collection_id: UUID, owner_id: UUID) -> Collection:
        collection = await self._repository.get_owned(
            collection_id=collection_id,
            owner_id=owner_id,
        )
        if collection is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")
        return collection


@dataclass(frozen=True, slots=True)
class CollectionPage:
    items: tuple[Collection, ...]
    has_more: bool


class ListCollections:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        owner_id: UUID,
        page_size: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> CollectionPage:
        items = await self._repository.list_owned(
            owner_id=owner_id,
            limit=page_size + 1,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        return CollectionPage(tuple(items[:page_size]), len(items) > page_size)


class DeleteCollection:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository

    async def execute(self, *, owner_id: UUID, collection_id: UUID) -> tuple[str, ...]:
        return await self._repository.tombstone(owner_id=owner_id, collection_id=collection_id)
