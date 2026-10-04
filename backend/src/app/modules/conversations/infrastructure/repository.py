from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collections.infrastructure.models import CollectionModel
from app.modules.conversations.application import (
    Conversation,
    GenerationCompleted,
    PersistedCitation,
    PersistedMessage,
)
from app.modules.conversations.application.answering import RunHandle
from app.modules.conversations.infrastructure.models import (
    CitationModel,
    ConversationModel,
    MessageModel,
    RagRunModel,
)
from app.modules.documents.infrastructure.models import DocumentModel, DocumentVersionModel
from app.modules.retrieval.application import Evidence, RetrievalDiagnostics
from app.modules.retrieval.infrastructure.models import ChunkModel
from app.platform.errors import NotFoundError


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_owned(
        self, *, owner_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        model = await self._session.scalar(
            select(ConversationModel)
            .join(CollectionModel, CollectionModel.id == ConversationModel.collection_id)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        return _to_conversation(model) if model is not None else None

    async def create(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        title: str | None,
    ) -> Conversation:
        collection = await self._session.scalar(
            select(CollectionModel.id).where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        if collection is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")
        model = ConversationModel(
            id=uuid4(),
            owner_id=owner_id,
            collection_id=collection_id,
            title=title,
        )
        self._session.add(model)
        await self._session.commit()
        return Conversation(
            id=model.id,
            collection_id=model.collection_id,
            title=model.title,
            created_at=model.created_at,
        )

    async def list_owned(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        limit: int,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ) -> list[Conversation]:
        collection_exists = await self._session.scalar(
            select(CollectionModel.id).where(
                CollectionModel.id == collection_id,
                CollectionModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        if collection_exists is None:
            raise NotFoundError("collection_not_found", "errors.collection_not_found")
        statement = select(ConversationModel).where(
            ConversationModel.owner_id == owner_id,
            ConversationModel.collection_id == collection_id,
            ConversationModel.collection_id.in_(
                select(CollectionModel.id).where(CollectionModel.deleted_at.is_(None))
            ),
        )
        if before_created_at is not None and before_id is not None:
            statement = statement.where(
                (ConversationModel.created_at < before_created_at)
                | and_(
                    ConversationModel.created_at == before_created_at,
                    ConversationModel.id < before_id,
                )
            )
        models = (
            await self._session.scalars(
                statement.order_by(
                    ConversationModel.created_at.desc(), ConversationModel.id.desc()
                ).limit(limit)
            )
        ).all()
        return [_to_conversation(item) for item in models]

    async def list_messages(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        limit: int,
        after_position: int | None,
    ) -> list[PersistedMessage]:
        conversation_exists = await self._session.scalar(
            select(ConversationModel.id)
            .join(CollectionModel, CollectionModel.id == ConversationModel.collection_id)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
        )
        if conversation_exists is None:
            raise NotFoundError("conversation_not_found", "errors.conversation_not_found")
        statement = (
            select(MessageModel)
            .join(ConversationModel, ConversationModel.id == MessageModel.conversation_id)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.owner_id == owner_id,
            )
        )
        if after_position is not None:
            statement = statement.where(MessageModel.position > after_position)
        messages = (
            await self._session.scalars(
                statement.order_by(MessageModel.position.asc()).limit(limit)
            )
        ).all()
        answer_ids = [item.id for item in messages if item.role == "assistant"]
        citations_by_message: dict[UUID, list[PersistedCitation]] = {}
        abstained_answer_ids: set[UUID] = set()
        if answer_ids:
            abstained_answer_ids = set(
                await self._session.scalars(
                    select(RagRunModel.answer_message_id).where(
                        RagRunModel.answer_message_id.in_(answer_ids),
                        RagRunModel.status == "abstained",
                    )
                )
            )
            rows = (
                await self._session.execute(
                    select(CitationModel, DocumentModel.display_name)
                    .join(ChunkModel, ChunkModel.id == CitationModel.chunk_id)
                    .join(
                        DocumentVersionModel,
                        DocumentVersionModel.id == ChunkModel.document_version_id,
                    )
                    .join(DocumentModel, DocumentModel.id == DocumentVersionModel.document_id)
                    .where(CitationModel.answer_message_id.in_(answer_ids))
                    .order_by(CitationModel.answer_message_id, CitationModel.position)
                )
            ).all()
            for citation, display_name in rows:
                citations_by_message.setdefault(citation.answer_message_id, []).append(
                    PersistedCitation(
                        evidence_id=f"E{citation.position + 1}",
                        document_name=display_name,
                        page_start=citation.page_start,
                        page_end=citation.page_end,
                        snippet=citation.snippet,
                    )
                )
        return [
            PersistedMessage(
                id=item.id,
                position=item.position,
                role=item.role,
                content=item.content,
                language=item.language,
                created_at=item.created_at,
                citations=tuple(citations_by_message.get(item.id, [])),
                abstained=item.id in abstained_answer_ids,
            )
            for item in messages
        ]

    async def begin_run(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        question: str,
        language: str,
    ) -> RunHandle:
        conversation = await self._session.scalar(
            select(ConversationModel)
            .join(CollectionModel, CollectionModel.id == ConversationModel.collection_id)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.owner_id == owner_id,
                CollectionModel.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if conversation is None:
            raise NotFoundError("conversation_not_found", "errors.conversation_not_found")
        position = await self._next_position(conversation_id)
        user_message = MessageModel(
            id=uuid4(),
            conversation_id=conversation_id,
            position=position,
            role="user",
            content=question,
            language=language,
        )
        run = RagRunModel(
            id=uuid4(),
            conversation_id=conversation_id,
            user_message_id=user_message.id,
            status="retrieving",
            retrieval_config={},
            model_metadata={},
            timing_metadata={},
        )
        self._session.add_all([user_message, run])
        await self._session.commit()
        return RunHandle(
            rag_run_id=run.id,
            conversation_id=conversation.id,
            collection_id=conversation.collection_id,
            user_message_id=user_message.id,
        )

    async def mark_generating(
        self,
        *,
        run: RunHandle,
        diagnostics: RetrievalDiagnostics,
    ) -> None:
        model = await self._session.get(RagRunModel, run.rag_run_id, with_for_update=True)
        if model is None:
            raise NotFoundError("rag_run_not_found", "errors.rag_run_not_found")
        model.status = "generating"
        model.retrieval_config = {
            "retriever": "hybrid-rrf-v1",
            "dense_candidates": diagnostics.dense_candidates,
            "lexical_candidates": diagnostics.lexical_candidates,
            "fused_candidates": diagnostics.fused_candidates,
            "packed_evidence": diagnostics.packed_evidence,
            "packed_tokens": diagnostics.packed_tokens,
            "duration_ms": round(diagnostics.duration_ms, 3),
        }
        await self._session.commit()

    async def complete(
        self,
        *,
        run: RunHandle,
        answer: str,
        language: str,
        citations: tuple[Evidence, ...],
        generation: GenerationCompleted,
        timing_metadata: dict[str, object],
    ) -> UUID:
        conversation = await self._session.scalar(
            select(ConversationModel)
            .where(ConversationModel.id == run.conversation_id)
            .with_for_update()
        )
        model = await self._session.get(RagRunModel, run.rag_run_id, with_for_update=True)
        if conversation is None or model is None:
            raise NotFoundError("rag_run_not_found", "errors.rag_run_not_found")
        position = await self._next_position(run.conversation_id)
        answer_message = MessageModel(
            id=uuid4(),
            conversation_id=run.conversation_id,
            position=position,
            role="assistant",
            content=answer,
            language=language,
        )
        self._session.add(answer_message)
        await self._session.flush()
        self._session.add_all(
            [
                CitationModel(
                    id=uuid4(),
                    answer_message_id=answer_message.id,
                    chunk_id=evidence.chunk_id,
                    position=index,
                    snippet=evidence.source_text,
                    page_start=evidence.page_start,
                    page_end=evidence.page_end,
                )
                for index, evidence in enumerate(citations)
            ]
        )
        model.answer_message_id = answer_message.id
        model.status = "abstained" if generation.abstained else "completed"
        model.model_metadata = {
            **generation.model_metadata,
            "input_tokens": generation.input_tokens,
            "output_tokens": generation.output_tokens,
        }
        model.timing_metadata = timing_metadata
        model.completed_at = datetime.now(UTC)
        model.error_code = None
        await self._session.commit()
        return answer_message.id

    async def fail(self, *, run: RunHandle, code: str, cancelled: bool = False) -> None:
        model = await self._session.get(RagRunModel, run.rag_run_id, with_for_update=True)
        if model is None or model.status in {"completed", "abstained", "cancelled"}:
            await self._session.rollback()
            return
        model.status = "cancelled" if cancelled else "failed"
        model.error_code = code
        model.completed_at = datetime.now(UTC)
        await self._session.commit()

    async def _next_position(self, conversation_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.max(MessageModel.position)).where(
                MessageModel.conversation_id == conversation_id
            )
        )
        return int(current) + 1 if current is not None else 0


def _to_conversation(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        collection_id=model.collection_id,
        title=model.title,
        created_at=model.created_at,
    )
