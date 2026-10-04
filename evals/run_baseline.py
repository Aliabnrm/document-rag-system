from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from app.core.settings import Settings
from app.modules.conversations.application import (
    AnswerDelta,
    CitationSuggestion,
    GenerationCompleted,
    validate_citation_ids,
)
from app.modules.ingestion.domain import SourcePage, chunk_pages, normalize_for_retrieval
from app.modules.ingestion.infrastructure.extraction import PdfTxtExtractor
from app.modules.retrieval.application import (
    Evidence,
    RetrievalCandidate,
    context_pack,
    reciprocal_rank_fusion,
)
from app.platform.ai import create_answer_generator, create_embedding_provider

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    category: str
    language: Literal["fa", "en"]
    question: str
    document: str | None
    answerable: bool
    expected_evidence: list[str]
    expected_answer_terms: list[str]
    expected_pages: list[int] | None = None


@dataclass(frozen=True, slots=True)
class EvalChunk:
    id: UUID
    document: str
    source_text: str
    normalized_text: str
    token_count: int
    page_start: int
    page_end: int


async def main() -> None:
    arguments = parse_arguments()
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    questions, dataset_names = load_questions(arguments.dataset)
    chunks = load_chunks(config)
    settings = Settings(
        embedding_provider=arguments.embedding_provider,
        embedding_model=arguments.embedding_model,
        embedding_source_repo=arguments.embedding_source_repo,
        embedding_revision=arguments.embedding_revision,
        embedding_dimensions=arguments.embedding_dimensions,
        answer_provider=arguments.answer_provider,
        answer_model=arguments.answer_model,
        ollama_base_url=arguments.ollama_base_url,
        request_timeout_seconds=arguments.request_timeout_seconds,
    )
    embedder = create_embedding_provider(settings)
    generator = create_answer_generator(settings)

    embedding_started = perf_counter()
    document_batch = await embedder.embed(tuple(item.normalized_text for item in chunks))
    embedding_seconds = perf_counter() - embedding_started
    results: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for question in questions:
        query_batch = await embedder.embed((normalize_for_retrieval(question.question),))
        evidence, retrieval_metrics = retrieve(
            question=question,
            chunks=chunks,
            document_vectors=document_batch.vectors,
            query_vector=query_batch.vectors[0],
            config=config,
        )
        generation_metrics, review = await evaluate_generation(
            question=question,
            evidence=evidence,
            generator=generator,
        )
        results.append(
            {
                "id": question.id,
                "category": question.category,
                "language": question.language,
                **retrieval_metrics,
                **generation_metrics,
            }
        )
        reviews.append(review)

    report = {
        "report_type": "measured_baseline",
        "measured_at": datetime.now(UTC).isoformat(),
        "dataset": arguments.dataset.name,
        "dataset_sources": dataset_names,
        "dataset_size": len(questions),
        "config": config,
        "providers": {
            "embedding": {
                "provider": arguments.embedding_provider,
                "model": document_batch.model_id,
                "revision": document_batch.revision,
                "dimensions": document_batch.dimensions,
                "maximum_input_tokens": document_batch.maximum_input_tokens,
                "runtime": document_batch.runtime,
                "throughput_chunks_per_second": round(len(chunks) / embedding_seconds, 3),
                "fixture_chunks": len(chunks),
            },
            "answer": {
                "provider": arguments.answer_provider,
                "model": arguments.answer_model,
                "runtime": await answer_runtime_context(settings),
            },
        },
        "hardware": hardware_context(),
        "summary": summarize(results),
        "by_category": summarize_by_category(results),
        "results": results,
        "notes": [
            "Lexical scores in this portable runner use normalized token overlap; "
            "production uses PostgreSQL full-text search.",
            "Groundedness is an automated citation-support proxy, not a human judge score.",
            "No release threshold is inferred from this first baseline.",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if arguments.review_output is not None:
        write_review_packet(arguments.review_output, reviews)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {arguments.output}")
    if arguments.review_output is not None:
        print(f"Human review packet: {arguments.review_output}")


def retrieve(
    *,
    question: Question,
    chunks: list[EvalChunk],
    document_vectors: tuple[tuple[float, ...], ...],
    query_vector: tuple[float, ...],
    config: dict[str, Any],
) -> tuple[tuple[Evidence, ...], dict[str, Any]]:
    dense = sorted(
        (
            to_candidate(chunk, cosine_similarity(query_vector, vector))
            for chunk, vector in zip(chunks, document_vectors, strict=True)
        ),
        key=lambda item: (-item.score, str(item.chunk_id)),
    )[: int(config["dense_k"])]
    query_tokens = set(normalize_for_retrieval(question.question).casefold().split())
    lexical = sorted(
        (
            to_candidate(
                chunk,
                len(query_tokens & set(chunk.normalized_text.casefold().split()))
                / max(1, len(query_tokens)),
            )
            for chunk in chunks
        ),
        key=lambda item: (-item.score, str(item.chunk_id)),
    )
    lexical = [item for item in lexical if item.score > 0][: int(config["lexical_k"])]
    fused = reciprocal_rank_fusion(tuple(dense), tuple(lexical))[: int(config["final_k"])]
    evidence = context_pack(
        fused,
        token_budget=int(config["context_token_budget"]),
    )
    expected_terms = [
        normalize_for_retrieval(item).casefold() for item in question.expected_evidence
    ]
    retrieved_texts = [normalize_for_retrieval(item.source_text).casefold() for item in evidence]
    all_support_retrieved = bool(expected_terms) and all(
        any(term in source for source in retrieved_texts) for term in expected_terms
    )
    first_relevant_rank = next(
        (
            index
            for index, item in enumerate(evidence, start=1)
            if any(
                term in normalize_for_retrieval(item.source_text).casefold()
                for term in expected_terms
            )
        ),
        None,
    )
    metrics = {
        "retrieval_recall_at_k": int(all_support_retrieved) if question.answerable else None,
        "reciprocal_rank": (
            round(1 / first_relevant_rank, 6)
            if question.answerable and first_relevant_rank is not None
            else 0.0
            if question.answerable
            else None
        ),
        "retrieved_evidence_ids": [item.evidence_id for item in evidence],
        "retrieved_documents": sorted({item.document_name for item in evidence}),
        "retrieved_pages": sorted(
            {
                page
                for item in evidence
                for page in range(item.page_start, item.page_end + 1)
            }
        ),
        "expected_page_retrieval": (
            int(
                all(
                    any(
                        item.document_name == question.document
                        and item.page_start <= page <= item.page_end
                        for item in evidence
                    )
                    for page in question.expected_pages
                )
            )
            if question.answerable and question.expected_pages
            else None
        ),
    }
    return evidence, metrics


async def evaluate_generation(
    *,
    question: Question,
    evidence: tuple[Evidence, ...],
    generator: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = perf_counter()
    first_delta: float | None = None
    answer_parts: list[str] = []
    suggestions: list[str] = []
    completion: GenerationCompleted | None = None
    provider_failure: str | None = None
    try:
        async for event in generator.stream(
            question=question.question,
            language=question.language,
            evidence=evidence,
        ):
            if isinstance(event, AnswerDelta):
                first_delta = first_delta or perf_counter()
                answer_parts.append(event.text)
            elif isinstance(event, CitationSuggestion):
                suggestions.append(event.evidence_id)
            else:
                completion = event
    except (httpx.HTTPError, TimeoutError, OSError) as error:
        provider_failure = type(error).__name__
    completed = perf_counter()
    answer = "".join(answer_parts)
    valid, invalid = validate_citation_ids(suggestions, evidence)
    cited_text = "\n".join(item.source_text for item in valid)
    expected_evidence = [
        normalize_for_retrieval(item).casefold() for item in question.expected_evidence
    ]
    expected_answers = [
        normalize_for_retrieval(item).casefold() for item in question.expected_answer_terms
    ]
    citation_support = (
        all(term in normalize_for_retrieval(cited_text).casefold() for term in expected_evidence)
        if question.answerable
        else len(valid) == 0
    ) if provider_failure is None else None
    answer_relevance = (
        all(term in normalize_for_retrieval(answer).casefold() for term in expected_answers)
        if question.answerable
        else bool(completion and completion.abstained)
    ) if provider_failure is None else None
    abstention_correct = (
        bool(completion) and completion.abstained != question.answerable
        if provider_failure is None
        else None
    )
    metrics = {
        "generation_succeeded": provider_failure is None,
        "provider_failure": provider_failure,
        "citation_identifier_valid": len(invalid) == 0 if provider_failure is None else None,
        "citation_support": citation_support,
        "groundedness_proxy": (
            len(invalid) == 0 and bool(citation_support)
            if provider_failure is None
            else None
        ),
        "answer_relevance": answer_relevance,
        "abstention_correct": abstention_correct,
        "abstained": bool(completion and completion.abstained),
        "generation_metadata": completion.model_metadata if completion else {},
        "input_tokens": completion.input_tokens if completion else None,
        "output_tokens": completion.output_tokens if completion else None,
        "time_to_first_token_ms": (
            round((first_delta - started) * 1000, 3) if first_delta is not None else None
        ),
        "total_latency_ms": round((completed - started) * 1000, 3),
    }
    review = {
        "question_id": question.id,
        "question": question.question,
        "language": question.language,
        "answerable": question.answerable,
        "answer": answer,
        "abstained": metrics["abstained"],
        "citations": [
            {
                "evidence_id": item.evidence_id,
                "document": item.document_name,
                "page_start": item.page_start,
                "page_end": item.page_end,
                "source_text": item.source_text,
            }
            for item in valid
        ],
        "human_scores": {
            "groundedness": None,
            "citation_support": None,
            "relevance": None,
            "language_quality": None,
            "abstention_correct": None,
            "reviewer_notes": "",
        },
        "provider_failure": provider_failure,
    }
    return metrics, review


def load_questions(path: Path) -> tuple[list[Question], list[str]]:
    paths = [path]
    if path.suffix == ".json":
        manifest = json.loads(path.read_text(encoding="utf-8"))
        paths = [path.parent / item for item in manifest["datasets"]]
    questions = [
        Question(**json.loads(line))
        for dataset_path in paths
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    identifiers = [item.id for item in questions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Evaluation question identifiers must be unique")
    return questions, [item.name for item in paths]


def load_chunks(config: dict[str, Any]) -> list[EvalChunk]:
    chunks: list[EvalChunk] = []
    extractor = PdfTxtExtractor()
    for document_config in config["documents"]:
        if isinstance(document_config, str):
            document_name = document_config
            expected_sha256 = None
        else:
            document_name = document_config["name"]
            expected_sha256 = document_config.get("sha256")
        source_path = ROOT / "fixtures" / document_name
        source_bytes = source_path.read_bytes()
        actual_sha256 = hashlib.sha256(source_bytes).hexdigest()
        if expected_sha256 is not None and actual_sha256 != expected_sha256:
            raise ValueError(
                f"Fixture checksum drift for {document_name}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
        if source_path.suffix.casefold() == ".pdf":
            with source_path.open("rb") as source:
                extraction = extractor.extract(source=source, media_type="application/pdf")
            pages = extraction.pages
        else:
            pages = (SourcePage(page_number=1, text=source_bytes.decode("utf-8")),)
        for chunk in chunk_pages(
            pages,
            chunk_size_tokens=int(config["chunk_size_tokens"]),
            overlap_tokens=int(config["chunk_overlap_tokens"]),
        ):
            chunks.append(
                EvalChunk(
                    id=uuid5(NAMESPACE_URL, f"{document_name}:{chunk.ordinal}"),
                    document=document_name,
                    source_text=chunk.source_text,
                    normalized_text=chunk.normalized_text,
                    token_count=chunk.token_count,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                )
            )
    return chunks


def write_review_packet(path: Path, reviews: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in reviews),
        encoding="utf-8",
    )


def to_candidate(chunk: EvalChunk, score: float) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk.id,
        document_version_id=uuid5(NAMESPACE_URL, chunk.document),
        document_name=chunk.document,
        source_text=chunk.source_text,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        token_count=chunk.token_count,
        score=score,
    )


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [item for item in results if item["retrieval_recall_at_k"] is not None]
    return {
        "retrieval_recall_at_k": average(answerable, "retrieval_recall_at_k"),
        "mrr": average(answerable, "reciprocal_rank"),
        "expected_page_retrieval": average(answerable, "expected_page_retrieval"),
        "generation_success_rate": average(results, "generation_succeeded"),
        "provider_failure_count": sum(not item["generation_succeeded"] for item in results),
        "citation_identifier_validity": average(results, "citation_identifier_valid"),
        "citation_support": average(results, "citation_support"),
        "groundedness_proxy": average(results, "groundedness_proxy"),
        "answer_relevance": average(results, "answer_relevance"),
        "abstention_accuracy": average(results, "abstention_correct"),
        "median_time_to_first_token_ms": median(results, "time_to_first_token_ms"),
        "median_total_latency_ms": median(results, "total_latency_ms"),
    }


def summarize_by_category(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result["category"])].append(result)
    return {category: summarize(items) for category, items in sorted(grouped.items())}


def average(items: list[dict[str, Any]], key: str) -> float | None:
    values = [float(item[key]) for item in items if item.get(key) is not None]
    return round(sum(values) / len(values), 6) if values else None


def median(items: list[dict[str, Any]], key: str) -> float | None:
    values = sorted(float(item[key]) for item in items if item.get(key) is not None)
    if not values:
        return None
    middle = len(values) // 2
    value = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return round(value, 3)


def hardware_context() -> dict[str, Any]:
    memory_bytes: int | None = None
    with suppress(ValueError, OSError, AttributeError):
        memory_bytes = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_gib": round(memory_bytes / (1024**3), 2) if memory_bytes else None,
        "python": platform.python_version(),
        "fastembed": installed_version("fastembed"),
        "onnxruntime": installed_version("onnxruntime"),
    }


async def answer_runtime_context(settings: Settings) -> dict[str, Any]:
    if settings.answer_provider != "ollama":
        return {"kind": "in-process-deterministic"}
    base_url = settings.ollama_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=10) as client:
        version_response, tags_response, processes_response = await asyncio.gather(
            client.get(f"{base_url}/api/version"),
            client.get(f"{base_url}/api/tags"),
            client.get(f"{base_url}/api/ps"),
        )
    version_response.raise_for_status()
    tags_response.raise_for_status()
    processes_response.raise_for_status()
    tags = tags_response.json().get("models", [])
    selected = next(
        (
            item
            for item in tags
            if item.get("name") == settings.answer_model
            or item.get("model") == settings.answer_model
        ),
        None,
    )
    processes = processes_response.json().get("models", [])
    loaded = next(
        (
            item
            for item in processes
            if item.get("name") == settings.answer_model
            or item.get("model") == settings.answer_model
        ),
        None,
    )
    return {
        "version": version_response.json().get("version"),
        "digest": selected.get("digest") if selected else None,
        "size_bytes": selected.get("size") if selected else None,
        "details": selected.get("details") if selected else None,
        "loaded_size_vram_bytes": loaded.get("size_vram") if loaded else None,
        "context_length": loaded.get("context_length") if loaded else None,
    }


def installed_version(package: str) -> str | None:
    try:
        return version(package)
    except Exception:
        return None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a versioned RAG evaluation baseline")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "sprint-1-baseline.json",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "sprint-1-v1.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "sprint-1-deterministic.json",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=None,
        help="Optional JSONL packet for blinded human scoring",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=("deterministic", "fastembed"),
        default="deterministic",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    parser.add_argument(
        "--embedding-source-repo",
        default="qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q",
    )
    parser.add_argument(
        "--embedding-revision",
        default="faf4aa4225822f3bc6376869cb1164e8e3feedd0",
    )
    parser.add_argument("--embedding-dimensions", type=int, default=384)
    parser.add_argument(
        "--answer-provider",
        choices=("deterministic", "ollama"),
        default="deterministic",
    )
    parser.add_argument("--answer-model", default="qwen2.5:1.5b")
    parser.add_argument("--ollama-base-url", default="http://localhost:11434")
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
