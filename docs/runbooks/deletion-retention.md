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

A deployed backup-expiration duration, restore verification, and legal/product erasure SLA still
require explicit acceptance before a public deletion promise. Application cleanup completion does
not prove that an older infrastructure backup has expired.
