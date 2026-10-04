import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

_context: ContextVar[dict[str, object] | None] = ContextVar(
    "observation_context",
    default=None,
)

_SAFE_FIELDS = (
    "request_id",
    "user_id",
    "collection_id",
    "document_version_id",
    "job_id",
    "cleanup_job_id",
    "resource_type",
    "conversation_id",
    "rag_run_id",
    "method",
    "route",
    "status_code",
    "stage",
    "attempt",
    "duration_ms",
    "error_code",
    "error_type",
    "dense_candidates",
    "lexical_candidates",
    "fused_candidates",
    "packed_evidence",
    "packed_tokens",
    "input_tokens",
    "output_tokens",
    "abstained",
)


class JsonLogFormatter(logging.Formatter):
    """Emit a privacy-bounded JSON record for machines and local humans."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(_context.get() or {})
        for field in _SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configure_logging(*, level: str) -> None:
    application_logger = logging.getLogger("app")
    application_logger.setLevel(level.upper())
    application_logger.propagate = False
    existing = next(
        (
            handler
            for handler in application_logger.handlers
            if getattr(handler, "_docqa_json", False)
        ),
        None,
    )
    if existing is not None:
        existing.setLevel(level.upper())
        return
    handler = logging.StreamHandler()
    handler.setLevel(level.upper())
    handler.setFormatter(JsonLogFormatter())
    handler._docqa_json = True  # type: ignore[attr-defined]
    application_logger.addHandler(handler)


def bind_observation(**values: object) -> Token[dict[str, object] | None]:
    clean = {key: str(value) for key, value in values.items() if value is not None}
    return _context.set({**(_context.get() or {}), **clean})


def reset_observation(token: Token[dict[str, object] | None]) -> None:
    _context.reset(token)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger.log(
        level,
        event,
        extra={key: value for key, value in fields.items() if value is not None},
    )
