from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.application import (
    CreateCollection,
    CreateCollectionCommand,
    GetCollection,
)
from app.modules.collections.infrastructure.repository import SqlAlchemyCollectionRepository
from app.modules.collections.presentation.schemas import (
    CollectionResponse,
    CreateCollectionRequest,
)
from app.platform.database.dependencies import get_db_session
from app.platform.identity import CurrentUser, get_current_user

router = APIRouter(prefix="/collections", tags=["collections"])


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
