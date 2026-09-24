# Ingestion worker runbook

## Responsibilities

The API validates/stores an upload and persists durable state. The worker owns extraction,
normalization, deterministic chunking, batch embedding, and the atomic transition to ready.

Run locally with:

```bash
cd backend
uv run celery -A app.entrypoints.worker.celery_app worker --beat --pool=solo --loglevel=INFO
```

`solo` avoids the macOS spawn/prefork limitation in local development. Deployed Linux workers can
use a measured process pool. Only one Beat scheduler should run in a deployed environment. Workers
can scale horizontally; every task is safe under duplicate delivery.

## Healthy lifecycle

```text
version: uploaded → queued → extracting → chunking → embedding → ready
job:     pending  → running                              → succeeded
```

The job records attempt count, dispatch count, stage, heartbeat, safe error code, start time, and
finish time. Structured logs correlate `job_id` and `document_version_id` and record stage latency,
but never file text or embeddings.

## Recovery behavior

- Worker crash after claim: late acknowledgement lets Celery redeliver; stale recovery is visible in
  job state and retry behavior.
- API crash around broker send: the scheduled reconciler leases queued jobs whose last dispatch is
  older than 60 seconds and sends them again.
- Duplicate message: the row lock/status check returns without processing a succeeded or running
  job.
- Partial chunk write: chunks and ready status commit together; retrieval sees only ready versions.
- Transient dependency failure: bounded exponential backoff with jitter, at most four attempts.
- Permanent document failure: encrypted, empty, invalid, unsupported, or likely scanned files stop
  with a localized-safe code and require a corrected upload or explicit retry.

## Diagnosis

1. Check `/api/v1/ready` to separate API process health from dependency health.
2. Inspect `docker compose -f infra/compose.yaml ps` for PostgreSQL, Redis, and MinIO.
3. Find the structured event using `job_id`; do not paste document text into logs or tickets.
4. Inspect persisted `status`, `stage`, `attempt_count`, `dispatch_count`, `heartbeat_at`, and
   `error_code`.
5. Retry through the public retry endpoint only when the version is failed.

Provider exception text is deliberately sanitized to stable codes such as
`dependency_timeout`/`dependency_unavailable`. Use local reproduction and dependency logs for root
cause without weakening the public error boundary.
