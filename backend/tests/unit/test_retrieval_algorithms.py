from uuid import UUID

from app.modules.retrieval.application import (
    RetrievalCandidate,
    context_pack,
    reciprocal_rank_fusion,
)


def candidate(value: int, *, tokens: int = 10) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=UUID(int=value),
        document_version_id=UUID(int=100 + value),
        document_name=f"document-{value}",
        source_text=f"evidence {value}",
        page_start=1,
        page_end=1,
        token_count=tokens,
        score=1.0,
    )


def test_rrf_deduplicates_and_rewards_candidates_in_both_rankings() -> None:
    shared = candidate(2)

    fused = reciprocal_rank_fusion(
        (candidate(1), shared),
        (shared, candidate(3)),
    )

    assert [item.candidate.chunk_id for item in fused] == [
        shared.chunk_id,
        UUID(int=1),
        UUID(int=3),
    ]
    assert fused[0].dense_rank == 2
    assert fused[0].lexical_rank == 1


def test_context_packing_obeys_budget_and_issues_backend_evidence_ids() -> None:
    fused = reciprocal_rank_fusion((candidate(1, tokens=8), candidate(2, tokens=7)), ())

    packed = context_pack(fused, token_budget=10)

    assert len(packed) == 1
    assert packed[0].evidence_id == "E1"
    assert packed[0].token_count <= 10
