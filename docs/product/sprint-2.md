# Sprint 2 — Trusted beta foundation

- Status: In progress
- Branch: `feat/trusted-foundation`
- Theme: verified ownership, measured answer quality, and controllable user data

## Goal

Turn the completed Sprint 1 RAG slice into a trustworthy beta product. A Persian- or
English-speaking user must be able to create an account, authenticate, see only their own resources, navigate
collections, resume persisted conversations, inspect validated citations, provide answer feedback,
and delete their data.

Sprint 2 is not a public-production launch. Public registration, automated recovery email, the
target model runtime, backup policy, load envelope, and operating budget require explicit
acceptance first.

## Why this sprint comes next

Sprint 1 proved upload, asynchronous ingestion, scoped hybrid retrieval, grounded generation
orchestration, citation validation, and the bilingual workspace. The remaining release blockers are:

1. the measured Qwen 2.5 0.5B generator is operationally small but fails grounded-quality proxies;
2. API ownership uses one configured development identity rather than a verified user session;
3. collection discovery, persisted conversation resume, deletion, feedback, and abuse protection are
   incomplete for external testers.

Adding OCR, Office formats, teams, or more AI stages before these blockers would grow the system
without making it safer or more useful.

## Demonstrable user outcome

A user can:

1. authenticate and recover from an expired or unavailable session;
2. list and open only their paginated collections through stable URLs;
3. upload a document and follow ingestion without losing navigation context;
4. ask with a real open-weight generator accepted by a recorded evaluation gate;
5. reopen a conversation and see the exact persisted answers and validated citations;
6. submit structured feedback tied to the exact answer run;
7. request document or collection deletion and observe a reliable terminal outcome.

A second user cannot read, search, mutate, stream, rate, or delete the first user's resources even
when they know every UUID.

## Decision gates

### Application-owned authentication

Sprint 2 uses application-owned email/password accounts with Argon2id and revocable opaque sessions.
It does not use OAuth, OIDC, social login, or an external identity provider. Building the Auth
workflow does not authorize custom cryptography: password hashing and randomness use maintained,
audited libraries and operating-system primitives.

Registration is available directly from the bilingual UI and is protected by per-IP and per-email
rate limits plus an atomic unique-email database write. Email verification and automated recovery
remain blocked until delivery cost, abuse controls, privacy, and Iranian-user accessibility are
explicitly accepted. An administrator can still issue short-lived reset tokens through the CLI.

### Generator runtime

Open weights do not make inference infrastructure free. A generator is accepted only after quality,
latency, memory, concurrency, failure behavior, license, and operating cost are measured together.
Deterministic generation remains a CI contract provider, not an end-user quality claim.

## Scope and priority

### P0 — beta blockers

- Expand the versioned evaluation to 80–100 reviewed questions and representative page-aware
  Persian/English PDFs.
- Export a separate human-review packet and record real-model hardware/runtime provenance.
- Compare at least two hardware-appropriate open-weight generators, beginning with the recorded
  `qwen2.5:1.5b` candidate.
- Implement rate-limited self-registration, Argon2id credentials, opaque database sessions, secure
  cookies, CSRF protection, operator-assisted reset tokens, and login abuse controls.
- Prove two-user isolation across every public resource and retrieval path.
- Add paginated collection discovery and stable deep links.
- Add paginated conversation history and exact persisted resume behavior.
- Implement authorized, idempotent document and collection deletion with explicit retention rules.

### P1 — beta learning and protection

- Structured feedback linked to the verified user, answer message, and RAG run.
- Configurable per-user upload, question, and concurrency quotas with safe `429` behavior.
- Privacy-bounded metrics for identity, queueing, ingestion, retrieval, generation, feedback,
  quotas, and deletion.
- Complete Persian/English session, empty, loading, failure, deletion, feedback, and quota states.

## Explicitly out of scope

- Full OCR, Office formats, complex table/diagram extraction, team workspaces, enterprise roles,
  billing, fine-tuning, autonomous agents, unmeasured reranking, microservices, high availability,
  and public launch.

## Work sequence

1. Record this sprint contract, threat model, identity/model/deletion decisions, and review rubric.
2. Expand evaluation and run the generator feasibility gate before coupling product behavior to a
   model that may not fit the target hardware.
3. Implement application-owned authentication and fail-closed cookie/session configuration, then
   prove two-user isolation.
4. Add collection navigation and conversation history on the verified ownership boundary.
5. Add immediate retrieval exclusion plus asynchronous, idempotent deletion cleanup.
6. Add feedback and quota policies.
7. Complete the authenticated bilingual UX, metrics, runbooks, end-to-end tests, and sprint review.

## Evaluation and release gates

- Citation identifier validity and cross-user isolation have zero tolerance for failure.
- Human reviewers score groundedness, citation support, relevance, Persian/English language quality,
  and correct abstention on controlled fixtures.
- Reports record exact model digest/revision, quantization, prompt/retriever/pipeline versions,
  hardware, memory, TTFT, total latency, and failures.
- Numeric quality and latency thresholds are accepted only after comparable candidates are
  measured; they are not invented in this plan.
- A model that misses the accepted quality or operating envelope remains rejected even when it is
  popular or fast.

## Risks

- Password, session, recovery, brute-force, and incident-response security now belong to this
  application and require continuous maintenance.
- Automated recovery email is intentionally absent from the beta profile.
- Small local generators may fit memory but fail groundedness or natural Persian quality.
- PDF text order and Persian glyph encoding can corrupt evaluation independently of the model.
- Deletion spans PostgreSQL, pgvector, object storage, queue retries, and backup retention.
- Browser token handling can introduce XSS, CSRF, callback, or refresh-token risk.

## Definition of Done

- Self-registration, Argon2id credentials, revocable opaque sessions, CSRF protection, and
  generic login failures are delivered without an external identity provider.
- Production-like environments fail closed and cannot use the development identity or insecure
  cookie settings.
- Two-user tests prove isolation across collections, documents, jobs, retrieval, conversations,
  messages, citations, feedback, and deletion.
- A real generator has a versioned automated and human evaluation report, or remains an explicit
  release blocker.
- Collections and conversations are paginated, deep-linkable, and resumable.
- Deleted resources leave retrieval immediately and cleanup is authorized, retryable, and
  idempotent.
- Feedback and quotas are owned by verified users and expose bilingual recovery states.
- Backend, frontend, migrations, deterministic end-to-end, security, accessibility, Compose, and
  diff quality gates pass.
- Architecture, API, environment, threat model, evaluation, operations, review, and Persian
  learning documentation match delivered behavior.
