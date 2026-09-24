from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.documents.domain.status import DocumentVersionStatus
from app.modules.ingestion.domain import IngestionJobStatus


@dataclass(frozen=True, slots=True)
class PendingDocumentUpload:
    document_id: UUID
    document_version_id: UUID
    job_id: UUID
    collection_id: UUID
    display_name: str
    version_number: int
    status: DocumentVersionStatus
    job_status: IngestionJobStatus
    stage: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    document_version_id: UUID
    display_name: str
    media_type: str
    size_bytes: int
    version_number: int
    status: DocumentVersionStatus
    job_id: UUID
    job_status: IngestionJobStatus
    stage: str
    attempt_count: int
    error_code: str | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime
