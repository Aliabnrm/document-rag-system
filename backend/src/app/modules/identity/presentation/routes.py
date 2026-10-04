from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application import (
    ChangePassword,
    CurrentSession,
    Login,
    LoginCommand,
    LogoutAll,
    Register,
    RegisterCommand,
    ResetPassword,
)
from app.modules.identity.infrastructure.rate_limit import RedisRateLimiter
from app.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from app.modules.identity.presentation.cookies import clear_auth_cookies, set_auth_cookies
from app.modules.identity.presentation.dependencies import get_current_session
from app.modules.identity.presentation.schemas import (
    ChangePasswordRequest,
    CompletePasswordResetRequest,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from app.platform.database.dependencies import get_db_session
from app.platform.errors import ApplicationError
from app.platform.observability import log_event

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/registrations",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="registerAccount",
)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUserResponse:
    settings = request.app.state.settings
    client_host = request.client.host if request.client else "unknown"
    use_case = Register(
        SqlAlchemyIdentityRepository(session),
        request.app.state.password_hasher,
        request.app.state.token_service,
        RedisRateLimiter(request.app.state.redis),
        idle_ttl=timedelta(minutes=settings.auth_session_idle_minutes),
        absolute_ttl=timedelta(hours=settings.auth_session_absolute_hours),
        limit=settings.auth_registration_attempt_limit,
        window_seconds=settings.auth_registration_window_seconds,
        max_active_sessions=settings.auth_max_active_sessions,
    )
    try:
        async with session.begin():
            issued = await use_case.execute(
                RegisterCommand(
                    email=body.email,
                    password=body.password,
                    display_name=body.display_name,
                    rate_identifier=client_host,
                )
            )
    except ApplicationError as error:
        log_event(logger, "registration_rejected", error_code=error.code)
        raise
    set_auth_cookies(response, issued, settings)
    log_event(logger, "registration_succeeded", user_id=issued.current.user.id)
    return CurrentUserResponse.from_session(issued.current)


@router.post(
    "/sessions",
    response_model=CurrentUserResponse,
    operation_id="login",
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUserResponse:
    settings = request.app.state.settings
    client_host = request.client.host if request.client else "unknown"
    use_case = Login(
        SqlAlchemyIdentityRepository(session),
        request.app.state.password_hasher,
        request.app.state.token_service,
        RedisRateLimiter(request.app.state.redis),
        idle_ttl=timedelta(minutes=settings.auth_session_idle_minutes),
        absolute_ttl=timedelta(hours=settings.auth_session_absolute_hours),
        limit=settings.auth_login_attempt_limit,
        window_seconds=settings.auth_login_window_seconds,
        max_active_sessions=settings.auth_max_active_sessions,
    )
    try:
        async with session.begin():
            issued = await use_case.execute(
                LoginCommand(email=body.email, password=body.password, rate_identifier=client_host)
            )
    except ApplicationError as error:
        log_event(logger, "login_rejected", error_code=error.code)
        raise
    set_auth_cookies(response, issued, settings)
    log_event(logger, "login_succeeded", user_id=issued.current.user.id)
    return CurrentUserResponse.from_session(issued.current)


@router.get("/me", response_model=CurrentUserResponse, operation_id="getCurrentUser")
async def me(
    current: Annotated[CurrentSession, Depends(get_current_session)],
) -> CurrentUserResponse:
    return CurrentUserResponse.from_session(current)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    raw_token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if raw_token is not None:
        async with session.begin():
            await SqlAlchemyIdentityRepository(session).revoke_session_by_digest(
                request.app.state.token_service.digest(raw_token),
                request.app.state.clock(),
            )
        log_event(logger, "session_revoked")
    clear_auth_cookies(response, request.app.state.settings)


@router.delete(
    "/sessions", status_code=status.HTTP_204_NO_CONTENT, operation_id="logoutAllSessions"
)
async def logout_all(
    request: Request,
    response: Response,
    current: Annotated[CurrentSession, Depends(get_current_session)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    async with session.begin():
        await LogoutAll(SqlAlchemyIdentityRepository(session)).execute(current.user.id)
    log_event(logger, "all_sessions_revoked", user_id=current.user.id)
    clear_auth_cookies(response, request.app.state.settings)


@router.post(
    "/password-changes",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="changePassword",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current: Annotated[CurrentSession, Depends(get_current_session)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    async with session.begin():
        await ChangePassword(
            SqlAlchemyIdentityRepository(session), request.app.state.password_hasher
        ).execute(
            current=current,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    log_event(logger, "password_changed", user_id=current.user.id)


@router.post(
    "/password-resets/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="completePasswordReset",
)
async def complete_password_reset(
    body: CompletePasswordResetRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    async with session.begin():
        user = await ResetPassword(
            SqlAlchemyIdentityRepository(session),
            request.app.state.password_hasher,
            request.app.state.token_service,
        ).execute(raw_token=body.token, new_password=body.new_password)
    log_event(logger, "password_reset", user_id=user.id)
