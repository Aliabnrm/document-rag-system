import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.application import AnswerQuestion, CreateConversation
from app.modules.conversations.infrastructure.repository import SqlAlchemyConversationRepository
from app.modules.conversations.presentation.schemas import (
    AskQuestionRequest,
    ConversationResponse,
    CreateConversationRequest,
)
from app.modules.retrieval.application import HybridRetriever
from app.modules.retrieval.infrastructure.repository import PgVectorRetrievalRepository
from app.platform.ai import create_answer_generator, create_embedding_provider
from app.platform.database.dependencies import get_db_session
from app.platform.identity import CurrentUser, get_current_user

_PERSIAN_OR_ARABIC = re.compile(r"[\u0600-\u06ff]")

collection_router = APIRouter(prefix="/collections/{collection_id}", tags=["conversations"])
conversation_router = APIRouter(prefix="/conversations", tags=["conversations"])


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
