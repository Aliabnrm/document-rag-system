from fastapi import Response

from app.core.settings import Settings
from app.modules.identity.application.use_cases import IssuedSession


def set_auth_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    max_age = settings.auth_session_absolute_hours * 3600
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.session_token,
        max_age=max_age,
        expires=issued.current.absolute_expires_at,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=issued.csrf_token,
        max_age=max_age,
        expires=issued.current.absolute_expires_at,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite="lax",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            key=name,
            path="/",
            secure=settings.auth_cookie_secure,
            httponly=name == settings.session_cookie_name,
            samesite="lax",
        )
