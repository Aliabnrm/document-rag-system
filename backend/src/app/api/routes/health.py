import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.platform.database.session import Database
from app.platform.errors import ApplicationError, FieldError

router = APIRouter()


class HealthResponse(BaseModel):
    """Stable public contract for process liveness."""

    status: Literal["ok"] = "ok"
    service: Literal["document-qa-api"] = "document-qa-api"
    version: str = "0.1.0"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["available"] = "available"
    queue: Literal["available"] = "available"
    object_storage: Literal["available"] = "available"


@router.get("/health", response_model=HealthResponse, operation_id="getHealth")
async def get_health() -> HealthResponse:
    """Confirm that the API process can serve requests."""
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse, operation_id="getReadiness")
async def get_readiness(request: Request) -> ReadinessResponse:
    """Confirm that required dependencies can serve application traffic."""
    database: Database = request.app.state.database
    checks = await asyncio.gather(
        _database_ready(database),
        _queue_ready(request.app.state.redis),
        _storage_ready(request.app.state.source_storage),
        return_exceptions=True,
    )
    names = ("database", "queue", "object_storage")
    unavailable = tuple(
        FieldError(field=name, code="unavailable")
        for name, result in zip(names, checks, strict=True)
        if isinstance(result, BaseException)
    )
    if unavailable:
        raise ApplicationError(
            code="dependencies_unavailable",
            message_key="errors.dependencies_unavailable",
            status_code=503,
            field_errors=unavailable,
        )
    return ReadinessResponse()


async def _database_ready(database: Database) -> None:
    async with asyncio.timeout(3):
        async with database.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))


async def _queue_ready(redis: object) -> None:
    async with asyncio.timeout(3):
        if not await redis.ping():  # type: ignore[attr-defined]
            raise RuntimeError("queue_not_ready")


async def _storage_ready(storage: object) -> None:
    async with asyncio.timeout(3):
        if not await storage.is_ready():  # type: ignore[attr-defined]
            raise RuntimeError("storage_not_ready")
