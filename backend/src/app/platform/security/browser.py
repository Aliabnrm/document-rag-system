from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.modules.identity.infrastructure.models import SessionModel

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_PRE_AUTH_PATHS = {
    "/auth/registrations",
    "/auth/sessions",
    "/auth/password-resets/complete",
}


class BrowserSecurityMiddleware(BaseHTTPMiddleware):
    """Enforce exact-origin and server-bound CSRF checks for cookie-authenticated writes."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = request.app.state.settings
        raw_session = request.cookies.get(settings.session_cookie_name)
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)
        allowed_origins = {str(item).rstrip("/") for item in settings.cors_origins}
        origin = request.headers.get("origin")
        if origin is None:
            referer = request.headers.get("referer")
            origin = _origin_from_referer(referer)
        if origin is not None and origin not in allowed_origins:
            return _denied(request, "invalid_request_origin")
        relative_path = request.url.path.removeprefix(settings.api_v1_prefix.rstrip("/"))
        if relative_path in _PRE_AUTH_PATHS:
            # Credentials or reset secrets authorize these endpoints. Exact Origin still blocks
            # browser login/registration CSRF, while a stale HttpOnly cookie cannot deadlock
            # re-authentication or recovery.
            return await call_next(request)
        if raw_session is None:
            return await call_next(request)
        if origin is None:
            return _denied(request, "invalid_request_origin")
        csrf_header = request.headers.get("x-csrf-token")
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        if (
            csrf_header is None
            or csrf_cookie is None
            or not secrets.compare_digest(csrf_header, csrf_cookie)
        ):
            return _denied(request, "csrf_validation_failed")
        token_service = request.app.state.token_service
        async with request.app.state.database.session_factory() as session:
            expected_digest = await session.scalar(
                select(SessionModel.csrf_token_digest).where(
                    SessionModel.token_digest == token_service.digest(raw_session),
                    SessionModel.revoked_at.is_(None),
                )
            )
        if expected_digest is None or not token_service.matches(csrf_header, expected_digest):
            return _denied(request, "csrf_validation_failed")
        return await call_next(request)


def _origin_from_referer(value: str | None) -> str | None:
    if value is None:
        return None
    from urllib.parse import urlsplit

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _denied(request: Request, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": code,
                "message_key": f"errors.{code}",
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        },
    )
