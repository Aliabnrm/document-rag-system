from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.conversations.application import Conversation, PersistedMessage


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationResponse(BaseModel):
    id: UUID
    collection_id: UUID
    title: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, item: Conversation) -> "ConversationResponse":
        return cls.model_validate(item, from_attributes=True)


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: str | None


class PersistedCitationResponse(BaseModel):
    evidence_id: str
    document_name: str
    page_start: int
    page_end: int
    snippet: str


class PersistedMessageResponse(BaseModel):
    id: UUID
    position: int
    role: Literal["user", "assistant"]
    content: str
    language: str
    created_at: datetime
    citations: list[PersistedCitationResponse]
    abstained: bool

    @classmethod
    def from_domain(cls, item: PersistedMessage) -> "PersistedMessageResponse":
        return cls.model_validate(item, from_attributes=True)


class MessageListResponse(BaseModel):
    items: list[PersistedMessageResponse]
    next_position: int | None


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    language: Literal["auto", "fa", "en"] = "auto"

    @field_validator("question")
    @classmethod
    def question_cannot_be_whitespace(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be empty")
        return normalized
