import json
import logging
from uuid import uuid4

from app.platform.observability import JsonLogFormatter, bind_observation, reset_observation


def test_structured_log_keeps_only_safe_metadata() -> None:
    token = bind_observation(request_id="request-1")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="retrieval_completed",
            args=(),
            exc_info=None,
        )
        record.packed_evidence = 3
        record.question = "private question"
        payload = json.loads(JsonLogFormatter().format(record))
    finally:
        reset_observation(token)

    assert payload["event"] == "retrieval_completed"
    assert payload["request_id"] == "request-1"
    assert payload["packed_evidence"] == 3
    assert "question" not in payload


def test_structured_log_serializes_uuid_correlation_fields() -> None:
    user_id = uuid4()
    record = logging.LogRecord(
        name="app.identity",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="login_succeeded",
        args=(),
        exc_info=None,
    )
    record.user_id = user_id

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["user_id"] == str(user_id)


def test_cleanup_log_keeps_operational_fields_without_storage_details() -> None:
    cleanup_job_id = uuid4()
    token = bind_observation(cleanup_job_id=cleanup_job_id)
    try:
        record = logging.LogRecord(
            name="app.entrypoints.worker",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="deletion_cleanup_failed",
            args=(),
            exc_info=None,
        )
        record.resource_type = "document"
        record.error_code = "cleanup_dependency_failed"
        record.error_type = "TimeoutError"
        record.duration_ms = 12.5
        record.storage_key = "owners/private/source.pdf"

        payload = json.loads(JsonLogFormatter().format(record))
    finally:
        reset_observation(token)

    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "warning",
        "logger": "app.entrypoints.worker",
        "event": "deletion_cleanup_failed",
        "cleanup_job_id": str(cleanup_job_id),
        "resource_type": "document",
        "duration_ms": 12.5,
        "error_code": "cleanup_dependency_failed",
        "error_type": "TimeoutError",
    }
