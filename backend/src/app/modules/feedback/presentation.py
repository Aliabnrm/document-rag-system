import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feedback.application import SubmitFeedback, SubmitFeedbackCommand
from app.modules.feedback.domain import FeedbackReason
from app.modules.feedback.infrastructure import SqlAlchemyFeedbackRepository
from app.modules.identity.presentation.dependencies import CurrentUser, get_current_user
from app.platform.database.dependencies import get_db_session
from app.platform.observability import log_event

router = APIRouter(prefix="/messages", tags=["feedback"])
logger = logging.getLogger(__name__)


class SubmitFeedbackRequest(BaseModel):
    rating: Literal[-1, 1]
    reason: FeedbackReason
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackAcceptedResponse(BaseModel):
    id: UUID


@router.post(
    "/{answer_message_id}/feedback",
    response_model=FeedbackAcceptedResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="submitAnswerFeedback",
)
async def submit_feedback(
    answer_message_id: UUID,
    body: SubmitFeedbackRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FeedbackAcceptedResponse:
    async with session.begin():
        feedback_id = await SubmitFeedback(SqlAlchemyFeedbackRepository(session)).execute(
            SubmitFeedbackCommand(
                owner_id=current_user.id,
                answer_message_id=answer_message_id,
                rating=body.rating,
                reason=body.reason,
                comment=body.comment,
            )
        )
    log_event(logger, "answer_feedback_submitted", user_id=current_user.id)
    return FeedbackAcceptedResponse(id=feedback_id)
