# ADR 0003: PostgreSQL and pgvector as the initial data platform

- Status: Accepted
- Date: 2026-09-23

## Context

The first release needs relational product data, transactions, metadata filtering, full-text search, and vector similarity. Operating separate managed databases early would raise cost and consistency complexity.

## Decision

Use PostgreSQL as the system of record and pgvector for initial dense retrieval. Use PostgreSQL full-text capabilities for the first lexical baseline. Keep retrieval behind a repository contract so a dedicated search engine can be evaluated later.

## Consequences

Local and beta infrastructure stays compact, and authorization filters can participate in retrieval queries. Scale and retrieval quality must be measured; migration to a specialized store remains possible through the adapter boundary.
