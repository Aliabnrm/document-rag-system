# Deletion and retention runbook

## Delivered behavior

Document and collection deletion first verifies owner UUID and atomically commits a tombstone plus
a durable cleanup job. Tombstoned
documents disappear from list/detail queries and are filtered inside dense and lexical SQL before
ranking. Workers check tombstones before claiming and before marking a version ready. Duplicate
delete delivery is harmless. Source-object deletion follows the durable tombstone in the worker.
Celery retries bounded failures and a periodic reconciler redispatches pending, failed, or stale
running cleanup jobs.

## Retained data

Cleanup deletes citations before their referenced chunks. Document deletion keeps conversation
messages but removes source snippets and vectors for that document. Collection deletion also
removes its conversations, messages, runs, citations, feedback, and chunks. Minimal tombstone rows
remain to preserve one-way state and safe duplicate deletion; user-controlled names, filenames,
checksums, extraction metadata, and queued storage keys are redacted after successful cleanup.
PostgreSQL and object-storage backups may retain earlier bytes until their external expiry.

## Recovery and remaining deployment policy

If object storage or PostgreSQL fails, the job records `cleanup_dependency_failed`; the tombstone
still blocks product access and Celery/reconciliation retries later. Automatic claims stop after 10
attempts to avoid an infinite failure loop. After repairing the dependency, run
`docqa-admin retry-deletion-cleanup --id <uuid>` (with confirmation) to reset the failed job; never
clear a tombstone to make cleanup easier. Inspect `deletion_cleanup_jobs` by status and age without
copying `storage_keys` into logs.

Every API, CLI, and worker database session loads the canonical application metadata registry before
using SQLAlchemy. This keeps foreign-key resolution consistent across process entrypoints instead of
depending on unrelated route imports. A worker composition regression test resolves the sorted table
graph in a fresh Python process so a missing model registration fails before a cleanup job is run.

Cleanup workers emit privacy-bounded JSON events for `deletion_cleanup_started`,
`deletion_cleanup_succeeded`, `deletion_cleanup_skipped`, and `deletion_cleanup_failed`. Each event
contains the cleanup job correlation ID; terminal events include duration, failures include a stable
error code and exception type, and no event contains filenames, object-storage keys, or document
content. `deletion_cleanup_failure_state_not_recorded` means the worker could not persist the failed
state and requires checking PostgreSQL availability before retrying.

A deployed backup-expiration duration, restore verification, and legal/product erasure SLA still
require explicit acceptance before a public deletion promise. Application cleanup completion does
not prove that an older infrastructure backup has expired.
