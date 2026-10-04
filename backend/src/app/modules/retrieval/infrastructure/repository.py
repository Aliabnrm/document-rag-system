from uuid import UUID

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.infrastructure.models import CollectionModel
from app.modules.documents.domain import DocumentVersionStatus
from app.modules.documents.infrastructure.models import DocumentModel, DocumentVersionModel
from app.modules.retrieval.application import RetrievalCandidate
from app.modules.retrieval.infrastructure.models import ChunkModel


class PgVectorRetrievalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def dense_search(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        query_vector: tuple[float, ...],
        limit: int,
    ) -> tuple[RetrievalCandidate, ...]:
        distance = ChunkModel.embedding.cosine_distance(list(query_vector)).label("distance")
        statement = (
            self._base_statement(owner_id=owner_id, collection_id=collection_id)
            .add_columns(distance)
            .order_by(distance.asc(), ChunkModel.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(_to_candidate(*row[:-1], score=1.0 - float(row[-1])) for row in rows)

    async def lexical_search(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        normalized_query: str,
        limit: int,
    ) -> tuple[RetrievalCandidate, ...]:
        query = func.websearch_to_tsquery("simple", normalized_query)
        rank = cast(func.ts_rank_cd(ChunkModel.search_vector, query), Float).label("rank")
        statement = (
            self._base_statement(owner_id=owner_id, collection_id=collection_id)
            .add_columns(rank)
            .where(ChunkModel.search_vector.op("@@")(query))
            .order_by(rank.desc(), ChunkModel.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(_to_candidate(*row[:-1], score=float(row[-1])) for row in rows)

    def _base_statement(self, *, owner_id: UUID, collection_id: UUID):  # type: ignore[no-untyped-def]
        return (
            select(
                ChunkModel,
                DocumentVersionModel,
                DocumentModel,
            )
            .join(
                DocumentVersionModel,
                DocumentVersionModel.id == ChunkModel.document_version_id,
            )
            .join(DocumentModel, DocumentModel.id == DocumentVersionModel.document_id)
            .join(CollectionModel, CollectionModel.id == DocumentModel.collection_id)
            .where(
                CollectionModel.owner_id == owner_id,
                CollectionModel.id == collection_id,
                CollectionModel.deleted_at.is_(None),
                DocumentModel.deleted_at.is_(None),
                DocumentVersionModel.status == DocumentVersionStatus.READY,
            )
        )


def _to_candidate(
    chunk: ChunkModel,
    version: DocumentVersionModel,
    document: DocumentModel,
    *,
    score: float,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk.id,
        document_version_id=version.id,
        document_name=document.display_name,
        source_text=chunk.source_text,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        token_count=chunk.token_count,
        score=score,
    )
