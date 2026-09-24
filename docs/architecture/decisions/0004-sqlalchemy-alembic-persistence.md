# ADR 0004: SQLAlchemy 2 and Alembic persistence

- Status: Accepted
- Date: 2026-09-24

## Context

Sprint 1 needs transactional ownership data, immutable document versions, job state, citations, lexical search, and vectors in PostgreSQL. The domain must remain testable without depending on ORM behavior, and schema changes must be reproducible from an empty database.

## Decision

Use SQLAlchemy 2.x typed declarative mappings with the async psycopg driver in the API. Keep ORM models in module infrastructure packages and map them to domain/application data at repository boundaries. Use one explicit async session per application unit of work. Use Alembic as the only mechanism for persistent schema changes.

Use PostgreSQL constraints to reinforce invariants and pgvector for the initial 384-dimensional embedding profile. Do not create an approximate vector index until the real-model baseline and query volume justify a specific index configuration.

## Alternatives considered

- SQLModel: convenient for small APIs, but it couples transport and persistence shapes more closely than this domain requires.
- Django ORM: mature, but it would introduce a second application framework and obscure the FastAPI application boundary.
- Raw psycopg: explicit and capable, but requires more handwritten mapping and migration discipline without improving this sprint's product outcome.

## Consequences

The API can use non-blocking database I/O, migrations are reviewable, and domain code stays framework-free. Repositories must perform explicit mapping. A future embedding-dimension change requires a versioned migration or parallel embedding profile rather than silently mixing incompatible vectors.
