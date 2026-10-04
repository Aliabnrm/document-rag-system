import asyncio
import logging
from time import perf_counter
from uuid import UUID

from app.core.settings import get_settings
from app.modules.data_lifecycle.infrastructure import SqlAlchemyCleanupRepository
from app.modules.ingestion.application import IngestionPipeline
from app.modules.ingestion.domain import RetryableIngestionError
from app.modules.ingestion.infrastructure.extraction import PdfTxtExtractor
from app.modules.ingestion.infrastructure.repository import (
    SqlAlchemyDispatchRecoveryRepository,
    SqlAlchemyIngestionRepository,
)
from app.platform.ai import create_embedding_provider
from app.platform.database.session import Database
from app.platform.observability import (
    bind_observation,
    configure_logging,
    log_event,
    reset_observation,
)
from app.platform.queue.celery import (
    DELETION_CLEANUP_TASK_NAME,
    INGESTION_TASK_NAME,
    RECONCILE_DELETION_TASK_NAME,
    RECONCILE_TASK_NAME,
    celery_app,
)
from app.platform.storage import S3SourceStorage

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name=INGESTION_TASK_NAME,
    autoretry_for=(RetryableIngestionError,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)  # type: ignore[untyped-decorator]
def process_document_version(
    _task: object,
    *,
    job_id: str,
    document_version_id: str,
) -> bool:
    return asyncio.run(
        _process_document_version(
            job_id=UUID(job_id),
            document_version_id=UUID(document_version_id),
        )
    )


async def _process_document_version(*, job_id: UUID, document_version_id: UUID) -> bool:
    settings = get_settings()
    configure_logging(level=settings.app_log_level)
    observation = bind_observation(job_id=job_id, document_version_id=document_version_id)
    database = Database(settings)
    storage = S3SourceStorage(settings)
    try:
        async with database.session_factory() as session:
            pipeline = IngestionPipeline(
                repository=SqlAlchemyIngestionRepository(session),
                storage=storage,
                extractor=PdfTxtExtractor(),
                embedding_provider=create_embedding_provider(settings),
                chunk_size_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
                expected_embedding_dimensions=settings.embedding_dimensions,
            )
            return await pipeline.process(
                job_id=job_id,
                document_version_id=document_version_id,
            )
    finally:
        await database.dispose()
        reset_observation(observation)


@celery_app.task(name=RECONCILE_TASK_NAME)  # type: ignore[untyped-decorator]
def reconcile_pending_dispatches() -> int:
    return asyncio.run(_reconcile_pending_dispatches())


async def _reconcile_pending_dispatches() -> int:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            requests = await SqlAlchemyDispatchRecoveryRepository(session).claim_stale_dispatches(
                stale_after_seconds=60, limit=100
            )
        for request in requests:
            celery_app.send_task(
                INGESTION_TASK_NAME,
                kwargs={
                    "job_id": str(request.job_id),
                    "document_version_id": str(request.document_version_id),
                },
            )
        return len(requests)
    finally:
        await database.dispose()


class RetryableCleanupError(RuntimeError):
    """Sanitized worker error that Celery may retry without exposing provider details."""


@celery_app.task(
    bind=True,
    name=DELETION_CLEANUP_TASK_NAME,
    autoretry_for=(RetryableCleanupError,),
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)  # type: ignore[untyped-decorator]
def cleanup_deleted_resource(_task: object, *, cleanup_job_id: str) -> bool:
    return asyncio.run(_cleanup_deleted_resource(cleanup_job_id=UUID(cleanup_job_id)))


async def _cleanup_deleted_resource(*, cleanup_job_id: UUID) -> bool:
    settings = get_settings()
    configure_logging(level=settings.app_log_level)
    observation = bind_observation(cleanup_job_id=cleanup_job_id)
    database = Database(settings)
    storage = S3SourceStorage(settings)
    cleanup_started = perf_counter()
    try:
        async with database.session_factory() as session:
            repository = SqlAlchemyCleanupRepository(session)
            try:
                request = await repository.claim(cleanup_job_id)
                if request is None:
                    log_event(
                        logger,
                        "deletion_cleanup_skipped",
                        duration_ms=_elapsed_ms(cleanup_started),
                    )
                    return False
                log_event(
                    logger,
                    "deletion_cleanup_started",
                    resource_type=request.resource_type,
                )
                for storage_key in request.storage_keys:
                    await storage.delete(key=storage_key)
                await repository.complete(request)
                log_event(
                    logger,
                    "deletion_cleanup_succeeded",
                    resource_type=request.resource_type,
                    duration_ms=_elapsed_ms(cleanup_started),
                )
                return True
            except Exception as error:
                await session.rollback()
                try:
                    await repository.fail(
                        cleanup_job_id,
                        error_code="cleanup_dependency_failed",
                    )
                except Exception as state_error:
                    await session.rollback()
                    log_event(
                        logger,
                        "deletion_cleanup_failure_state_not_recorded",
                        level=logging.ERROR,
                        error_code="cleanup_state_persistence_failed",
                        error_type=type(state_error).__name__,
                    )
                log_event(
                    logger,
                    "deletion_cleanup_failed",
                    level=logging.WARNING,
                    error_code="cleanup_dependency_failed",
                    error_type=type(error).__name__,
                    duration_ms=_elapsed_ms(cleanup_started),
                )
                raise RetryableCleanupError("deletion cleanup dependency failed") from error
    finally:
        await database.dispose()
        reset_observation(observation)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


@celery_app.task(name=RECONCILE_DELETION_TASK_NAME)  # type: ignore[untyped-decorator]
def reconcile_cleanup_dispatches() -> int:
    return asyncio.run(_reconcile_cleanup_dispatches())


async def _reconcile_cleanup_dispatches() -> int:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            job_ids = await SqlAlchemyCleanupRepository(session).list_dispatchable(
                stale_after_seconds=300,
                limit=100,
            )
        for job_id in job_ids:
            celery_app.send_task(
                DELETION_CLEANUP_TASK_NAME,
                kwargs={"cleanup_job_id": str(job_id)},
            )
        return len(job_ids)
    finally:
        await database.dispose()
