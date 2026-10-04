from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.router import api_router
from app.core.settings import Settings, get_settings
from app.platform.database.session import Database
from app.platform.http import RequestContextMiddleware, install_exception_handlers
from app.platform.observability import configure_logging
from app.platform.queue import CeleryDeletionDispatcher, CeleryJobDispatcher
from app.platform.queue.celery import create_celery_app
from app.platform.security import Argon2PasswordHasher, SecureTokenService
from app.platform.security.browser import BrowserSecurityMiddleware
from app.platform.storage import S3SourceStorage


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(level=runtime_settings.app_log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(runtime_settings)
        redis = Redis.from_url(runtime_settings.redis_url, decode_responses=True)
        source_storage = S3SourceStorage(runtime_settings)
        application.state.database = database
        application.state.redis = redis
        application.state.source_storage = source_storage
        celery = create_celery_app(runtime_settings)
        application.state.job_dispatcher = CeleryJobDispatcher(celery)
        application.state.deletion_dispatcher = CeleryDeletionDispatcher(celery)
        try:
            await source_storage.ensure_bucket()
            yield
        finally:
            await redis.aclose()
            await database.dispose()

    application = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        docs_url="/docs" if runtime_settings.docs_enabled else None,
        redoc_url="/redoc" if runtime_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    application.state.token_service = SecureTokenService()
    application.state.password_hasher = Argon2PasswordHasher(
        time_cost=runtime_settings.auth_argon2_time_cost,
        memory_cost_kib=runtime_settings.auth_argon2_memory_cost_kib,
        parallelism=runtime_settings.auth_argon2_parallelism,
    )
    application.state.clock = lambda: datetime.now(UTC)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(BrowserSecurityMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in runtime_settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )
    install_exception_handlers(application)
    application.include_router(api_router, prefix=runtime_settings.api_v1_prefix)
    return application
