from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    collection_id: UUID
    title: str | None
    created_at: datetime


class ConversationRepository(Protocol):
    async def create(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        title: str | None,
    ) -> Conversation: ...


class CreateConversation:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        title: str | None,
    ) -> Conversation:
        return await self._repository.create(
            owner_id=owner_id,
            collection_id=collection_id,
            title=title.strip() if title else None,
        )
