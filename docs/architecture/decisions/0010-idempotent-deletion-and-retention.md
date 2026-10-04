# ADR 0010: Retrieval-first, idempotent deletion

- Status: Accepted
- Date: 2026-09-26

## Context

Deleting a document or collection spans relational rows, vectors, object storage, queued ingestion,
citations, and backups. A direct cascade can fail on historical evidence or recreate artifacts when
an old queue message arrives.

## Decision

Represent deletion as an authorized operation with explicit state. First tombstone the resource and
exclude it from every read and retrieval query in the same database transaction. Then dispatch an
idempotent cleanup job that removes object bytes and owned persistence in a documented order.
Duplicate cleanup delivery is harmless, and ingestion claim/finalization must refuse a tombstoned
target. A database-backed cleanup job is created in the same transaction as the tombstone. Celery
delivery is recoverable by a periodic reconciler; the worker removes source objects, citations, and
chunks, redacts retained tombstone metadata, and records success or a sanitized retryable failure.

Operational data becomes unavailable immediately. Backup expiry is governed by a separately
accepted deployment retention period and must not be described as instantaneous physical erasure.

## Alternatives considered

- Synchronous cascade in the HTTP request: simpler but couples latency and failure to object storage
  and cannot recover cleanly from partial deletion.
- Soft-delete forever: easy retrieval exclusion but fails the user's data-removal expectation.
- Delete object storage first: risks leaving a visible database document that can no longer be
  processed or cited.

## Consequences

Queries need consistent active/deletion predicates, workers need replay guards, and deletion needs a
runbook and observable safe error codes. The exact retention duration remains a deployment decision.
