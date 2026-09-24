from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    code: str


class ApplicationError(Exception):
    """A safe, stable failure that may cross the HTTP boundary."""

    def __init__(
        self,
        *,
        code: str,
        message_key: str,
        status_code: int,
        field_errors: tuple[FieldError, ...] = (),
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.message_key = message_key
        self.status_code = status_code
        self.field_errors = field_errors
        self.context = context or {}


class NotFoundError(ApplicationError):
    def __init__(self, code: str, message_key: str) -> None:
        super().__init__(code=code, message_key=message_key, status_code=404)


class ConflictError(ApplicationError):
    def __init__(self, code: str, message_key: str) -> None:
        super().__init__(code=code, message_key=message_key, status_code=409)


class UnsupportedDocumentError(ApplicationError):
    def __init__(self, code: str, message_key: str) -> None:
        super().__init__(code=code, message_key=message_key, status_code=422)
