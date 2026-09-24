from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.documents.domain import DocumentSummary, PendingDocumentUpload


class UploadAcceptedResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    job_id: UUID
    collection_id: UUID
    display_name: str
    version_number: int
    status: str
    job_status: str
    stage: str
    created_at: datetime

    @classmethod
    def from_domain(cls, item: PendingDocumentUpload) -> "UploadAcceptedResponse":
        return cls.model_validate(item, from_attributes=True)


class DocumentResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    display_name: str
    media_type: str
    size_bytes: int
    version_number: int
    status: str
    job_id: UUID
    job_status: str
    stage: str
    attempt_count: int
    error_code: str | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: DocumentSummary) -> "DocumentResponse":
        return cls.model_validate(item, from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    next_cursor: str | None
