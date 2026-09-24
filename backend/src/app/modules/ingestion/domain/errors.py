class IngestionError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PermanentIngestionError(IngestionError):
    """Content cannot be processed without changing the source or pipeline."""


class RetryableIngestionError(IngestionError):
    """Infrastructure failed transiently and bounded retry is appropriate."""
