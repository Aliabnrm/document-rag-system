from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.domain import Collection
from app.modules.collections.infrastructure.models import CollectionModel
from app.modules.documents.infrastructure.models import DocumentModel, DocumentVersionModel
from app.modules.ingestion.domain import IngestionJobStatus
from app.modules.ingestion.infrastructure.models import IngestionJobModel
from app.platform.errors import NotFoundError


class SqlAlchemyCollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        owner_id: UUID,
        name: str,
        description: str | None,
    ) -> Collection:
        model = CollectionModel(
            id=uuid4(),
            owner_id=owner_id,
            name=name,
            description=description,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain(model)

    async def get_owned(self, *, collection_id: UUID, owner_id: UUID) -> Collection | None:
        model = await self._session.scalar(
            select(CollectionModel).where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        return _to_domain(model) if model is not None else None

    async def list_owned(
        self,
        *,
        owner_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[Collection]:
        statement = select(CollectionModel).where(
            CollectionModel.owner_id == owner_id,
            CollectionModel.deleted_at.is_(None),
        )
        if before_created_at is not None and before_id is not None:
            statement = statement.where(
                (CollectionModel.created_at < before_created_at)
                | and_(
                    CollectionModel.created_at == before_created_at,
                    CollectionModel.id < before_id,
                )
            )
        models = (
            await self._session.scalars(
                statement.order_by(
                    CollectionModel.created_at.desc(), CollectionModel.id.desc()
                ).limit(limit)
            )
        ).all()
        return [_to_domain(item) for item in models]

    async def tombstone(self, *, owner_id: UUID, collection_id: UUID) -> tuple[str, ...]:
        collection = await self._session.scalar(
            select(CollectionModel)
            .where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
            )
            .with_for_update()
        )
        if collection is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")
        rows = (
            await self._session.execute(
                select(
                    DocumentModel,
                    DocumentVersionModel.id,
                    DocumentVersionModel.storage_key,
                )
                .join(
                    DocumentVersionModel,
                    DocumentVersionModel.document_id == DocumentModel.id,
                )
                .where(DocumentModel.collection_id == collection_id)
            )
        ).all()
        if collection.deleted_at is None:
            now = datetime.now(UTC)
            collection.deleted_at = now
            version_ids = [row[1] for row in rows]
            for document, _, _ in rows:
                document.deleted_at = document.deleted_at or now
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
                        job.error_code = "collection_deleted"
                        job.finished_at = now
        await self._session.flush()
        return tuple(row[2] for row in rows)


def _to_domain(model: CollectionModel) -> Collection:
    return Collection(
        id=model.id,
        owner_id=model.owner_id,
        name=model.name,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
