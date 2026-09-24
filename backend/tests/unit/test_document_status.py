import pytest

from app.modules.documents.domain import (
    DocumentVersionState,
    DocumentVersionStatus,
    InvalidDocumentTransitionError,
)


def test_document_version_follows_ingestion_lifecycle() -> None:
    state = DocumentVersionState(DocumentVersionStatus.UPLOADED)

    for target in (
        DocumentVersionStatus.QUEUED,
        DocumentVersionStatus.EXTRACTING,
        DocumentVersionStatus.CHUNKING,
        DocumentVersionStatus.EMBEDDING,
        DocumentVersionStatus.READY,
    ):
        state = state.transition_to(target)

    assert state.status is DocumentVersionStatus.READY


def test_ready_document_version_is_immutable() -> None:
    state = DocumentVersionState(DocumentVersionStatus.READY)

    with pytest.raises(InvalidDocumentTransitionError):
        state.transition_to(DocumentVersionStatus.QUEUED)


def test_failed_document_version_can_be_requeued() -> None:
    state = DocumentVersionState(DocumentVersionStatus.FAILED)

    assert state.transition_to(DocumentVersionStatus.QUEUED).status is DocumentVersionStatus.QUEUED
