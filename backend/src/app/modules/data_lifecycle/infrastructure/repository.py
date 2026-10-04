from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.infrastructure.models import CollectionModel
from app.modules.conversations.infrastructure.models import CitationModel, ConversationModel
from app.modules.data_lifecycle.application import CleanupRequest, CleanupResourceType
from app.modules.data_lifecycle.infrastructure.models import DeletionCleanupJobModel
from app.modules.documents.infrastructure.models import DocumentModel, DocumentVersionModel
from app.modules.retrieval.infrastructure.models import ChunkModel

MAX_AUTOMATIC_CLEANUP_ATTEMPTS = 10


class SqlAlchemyCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schedule(
        self,
        *,
        owner_id: UUID,
        resource_type: CleanupResourceType,
        resource_id: UUID,
        storage_keys: tuple[str, ...],
    ) -> CleanupRequest:
        existing = await self._session.scalar(
            select(DeletionCleanupJobModel).where(
                DeletionCleanupJobModel.owner_id == owner_id,
                DeletionCleanupJobModel.resource_type == resource_type,
                DeletionCleanupJobModel.resource_id == resource_id,
            )
        )
        if existing is None:
            existing = DeletionCleanupJobModel(
                id=uuid4(),
                owner_id=owner_id,
                resource_type=resource_type,
                resource_id=resource_id,
                storage_keys=list(storage_keys),
                status="pending",
            )
            self._session.add(existing)
            await self._session.flush()
        return _to_request(existing)

    async def claim(self, job_id: UUID, *, stale_after_seconds: int = 300) -> CleanupRequest | None:
        job = await self._session.scalar(
            select(DeletionCleanupJobModel)
            .where(DeletionCleanupJobModel.id == job_id)
            .with_for_update()
        )
        if (
            job is None
            or job.status == "succeeded"
            or job.attempt_count >= MAX_AUTOMATIC_CLEANUP_ATTEMPTS
        ):
            await self._session.rollback()
            return None
        now = datetime.now(UTC)
        if (
            job.status == "running"
            and job.started_at is not None
            and job.started_at > now - timedelta(seconds=stale_after_seconds)
        ):
            await self._session.rollback()
            return None
        job.status = "running"
        job.attempt_count += 1
        job.started_at = now
        job.error_code = None
        await self._session.commit()
        return _to_request(job)

    async def complete(self, request: CleanupRequest) -> None:
        job = await self._session.get(DeletionCleanupJobModel, request.id, with_for_update=True)
        if job is None or job.status == "succeeded":
            await self._session.rollback()
            return

        version_ids = select(DocumentVersionModel.id).join(
            DocumentModel, DocumentModel.id == DocumentVersionModel.document_id
        )
        if request.resource_type == CleanupResourceType.DOCUMENT:
            version_ids = version_ids.where(DocumentModel.id == request.resource_id)
        else:
            version_ids = version_ids.where(DocumentModel.collection_id == request.resource_id)
            await self._session.execute(
                delete(ConversationModel).where(
                    ConversationModel.collection_id == request.resource_id,
                    ConversationModel.owner_id == request.owner_id,
                )
            )

        chunk_ids = select(ChunkModel.id).where(
            ChunkModel.document_version_id.in_(version_ids)
        )
        await self._session.execute(
            delete(CitationModel).where(CitationModel.chunk_id.in_(chunk_ids))
        )
        await self._session.execute(
            delete(ChunkModel).where(ChunkModel.document_version_id.in_(version_ids))
        )

        documents = select(DocumentModel.id)
        if request.resource_type == CleanupResourceType.DOCUMENT:
            documents = documents.where(DocumentModel.id == request.resource_id)
        else:
            documents = documents.where(DocumentModel.collection_id == request.resource_id)
            await self._session.execute(
                update(CollectionModel)
                .where(
                    CollectionModel.id == request.resource_id,
                    CollectionModel.owner_id == request.owner_id,
                )
                .values(name="Deleted collection", description=None)
            )
        await self._session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.document_id.in_(documents))
            .values(
                original_filename="deleted",
                sha256="0" * 64,
                extraction_metadata={},
                error_code=None,
            )
        )
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id.in_(documents))
            .values(display_name="Deleted document")
        )
        job.status = "succeeded"
        job.completed_at = datetime.now(UTC)
        job.error_code = None
        job.storage_keys = []
        await self._session.commit()

    async def fail(self, job_id: UUID, *, error_code: str) -> None:
        job = await self._session.get(DeletionCleanupJobModel, job_id, with_for_update=True)
        if job is None or job.status == "succeeded":
            await self._session.rollback()
            return
        job.status = "failed"
        job.error_code = error_code
        await self._session.commit()

    async def list_dispatchable(
        self, *, stale_after_seconds: int, limit: int
    ) -> tuple[UUID, ...]:
        stale_before = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
        ids = (
            await self._session.scalars(
                select(DeletionCleanupJobModel.id)
                .where(
                    or_(
                        DeletionCleanupJobModel.status.in_(("pending", "failed")),
                        (
                            (DeletionCleanupJobModel.status == "running")
                            & (DeletionCleanupJobModel.started_at < stale_before)
                        ),
                    )
                    & (
                        DeletionCleanupJobModel.attempt_count
                        < MAX_AUTOMATIC_CLEANUP_ATTEMPTS
                    )
                )
                .order_by(DeletionCleanupJobModel.created_at.asc())
                .limit(limit)
            )
        ).all()
        return tuple(ids)

    async def reschedule_failed(self, job_id: UUID) -> bool:
        job = await self._session.get(DeletionCleanupJobModel, job_id, with_for_update=True)
        if job is None or job.status != "failed":
            return False
        job.status = "pending"
        job.attempt_count = 0
        job.error_code = None
        job.started_at = None
        job.completed_at = None
        await self._session.flush()
        return True


def _to_request(model: DeletionCleanupJobModel) -> CleanupRequest:
    return CleanupRequest(
        id=model.id,
        owner_id=model.owner_id,
        resource_type=CleanupResourceType(model.resource_type),
        resource_id=model.resource_id,
        storage_keys=tuple(model.storage_keys),
    )
