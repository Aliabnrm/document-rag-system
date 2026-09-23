# System overview

## Context

The browser talks only to the backend API. The backend owns authorization, application rules, persistence, orchestration, and access to AI providers. Long-running ingestion work is executed by a worker. Original files live in object storage; relational product data and vectors initially live in PostgreSQL.

```mermaid
flowchart LR
    U[User] --> F[Next.js frontend]
    F --> A[FastAPI backend]
    A --> P[(PostgreSQL + pgvector)]
    A --> O[(S3-compatible object storage)]
    A --> R[(Redis queue)]
    R --> W[Ingestion worker]
    W --> O
    W --> P
    W --> E[Embedding service]
    A --> G[Generation service]
```

## Backend style

The backend is a modular monolith. Each module owns its vocabulary and behavior, while sharing one deployment and database initially. Application code depends on interfaces; infrastructure adapters implement database, object-storage, queue, embedding, reranking, and generation access.

Initial modules:

- `documents`: collections, documents, versions, ownership, and lifecycle.
- `ingestion`: extraction, normalization, chunking, embedding, and job state.
- `retrieval`: query preparation, hybrid search, fusion, and reranking.
- `conversations`: questions, answers, citations, feedback, and streaming.

## Ingestion flow

1. API validates identity, access, metadata, type, and size.
2. Original file is stored and a document version is created transactionally.
3. A durable ingestion job is queued; upload returns immediately.
4. Worker extracts page-aware text and records extraction diagnostics.
5. Text is normalized for retrieval while source text is preserved for citations.
6. Deterministic chunks are generated and embedded in batches.
7. The new document version becomes ready only after all required artifacts commit.

Jobs must be idempotent: retrying the same document version cannot create duplicate chunks.

## Query flow

1. API resolves the user's allowed document versions before retrieval.
2. The query is normalized and optionally rewritten using conversation context.
3. Dense and lexical searches produce candidates inside that authorization scope.
4. Results are fused, deduplicated, and reranked.
5. Context is packed within a measured token budget.
6. The generation model produces a structured answer referencing source identifiers.
7. Citations are validated and the answer streams to the browser.
8. Retrieval, model, latency, and feedback signals are recorded without logging private document content by default.

## Dependency rule

Domain rules do not import FastAPI, SQLAlchemy, Redis, model SDKs, or storage SDKs. Infrastructure may depend inward on domain and application contracts. This keeps business behavior testable and makes provider replacement controlled.
