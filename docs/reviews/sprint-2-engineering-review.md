# Sprint 2 engineering review

- Status: In progress; human generator review and backup-policy gates remain open
- Review date: 2026-09-26

## Delivered behavior

The beta slice now owns email/password authentication without OAuth or an external identity
provider. Rate-limited self-registration, Argon2id credentials, digest-only opaque sessions,
CSRF/Origin/CORS controls, login limits, CLI reset administration, paginated collections, stable
URLs, exact conversation resume, structured feedback, server quotas, and retrieval-first idempotent deletion
are implemented in the modular monolith. Persian and English screens cover registration, login,
session actions, history, deletion confirmation, feedback reasons, and recovery errors.

## Architecture and request flow

Identity presentation maps cookies/headers to application commands. Application use cases depend on
repository, hasher, token, clock, and limiter contracts. SQLAlchemy/Argon2/Redis adapters remain at
the infrastructure edge. Product modules receive only the internal UUID. Dense and lexical queries
enforce owner/live/ready predicates before returning candidates.

The frontend keeps Axios calls in typed API modules, validates unknown finite responses with Zod,
uses focused TanStack Query hooks for server state, and keeps feature components presentation-led.
HttpOnly session state is never copied into browser storage.

## Measured decisions

- Argon2id on Apple M2: 64 MiB, time cost 3, parallelism 2; median hash `56.56ms`, verify `57.84ms`.
- Deterministic 80-question baseline: Recall@8 `0.851351`, MRR `0.743131`, document+page retrieval
  `0.894737`, citation-ID validity `1.0`.
- Real multilingual embedder with Qwen 2.5 1.5B: Recall@8 `0.891892`, MRR `0.796734`, page metric
  `1.0`, generation success `1.0`, median TTFT `1980.312ms`, median total latency `2327.956ms`.
- Qwen 2.5 generation is rejected for beta: citation support/groundedness proxy `0.1875`, relevance
  `0.3875`, abstention `0.65`.
- Qwen 3 1.7B (Apache-2.0, Q4_K_M, digest `8f68893c685c…`) improved support/groundedness to
  `0.75`, relevance to `0.60`, and abstention to `0.9125`, with median TTFT `2007.902ms` and median
  total latency `2353.689ms`. It is the leading automated candidate, not an accepted default;
  independent human scoring remains required.

## Meaningful failures and tradeoffs

The first Qwen run completed many prompts and then hit a three-minute provider timeout. An early
Qwen 3 run also exposed fake streaming: the adapter buffered the complete response and then emitted
words, while model thinking raised median TTFT to about 8.25 seconds. Generation now consumes the
real Ollama stream, hides protocol markers, disables thinking for this contract, and has deterministic
temperature/seed, a 384-token hard output bound, per-question sanitized failure capture, and a user
concurrency lease. Both models were rerun through that path, so operational failure and UX latency
are now measured rather than inferred.

Deletion now atomically persists a tombstone and cleanup job. A retryable worker removes source
objects, citations, chunks, and collection conversations in dependency-safe order, redacts retained
tombstone metadata, and a periodic reconciler repairs API-to-broker dispatch gaps. Backup expiration
remains a deployment policy gate and is not conflated with application cleanup.

Application-owned Auth avoids OAuth cost/provider/regional availability, but transfers credential
patching, recovery, abuse defense, and incident response to this project. Removing the onboarding
token makes account creation understandable and independent of an operator, but unverified email
and automated signup abuse remain release risks. Registration therefore combines Redis IP/email
limits with an atomic PostgreSQL unique-email claim. Operator-assisted recovery is manual by design.

## Validation evidence

Backend Ruff/Mypy/Pytest/Alembic drift checks and frontend lint/typecheck/tests/build pass on the
final code path. Compose validation and `git diff --check` pass. The repository audit found no
staged files, merge conflicts, secrets, model weights, runtime caches, or private documents among
the proposed Sprint 2 artifacts.
Integration coverage exercises self-registration, registration throttling, atomic duplicate-email
handling, cookie issuance, CSRF rejection, generic login errors, digest-only tokens,
upload/ingestion/answer/citation, persisted resume, feedback,
two-user endpoint isolation, safe foreign-list 404s, retrieval exclusion, duplicate deletion,
physical cleanup, active-session caps, reset single use/session revocation, actual cursor pages,
quotas, concurrency leases, and UUID-safe structured logs. Empty-database and Sprint 1 upgrade-path
migration verification pass. Full visual inspection remains a completion gate.
The registration and authenticated empty-workspace screens were visually inspected in Persian and
English at mobile and desktop widths, including RTL/LTR structure, long account identifiers, labels,
and accessible names.

## Remaining blockers

- Complete independent human review and accept or reject the Qwen 3 candidate explicitly.
- Accept and verify a deployed backup-expiration policy.
- Complete hands-on visual inspection of populated chat/citation, feedback, and deletion states in
  both locales.
