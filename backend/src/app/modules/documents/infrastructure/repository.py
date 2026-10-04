from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.infrastructure.models import CollectionModel
from app.modules.documents.application.upload import FileInspection
from app.modules.documents.domain import (
    DocumentSummary,
    DocumentVersionState,
    DocumentVersionStatus,
    PendingDocumentUpload,
)
from app.modules.documents.infrastructure.models import DocumentModel, DocumentVersionModel
from app.modules.ingestion.domain import IngestionJobState, IngestionJobStatus
from app.modules.ingestion.infrastructure.models import IngestionJobModel
from app.platform.errors import ConflictError, NotFoundError


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_owned_documents(self, owner_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(DocumentModel)
            .join(CollectionModel, CollectionModel.id == DocumentModel.collection_id)
            .where(
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
                DocumentModel.deleted_at.is_(None),
            )
        )
        return int(value or 0)

    async def create_pending(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
        display_name: str,
        inspection: FileInspection,
        storage_key: str,
        pipeline_version: str,
    ) -> PendingDocumentUpload:
        collection_exists = await self._session.scalar(
            select(CollectionModel.id).where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        if collection_exists is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")

        document = DocumentModel(
            id=document_id,
            collection_id=collection_id,
            display_name=display_name,
        )
        version = DocumentVersionModel(
            id=document_version_id,
            document_id=document_id,
            version_number=1,
            status=DocumentVersionStatus.UPLOADED,
            original_filename=inspection.filename,
            media_type=inspection.media_type,
            size_bytes=inspection.size_bytes,
            sha256=inspection.sha256,
            storage_key=storage_key,
            pipeline_version=pipeline_version,
        )
        job = IngestionJobModel(
            id=job_id,
            document_version_id=document_version_id,
            status=IngestionJobStatus.PENDING,
            stage="queued",
        )
        self._session.add_all([document, version, job])
        await self._session.flush()
        return _to_pending(document, version, job)

    async def mark_dispatched(
        self,
        *,
        owner_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
    ) -> PendingDocumentUpload:
        document, version, job = await self._owned_models(
            owner_id=owner_id,
            document_version_id=document_version_id,
            job_id=job_id,
            for_update=True,
        )
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status))
            .transition_to(DocumentVersionStatus.QUEUED)
            .status
        )
        job.stage = "queued"
        job.dispatch_count += 1
        job.dispatched_at = datetime.now(UTC)
        await self._session.flush()
        return _to_pending(document, version, job)

    async def mark_dispatch_failed(
        self,
        *,
        owner_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
    ) -> PendingDocumentUpload:
        document, version, job = await self._owned_models(
            owner_id=owner_id,
            document_version_id=document_version_id,
            job_id=job_id,
            for_update=True,
        )
        version.status = DocumentVersionStatus.FAILED
        version.error_code = "queue_unavailable"
        job.status = IngestionJobStatus.FAILED
        job.stage = "queued"
        job.error_code = "queue_unavailable"
        job.error_detail = None
        job.finished_at = datetime.now(UTC)
        await self._session.flush()
        return _to_pending(document, version, job)

    async def get_summary(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
    ) -> DocumentSummary:
        statement = self._summary_statement(owner_id=owner_id, collection_id=collection_id).where(
            DocumentModel.id == document_id
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise NotFoundError("document_not_found", "errors.document_not_found")
        return _to_summary(*row)

    async def list_summaries(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[DocumentSummary]:
        collection_exists = await self._session.scalar(
            select(CollectionModel.id).where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        if collection_exists is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")
        statement = self._summary_statement(owner_id=owner_id, collection_id=collection_id)
        if before_created_at is not None and before_id is not None:
            statement = statement.where(
                (DocumentModel.created_at < before_created_at)
                | and_(
                    DocumentModel.created_at == before_created_at,
                    DocumentModel.id < before_id,
                )
            )
        statement = statement.order_by(
            DocumentModel.created_at.desc(),
            DocumentModel.id.desc(),
        ).limit(limit)
        return [_to_summary(*row) for row in (await self._session.execute(statement)).all()]

    async def schedule_retry(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
    ) -> DocumentSummary:
        statement = (
            self._summary_statement(owner_id=owner_id, collection_id=collection_id)
            .where(DocumentModel.id == document_id)
            .with_for_update()
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise NotFoundError("document_not_found", "errors.document_not_found")
        document, version, job = row
        if version.status != DocumentVersionStatus.FAILED:
            raise ConflictError("document_not_retryable", "errors.document_not_retryable")
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status))
            .transition_to(DocumentVersionStatus.QUEUED)
            .status
        )
        version.error_code = None
        job.status = (
            IngestionJobState(IngestionJobStatus(job.status))
            .transition_to(IngestionJobStatus.RETRY_SCHEDULED)
            .status
        )
        job.stage = "queued"
        job.dispatch_count += 1
        job.dispatched_at = datetime.now(UTC)
        job.error_code = None
        job.error_detail = None
        job.finished_at = None
        await self._session.flush()
        return _to_summary(document, version, job)

    async def mark_retry_dispatch_failed(self, *, job_id: UUID) -> None:
        job = await self._session.get(IngestionJobModel, job_id, with_for_update=True)
        if job is None:
            return
        version = await self._session.get(
            DocumentVersionModel,
            job.document_version_id,
            with_for_update=True,
        )
        if version is None:
            return
        version.status = DocumentVersionStatus.FAILED
        version.error_code = "queue_unavailable"
        job.status = IngestionJobStatus.FAILED
        job.error_code = "queue_unavailable"
        job.finished_at = datetime.now(UTC)
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def tombstone(
        self, *, owner_id: UUID, collection_id: UUID, document_id: UUID
    ) -> tuple[str, ...]:
        row = (
            await self._session.execute(
                select(DocumentModel, CollectionModel)
                .join(CollectionModel, CollectionModel.id == DocumentModel.collection_id)
                .where(
                    DocumentModel.id == document_id,
                    CollectionModel.id == collection_id,
                    CollectionModel.owner_id == owner_id,
                )
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            raise NotFoundError("document_not_found", "errors.document_not_found")
        document, collection = row
        if collection.deleted_at is not None:
            raise NotFoundError("document_not_found", "errors.document_not_found")
        version_rows = (
            await self._session.execute(
                select(DocumentVersionModel.id, DocumentVersionModel.storage_key).where(
                    DocumentVersionModel.document_id == document_id
                )
            )
        ).all()
        version_ids = [item.id for item in version_rows]
        if document.deleted_at is None:
            now = datetime.now(UTC)
            document.deleted_at = now
            if version_ids:
                jobs = (
                    await self._session.scalars(
                        select(IngestionJobModel).where(
                            IngestionJobModel.document_version_id.in_(version_ids)
                        )
                    )
                ).all()
                for job in jobs:
                    if job.status != IngestionJobStatus.SUCCEEDED:
                        job.status = IngestionJobStatus.FAILED
                        job.error_code = "document_deleted"
                        job.finished_at = now
        await self._session.flush()
        return tuple(item.storage_key for item in version_rows)

    def _summary_statement(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
    ) -> Select[tuple[DocumentModel, DocumentVersionModel, IngestionJobModel]]:
        return (
            select(DocumentModel, DocumentVersionModel, IngestionJobModel)
            .join(CollectionModel, CollectionModel.id == DocumentModel.collection_id)
            .join(DocumentVersionModel, DocumentVersionModel.document_id == DocumentModel.id)
            .join(
                IngestionJobModel,
                IngestionJobModel.document_version_id == DocumentVersionModel.id,
            )
            .where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
                DocumentModel.deleted_at.is_(None),
            )
        )

    async def _owned_models(
        self,
        *,
        owner_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
        for_update: bool,
    ) -> tuple[DocumentModel, DocumentVersionModel, IngestionJobModel]:
        statement = (
            select(DocumentModel, DocumentVersionModel, IngestionJobModel)
            .join(DocumentVersionModel, DocumentVersionModel.document_id == DocumentModel.id)
            .join(
                IngestionJobModel,
                IngestionJobModel.document_version_id == DocumentVersionModel.id,
            )
            .join(CollectionModel, CollectionModel.id == DocumentModel.collection_id)
            .where(
                DocumentVersionModel.id == document_version_id,
                IngestionJobModel.id == job_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
                DocumentModel.deleted_at.is_(None),
            )
        )
        if for_update:
            statement = statement.with_for_update()
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise NotFoundError("document_not_found", "errors.document_not_found")
        return row._tuple()


def _to_pending(
    document: DocumentModel,
    version: DocumentVersionModel,
    job: IngestionJobModel,
) -> PendingDocumentUpload:
    return PendingDocumentUpload(
        document_id=document.id,
        document_version_id=version.id,
        job_id=job.id,
        collection_id=document.collection_id,
        display_name=document.display_name,
        version_number=version.version_number,
        status=DocumentVersionStatus(version.status),
        job_status=IngestionJobStatus(job.status),
        stage=job.stage,
        created_at=version.created_at,
    )


def _to_summary(
    document: DocumentModel,
    version: DocumentVersionModel,
    job: IngestionJobModel,
) -> DocumentSummary:
    return DocumentSummary(
        document_id=document.id,
        document_version_id=version.id,
        display_name=document.display_name,
        media_type=version.media_type,
        size_bytes=version.size_bytes,
        version_number=version.version_number,
        status=DocumentVersionStatus(version.status),
        job_id=job.id,
        job_status=IngestionJobStatus(job.status),
        stage=job.stage,
        attempt_count=job.attempt_count,
        error_code=job.error_code or version.error_code,
        page_count=version.page_count,
        created_at=document.created_at,
        updated_at=version.updated_at,
    )
