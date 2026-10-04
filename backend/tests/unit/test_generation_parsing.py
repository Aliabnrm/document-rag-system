from typing import Literal
from uuid import uuid4

import pytest

from app.modules.conversations.application import (
    AnswerDelta,
    CitationSuggestion,
    GenerationCompleted,
)
from app.modules.retrieval.application import Evidence
from app.platform.ai.generation import (
    DeterministicAnswerGenerator,
    _parse_model_answer,
    _safe_stream_end,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "question", "source_text"),
    [
        ("fa", "دفتر چه روزهایی تعطیل است؟", "دفتر در روزهای جمعه و شنبه تعطیل است."),
        ("en", "When is the office closed?", "The office is closed on Friday and Saturday."),
    ],
)
async def test_deterministic_answer_is_direct_and_keeps_source_in_citation_only(
    language: Literal["fa", "en"],
    question: str,
    source_text: str,
) -> None:
    evidence = Evidence(
        evidence_id="E1",
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        document_name="bilingual-office-handbook.txt",
        source_text=source_text,
        page_start=1,
        page_end=1,
        token_count=10,
        fused_score=1.0,
    )

    events = [
        event
        async for event in DeterministicAnswerGenerator().stream(
            question=question,
            language=language,
            evidence=(evidence,),
        )
    ]
    answer = "".join(event.text for event in events if isinstance(event, AnswerDelta))
    citations = [
        event.evidence_id for event in events if isinstance(event, CitationSuggestion)
    ]
    completion = next(event for event in events if isinstance(event, GenerationCompleted))

    assert answer == source_text
    assert evidence.document_name not in answer
    assert citations == ["E1"]
    assert completion.model_metadata["model"] == "extractive-overlap-v2"


def test_parses_inline_backend_validated_citation_footer() -> None:
    answer, citations, abstained = _parse_model_answer(
        "The office is in Tehran. CITATIONS: E1,E3",
        "en",
    )

    assert answer == "The office is in Tehran."
    assert citations == ["E1", "E3"]
    assert abstained is False


def test_parses_insufficient_evidence_without_accepting_a_citation() -> None:
    answer, citations, abstained = _parse_model_answer(
        "INSUFFICIENT_EVIDENCE\nCITATIONS: none",
        "fa",
    )

    assert answer == "پاسخی برای این پرسش در اسناد آماده پیدا نکردم."
    assert citations == []
    assert abstained is True


def test_stream_prefix_holds_control_markers_out_of_visible_text() -> None:
    partial = "The office is in Tehran. CITATIONS: E1"

    safe_end = _safe_stream_end(partial)

    assert partial[:safe_end] == "The office is in Tehran."
    assert _safe_stream_end("A short answer") == 0
