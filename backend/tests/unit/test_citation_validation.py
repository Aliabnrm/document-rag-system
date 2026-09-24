from uuid import UUID

from app.modules.conversations.application import validate_citation_ids
from app.modules.retrieval.application import Evidence


def evidence(identifier: str, value: int) -> Evidence:
    return Evidence(
        evidence_id=identifier,
        chunk_id=UUID(int=value),
        document_version_id=UUID(int=value + 100),
        document_name="source.txt",
        source_text="source",
        page_start=1,
        page_end=1,
        token_count=1,
        fused_score=1.0,
    )


def test_citation_validation_accepts_only_backend_issued_identifiers() -> None:
    allowed = (evidence("E1", 1), evidence("E2", 2))

    valid, invalid = validate_citation_ids(["E2", "E999", "E2"], allowed)

    assert [item.evidence_id for item in valid] == ["E2"]
    assert invalid == ("E999",)
