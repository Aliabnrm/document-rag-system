import hashlib
import re
from dataclasses import dataclass

from app.modules.ingestion.domain.normalization import normalize_for_retrieval

CHUNKER_VERSION = "boundary-token-v1"
_TOKEN = re.compile(r"\w+(?:\u200c\w+)*|[^\w\s]", flags=re.UNICODE)


@dataclass(frozen=True, slots=True)
class SourcePage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class TextChunk:
    ordinal: int
    source_text: str
    normalized_text: str
    page_start: int
    page_end: int
    source_start: int
    source_end: int
    token_count: int
    content_hash: str


@dataclass(frozen=True, slots=True)
class _PageRange:
    page_number: int
    start: int
    end: int


def count_tokens(value: str) -> int:
    return sum(1 for _ in _TOKEN.finditer(value))


def chunk_pages(
    pages: tuple[SourcePage, ...],
    *,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> tuple[TextChunk, ...]:
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= chunk_size_tokens:
        raise ValueError("overlap_tokens must be non-negative and smaller than chunk size")

    source, page_ranges = _join_pages(pages)
    tokens = list(_TOKEN.finditer(source))
    if not tokens:
        return ()

    chunks: list[TextChunk] = []
    token_start = 0
    while token_start < len(tokens):
        hard_end = min(token_start + chunk_size_tokens, len(tokens))
        token_end = _preferred_boundary(source, tokens, token_start, hard_end, page_ranges)
        start_offset = tokens[token_start].start()
        end_offset = tokens[token_end - 1].end()
        source_text = source[start_offset:end_offset]
        page_start, page_end = _page_span(start_offset, end_offset, page_ranges)
        normalized_text = normalize_for_retrieval(source_text)
        content_hash = hashlib.sha256(
            f"{page_start}:{page_end}:{normalized_text}".encode()
        ).hexdigest()
        chunks.append(
            TextChunk(
                ordinal=len(chunks),
                source_text=source_text,
                normalized_text=normalized_text,
                page_start=page_start,
                page_end=page_end,
                source_start=start_offset,
                source_end=end_offset,
                token_count=token_end - token_start,
                content_hash=content_hash,
            )
        )
        if token_end == len(tokens):
            break
        token_start = max(token_start + 1, token_end - overlap_tokens)

    return tuple(chunks)


def _join_pages(pages: tuple[SourcePage, ...]) -> tuple[str, tuple[_PageRange, ...]]:
    pieces: list[str] = []
    ranges: list[_PageRange] = []
    position = 0
    for index, page in enumerate(pages):
        if index:
            separator = "\n\n"
            pieces.append(separator)
            position += len(separator)
        start = position
        pieces.append(page.text)
        position += len(page.text)
        ranges.append(_PageRange(page_number=page.page_number, start=start, end=position))
    return "".join(pieces), tuple(ranges)


def _preferred_boundary(
    source: str,
    tokens: list[re.Match[str]],
    token_start: int,
    hard_end: int,
    page_ranges: tuple[_PageRange, ...],
) -> int:
    if hard_end == len(tokens):
        return hard_end
    minimum = token_start + max(1, (hard_end - token_start) // 2)
    page_ends = {page.end for page in page_ranges}
    for candidate in range(hard_end, minimum - 1, -1):
        end_offset = tokens[candidate - 1].end()
        gap_end = tokens[candidate].start() if candidate < len(tokens) else len(source)
        gap = source[end_offset:gap_end]
        if end_offset in page_ends or "\n\n" in gap:
            return candidate
    return hard_end


def _page_span(
    start: int,
    end: int,
    page_ranges: tuple[_PageRange, ...],
) -> tuple[int, int]:
    touched = [page.page_number for page in page_ranges if page.end > start and page.start < end]
    if not touched:
        raise ValueError("Chunk does not overlap a source page")
    return min(touched), max(touched)
