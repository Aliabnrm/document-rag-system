from uuid import UUID

from celery import Celery  # type: ignore[import-untyped]
from starlette.concurrency import run_in_threadpool

from app.core.settings import Settings, get_settings

INGESTION_TASK_NAME = "app.ingestion.process_document_version"
RECONCILE_TASK_NAME = "app.ingestion.reconcile_pending_dispatches"


def create_celery_app(settings: Settings) -> Celery:
    application = Celery(
        "document_qa",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.entrypoints.worker"],
    )
    application.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_always_eager=settings.celery_task_always_eager,
        beat_schedule_filename="/tmp/document-qa-celerybeat-schedule",
        beat_schedule={
            "reconcile-persisted-ingestion-dispatches": {
                "task": RECONCILE_TASK_NAME,
                "schedule": 30.0,
            }
        },
    )
    return application


celery_app = create_celery_app(get_settings())


class CeleryJobDispatcher:
    def __init__(self, application: Celery = celery_app) -> None:
        self._application = application

    async def dispatch(self, *, job_id: UUID, document_version_id: UUID) -> None:
        await run_in_threadpool(
            self._application.send_task,
            INGESTION_TASK_NAME,
            kwargs={
                "job_id": str(job_id),
                "document_version_id": str(document_version_id),
            },
        )
