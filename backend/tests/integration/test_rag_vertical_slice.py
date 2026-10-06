import asyncio
import socket
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.settings import Settings
from app.entrypoints.api import create_app
from app.entrypoints.worker import _cleanup_deleted_resource
from app.modules.conversations.infrastructure.models import CitationModel
from app.modules.ingestion.application import IngestionPipeline
from app.modules.ingestion.infrastructure.extraction import PdfTxtExtractor
from app.modules.ingestion.infrastructure.repository import (
    SqlAlchemyDispatchRecoveryRepository,
    SqlAlchemyIngestionRepository,
)
from app.modules.retrieval.infrastructure.models import ChunkModel
from app.modules.retrieval.infrastructure.repository import PgVectorRetrievalRepository
from app.platform.ai import create_embedding_provider
from app.platform.database.session import Database
from app.platform.storage import S3SourceStorage


def services_are_available() -> bool:
    for port in (55432, 56379, 59000):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                pass
        except OSError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not services_are_available(),
    reason="PostgreSQL and MinIO integration services are not running",
)


@dataclass
class RecordingDispatcher:
    dispatched: list[tuple[UUID, UUID]] = field(default_factory=list)

    async def dispatch(self, *, job_id: UUID, document_version_id: UUID) -> None:
        self.dispatched.append((job_id, document_version_id))


@dataclass
class RecordingDeletionDispatcher:
    dispatched: list[UUID] = field(default_factory=list)

    async def dispatch(self, *, cleanup_job_id: UUID) -> None:
        self.dispatched.append(cleanup_job_id)


def test_create_upload_ingest_ask_and_validate_citation() -> None:
    settings = Settings(quota_documents_per_user=1, quota_questions_per_day=2)
    application = create_app(settings)
    dispatcher = RecordingDispatcher()
    deletion_dispatcher = RecordingDeletionDispatcher()
    source = "راهنمای شركت آوا\n\nمدیر عامل شرکت آوا، لیلا نوری است. تاریخ تأسیس ۱۴۰۲ است."
    owner_email = f"owner-{uuid4()}@example.com"

    with TestClient(application, client=(f"rag-owner-{uuid4()}", 50000)) as client:
        application.state.job_dispatcher = dispatcher
        application.state.deletion_dispatcher = deletion_dispatcher
        readiness_response = client.get("/api/v1/ready")
        assert readiness_response.status_code == 200
        assert readiness_response.json() == {
            "status": "ready",
            "database": "available",
            "queue": "available",
            "object_storage": "available",
        }
        registration_response = client.post(
            "/api/v1/auth/registrations",
            json={
                "email": owner_email,
                "password": "correct horse battery staple",
                "display_name": "Owner",
            },
        )
        assert registration_response.status_code == 201
        owner_id = UUID(registration_response.json()["id"])
        client.headers.update(
            {
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
            }
        )
        collection_response = client.post(
            "/api/v1/collections",
            json={"name": "راهنمای آوا", "description": "آزمون واقعی"},
        )
        assert collection_response.status_code == 201
        collection_id = UUID(collection_response.json()["id"])

        upload_response = client.post(
            f"/api/v1/collections/{collection_id}/documents",
            files={"file": ("ava-guide.txt", source.encode(), "text/plain")},
        )
        assert upload_response.status_code == 202
        upload = upload_response.json()
        document_id = UUID(upload["document_id"])
        version_id = UUID(upload["document_version_id"])
        job_id = UUID(upload["job_id"])
        assert upload["status"] == "queued"
        assert dispatcher.dispatched == [(job_id, version_id)]
        quota_response = client.post(
            f"/api/v1/collections/{collection_id}/documents",
            files={"file": ("second.txt", b"quota", "text/plain")},
        )
        assert quota_response.status_code == 429
        assert quota_response.json()["error"]["code"] == "document_quota_exceeded"

        recovered = asyncio.run(claim_dispatch_recovery(settings))
        assert recovered == [(job_id, version_id)]

        processed = asyncio.run(
            run_ingestion(settings=settings, job_id=job_id, document_version_id=version_id)
        )
        assert processed is True
        duplicate = asyncio.run(
            run_ingestion(settings=settings, job_id=job_id, document_version_id=version_id)
        )
        assert duplicate is False

        status_response = client.get(f"/api/v1/collections/{collection_id}/documents/{document_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "ready"
        assert status_response.json()["page_count"] == 1

        chunk_evidence = asyncio.run(read_chunk_evidence(settings, version_id))
        assert chunk_evidence["count"] == 1
        assert "شركت" in str(chunk_evidence["source_text"])
        assert "شرکت" in str(chunk_evidence["normalized_text"])

        conversation_response = client.post(
            f"/api/v1/collections/{collection_id}/conversations",
            json={"title": "مدیریت"},
        )
        conversation_id = conversation_response.json()["id"]
        answer_response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages:stream",
            json={"question": "مدیر عامل شرکت آوا چه کسی است؟", "language": "fa"},
        )
        assert answer_response.status_code == 200
        assert "event: citations" in answer_response.text
        assert '"evidence_id": "E1"' in answer_response.text
        assert '"page_start": 1' in answer_response.text
        assert "لیلا نوری" in answer_response.text
        assert '"abstained": false' in answer_response.text
        abstention_response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages:stream",
            json={"question": "What is the lunar orbital period?", "language": "en"},
        )
        assert abstention_response.status_code == 200
        assert '"abstained": true' in abstention_response.text
        assert "event: answer_delta" in abstention_response.text
        assert "event: citations" not in abstention_response.text

        question_quota = client.post(
            f"/api/v1/conversations/{conversation_id}/messages:stream",
            json={"question": "What year was Ava founded?", "language": "en"},
        )
        assert question_quota.status_code == 429
        assert question_quota.json()["error"]["code"] == "question_quota_exceeded"

        persisted_messages = client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        )
        assert persisted_messages.status_code == 200
        message_items = persisted_messages.json()["items"]
        assert [item["role"] for item in message_items] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert message_items[1]["content"]
        assert message_items[1]["abstained"] is False
        assert message_items[1]["citations"][0]["page_start"] == 1
        assert message_items[3]["abstained"] is True
        assert message_items[3]["content"] == (
            "I could not find an answer to this question in the ready documents."
        )
        assert message_items[3]["citations"] == []
        answer_message_id = message_items[1]["id"]

        feedback_response = client.post(
            f"/api/v1/messages/{answer_message_id}/feedback",
            json={
                "rating": -1,
                "reason": "citation_mismatch",
                "comment": "Controlled integration feedback",
            },
        )
        assert feedback_response.status_code == 201

        extra_collection_ids = {
            client.post("/api/v1/collections", json={"name": f"Extra {index}"}).json()["id"]
            for index in range(2)
        }
        paged_collection_ids = collect_cursor_pages(
            client,
            "/api/v1/collections",
            cursor_name="cursor",
        )
        assert set(paged_collection_ids) == {str(collection_id), *extra_collection_ids}
        assert len(paged_collection_ids) == len(set(paged_collection_ids))

        extra_conversation_ids = {
            client.post(
                f"/api/v1/collections/{collection_id}/conversations",
                json={"title": f"Extra {index}"},
            ).json()["id"]
            for index in range(2)
        }
        paged_conversation_ids = collect_cursor_pages(
            client,
            f"/api/v1/collections/{collection_id}/conversations",
            cursor_name="cursor",
        )
        assert set(paged_conversation_ids) == {conversation_id, *extra_conversation_ids}
        assert len(paged_conversation_ids) == len(set(paged_conversation_ids))

        assert_other_user_is_isolated(
            settings=settings,
            collection_id=collection_id,
            document_id=document_id,
            conversation_id=UUID(conversation_id),
            answer_message_id=UUID(answer_message_id),
        )

        deletion_response = client.delete(
            f"/api/v1/collections/{collection_id}/documents/{document_id}"
        )
        assert deletion_response.status_code == 204
        duplicate_deletion = client.delete(
            f"/api/v1/collections/{collection_id}/documents/{document_id}"
        )
        assert duplicate_deletion.status_code == 204
        document_cleanup_id = deletion_dispatcher.dispatched[-1]
        assert asyncio.run(_cleanup_deleted_resource(cleanup_job_id=document_cleanup_id)) is True
        assert asyncio.run(_cleanup_deleted_resource(cleanup_job_id=document_cleanup_id)) is False
        deleted_status = client.get(f"/api/v1/collections/{collection_id}/documents/{document_id}")
        assert deleted_status.status_code == 404
        assert client.delete(f"/api/v1/collections/{collection_id}").status_code == 204
        assert client.delete(f"/api/v1/collections/{collection_id}").status_code == 204
        collection_cleanup_id = deletion_dispatcher.dispatched[-1]
        assert asyncio.run(_cleanup_deleted_resource(cleanup_job_id=collection_cleanup_id)) is True
        assert client.get(f"/api/v1/collections/{collection_id}").status_code == 404

    citation_count = asyncio.run(count_citations(settings, version_id))
    assert citation_count == 0
    deleted_results = asyncio.run(
        retrieve_as_other_user(
            settings,
            owner_id=owner_id,
            collection_id=collection_id,
        )
    )
    assert deleted_results == 0
    unauthorized_results = asyncio.run(
        retrieve_as_other_user(settings, owner_id=uuid4(), collection_id=collection_id)
    )
    assert unauthorized_results == 0



def assert_other_user_is_isolated(
    *,
    settings: Settings,
    collection_id: UUID,
    document_id: UUID,
    conversation_id: UUID,
    answer_message_id: UUID,
) -> None:
    other_email = f"other-{uuid4()}@example.com"
    other_user_app = create_app(settings)
    with TestClient(
        other_user_app, client=(f"rag-other-{uuid4()}", 50000)
    ) as other_client:
        other_registration = other_client.post(
            "/api/v1/auth/registrations",
            json={
                "email": other_email,
                "password": "another correct horse battery staple",
            },
        )
        assert other_registration.status_code == 201
        other_client.headers.update(
            {
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": other_client.cookies[settings.csrf_cookie_name],
            }
        )

        assert other_client.get(f"/api/v1/collections/{collection_id}").status_code == 404
        foreign_document = other_client.get(
            f"/api/v1/collections/{collection_id}/documents/{document_id}"
        )
        assert foreign_document.status_code == 404
        assert foreign_document.json()["error"]["code"] == "document_not_found"
        assert other_client.get(
            f"/api/v1/collections/{collection_id}/documents"
        ).status_code == 404
        assert other_client.post(
            f"/api/v1/collections/{collection_id}/documents",
            files={"file": ("foreign.txt", b"private", "text/plain")},
        ).status_code == 404
        assert other_client.post(
            f"/api/v1/collections/{collection_id}/documents/{document_id}/ingestion-retries"
        ).status_code == 404
        foreign_conversations = other_client.get(
            f"/api/v1/collections/{collection_id}/conversations"
        )
        assert foreign_conversations.status_code == 404
        foreign_messages = other_client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        )
        assert foreign_messages.status_code == 404
        foreign_stream = other_client.post(
            f"/api/v1/conversations/{conversation_id}/messages:stream",
            json={"question": "Reveal the private answer", "language": "en"},
        )
        assert foreign_stream.status_code == 404
        assert other_client.post(
            f"/api/v1/messages/{answer_message_id}/feedback",
            json={"rating": 1, "reason": "helpful"},
        ).status_code == 404
        assert other_client.delete(
            f"/api/v1/collections/{collection_id}/documents/{document_id}"
        ).status_code == 404
        assert other_client.delete(f"/api/v1/collections/{collection_id}").status_code == 404


def collect_cursor_pages(
    client: TestClient,
    path: str,
    *,
    cursor_name: str,
) -> list[str]:
    cursor: str | None = None
    identifiers: list[str] = []
    while True:
        params: dict[str, str | int] = {"page_size": 1}
        if cursor is not None:
            params[cursor_name] = cursor
        response = client.get(path, params=params)
        assert response.status_code == 200
        payload = response.json()
        identifiers.extend(item["id"] for item in payload["items"])
        cursor = payload["next_cursor"]
        if cursor is None:
            return identifiers


async def run_ingestion(
    *,
    settings: Settings,
    job_id: UUID,
    document_version_id: UUID,
) -> bool:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            pipeline = IngestionPipeline(
                repository=SqlAlchemyIngestionRepository(session),
                storage=S3SourceStorage(settings),
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


async def claim_dispatch_recovery(settings: Settings) -> list[tuple[UUID, UUID]]:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            requests = await SqlAlchemyDispatchRecoveryRepository(session).claim_stale_dispatches(
                stale_after_seconds=0, limit=10
            )
            return [(item.job_id, item.document_version_id) for item in requests]
    finally:
        await database.dispose()


async def read_chunk_evidence(settings: Settings, version_id: UUID) -> dict[str, object]:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            chunks = (
                await session.scalars(
                    select(ChunkModel).where(ChunkModel.document_version_id == version_id)
                )
            ).all()
            return {
                "count": len(chunks),
                "source_text": chunks[0].source_text,
                "normalized_text": chunks[0].normalized_text,
            }
    finally:
        await database.dispose()


async def count_citations(settings: Settings, version_id: UUID) -> int:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(CitationModel)
                .join(ChunkModel, ChunkModel.id == CitationModel.chunk_id)
                .where(ChunkModel.document_version_id == version_id)
            )
            return int(value or 0)
    finally:
        await database.dispose()


async def retrieve_as_other_user(
    settings: Settings,
    *,
    owner_id: UUID,
    collection_id: UUID,
) -> int:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            results = await PgVectorRetrievalRepository(session).dense_search(
                owner_id=owner_id,
                collection_id=collection_id,
                query_vector=tuple(0.0 for _ in range(settings.embedding_dimensions)),
                limit=5,
            )
            return len(results)
    finally:
        await database.dispose()
