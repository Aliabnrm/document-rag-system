import asyncio
import base64
import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.application import (
    AnswerQuestion,
    CreateConversation,
    GetConversation,
    ListConversationMessages,
    ListConversations,
)
from app.modules.conversations.infrastructure.repository import SqlAlchemyConversationRepository
from app.modules.conversations.presentation.schemas import (
    AskQuestionRequest,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageListResponse,
    PersistedMessageResponse,
)
from app.modules.identity.infrastructure.rate_limit import (
    RedisConcurrencyLimiter,
    RedisRateLimiter,
)
from app.modules.identity.presentation.dependencies import CurrentUser, get_current_user
from app.modules.retrieval.application import HybridRetriever
from app.modules.retrieval.infrastructure.repository import PgVectorRetrievalRepository
from app.platform.ai import create_answer_generator, create_embedding_provider
from app.platform.database.dependencies import get_db_session
from app.platform.errors import ApplicationError

_PERSIAN_OR_ARABIC = re.compile(r"[\u0600-\u06ff]")

collection_router = APIRouter(prefix="/collections/{collection_id}", tags=["conversations"])
conversation_router = APIRouter(prefix="/conversations", tags=["conversations"])


@collection_router.get(
    "/conversations",
    response_model=ConversationListResponse,
    operation_id="listConversations",
)
async def list_conversations(
    collection_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cursor: Annotated[str | None, Query()] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConversationListResponse:
    before_created_at, before_id = _decode_cursor(cursor)
    page = await ListConversations(SqlAlchemyConversationRepository(session)).execute(
        owner_id=current_user.id,
        collection_id=collection_id,
        page_size=page_size,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    next_cursor = None
    if page.has_more and page.items:
        last = page.items[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)
    return ConversationListResponse(
        items=[ConversationResponse.from_domain(item) for item in page.items],
        next_cursor=next_cursor,
    )


@collection_router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createConversation",
)
async def create_conversation(
    collection_id: UUID,
    body: CreateConversationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationResponse:
    conversation = await CreateConversation(SqlAlchemyConversationRepository(session)).execute(
        owner_id=current_user.id,
        collection_id=collection_id,
        title=body.title,
    )
    return ConversationResponse.from_domain(conversation)


@conversation_router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    operation_id="listConversationMessages",
)
async def list_conversation_messages(
    conversation_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    after_position: Annotated[int | None, Query(ge=0)] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MessageListResponse:
    page = await ListConversationMessages(SqlAlchemyConversationRepository(session)).execute(
        owner_id=current_user.id,
        conversation_id=conversation_id,
        page_size=page_size,
        after_position=after_position,
    )
    next_position = page.items[-1].position if page.has_more and page.items else None
    return MessageListResponse(
        items=[PersistedMessageResponse.from_domain(item) for item in page.items],
        next_position=next_position,
    )


@conversation_router.post(
    "/{conversation_id}/messages:stream",
    response_class=StreamingResponse,
    operation_id="streamGroundedAnswer",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_grounded_answer(
    conversation_id: UUID,
    body: AskQuestionRequest,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StreamingResponse:
    settings = request.app.state.settings
    repository = SqlAlchemyConversationRepository(session)
    await GetConversation(repository).execute(
        owner_id=current_user.id,
        conversation_id=conversation_id,
    )
    question_count = await RedisRateLimiter(request.app.state.redis).hit(
        scope="questions-daily",
        identifier=str(current_user.id),
        limit=settings.quota_questions_per_day,
        window_seconds=86400,
    )
    if question_count > settings.quota_questions_per_day:
        raise ApplicationError(
            code="question_quota_exceeded",
            message_key="errors.question_quota_exceeded",
            status_code=429,
            context={"retry_after": 86400},
        )
    concurrency_limiter = RedisConcurrencyLimiter(request.app.state.redis)
    concurrency_identifier = str(current_user.id)
    acquired = await concurrency_limiter.try_acquire(
        scope="generation",
        identifier=concurrency_identifier,
        limit=settings.quota_concurrent_generations_per_user,
        lease_seconds=int(settings.request_timeout_seconds) + 30,
    )
    if not acquired:
        raise ApplicationError(
            code="generation_concurrency_exceeded",
            message_key="errors.generation_concurrency_exceeded",
            status_code=429,
            context={"retry_after": 5},
        )
    retriever = HybridRetriever(
        repository=PgVectorRetrievalRepository(session),
        embedding_provider=create_embedding_provider(settings),
        dense_k=settings.retrieval_dense_k,
        lexical_k=settings.retrieval_lexical_k,
        final_k=settings.retrieval_final_k,
        context_token_budget=settings.context_token_budget,
    )
    answer_question = AnswerQuestion(
        repository=repository,
        retriever=retriever,
        generator=create_answer_generator(settings),
    )
    language = _resolve_language(body.question, body.language)

    async def events() -> AsyncIterator[str]:
        try:
            async for event in answer_question.stream(
                owner_id=current_user.id,
                conversation_id=conversation_id,
                question=body.question,
                language=language,
            ):
                if await request.is_disconnected():
                    raise asyncio.CancelledError
                payload = {**event.data, "request_id": request.state.request_id}
                yield _sse(event.event, payload)
        except asyncio.CancelledError:
            raise
        finally:
            await concurrency_limiter.release(
                scope="generation",
                identifier=concurrency_identifier,
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _resolve_language(
    question: str,
    requested: Literal["auto", "fa", "en"],
) -> Literal["fa", "en"]:
    if requested != "auto":
        return requested
    return "fa" if _PERSIAN_OR_ARABIC.search(question) else "en"


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _encode_cursor(created_at: datetime, conversation_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(conversation_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime | None, UUID | None]:
    if cursor is None:
        return None, None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ApplicationError(
            code="invalid_cursor", message_key="errors.invalid_cursor", status_code=422
        ) from error
