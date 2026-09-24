from dataclasses import dataclass
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
