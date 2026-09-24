# Sprint 1 engineering review

## Delivered user behavior

A Persian- or English-speaking user can create a collection, upload a UTF-8 TXT or text-based PDF,
follow asynchronous processing, ask a question, receive an SSE answer, and inspect document/page
citations. Unsupported, encrypted, empty, likely scanned, disconnected, failed, loading, empty,
retry, and insufficient-evidence paths have explicit product states.

## Architecture and data flow

The backend is a modular monolith with separate API and Celery worker entry points. PostgreSQL plus
pgvector owns relational/vector truth, MinIO owns immutable source files, and Redis transports
at-least-once jobs. Domain transitions are framework-free; application use cases depend on ports;
SQLAlchemy, Celery, S3, pypdf, FastEmbed, and Ollama stay in infrastructure adapters.

Upload commits immutable version/job state before dispatch. A scheduled relay repairs the
commit-to-broker crash window. Workers claim jobs under a row lock, spool large sources, extract
page-aware text, preserve source and normalized copies, chunk deterministically, embed in batches,
and atomically write chunks plus ready status.

Question answering authorizes the collection before both SQL searches, fuses dense and lexical
results with deterministic RRF, packs an explicit token budget, treats passages as untrusted data,
validates model-suggested evidence IDs, persists provenance/timing, and streams safe events.

## Significant decisions

- PostgreSQL/pgvector avoids another data store while preserving transaction and authorization
  boundaries.
- Celery/Redis provides familiar at-least-once operation; database state plus idempotent claims is
  the correctness boundary.
- pypdf supports page-aware text PDFs; OCR is explicitly deferred.
- Deterministic providers keep CI reproducible. The first real embedding model is pinned to an
  exact source commit and justified by a versioned bilingual evaluation.
- No reranker is shipped without measured gain.
- The Ollama adapter buffers provider output before SSE chunking. This trades true provider TTFT
  for clean control parsing and citation safety; metrics expose the cost.

## Reliability, security, and privacy

- File size/type/encoding/signature, filename metadata, generated storage keys, SHA-256, ownership,
  cursor input, and public schemas are validated at boundaries.
- Retrieval filters owner, collection, and ready immutable versions before ranking.
- Partial index artifacts are invisible until the ready transaction.
- Error responses and structured logs exclude provider messages, source passages, questions,
  answers, prompts, credentials, vectors, and storage keys.
- Liveness is independent of dependency readiness; readiness covers PostgreSQL, Redis, and MinIO.
- Development identity is an explicit boundary, not production authentication.

## UI and design system

The Next.js interface supports `/fa` and `/en`, structural RTL/LTR, mixed-direction filenames and
citations, keyboard operation, visible focus, live status, reduced motion, upload cancellation,
responsive layouts, and stable streaming/citation panels. Semantic tokens centralize warm ivory,
charcoal, restrained emerald, warm evidence accent, typography, spacing, radii, elevation, motion,
and breakpoints. Feature code does not introduce ad-hoc palette or layout values.

## Verification evidence

- Backend unit/integration suite exercises state machines, Persian normalization, extraction,
  chunk overlap, fusion, context packing, citation validation, migrations/infrastructure, duplicate
  ingestion, authorization, dispatch recovery, readiness, and the complete deterministic flow.
- Frontend tests exercise injected API contracts, SSE parsing, file validation, streamed-message
  reduction, and collection/chat availability behavior.
- The versioned 40-question evaluation records retrieval, citation, abstention, relevance, latency,
  throughput, model/prompt/chunker/retriever/pipeline, and hardware context.
- Empty-database upgrade/check/downgrade/re-upgrade passed. Ruff, strict MyPy, 20 backend tests,
  ESLint, TypeScript, 9 frontend tests, production build, peer check, Compose validation, and diff
  whitespace validation passed on 2026-09-24.
- The visual matrix and exact contrast evidence are recorded in
  `sprint-1-visual-accessibility-review.md`.

## Challenges and honest limitations

- Eight GiB unified memory constrains simultaneous local services and models. BGE-M3 was not chosen
  without evidence. Qwen 0.5B completed but failed grounded-quality proxies; 1.5B download was
  unstable in Ollama 0.15.5; the local 7.6B coder used about 4.81 GB VRAM and destabilized the
  concurrent local stack. Operational feasibility is kept separate from model-quality claims.
- pypdf cannot recover image-only scans or guarantee correct reading order for complex layouts.
- Token counting is a deterministic approximation, not each provider's tokenizer.
- The small controlled dataset cannot establish public release thresholds or broad domain quality.
- Development identity, quotas, document deletion, conversation history UI, feedback, OCR, backup
  restore, and public deployment hardening remain outside Sprint 1.
- A single local worker can embed with the real model, but production concurrency/resource limits
  still require load testing.
