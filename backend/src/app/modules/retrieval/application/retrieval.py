from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
from uuid import UUID

from app.modules.ingestion.application import EmbeddingProvider
from app.modules.ingestion.domain import normalize_for_retrieval


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    chunk_id: UUID
    document_version_id: UUID
    document_name: str
    source_text: str
    page_start: int
    page_end: int
    token_count: int
    score: float


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    candidate: RetrievalCandidate
    fused_score: float
    dense_rank: int | None
    lexical_rank: int | None


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    chunk_id: UUID
    document_version_id: UUID
    document_name: str
    source_text: str
    page_start: int
    page_end: int
    token_count: int
    fused_score: float


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    dense_candidates: int
    lexical_candidates: int
    fused_candidates: int
    packed_evidence: int
    packed_tokens: int
    duration_ms: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    evidence: tuple[Evidence, ...]
    diagnostics: RetrievalDiagnostics


class RetrievalRepository(Protocol):
    async def dense_search(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        query_vector: tuple[float, ...],
        limit: int,
    ) -> tuple[RetrievalCandidate, ...]: ...

    async def lexical_search(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        normalized_query: str,
        limit: int,
    ) -> tuple[RetrievalCandidate, ...]: ...


class HybridRetriever:
    def __init__(
        self,
        *,
        repository: RetrievalRepository,
        embedding_provider: EmbeddingProvider,
        dense_k: int,
        lexical_k: int,
        final_k: int,
        context_token_budget: int,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._dense_k = dense_k
        self._lexical_k = lexical_k
        self._final_k = final_k
        self._context_token_budget = context_token_budget

    async def retrieve(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        query: str,
    ) -> RetrievalResult:
        started = perf_counter()
        normalized_query = normalize_for_retrieval(query)
        if not normalized_query:
            return RetrievalResult(
                evidence=(),
                diagnostics=RetrievalDiagnostics(0, 0, 0, 0, 0, 0.0),
            )
        embedding_batch = await self._embedding_provider.embed((normalized_query,))
        query_vector = embedding_batch.vectors[0]
        dense = await self._repository.dense_search(
            owner_id=owner_id,
            collection_id=collection_id,
            query_vector=query_vector,
            limit=self._dense_k,
        )
        lexical = await self._repository.lexical_search(
            owner_id=owner_id,
            collection_id=collection_id,
            normalized_query=normalized_query,
            limit=self._lexical_k,
        )
        fused = reciprocal_rank_fusion(dense, lexical)[: self._final_k]
        evidence = context_pack(fused, token_budget=self._context_token_budget)
        duration_ms = (perf_counter() - started) * 1000
        return RetrievalResult(
            evidence=evidence,
            diagnostics=RetrievalDiagnostics(
                dense_candidates=len(dense),
                lexical_candidates=len(lexical),
                fused_candidates=len(fused),
                packed_evidence=len(evidence),
                packed_tokens=sum(item.token_count for item in evidence),
                duration_ms=duration_ms,
            ),
        )


def reciprocal_rank_fusion(
    dense: tuple[RetrievalCandidate, ...],
    lexical: tuple[RetrievalCandidate, ...],
    *,
    rank_constant: int = 60,
) -> tuple[FusedCandidate, ...]:
    by_id: dict[UUID, RetrievalCandidate] = {}
    scores: dict[UUID, float] = {}
    dense_ranks: dict[UUID, int] = {}
    lexical_ranks: dict[UUID, int] = {}
    for rank, candidate in enumerate(dense, start=1):
        by_id.setdefault(candidate.chunk_id, candidate)
        dense_ranks.setdefault(candidate.chunk_id, rank)
        scores[candidate.chunk_id] = scores.get(candidate.chunk_id, 0.0) + 1.0 / (
            rank_constant + rank
        )
    for rank, candidate in enumerate(lexical, start=1):
        by_id.setdefault(candidate.chunk_id, candidate)
        lexical_ranks.setdefault(candidate.chunk_id, rank)
        scores[candidate.chunk_id] = scores.get(candidate.chunk_id, 0.0) + 1.0 / (
            rank_constant + rank
        )
    items = [
        FusedCandidate(
            candidate=candidate,
            fused_score=scores[chunk_id],
            dense_rank=dense_ranks.get(chunk_id),
            lexical_rank=lexical_ranks.get(chunk_id),
        )
        for chunk_id, candidate in by_id.items()
    ]
    items.sort(key=lambda item: (-item.fused_score, str(item.candidate.chunk_id)))
    return tuple(items)


def context_pack(
    candidates: tuple[FusedCandidate, ...],
    *,
    token_budget: int,
) -> tuple[Evidence, ...]:
    packed: list[Evidence] = []
    used_tokens = 0
    for item in candidates:
        candidate = item.candidate
        if used_tokens + candidate.token_count > token_budget:
            continue
        evidence_id = f"E{len(packed) + 1}"
        packed.append(
            Evidence(
                evidence_id=evidence_id,
                chunk_id=candidate.chunk_id,
                document_version_id=candidate.document_version_id,
                document_name=candidate.document_name,
                source_text=candidate.source_text,
                page_start=candidate.page_start,
                page_end=candidate.page_end,
                token_count=candidate.token_count,
                fused_score=item.fused_score,
            )
        )
        used_tokens += candidate.token_count
    return tuple(packed)
