import base64
import json
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_lifecycle import RequestDocumentDeletion
from app.modules.data_lifecycle.infrastructure import SqlAlchemyCleanupRepository
from app.modules.documents.application import (
    CreateDocumentUpload,
    ListDocuments,
    RetryIngestion,
)
from app.modules.documents.infrastructure.repository import SqlAlchemyDocumentRepository
from app.modules.documents.presentation.schemas import (
    DocumentListResponse,
    DocumentResponse,
    UploadAcceptedResponse,
)
from app.modules.identity.presentation.dependencies import CurrentUser, get_current_user
from app.platform.database.dependencies import get_db_session
from app.platform.errors import ApplicationError
from app.platform.observability import log_event

router = APIRouter(prefix="/collections/{collection_id}", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post(
    "/documents",
    response_model=UploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="uploadDocument",
)
async def upload_document(
    collection_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadAcceptedResponse:
    settings = request.app.state.settings
    use_case = CreateDocumentUpload(
        repository=SqlAlchemyDocumentRepository(session),
        storage=request.app.state.source_storage,
        dispatcher=request.app.state.job_dispatcher,
        max_upload_bytes=settings.max_upload_bytes,
        max_documents_per_user=settings.quota_documents_per_user,
        pipeline_version=settings.pipeline_version,
    )
    result = await use_case.execute(
        owner_id=current_user.id,
        collection_id=collection_id,
        upload=file,
    )
    return UploadAcceptedResponse.from_domain(result)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    operation_id="listDocuments",
)
async def list_documents(
    collection_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cursor: Annotated[str | None, Query()] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    before_created_at, before_id = _decode_cursor(cursor)
    page = await ListDocuments(SqlAlchemyDocumentRepository(session)).execute(
        owner_id=current_user.id,
        collection_id=collection_id,
        page_size=page_size,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    next_cursor = None
    if page.has_more and page.items:
        last = page.items[-1]
        next_cursor = _encode_cursor(last.created_at, last.document_id)
    return DocumentListResponse(
        items=[DocumentResponse.from_domain(item) for item in page.items],
        next_cursor=next_cursor,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    operation_id="getDocumentStatus",
)
async def get_document_status(
    collection_id: UUID,
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentResponse:
    item = await SqlAlchemyDocumentRepository(session).get_summary(
        owner_id=current_user.id,
        collection_id=collection_id,
        document_id=document_id,
    )
    return DocumentResponse.from_domain(item)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteDocument",
)
async def delete_document(
    collection_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    async with session.begin():
        cleanup = await RequestDocumentDeletion(
            documents=SqlAlchemyDocumentRepository(session),
            cleanup=SqlAlchemyCleanupRepository(session),
        ).execute(
            owner_id=current_user.id,
            collection_id=collection_id,
            document_id=document_id,
        )
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
        "document_deleted",
        user_id=current_user.id,
        collection_id=collection_id,
    )


@router.post(
    "/documents/{document_id}/ingestion-retries",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="retryDocumentIngestion",
)
async def retry_document_ingestion(
    collection_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentResponse:
    repository = SqlAlchemyDocumentRepository(session)
    item = await RetryIngestion(
        repository=repository,
        dispatcher=request.app.state.job_dispatcher,
    ).execute(
        owner_id=current_user.id,
        collection_id=collection_id,
        document_id=document_id,
    )
    return DocumentResponse.from_domain(item)


def _encode_cursor(created_at: datetime, document_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(document_id)},
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
            code="invalid_cursor",
            message_key="errors.invalid_cursor",
            status_code=422,
        ) from error
