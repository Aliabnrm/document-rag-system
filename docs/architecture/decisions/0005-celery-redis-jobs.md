# ADR 0005: Redis-backed Celery ingestion jobs

- Status: Accepted
- Date: 2026-09-24

## Context

Extraction, chunking, embedding, and indexing can outlive an HTTP request and must tolerate duplicate delivery, transient failure, and process restart. The team also needs observable job semantics that are familiar to backend reviewers.

## Decision

Use Celery with Redis as the initial broker. Treat delivery as at-least-once: the database is the source of truth, every task receives an immutable document-version identifier, and workers claim and transition persisted job state idempotently. A task acknowledgement occurs only after the unit of work finishes. Retries use bounded exponential backoff with jitter for transient errors; permanent document errors are not retried automatically.

Redis is transport state only. Losing Redis may delay work but must not erase the authoritative ingestion state stored in PostgreSQL.

The ingestion job row also supports dispatch recovery. The API records `dispatched_at` and a
dispatch count before sending. Celery Beat runs a reconciler every 30 seconds; jobs still queued
after the 60-second lease are re-sent. A crash can still duplicate a message, so the worker's
database claim remains the correctness boundary. This is a small transactional-outbox pattern
without a separate outbox table because one ingestion job maps to exactly one immutable version.

## Alternatives considered

- In-process FastAPI background tasks: simple, but jobs are lost on restart and cannot scale or retry independently.
- ARQ/Taskiq: attractive async APIs, but Celery has broader operational knowledge, mature delivery controls, and clearer portfolio recognition for this stage.
- A database-only queue: reduces infrastructure, but requires custom polling, leasing, retry, and observability behavior that is outside the product goal.

## Consequences

Workers and API deploy separately from one codebase. Idempotency is mandatory because Celery does not guarantee exactly-once delivery. Async database work inside workers needs a worker-owned event loop/session boundary and must not reuse API sessions.

Local development runs one worker with embedded Beat for convenience. Production should run Beat
as a single separately supervised process so multiple workers do not publish the same schedule.
