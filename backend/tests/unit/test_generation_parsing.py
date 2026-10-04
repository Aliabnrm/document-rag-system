from app.platform.ai.generation import _parse_model_answer, _safe_stream_end


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

    assert answer == "در اسناد آماده، شواهد کافی برای پاسخ پیدا نکردم."
    assert citations == []
    assert abstained is True


def test_stream_prefix_holds_control_markers_out_of_visible_text() -> None:
    partial = "The office is in Tehran. CITATIONS: E1"

    safe_end = _safe_stream_end(partial)

    assert partial[:safe_end] == "The office is in Tehran."
    assert _safe_stream_end("A short answer") == 0
