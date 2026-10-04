import base64
import json
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.application import (
    CreateCollection,
    CreateCollectionCommand,
    GetCollection,
    ListCollections,
)
from app.modules.collections.infrastructure.repository import SqlAlchemyCollectionRepository
from app.modules.collections.presentation.schemas import (
    CollectionListResponse,
    CollectionResponse,
    CreateCollectionRequest,
)
from app.modules.data_lifecycle import RequestCollectionDeletion
from app.modules.data_lifecycle.infrastructure import SqlAlchemyCleanupRepository
from app.modules.identity.presentation.dependencies import CurrentUser, get_current_user
from app.platform.database.dependencies import get_db_session
from app.platform.errors import ApplicationError
from app.platform.observability import log_event

router = APIRouter(prefix="/collections", tags=["collections"])
logger = logging.getLogger(__name__)


@router.get("", response_model=CollectionListResponse, operation_id="listCollections")
async def list_collections(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cursor: Annotated[str | None, Query()] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CollectionListResponse:
    before_created_at, before_id = _decode_cursor(cursor)
    page = await ListCollections(SqlAlchemyCollectionRepository(session)).execute(
        owner_id=current_user.id,
        page_size=page_size,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    next_cursor = None
    if page.has_more and page.items:
        last = page.items[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)
    return CollectionListResponse(
        items=[CollectionResponse.from_domain(item) for item in page.items],
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createCollection",
)
async def create_collection(
    body: CreateCollectionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CollectionResponse:
    repository = SqlAlchemyCollectionRepository(session)
    use_case = CreateCollection(repository)
    async with session.begin():
        collection = await use_case.execute(
            CreateCollectionCommand(
                owner_id=current_user.id,
                name=body.name,
                description=body.description,
            )
        )
    return CollectionResponse.from_domain(collection)


def _encode_cursor(created_at: datetime, collection_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(collection_id)},
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


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    operation_id="getCollection",
)
async def get_collection(
    collection_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CollectionResponse:
    collection = await GetCollection(SqlAlchemyCollectionRepository(session)).execute(
        collection_id=collection_id,
        owner_id=current_user.id,
    )
    return CollectionResponse.from_domain(collection)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteCollection",
)
async def delete_collection(
    collection_id: UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    async with session.begin():
        cleanup = await RequestCollectionDeletion(
            collections=SqlAlchemyCollectionRepository(session),
            cleanup=SqlAlchemyCleanupRepository(session),
        ).execute(owner_id=current_user.id, collection_id=collection_id)
    try:
        await request.app.state.deletion_dispatcher.dispatch(cleanup_job_id=cleanup.id)
    except Exception:
        log_event(
            logger,
            "deletion_cleanup_dispatch_deferred",
            user_id=current_user.id,
            collection_id=collection_id,
            error_code="queue_unavailable",
        )
    log_event(
        logger,
        "collection_deleted",
        user_id=current_user.id,
        collection_id=collection_id,
    )
