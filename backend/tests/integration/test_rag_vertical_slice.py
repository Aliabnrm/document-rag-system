import asyncio
import socket
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.settings import Settings
from app.entrypoints.api import create_app
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


def test_create_upload_ingest_ask_and_validate_citation() -> None:
    owner_id = uuid4()
    settings = Settings(development_user_id=owner_id)
    application = create_app(settings)
    dispatcher = RecordingDispatcher()
    source = "راهنمای شركت آوا\n\nمدیر عامل شرکت آوا، لیلا نوری است. تاریخ تأسیس ۱۴۰۲ است."

    with TestClient(application) as client:
        application.state.job_dispatcher = dispatcher
        readiness_response = client.get("/api/v1/ready")
        assert readiness_response.status_code == 200
        assert readiness_response.json() == {
            "status": "ready",
            "database": "available",
            "queue": "available",
            "object_storage": "available",
        }
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

    citation_count = asyncio.run(count_citations(settings, version_id))
    assert citation_count == 1
    unauthorized_results = asyncio.run(
        retrieve_as_other_user(settings, owner_id=uuid4(), collection_id=collection_id)
    )
    assert unauthorized_results == 0

    other_user_app = create_app(Settings(development_user_id=uuid4()))
    with TestClient(other_user_app) as other_client:
        response = other_client.get(f"/api/v1/collections/{collection_id}/documents/{document_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "document_not_found"


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
            requests = await SqlAlchemyDispatchRecoveryRepository(
                session
            ).claim_stale_dispatches(stale_after_seconds=0, limit=10)
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
