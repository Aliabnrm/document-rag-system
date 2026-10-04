from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.modules.identity.application import CurrentSession, ResolveSession
from app.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from app.platform.errors import ApplicationError
from app.platform.observability import bind_observation


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID


async def get_current_session(
    request: Request,
) -> CurrentSession:
    cookie_name = request.app.state.settings.session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if raw_token is None:
        raise ApplicationError(
            code="authentication_required",
            message_key="errors.authentication_required",
            status_code=401,
        )
    async with request.app.state.database.session_factory() as session:
        current = await ResolveSession(
            SqlAlchemyIdentityRepository(session),
            request.app.state.token_service,
            idle_ttl=timedelta(minutes=request.app.state.settings.auth_session_idle_minutes),
        ).execute(raw_token)
        await session.commit()
    bind_observation(user_id=current.user.id)
    return current


async def get_current_user(
    current: Annotated[CurrentSession, Depends(get_current_session)],
) -> CurrentUser:
    return CurrentUser(id=current.user.id)
