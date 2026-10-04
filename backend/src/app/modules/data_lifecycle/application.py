from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class CleanupResourceType(StrEnum):
    DOCUMENT = "document"
    COLLECTION = "collection"


@dataclass(frozen=True, slots=True)
class CleanupRequest:
    id: UUID
    owner_id: UUID
    resource_type: CleanupResourceType
    resource_id: UUID
    storage_keys: tuple[str, ...]


class DocumentTombstoneRepository(Protocol):
    async def tombstone(
        self, *, owner_id: UUID, collection_id: UUID, document_id: UUID
    ) -> tuple[str, ...]: ...


class CollectionTombstoneRepository(Protocol):
    async def tombstone(self, *, owner_id: UUID, collection_id: UUID) -> tuple[str, ...]: ...


class CleanupRepository(Protocol):
    async def schedule(
        self,
        *,
        owner_id: UUID,
        resource_type: CleanupResourceType,
        resource_id: UUID,
        storage_keys: tuple[str, ...],
    ) -> CleanupRequest: ...


class RequestDocumentDeletion:
    def __init__(
        self,
        *,
        documents: DocumentTombstoneRepository,
        cleanup: CleanupRepository,
    ) -> None:
        self._documents = documents
        self._cleanup = cleanup

    async def execute(
        self, *, owner_id: UUID, collection_id: UUID, document_id: UUID
    ) -> CleanupRequest:
        storage_keys = await self._documents.tombstone(
            owner_id=owner_id,
            collection_id=collection_id,
            document_id=document_id,
        )
        return await self._cleanup.schedule(
            owner_id=owner_id,
            resource_type=CleanupResourceType.DOCUMENT,
            resource_id=document_id,
            storage_keys=storage_keys,
        )


class RequestCollectionDeletion:
    def __init__(
        self,
        *,
        collections: CollectionTombstoneRepository,
        cleanup: CleanupRepository,
    ) -> None:
        self._collections = collections
        self._cleanup = cleanup

    async def execute(self, *, owner_id: UUID, collection_id: UUID) -> CleanupRequest:
        storage_keys = await self._collections.tombstone(
            owner_id=owner_id,
            collection_id=collection_id,
        )
        return await self._cleanup.schedule(
            owner_id=owner_id,
            resource_type=CleanupResourceType.COLLECTION,
            resource_id=collection_id,
            storage_keys=storage_keys,
        )
