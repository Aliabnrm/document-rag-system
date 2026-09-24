from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.domain import DocumentVersionState, DocumentVersionStatus
from app.modules.documents.infrastructure.models import DocumentVersionModel
from app.modules.ingestion.application import DispatchRequest, ExtractionResult, WorkerDocument
from app.modules.ingestion.application.pipeline import IndexedChunk
from app.modules.ingestion.domain import IngestionJobState, IngestionJobStatus
from app.modules.ingestion.infrastructure.models import IngestionJobModel
from app.modules.retrieval.infrastructure.models import ChunkModel


class SqlAlchemyIngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        job_id: UUID,
        document_version_id: UUID,
    ) -> WorkerDocument | None:
        row = (
            await self._session.execute(
                select(IngestionJobModel, DocumentVersionModel)
                .join(
                    DocumentVersionModel,
                    DocumentVersionModel.id == IngestionJobModel.document_version_id,
                )
                .where(
                    IngestionJobModel.id == job_id,
                    DocumentVersionModel.id == document_version_id,
                )
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        job, version = row
        job_status = IngestionJobStatus(job.status)
        version_status = DocumentVersionStatus(version.status)
        if job_status in {IngestionJobStatus.SUCCEEDED, IngestionJobStatus.RUNNING}:
            await self._session.rollback()
            return None
        if job_status not in {
            IngestionJobStatus.PENDING,
            IngestionJobStatus.RETRY_SCHEDULED,
        }:
            await self._session.rollback()
            return None

        if version_status in {
            DocumentVersionStatus.UPLOADED,
            DocumentVersionStatus.FAILED,
        }:
            version_status = (
                DocumentVersionState(version_status)
                .transition_to(DocumentVersionStatus.QUEUED)
                .status
            )
        version.status = (
            DocumentVersionState(version_status)
            .transition_to(DocumentVersionStatus.EXTRACTING)
            .status
        )
        version.error_code = None
        job.status = IngestionJobState(job_status).transition_to(IngestionJobStatus.RUNNING).status
        job.stage = "extracting"
        job.attempt_count += 1
        job.error_code = None
        job.error_detail = None
        job.started_at = job.started_at or datetime.now(UTC)
        job.heartbeat_at = datetime.now(UTC)
        job.finished_at = None
        await self._session.commit()
        return WorkerDocument(
            job_id=job.id,
            document_version_id=version.id,
            storage_key=version.storage_key,
            media_type=version.media_type,
            pipeline_version=version.pipeline_version,
            attempt_count=job.attempt_count,
        )

    async def set_stage(self, *, job_id: UUID, stage: str) -> None:
        target_statuses = {
            "chunking": DocumentVersionStatus.CHUNKING,
            "embedding": DocumentVersionStatus.EMBEDDING,
        }
        target = target_statuses[stage]
        job, version = await self._locked_models(job_id)
        if IngestionJobStatus(job.status) is not IngestionJobStatus.RUNNING:
            await self._session.rollback()
            return
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status)).transition_to(target).status
        )
        job.stage = stage
        job.heartbeat_at = datetime.now(UTC)
        await self._session.commit()

    async def complete(
        self,
        *,
        worker_document: WorkerDocument,
        extraction: ExtractionResult,
        chunks: tuple[IndexedChunk, ...],
    ) -> None:
        job, version = await self._locked_models(worker_document.job_id)
        if (
            IngestionJobStatus(job.status) is not IngestionJobStatus.RUNNING
            or DocumentVersionStatus(version.status) is not DocumentVersionStatus.EMBEDDING
        ):
            await self._session.rollback()
            return

        await self._session.execute(
            delete(ChunkModel).where(
                ChunkModel.document_version_id == worker_document.document_version_id
            )
        )
        self._session.add_all(
            [
                ChunkModel(
                    id=uuid4(),
                    document_version_id=worker_document.document_version_id,
                    ordinal=item.chunk.ordinal,
                    source_text=item.chunk.source_text,
                    normalized_text=item.chunk.normalized_text,
                    page_start=item.chunk.page_start,
                    page_end=item.chunk.page_end,
                    source_start=item.chunk.source_start,
                    source_end=item.chunk.source_end,
                    token_count=item.chunk.token_count,
                    content_hash=item.chunk.content_hash,
                    chunker_version="boundary-token-v1",
                    pipeline_version=item.pipeline_version,
                    embedding_model=item.embedding_model,
                    embedding_revision=item.embedding_revision,
                    embedding=list(item.embedding),
                )
                for item in chunks
            ]
        )
        now = datetime.now(UTC)
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status))
            .transition_to(DocumentVersionStatus.READY)
            .status
        )
        version.page_count = len(extraction.pages)
        version.extraction_metadata = extraction.diagnostics
        version.ready_at = now
        version.error_code = None
        job.status = (
            IngestionJobState(IngestionJobStatus(job.status))
            .transition_to(IngestionJobStatus.SUCCEEDED)
            .status
        )
        job.stage = "ready"
        job.heartbeat_at = now
        job.finished_at = now
        job.error_code = None
        job.error_detail = None
        await self._session.commit()

    async def fail_permanently(self, *, job_id: UUID, code: str) -> None:
        job, version = await self._locked_models(job_id)
        if IngestionJobStatus(job.status) is not IngestionJobStatus.RUNNING:
            await self._session.rollback()
            return
        now = datetime.now(UTC)
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status))
            .transition_to(DocumentVersionStatus.FAILED)
            .status
        )
        version.error_code = code
        job.status = (
            IngestionJobState(IngestionJobStatus(job.status))
            .transition_to(IngestionJobStatus.FAILED)
            .status
        )
        job.error_code = code
        job.error_detail = None
        job.heartbeat_at = now
        job.finished_at = now
        await self._session.commit()

    async def schedule_retry(
        self,
        *,
        job_id: UUID,
        code: str,
        maximum_attempts: int,
    ) -> bool:
        job, version = await self._locked_models(job_id)
        if IngestionJobStatus(job.status) is not IngestionJobStatus.RUNNING:
            await self._session.rollback()
            return False
        now = datetime.now(UTC)
        version.status = (
            DocumentVersionState(DocumentVersionStatus(version.status))
            .transition_to(DocumentVersionStatus.FAILED)
            .status
        )
        version.error_code = code
        if job.attempt_count >= maximum_attempts:
            job.status = (
                IngestionJobState(IngestionJobStatus(job.status))
                .transition_to(IngestionJobStatus.FAILED)
                .status
            )
            should_retry = False
            job.finished_at = now
        else:
            job.status = (
                IngestionJobState(IngestionJobStatus(job.status))
                .transition_to(IngestionJobStatus.RETRY_SCHEDULED)
                .status
            )
            should_retry = True
        job.error_code = code
        job.error_detail = None
        job.heartbeat_at = now
        await self._session.commit()
        return should_retry

    async def _locked_models(
        self,
        job_id: UUID,
    ) -> tuple[IngestionJobModel, DocumentVersionModel]:
        row = (
            await self._session.execute(
                select(IngestionJobModel, DocumentVersionModel)
                .join(
                    DocumentVersionModel,
                    DocumentVersionModel.id == IngestionJobModel.document_version_id,
                )
                .where(IngestionJobModel.id == job_id)
                .with_for_update()
            )
        ).one()
        return row._tuple()


class SqlAlchemyDispatchRecoveryRepository:
    """Lease durable queued jobs so a broker-send crash can be repaired."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_stale_dispatches(
        self,
        *,
        stale_after_seconds: int,
        limit: int,
    ) -> tuple[DispatchRequest, ...]:
        stale_before = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
        jobs = (
            await self._session.scalars(
                select(IngestionJobModel)
                .where(
                    IngestionJobModel.status.in_(
                        (IngestionJobStatus.PENDING, IngestionJobStatus.RETRY_SCHEDULED)
                    ),
                    IngestionJobModel.stage == "queued",
                    (IngestionJobModel.dispatched_at.is_(None))
                    | (IngestionJobModel.dispatched_at < stale_before),
                )
                .order_by(IngestionJobModel.created_at.asc(), IngestionJobModel.id.asc())
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
        ).all()
        now = datetime.now(UTC)
        requests = tuple(
            DispatchRequest(job_id=job.id, document_version_id=job.document_version_id)
            for job in jobs
        )
        for job in jobs:
            job.dispatched_at = now
            job.dispatch_count += 1
        await self._session.commit()
        return requests
