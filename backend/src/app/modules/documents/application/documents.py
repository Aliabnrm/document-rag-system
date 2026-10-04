from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.documents.application.upload import JobDispatcher
from app.modules.documents.domain import DocumentSummary


class DocumentQueryRepository(Protocol):
    async def get_summary(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
    ) -> DocumentSummary: ...

    async def list_summaries(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[DocumentSummary]: ...

    async def schedule_retry(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
    ) -> DocumentSummary: ...

    async def mark_retry_dispatch_failed(self, *, job_id: UUID) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def tombstone(
        self, *, owner_id: UUID, collection_id: UUID, document_id: UUID
    ) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class DocumentPage:
    items: tuple[DocumentSummary, ...]
    has_more: bool


class ListDocuments:
    def __init__(self, repository: DocumentQueryRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        page_size: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> DocumentPage:
        items = await self._repository.list_summaries(
            owner_id=owner_id,
            collection_id=collection_id,
            limit=page_size + 1,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        return DocumentPage(items=tuple(items[:page_size]), has_more=len(items) > page_size)


class RetryIngestion:
    def __init__(
        self,
        *,
        repository: DocumentQueryRepository,
        dispatcher: JobDispatcher,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher

    async def execute(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
    ) -> DocumentSummary:
        summary = await self._repository.schedule_retry(
            owner_id=owner_id,
            collection_id=collection_id,
            document_id=document_id,
        )
        await self._repository.commit()
        try:
            await self._dispatcher.dispatch(
                job_id=summary.job_id,
                document_version_id=summary.document_version_id,
            )
        except Exception:
            await self._repository.rollback()
            await self._repository.mark_retry_dispatch_failed(job_id=summary.job_id)
            await self._repository.commit()
        return await self._repository.get_summary(
            owner_id=owner_id,
            collection_id=collection_id,
            document_id=document_id,
        )


class DeleteDocument:
    def __init__(self, repository: DocumentQueryRepository) -> None:
        self._repository = repository

    async def execute(
        self, *, owner_id: UUID, collection_id: UUID, document_id: UUID
    ) -> tuple[str, ...]:
        return await self._repository.tombstone(
            owner_id=owner_id,
            collection_id=collection_id,
            document_id=document_id,
        )
