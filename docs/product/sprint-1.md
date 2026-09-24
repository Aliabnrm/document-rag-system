# Sprint 1 — First end-to-end RAG vertical slice

- Status: Completed (2026-09-24)
- Branch: `feat/sprint-1-rag-vertical-slice`
- Theme: upload one supported document and receive a grounded, citable answer

## Goal

Prove the complete product and engineering path: a user creates a collection, uploads a Persian or English text-based PDF/TXT file, sees asynchronous processing, asks a question, and receives a streamed answer with validated page-aware citations or an explicit insufficient-evidence result.

## Demonstrable outcome

The sprint demo must use at least one controlled Persian document and one controlled English document. A reviewer can trace the request from UI to API, storage, job, extraction, chunking, embedding, retrieval, generation, citation validation, persistence, and back to the UI.

## In scope

- Initial relational schema and Alembic migrations for users/development identity, collections, documents, immutable document versions, ingestion jobs, chunks, conversations, messages, citations, and RAG runs.
- PostgreSQL/pgvector persistence, Redis-backed background jobs, and MinIO object storage adapters.
- Streaming PDF/TXT upload with MIME/content validation, configurable limits, checksum, generated storage key, and safe error responses.
- Idempotent extraction, Persian-aware normalization, deterministic token-aware chunking with overlap, batch embedding, and atomic ready state.
- Authorized collection/document-version retrieval with dense and lexical baselines, deterministic fusion, and an optional reranker only if measured value justifies it.
- Provider ports for embedding and answer generation, grounded prompting, answer streaming, citation validation, and abstention.
- Bilingual collection, upload/status, and chat/citation user flows with responsive accessible states.
- Versioned Persian/English evaluation fixtures, deterministic CI providers, real-model benchmark scripts, structured telemetry, and learning documentation.

## Out of scope

- Full OCR for scanned PDFs, complex table/diagram extraction, Office formats, team workspaces, billing, public-scale deployment, fine-tuning, agents/tool calling, and high-availability infrastructure.
- Production authentication may be deferred, but ownership must be represented and authorization must have an explicit application boundary rather than being omitted.

## Work sequence

1. Accept ADRs for persistence/access, background jobs, extraction, and initial model/runtime decisions.
2. Implement settings, database session/transaction foundation, migrations, domain states, and repository integration tests.
3. Implement collection and streamed document upload through object storage and enqueue an ingestion job.
4. Implement worker state transitions, extraction diagnostics, normalization, chunking, idempotency, and retry behavior.
5. Implement embedding adapter and vector persistence with recorded model/pipeline versions.
6. Implement scoped dense and lexical retrieval, fusion, context packing, and retrieval evaluation.
7. Implement grounded streaming generation, backend-owned citation validation, persistence, and abstention behavior.
8. Implement the bilingual accessible UI and traceable failure/retry states.
9. Run evaluation and failure-path tests; update architecture, runbooks, sprint review, and Persian learning walkthrough.

## Evaluation baseline

Create 30–50 versioned questions covering direct, semantic, cross-lingual, exact identifier/date, multi-passage, ambiguous, and unanswerable cases. Record at least retrieval Recall@K/MRR, citation validity/support, groundedness, abstention behavior, time to first token, total latency, and pipeline/model versions. Thresholds become release gates only after the first honest baseline is recorded.

## Risks to resolve explicitly

- Local hardware may constrain embedding, reranking, and generation model size.
- PDF extraction quality varies across Persian fonts and document producers.
- Duplicate job delivery can create inconsistent or repeated chunks without idempotency.
- Citation syntax from a model is not trustworthy until checked against supplied evidence IDs.
- A polished happy path can hide authorization, disconnect, retry, and insufficient-evidence failures.

## Definition of Done

- A clean checkout can start required services and apply migrations from an empty database.
- Upload returns promptly and processing continues in a worker with observable stages.
- Retrying the same document version does not create duplicate artifacts.
- Source text/page metadata and normalized retrieval text remain distinct and versioned.
- Retrieval is restricted before search to authorized immutable document versions.
- Persian and English questions produce grounded answers with backend-validated citations; unanswerable questions abstain.
- CI covers public contracts and the end-to-end flow using deterministic providers; real-provider evaluation produces a versioned report.
- Frontend lint/type/test/build, backend lint/type/test, Compose validation, and diff checks pass.
- Persian and English mobile/desktop flows are visually and accessibility reviewed.
- Architecture/API/runbook docs, an English sprint review, and a Persian backend/AI learning walkthrough match the delivered system.

## Completion evidence

- Empty PostgreSQL database: upgrade to head, `alembic check`, downgrade to base, and re-upgrade all
  passed.
- Backend: Ruff passed, strict MyPy passed, and 20 tests passed with live PostgreSQL/MinIO/Redis
  integration services.
- Frontend: ESLint, TypeScript, 5 Vitest tests, production build, and peer-dependency check passed.
- Infrastructure: Compose configuration and all three service health checks passed.
- Evaluation: 40-question deterministic, real multilingual embedding, and real Qwen 0.5B reports
  were recorded; rejected/incomplete generator attempts are not misrepresented as successful scores.
- Visual/accessibility: Persian and English citation flows passed at 1440×1000 and 390×844 with no
  horizontal overflow; semantic color pairs pass WCAG 2.2 AA contrast.
