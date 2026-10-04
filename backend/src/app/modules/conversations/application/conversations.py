from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.platform.errors import NotFoundError


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    collection_id: UUID
    title: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PersistedCitation:
    evidence_id: str
    document_name: str
    page_start: int
    page_end: int
    snippet: str


@dataclass(frozen=True, slots=True)
class PersistedMessage:
    id: UUID
    position: int
    role: str
    content: str
    language: str
    created_at: datetime
    citations: tuple[PersistedCitation, ...]


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: tuple[Conversation, ...]
    has_more: bool


@dataclass(frozen=True, slots=True)
class MessagePage:
    items: tuple[PersistedMessage, ...]
    has_more: bool


class ConversationRepository(Protocol):
    async def get_owned(
        self, *, owner_id: UUID, conversation_id: UUID
    ) -> Conversation | None: ...

    async def create(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        title: str | None,
    ) -> Conversation: ...

    async def list_owned(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[Conversation]: ...

    async def list_messages(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        limit: int,
        after_position: int | None,
    ) -> list[PersistedMessage]: ...


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


class GetConversation:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def execute(self, *, owner_id: UUID, conversation_id: UUID) -> Conversation:
        conversation = await self._repository.get_owned(
            owner_id=owner_id,
            conversation_id=conversation_id,
        )
        if conversation is None:
            raise NotFoundError("conversation_not_found", "errors.conversation_not_found")
        return conversation


class ListConversations:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        page_size: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> ConversationPage:
        items = await self._repository.list_owned(
            owner_id=owner_id,
            collection_id=collection_id,
            limit=page_size + 1,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        return ConversationPage(tuple(items[:page_size]), len(items) > page_size)


class ListConversationMessages:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        page_size: int,
        after_position: int | None,
    ) -> MessagePage:
        items = await self._repository.list_messages(
            owner_id=owner_id,
            conversation_id=conversation_id,
            limit=page_size + 1,
            after_position=after_position,
        )
        return MessagePage(tuple(items[:page_size]), len(items) > page_size)
