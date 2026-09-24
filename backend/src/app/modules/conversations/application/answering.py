import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, Protocol
from uuid import UUID

from app.modules.retrieval.application import Evidence, HybridRetriever, RetrievalDiagnostics
from app.platform.observability import bind_observation, log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnswerDelta:
    text: str


@dataclass(frozen=True, slots=True)
class CitationSuggestion:
    evidence_id: str


@dataclass(frozen=True, slots=True)
class GenerationCompleted:
    abstained: bool
    model_metadata: dict[str, object]
    input_tokens: int | None = None
    output_tokens: int | None = None


GeneratorEvent = AnswerDelta | CitationSuggestion | GenerationCompleted


class AnswerGenerator(Protocol):
    def stream(
        self,
        *,
        question: str,
        language: Literal["fa", "en"],
        evidence: tuple[Evidence, ...],
    ) -> AsyncIterator[GeneratorEvent]: ...


@dataclass(frozen=True, slots=True)
class RunHandle:
    rag_run_id: UUID
    conversation_id: UUID
    collection_id: UUID
    user_message_id: UUID


class AnswerRepository(Protocol):
    async def begin_run(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        question: str,
        language: str,
    ) -> RunHandle: ...

    async def mark_generating(
        self,
        *,
        run: RunHandle,
        diagnostics: RetrievalDiagnostics,
    ) -> None: ...

    async def complete(
        self,
        *,
        run: RunHandle,
        answer: str,
        language: str,
        citations: tuple[Evidence, ...],
        generation: GenerationCompleted,
        timing_metadata: dict[str, object],
    ) -> UUID: ...

    async def fail(self, *, run: RunHandle, code: str, cancelled: bool = False) -> None: ...


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event: str
    data: dict[str, object]


class AnswerQuestion:
    def __init__(
        self,
        *,
        repository: AnswerRepository,
        retriever: HybridRetriever,
        generator: AnswerGenerator,
        prompt_version: str = "grounded-answer-v1",
    ) -> None:
        self._repository = repository
        self._retriever = retriever
        self._generator = generator
        self._prompt_version = prompt_version

    async def stream(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        question: str,
        language: Literal["fa", "en"],
    ) -> AsyncIterator[StreamEvent]:
        started = perf_counter()
        run = await self._repository.begin_run(
            owner_id=owner_id,
            conversation_id=conversation_id,
            question=question,
            language=language,
        )
        bind_observation(
            collection_id=run.collection_id,
            conversation_id=run.conversation_id,
            rag_run_id=run.rag_run_id,
        )
        first_delta_at: float | None = None
        try:
            yield StreamEvent(
                event="retrieval_started",
                data={"rag_run_id": str(run.rag_run_id)},
            )
            retrieval = await self._retriever.retrieve(
                owner_id=owner_id,
                collection_id=run.collection_id,
                query=question,
            )
            await self._repository.mark_generating(run=run, diagnostics=retrieval.diagnostics)
            log_event(
                logger,
                "retrieval_completed",
                duration_ms=round(retrieval.diagnostics.duration_ms, 3),
                dense_candidates=retrieval.diagnostics.dense_candidates,
                lexical_candidates=retrieval.diagnostics.lexical_candidates,
                fused_candidates=retrieval.diagnostics.fused_candidates,
                packed_evidence=retrieval.diagnostics.packed_evidence,
                packed_tokens=retrieval.diagnostics.packed_tokens,
            )
            yield StreamEvent(
                event="retrieval_completed",
                data={"evidence_count": len(retrieval.evidence)},
            )

            if not retrieval.evidence:
                async for event in self._persist_abstention(
                    run=run,
                    language=language,
                    started=started,
                    reason="no_evidence",
                ):
                    yield event
                return

            answer_parts: list[str] = []
            suggested_ids: list[str] = []
            completion: GenerationCompleted | None = None
            async for generated in self._generator.stream(
                question=question,
                language=language,
                evidence=retrieval.evidence,
            ):
                if isinstance(generated, AnswerDelta):
                    if first_delta_at is None:
                        first_delta_at = perf_counter()
                    answer_parts.append(generated.text)
                    yield StreamEvent(event="answer_delta", data={"text": generated.text})
                elif isinstance(generated, CitationSuggestion):
                    suggested_ids.append(generated.evidence_id)
                else:
                    completion = generated

            answer = "".join(answer_parts).strip()
            completion = completion or GenerationCompleted(
                abstained=True,
                model_metadata={"provider": "unknown", "prompt_version": self._prompt_version},
            )
            valid_evidence, invalid_ids = validate_citation_ids(
                suggested_ids,
                retrieval.evidence,
            )
            if invalid_ids or (not completion.abstained and not valid_evidence):
                await self._repository.fail(run=run, code="invalid_model_citations")
                yield StreamEvent(
                    event="failure",
                    data={
                        "code": "invalid_model_citations",
                        "message_key": "errors.invalid_model_citations",
                    },
                )
                return

            timing = _timing(started, first_delta_at)
            answer_message_id = await self._repository.complete(
                run=run,
                answer=answer,
                language=language,
                citations=valid_evidence,
                generation=completion,
                timing_metadata=timing,
            )
            log_event(
                logger,
                "answer_completed",
                duration_ms=timing["total_duration_ms"],
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                packed_evidence=len(valid_evidence),
                abstained=completion.abstained,
            )
            if valid_evidence:
                yield StreamEvent(
                    event="citations",
                    data={
                        "items": [
                            {
                                "evidence_id": item.evidence_id,
                                "document_name": item.document_name,
                                "page_start": item.page_start,
                                "page_end": item.page_end,
                                "snippet": item.source_text,
                            }
                            for item in valid_evidence
                        ]
                    },
                )
            yield StreamEvent(
                event="completed",
                data={
                    "rag_run_id": str(run.rag_run_id),
                    "answer_message_id": str(answer_message_id),
                    "abstained": completion.abstained,
                    **timing,
                },
            )
        except asyncio.CancelledError:
            await self._repository.fail(run=run, code="client_disconnected", cancelled=True)
            log_event(
                logger,
                "answer_cancelled",
                level=logging.INFO,
                error_code="client_disconnected",
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )
            raise
        except Exception as error:
            await self._repository.fail(run=run, code="answer_pipeline_failed")
            log_event(
                logger,
                "answer_failed",
                level=logging.ERROR,
                error_code="answer_pipeline_failed",
                error_type=type(error).__name__,
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )
            yield StreamEvent(
                event="failure",
                data={
                    "code": "answer_pipeline_failed",
                    "message_key": "errors.answer_pipeline_failed",
                },
            )

    async def _persist_abstention(
        self,
        *,
        run: RunHandle,
        language: Literal["fa", "en"],
        started: float,
        reason: str,
    ) -> AsyncIterator[StreamEvent]:
        answer = (
            "در اسناد آماده، شواهد کافی برای پاسخ به این پرسش پیدا نکردم."
            if language == "fa"
            else "I could not find enough evidence in the ready documents to answer this question."
        )
        yield StreamEvent(event="answer_delta", data={"text": answer})
        completion = GenerationCompleted(
            abstained=True,
            model_metadata={
                "provider": "backend-abstention",
                "reason": reason,
                "prompt_version": self._prompt_version,
            },
        )
        timing = _timing(started, perf_counter())
        answer_message_id = await self._repository.complete(
            run=run,
            answer=answer,
            language=language,
            citations=(),
            generation=completion,
            timing_metadata=timing,
        )
        yield StreamEvent(
            event="completed",
            data={
                "rag_run_id": str(run.rag_run_id),
                "answer_message_id": str(answer_message_id),
                "abstained": True,
                **timing,
            },
        )


def validate_citation_ids(
    suggested_ids: list[str],
    evidence: tuple[Evidence, ...],
) -> tuple[tuple[Evidence, ...], tuple[str, ...]]:
    allowed = {item.evidence_id: item for item in evidence}
    valid: list[Evidence] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for evidence_id in suggested_ids:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        selected = allowed.get(evidence_id)
        if selected is None:
            invalid.append(evidence_id)
        else:
            valid.append(selected)
    return tuple(valid), tuple(invalid)


def _timing(started: float, first_delta_at: float | None) -> dict[str, object]:
    completed = perf_counter()
    return {
        "time_to_first_token_ms": (
            round((first_delta_at - started) * 1000, 3) if first_delta_at is not None else None
        ),
        "total_duration_ms": round((completed - started) * 1000, 3),
    }
