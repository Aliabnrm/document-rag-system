from app.modules.ingestion.domain import SourcePage, chunk_pages


def test_chunking_is_deterministic_and_preserves_page_metadata() -> None:
    pages = (
        SourcePage(1, "one two three four five six\n\nseven eight nine ten"),
        SourcePage(2, "eleven twelve thirteen fourteen fifteen sixteen"),
    )

    first = chunk_pages(pages, chunk_size_tokens=8, overlap_tokens=2)
    second = chunk_pages(pages, chunk_size_tokens=8, overlap_tokens=2)

    assert first == second
    assert [chunk.ordinal for chunk in first] == list(range(len(first)))
    assert all(chunk.token_count <= 8 for chunk in first)
    assert first[0].page_start == 1
    assert first[-1].page_end == 2
    assert len({chunk.content_hash for chunk in first}) == len(first)


def test_chunk_overlap_repeats_exact_tokens_without_duplicate_artifacts() -> None:
    pages = (SourcePage(1, "one two three four five six seven eight nine ten eleven"),)

    chunks = chunk_pages(pages, chunk_size_tokens=6, overlap_tokens=2)

    assert chunks[0].source_text.split()[-2:] == chunks[1].source_text.split()[:2]
    assert chunks[0].source_start < chunks[1].source_start
    assert chunks[0].ordinal != chunks[1].ordinal
