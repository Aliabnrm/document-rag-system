# ADR 0001: Root-level frontend and backend

- Status: Accepted
- Date: 2026-09-23

## Context

The product has two primary deployable applications and should remain easy to navigate for learning and portfolio review.

## Decision

Place `frontend/` and `backend/` at the repository root. Do not wrap them in an `apps/` directory. Shared specifications and generated clients may later live under `packages/` if a concrete need appears.

## Consequences

The repository is immediately legible and each application owns its tooling. Cross-application consistency is enforced through API contracts, CI, documentation, and root commands rather than a JavaScript-focused workspace abstraction.
