import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.platform.errors import ApplicationError
from app.platform.observability import bind_observation, log_event, reset_observation

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    field: str
    code: str


class ErrorBody(BaseModel):
    code: str
    message_key: str
    request_id: str
    details: list[ErrorDetail] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _parse_request_id(request.headers.get("x-request-id"))
        request.state.request_id = str(request_id)
        started = perf_counter()
        token = bind_observation(request_id=request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = str(request_id)
            route = request.scope.get("route")
            log_event(
                logger,
                "http_request_completed",
                method=request.method,
                route=getattr(route, "path", request.url.path),
                status_code=response.status_code,
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )
            return response
        finally:
            reset_observation(token)


def _parse_request_id(value: str | None) -> UUID:
    if value is None:
        return uuid4()
    try:
        return UUID(value)
    except ValueError:
        return uuid4()


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        error: ApplicationError,
    ) -> JSONResponse:
        details = [
            ErrorDetail(field=item.field, code=item.code).model_dump()
            for item in error.field_errors
        ]
        return JSONResponse(
            status_code=error.status_code,
            content=_error_content(
                request,
                code=error.code,
                message_key=error.message_key,
                details=details or None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        details: list[dict[str, str]] = []
        for item in error.errors():
            location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
            details.append({"field": location or "request", "code": str(item["type"])})
        return JSONResponse(
            status_code=422,
            content=_error_content(
                request,
                code="validation_failed",
                message_key="errors.validation_failed",
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        code = "not_found" if error.status_code == 404 else "http_error"
        return JSONResponse(
            status_code=error.status_code,
            content=_error_content(
                request,
                code=code,
                message_key=f"errors.{code}",
            ),
            headers=error.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        log_event(
            logger,
            "http_request_failed",
            level=logging.ERROR,
            route=request.url.path,
            error_type=type(error).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=_error_content(
                request,
                code="internal_error",
                message_key="errors.internal_error",
            ),
        )


def _error_content(
    request: Request,
    *,
    code: str,
    message_key: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body = ErrorBody(
        code=code,
        message_key=message_key,
        request_id=getattr(request.state, "request_id", "unknown"),
        details=[ErrorDetail.model_validate(item) for item in details] if details else None,
    )
    return ErrorEnvelope(error=body).model_dump(exclude_none=True)
