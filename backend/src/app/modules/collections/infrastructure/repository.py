from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.domain import Collection
from app.modules.collections.infrastructure.models import CollectionModel
from app.platform.identity.models import UserModel


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
        await self._session.execute(
            insert(UserModel).values(id=owner_id).on_conflict_do_nothing(index_elements=["id"])
        )
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
            )
        )
        return _to_domain(model) if model is not None else None


def _to_domain(model: CollectionModel) -> Collection:
    return Collection(
        id=model.id,
        owner_id=model.owner_id,
        name=model.name,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
