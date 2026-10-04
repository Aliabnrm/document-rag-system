from __future__ import annotations

import asyncio
import socket
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.settings import Settings
from app.entrypoints.api import create_app
from app.modules.identity.application import CreatePasswordReset
from app.modules.identity.infrastructure.models import SessionModel
from app.modules.identity.infrastructure.rate_limit import RedisConcurrencyLimiter
from app.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from app.platform.database.session import Database
from app.platform.security import SecureTokenService


def services_are_available() -> bool:
    for port in (55432, 56379, 59000):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                pass
        except OSError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not services_are_available(),
    reason="PostgreSQL, Redis, and MinIO integration services are not running",
)


def test_registration_session_csrf_login_and_revocation() -> None:
    settings = Settings()
    email = f"auth-{uuid4()}@example.com"
    app = create_app(settings)
    client_host = f"auth-flow-{uuid4()}"

    with TestClient(app, client=(client_host, 50000)) as client:
        cross_origin_registration = client.post(
            "/api/v1/auth/registrations",
            json={
                "email": f"attacker-{uuid4()}@example.com",
                "password": "correct horse battery staple",
            },
            headers={"Origin": "https://attacker.invalid"},
        )
        assert cross_origin_registration.status_code == 403
        assert cross_origin_registration.json()["error"]["code"] == "invalid_request_origin"

        registered = client.post(
            "/api/v1/auth/registrations",
            json={
                "email": email.upper(),
                "password": "correct horse battery staple",
                "display_name": "Registered User",
            },
        )
        assert registered.status_code == 201
        assert registered.json()["email"] == email.upper()
        set_cookie = registered.headers.get_list("set-cookie")
        assert any("HttpOnly" in item and "SameSite=lax" in item for item in set_cookie)
        assert settings.session_cookie_name in client.cookies
        assert settings.csrf_cookie_name in client.cookies

        duplicate = client.post(
            "/api/v1/auth/registrations",
            json={"email": email, "password": "another correct horse battery staple"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "registration_unavailable"

        cross_origin_login = client.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "correct horse battery staple"},
            headers={"Origin": "https://attacker.invalid"},
        )
        assert cross_origin_login.status_code == 403
        assert cross_origin_login.json()["error"]["code"] == "invalid_request_origin"

        current = client.get("/api/v1/auth/me")
        assert current.status_code == 200
        assert current.json()["id"] == registered.json()["id"]

        without_csrf = client.post("/api/v1/collections", json={"name": "Denied"})
        assert without_csrf.status_code == 403
        assert without_csrf.json()["error"]["code"] == "invalid_request_origin"

        csrf = client.cookies[settings.csrf_cookie_name]
        client.headers.update({"Origin": "http://localhost:3000", "X-CSRF-Token": csrf})
        with_csrf = client.post("/api/v1/collections", json={"name": "Owned"})
        assert with_csrf.status_code == 201

        logout = client.delete("/api/v1/auth/session")
        assert logout.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.delete("/api/v1/auth/session").status_code == 204

        unknown = client.post(
            "/api/v1/auth/sessions",
            json={"email": f"missing-{uuid4()}@example.com", "password": "wrong password"},
        )
        wrong = client.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "wrong password"},
        )
        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json()["error"]["code"] == wrong.json()["error"]["code"]

        logged_in = client.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "correct horse battery staple"},
        )
        assert logged_in.status_code == 200

    asyncio.run(assert_session_tokens_are_hashed(settings))


def test_active_session_cap_and_single_use_password_reset() -> None:
    settings = Settings(auth_max_active_sessions=2)
    email = f"session-cap-{uuid4()}@example.com"
    client_host = f"session-flow-{uuid4()}"
    with (
        TestClient(create_app(settings), client=(client_host, 50000)) as first,
        TestClient(create_app(settings), client=(client_host, 50001)) as second,
        TestClient(create_app(settings), client=(client_host, 50002)) as third,
    ):
        registered = first.post(
            "/api/v1/auth/registrations",
            json={
                "email": email,
                "password": "correct horse battery staple",
            },
        )
        assert registered.status_code == 201
        assert second.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "correct horse battery staple"},
        ).status_code == 200
        assert third.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "correct horse battery staple"},
        ).status_code == 200

        assert first.get("/api/v1/auth/me").status_code == 401
        assert second.get("/api/v1/auth/me").status_code == 200
        assert third.get("/api/v1/auth/me").status_code == 200

        reset_token = asyncio.run(create_password_reset(settings, email))
        reset_headers = {"Origin": "http://localhost:3000"}
        completed = first.post(
            "/api/v1/auth/password-resets/complete",
            json={"token": reset_token, "new_password": "new correct horse battery staple"},
            headers=reset_headers,
        )
        assert completed.status_code == 204
        reused = first.post(
            "/api/v1/auth/password-resets/complete",
            json={"token": reset_token, "new_password": "another correct horse battery staple"},
            headers=reset_headers,
        )
        assert reused.status_code == 400
        assert reused.json()["error"]["code"] == "invalid_password_reset"
        assert second.get("/api/v1/auth/me").status_code == 401
        assert third.get("/api/v1/auth/me").status_code == 401
        assert first.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "correct horse battery staple"},
        ).status_code == 401
        assert first.post(
            "/api/v1/auth/sessions",
            json={"email": email, "password": "new correct horse battery staple"},
        ).status_code == 200


def test_registration_rate_limit_is_enforced_by_client() -> None:
    client_host = f"registration-rate-{uuid4()}"
    settings = Settings(auth_registration_attempt_limit=1)
    with TestClient(create_app(settings), client=(client_host, 50000)) as client:
        first = client.post(
            "/api/v1/auth/registrations",
            json={
                "email": f"first-{uuid4()}@example.com",
                "password": "correct horse battery staple",
            },
        )
        assert first.status_code == 201

        limited = client.post(
            "/api/v1/auth/registrations",
            json={
                "email": f"second-{uuid4()}@example.com",
                "password": "correct horse battery staple",
            },
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "rate_limited"


def test_concurrent_generation_lease_is_bounded_and_releasable() -> None:
    asyncio.run(assert_concurrency_lease(Settings()))


async def create_password_reset(settings: Settings, email: str) -> str:
    database = Database(settings)
    try:
        async with database.session_factory() as session, session.begin():
            created = await CreatePasswordReset(
                SqlAlchemyIdentityRepository(session), SecureTokenService()
            ).execute(email=email, expires_in=timedelta(minutes=30))
            assert created is not None
            return created[1]
    finally:
        await database.dispose()


async def assert_session_tokens_are_hashed(settings: Settings) -> None:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            sessions = (await session.scalars(select(SessionModel))).all()
            assert all(len(item.token_digest) == 64 for item in sessions)
    finally:
        await database.dispose()


async def assert_concurrency_lease(settings: Settings) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    identifier = str(uuid4())
    limiter = RedisConcurrencyLimiter(redis)
    try:
        assert await limiter.try_acquire(
            scope="test-generation",
            identifier=identifier,
            limit=1,
            lease_seconds=30,
        )
        assert not await limiter.try_acquire(
            scope="test-generation",
            identifier=identifier,
            limit=1,
            lease_seconds=30,
        )
        await limiter.release(scope="test-generation", identifier=identifier)
        assert await limiter.try_acquire(
            scope="test-generation",
            identifier=identifier,
            limit=1,
            lease_seconds=30,
        )
        await limiter.release(scope="test-generation", identifier=identifier)
    finally:
        await redis.aclose()
