# Backend and AI engineering rules

These rules specialize the repository contract for `backend/`.

## Architecture

The backend is a modular monolith with separate API and worker entry points. Organize code by business capability, then by responsibility when complexity requires it:

```text
src/app/
  modules/<capability>/
    domain/           framework-free entities, values, policies, events
    application/      use cases, ports, commands, queries, DTOs
    infrastructure/   database, storage, queue, and AI adapters
    presentation/     FastAPI routes and HTTP schemas
  platform/           shared database, queue, storage, telemetry foundations
  entrypoints/        API and worker process composition
```

Do not create empty layers. Begin with a cohesive module and extract a layer when behavior or an external boundary exists.

Dependencies point inward: presentation and infrastructure may depend on application/domain contracts; domain code never imports FastAPI, SQLAlchemy, Redis/Celery, object-storage SDKs, or model SDKs. Cross-module behavior goes through an application use case or explicit domain event, not another module's tables.

## Domain and persistence

- Model invariants and state transitions explicitly. Illegal transitions fail with domain-specific errors.
- `Document` is stable identity; `DocumentVersion` is immutable source content and pipeline target.
- Persist citations against immutable document versions and chunks.
- Use SQLAlchemy 2.x patterns, explicit transactions, and Alembic for every schema change.
- Keep migrations forward-safe and review generated SQL. Never edit an applied migration casually.
- Put authorization predicates into retrieval/database queries before candidates are returned.
- Use UTC timestamps, database constraints, foreign keys, and uniqueness constraints to reinforce domain rules.
- Pagination is deterministic with an explicit stable ordering. Use cursor pagination when lists can grow or mutate materially.

## API contracts

- Version public routes under `/api/v1` and give operations stable `operation_id` values.
- Separate HTTP/Pydantic schemas from domain objects and persistence models.
- Validate content type, body size, identifiers, filters, and pagination at the boundary.
- Use one documented error envelope with a stable machine code, user-safe message, request ID, and optional field details.
- Do not expose stack traces, provider errors, storage keys, prompts, or internal exception text.
- Stream uploads and generated answers; define disconnect and retry behavior.
- Keep OpenAPI accurate and update contract tests when behavior changes.

## Background work and storage

- CPU-heavy or long-running extraction, chunking, embedding, and indexing run in workers, never in an API request handler.
- Jobs are idempotent, retryable with bounded exponential backoff, observable, and safe against duplicate delivery.
- Persist job state before acknowledging work and record attempt, stage, heartbeat, and sanitized failure code.
- Derive storage keys from generated identifiers; never trust filenames as paths.
- Stream file content, verify MIME using content, calculate a checksum, and enforce configurable limits.
- Make partial ingestion outputs invisible to queries. Mark a document version ready only after all required artifacts commit.

## RAG implementation

Maintain explicit ports for extraction, embedding, reranking, and answer generation. Adapters expose model identifier, revision, dimensions/context limits, and runtime metadata.

Ingestion order:

```text
validate → store source → extract page-aware text → normalize retrieval copy
→ deterministic token-aware chunks → batch embeddings → atomic ready state
```

Query order:

```text
authorize scope → normalize query → dense + lexical candidates
→ fuse/deduplicate → optional measured rerank → context packing
→ grounded generation → citation validation → persist/stream result
```

- Keep source text unchanged for display; normalize a separate field for retrieval.
- Record page range, source offsets, token count, content hash, and pipeline versions on chunks.
- Use hybrid retrieval as a measured baseline. Changes to `top_k`, chunk size, overlap, fusion, reranking, or prompt require evaluation evidence.
- Context packing has an explicit token budget and deterministic ordering.
- Treat retrieved passages as quoted evidence. Delimit them and instruct the model that embedded instructions are untrusted.
- Validate citation IDs against supplied context and fail safely when an answer cannot be grounded.

## Observability and privacy

Use structured logs with request, job, document-version, conversation, and RAG-run correlation IDs. Measure stage latency, candidate counts, token usage, retries, and failure codes. Do not log raw files, source passages, questions, answers, prompts, credentials, or embeddings by default.

Separate liveness from readiness. A dependency outage should make readiness fail without causing a process restart loop.

## Tests and learning evidence

- Unit-test normalization, chunk boundaries/overlap, state machines, fusion, context packing, and citation validation.
- Integration-test migrations, constraints, repositories, pgvector queries, object storage, queue behavior, idempotent retries, and API contracts with real local dependencies where valuable.
- Use deterministic fake AI providers in CI; keep real model benchmarks under `evals/`.
- For every non-trivial pipeline change, update an English technical note and the sprint's Persian learning walkthrough with a trace of one real request.

Backend quality command:

```bash
uv run ruff check . && uv run mypy src && uv run pytest
```
