from dataclasses import dataclass
from enum import StrEnum


class DocumentVersionStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


ALLOWED_DOCUMENT_TRANSITIONS: dict[DocumentVersionStatus, frozenset[DocumentVersionStatus]] = {
    DocumentVersionStatus.UPLOADED: frozenset(
        {DocumentVersionStatus.QUEUED, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.QUEUED: frozenset(
        {DocumentVersionStatus.EXTRACTING, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.EXTRACTING: frozenset(
        {DocumentVersionStatus.CHUNKING, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.CHUNKING: frozenset(
        {DocumentVersionStatus.EMBEDDING, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.EMBEDDING: frozenset(
        {DocumentVersionStatus.READY, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.READY: frozenset(),
    DocumentVersionStatus.FAILED: frozenset({DocumentVersionStatus.QUEUED}),
}


class InvalidDocumentTransitionError(ValueError):
    def __init__(self, current: DocumentVersionStatus, target: DocumentVersionStatus) -> None:
        super().__init__(f"Cannot transition document version from {current} to {target}")
        self.current = current
        self.target = target


@dataclass(frozen=True, slots=True)
class DocumentVersionState:
    status: DocumentVersionStatus

    def transition_to(self, target: DocumentVersionStatus) -> "DocumentVersionState":
        if target not in ALLOWED_DOCUMENT_TRANSITIONS[self.status]:
            raise InvalidDocumentTransitionError(self.status, target)
        return DocumentVersionState(status=target)
