# ADR 0002: Modular monolith backend

- Status: Accepted
- Date: 2026-09-23

## Context

Ingestion, retrieval, and conversations have different responsibilities. Premature service separation would add distributed transactions, network failure modes, deployment overhead, and local-development friction before usage requires them.

## Decision

Use one FastAPI codebase organized by domain modules. Run HTTP and background-worker entry points as separate processes. Keep AI and infrastructure providers behind application interfaces.

## Consequences

Module boundaries remain visible and testable while operations stay manageable. A module can later be extracted when observed load, ownership, or reliability requirements justify that change.
