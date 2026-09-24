import logging
from dataclasses import dataclass
from time import perf_counter
from typing import BinaryIO, Protocol
from uuid import UUID

from app.modules.documents.application import SourceStorage
from app.modules.ingestion.domain import (
    PermanentIngestionError,
    RetryableIngestionError,
    SourcePage,
    TextChunk,
    chunk_pages,
)
from app.platform.observability import log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    pages: tuple[SourcePage, ...]
    diagnostics: dict[str, object]


class DocumentExtractor(Protocol):
    def extract(self, *, source: BinaryIO, media_type: str) -> ExtractionResult: ...


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    vectors: tuple[tuple[float, ...], ...]
    model_id: str
    revision: str
    dimensions: int
    maximum_input_tokens: int
    runtime: str


class EmbeddingProvider(Protocol):
    async def embed(self, texts: tuple[str, ...]) -> EmbeddingBatch: ...


@dataclass(frozen=True, slots=True)
class WorkerDocument:
    job_id: UUID
    document_version_id: UUID
    storage_key: str
    media_type: str
    pipeline_version: str
    attempt_count: int


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    chunk: TextChunk
    embedding: tuple[float, ...]
    embedding_model: str
    embedding_revision: str
    pipeline_version: str


class IngestionRepository(Protocol):
    async def claim(self, *, job_id: UUID, document_version_id: UUID) -> WorkerDocument | None: ...

    async def set_stage(self, *, job_id: UUID, stage: str) -> None: ...

    async def complete(
        self,
        *,
        worker_document: WorkerDocument,
        extraction: ExtractionResult,
        chunks: tuple[IndexedChunk, ...],
    ) -> None: ...

    async def fail_permanently(self, *, job_id: UUID, code: str) -> None: ...

    async def schedule_retry(
        self,
        *,
        job_id: UUID,
        code: str,
        maximum_attempts: int,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class DispatchRequest:
    job_id: UUID
    document_version_id: UUID


class DispatchRecoveryRepository(Protocol):
    async def claim_stale_dispatches(
        self,
        *,
        stale_after_seconds: int,
        limit: int,
    ) -> tuple[DispatchRequest, ...]: ...


class IngestionPipeline:
    def __init__(
        self,
        *,
        repository: IngestionRepository,
        storage: SourceStorage,
        extractor: DocumentExtractor,
        embedding_provider: EmbeddingProvider,
        chunk_size_tokens: int,
        overlap_tokens: int,
        expected_embedding_dimensions: int,
        embedding_batch_size: int = 32,
        maximum_attempts: int = 4,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._extractor = extractor
        self._embedding_provider = embedding_provider
        self._chunk_size_tokens = chunk_size_tokens
        self._overlap_tokens = overlap_tokens
        self._expected_embedding_dimensions = expected_embedding_dimensions
        self._embedding_batch_size = embedding_batch_size
        self._maximum_attempts = maximum_attempts

    async def process(self, *, job_id: UUID, document_version_id: UUID) -> bool:
        worker_document = await self._repository.claim(
            job_id=job_id,
            document_version_id=document_version_id,
        )
        if worker_document is None:
            log_event(logger, "ingestion_duplicate_delivery_ignored")
            return False

        pipeline_started = perf_counter()
        try:
            stage_started = perf_counter()
            source = await self._storage.download_file(key=worker_document.storage_key)
            try:
                extraction = self._extractor.extract(
                    source=source,
                    media_type=worker_document.media_type,
                )
            finally:
                source.close()
            log_event(
                logger,
                "ingestion_stage_completed",
                stage="extracting",
                attempt=worker_document.attempt_count,
                duration_ms=_elapsed_ms(stage_started),
            )
            await self._repository.set_stage(job_id=job_id, stage="chunking")
            stage_started = perf_counter()
            text_chunks = chunk_pages(
                extraction.pages,
                chunk_size_tokens=self._chunk_size_tokens,
                overlap_tokens=self._overlap_tokens,
            )
            if not text_chunks:
                raise PermanentIngestionError("empty_document")
            log_event(
                logger,
                "ingestion_stage_completed",
                stage="chunking",
                attempt=worker_document.attempt_count,
                duration_ms=_elapsed_ms(stage_started),
            )

            await self._repository.set_stage(job_id=job_id, stage="embedding")
            stage_started = perf_counter()
            indexed_chunks = await self._embed_chunks(
                text_chunks,
                pipeline_version=worker_document.pipeline_version,
            )
            log_event(
                logger,
                "ingestion_stage_completed",
                stage="embedding",
                attempt=worker_document.attempt_count,
                duration_ms=_elapsed_ms(stage_started),
            )
            await self._repository.complete(
                worker_document=worker_document,
                extraction=extraction,
                chunks=indexed_chunks,
            )
            log_event(
                logger,
                "ingestion_completed",
                stage="ready",
                attempt=worker_document.attempt_count,
                duration_ms=_elapsed_ms(pipeline_started),
            )
            return True
        except PermanentIngestionError as error:
            await self._repository.fail_permanently(job_id=job_id, code=error.code)
            log_event(
                logger,
                "ingestion_failed",
                level=logging.WARNING,
                stage="failed",
                attempt=worker_document.attempt_count,
                error_code=error.code,
                duration_ms=_elapsed_ms(pipeline_started),
            )
            return False
        except RetryableIngestionError:
            raise
        except Exception as error:
            should_retry = await self._repository.schedule_retry(
                job_id=job_id,
                code=_safe_transient_code(error),
                maximum_attempts=self._maximum_attempts,
            )
            if should_retry:
                log_event(
                    logger,
                    "ingestion_retry_scheduled",
                    level=logging.WARNING,
                    attempt=worker_document.attempt_count,
                    error_code=_safe_transient_code(error),
                    duration_ms=_elapsed_ms(pipeline_started),
                )
                raise RetryableIngestionError("transient_dependency_failure") from error
            log_event(
                logger,
                "ingestion_failed",
                level=logging.ERROR,
                stage="failed",
                attempt=worker_document.attempt_count,
                error_code=_safe_transient_code(error),
                duration_ms=_elapsed_ms(pipeline_started),
            )
            return False

    async def _embed_chunks(
        self,
        chunks: tuple[TextChunk, ...],
        *,
        pipeline_version: str,
    ) -> tuple[IndexedChunk, ...]:
        indexed: list[IndexedChunk] = []
        for start in range(0, len(chunks), self._embedding_batch_size):
            batch_chunks = chunks[start : start + self._embedding_batch_size]
            batch = await self._embedding_provider.embed(
                tuple(chunk.normalized_text for chunk in batch_chunks)
            )
            if len(batch.vectors) != len(batch_chunks):
                raise RuntimeError("embedding_batch_size_mismatch")
            if batch.dimensions != self._expected_embedding_dimensions:
                raise RuntimeError("configured_embedding_dimension_mismatch")
            if any(len(vector) != batch.dimensions for vector in batch.vectors):
                raise RuntimeError("embedding_dimension_mismatch")
            indexed.extend(
                IndexedChunk(
                    chunk=chunk,
                    embedding=vector,
                    embedding_model=batch.model_id,
                    embedding_revision=batch.revision,
                    pipeline_version=pipeline_version,
                )
                for chunk, vector in zip(batch_chunks, batch.vectors, strict=True)
            )
        return tuple(indexed)


def _safe_transient_code(error: Exception) -> str:
    error_name = type(error).__name__.lower()
    if "timeout" in error_name:
        return "dependency_timeout"
    return "dependency_unavailable"


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)
