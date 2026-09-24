import json
import logging

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
