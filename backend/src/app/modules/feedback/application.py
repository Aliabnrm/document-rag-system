from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.feedback.domain import FeedbackReason


class FeedbackRepository(Protocol):
    async def save(
        self,
        *,
        owner_id: UUID,
        answer_message_id: UUID,
        rating: int,
        reason: FeedbackReason,
        comment: str | None,
    ) -> UUID: ...


@dataclass(frozen=True, slots=True)
class SubmitFeedbackCommand:
    owner_id: UUID
    answer_message_id: UUID
    rating: int
    reason: FeedbackReason
    comment: str | None


class SubmitFeedback:
    def __init__(self, repository: FeedbackRepository) -> None:
        self._repository = repository

    async def execute(self, command: SubmitFeedbackCommand) -> UUID:
        comment = command.comment.strip() if command.comment else None
        return await self._repository.save(
            owner_id=command.owner_id,
            answer_message_id=command.answer_message_id,
            rating=command.rating,
            reason=command.reason,
            comment=comment or None,
        )
