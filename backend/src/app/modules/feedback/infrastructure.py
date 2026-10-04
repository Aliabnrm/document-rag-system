from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.conversations.infrastructure.models import (
    ConversationModel,
    MessageModel,
    RagRunModel,
)
from app.modules.feedback.domain import FeedbackReason
from app.platform.database.base import Base, TimestampMixin
from app.platform.errors import ConflictError, NotFoundError


class AnswerFeedbackModel(TimestampMixin, Base):
    __tablename__ = "answer_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "answer_message_id"),
        CheckConstraint("rating IN (-1, 1)", name="valid_rating"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    answer_message_id: Mapped[UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    rag_run_id: Mapped[UUID] = mapped_column(ForeignKey("rag_runs.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    pipeline_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class SqlAlchemyFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        owner_id: UUID,
        answer_message_id: UUID,
        rating: int,
        reason: FeedbackReason,
        comment: str | None,
    ) -> UUID:
        row = (
            await self._session.execute(
                select(MessageModel, RagRunModel)
                .join(ConversationModel, ConversationModel.id == MessageModel.conversation_id)
                .join(RagRunModel, RagRunModel.answer_message_id == MessageModel.id)
                .where(
                    MessageModel.id == answer_message_id,
                    MessageModel.role == "assistant",
                    ConversationModel.owner_id == owner_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise NotFoundError("answer_not_found", "errors.answer_not_found")
        _, rag_run = row
        exists = await self._session.scalar(
            select(AnswerFeedbackModel.id).where(
                AnswerFeedbackModel.user_id == owner_id,
                AnswerFeedbackModel.answer_message_id == answer_message_id,
            )
        )
        if exists is not None:
            raise ConflictError("feedback_already_submitted", "errors.feedback_already_submitted")
        model = AnswerFeedbackModel(
            id=uuid4(),
            user_id=owner_id,
            answer_message_id=answer_message_id,
            rag_run_id=rag_run.id,
            rating=rating,
            reason=reason,
            comment=comment,
            pipeline_metadata={
                "model": rag_run.model_metadata,
                "retrieval": rag_run.retrieval_config,
            },
        )
        self._session.add(model)
        await self._session.flush()
        return model.id
