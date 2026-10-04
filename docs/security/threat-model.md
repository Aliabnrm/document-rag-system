# Authentication and product threat model

- Status: Initial Sprint 2 baseline
- Last reviewed: 2026-09-26

## Assets and trust boundaries

Protected assets include password hashes, session/reset token digests, source documents,
extracted passages, questions, answers, citations, feedback, object-storage keys, prompts, and
deletion state. The browser, Next.js frontend, FastAPI API, PostgreSQL, Redis/Celery, MinIO, worker,
administrator CLI, and model runtime are separate trust boundaries. Document text and model output
are always untrusted data.

## Security invariants

- Passwords are stored only as Argon2id encoded hashes produced by a maintained library.
- Raw session and reset tokens are returned at most once and never stored; PostgreSQL
  stores only SHA-256 digests of at least 256-bit random tokens.
- Production-like environments never fall back to a fixed development identity or insecure cookie
  settings.
- A session is accepted only when its digest matches, it is active and unexpired, and its user is
  active.
- Cookie-authenticated unsafe requests require an allowed Origin and a valid server-bound CSRF
  token.
- Pre-authentication registration/login/reset requests require an exact browser Origin but ignore a
  stale session for CSRF binding, so expired cookies cannot block recovery.
- Product ownership uses an internal user UUID, never email.
- Authorization filters run before rows, vectors, messages, citations, feedback, or deletion state
  leave persistence.
- Login and recovery responses do not disclose whether an account exists.
- Document instructions cannot override application or system instructions.
- Sensitive authentication and RAG content is excluded from default logs.
- Deletion makes data unavailable to retrieval before asynchronous physical cleanup.

## Threats and required controls

| Threat | Impact | Required controls |
| --- | --- | --- |
| Password database compromise | Offline password cracking | Argon2id with measured cost, unique salts, rehash support, strong password policy |
| Credential stuffing or brute force | Account takeover or resource exhaustion | Atomic per-IP/identifier limits, bounded backoff, generic errors, safe `Retry-After` |
| Account enumeration or timing difference | User privacy leak | One public login error and a dummy Argon2 verification for unknown users |
| Automated or mass registration | Resource exhaustion and abuse | Per-IP and per-email limits, document/question quotas, monitoring; verified email/CAPTCHA remains a release gate |
| Concurrent registration for one email | Duplicate or inconsistent accounts | Atomic unique normalized-email insert in the registration transaction |
| Unverified email ownership | Impersonation or unreachable recovery | UI does not claim verification; automated recovery/public launch remains blocked until email verification exists |
| Weak or reused password | Easier takeover | Length-based Unicode policy, bounded maximum, optional versioned common-password denylist |
| Session fixation | Attacker controls authenticated session | Generate a fresh random session after login/registration; never accept caller IDs |
| Session token theft | Account takeover | HttpOnly/Secure/SameSite cookie, digest-only storage, expiry, revocation, XSS controls |
| Cookie-authenticated CSRF | Unauthorized state change | Exact CORS origins, Origin/Referer checks, server-bound CSRF header, SameSite cookie |
| Reset token theft/replay | Account takeover | Short lifetime, digest storage, atomic single use, session revocation after reset |
| Disabled-user session reuse | Continued access | Session resolution joins active user state; disabling revokes sessions |
| Missing password-change revocation | Stolen session survives | Documented current/other-session revocation policy and integration tests |
| Horizontal UUID access | Cross-user disclosure or mutation | Owner predicates in repositories/retrieval and two-user route tests |
| Cross-user vector search | Passage and ranking leakage | Filter owner/collection/ready versions inside dense and lexical SQL before ranking |
| Upload/resource exhaustion | Availability and cost loss | Size/storage/question/concurrency quotas and bounded spooling |
| Document prompt injection | Policy override or leakage | Delimited untrusted evidence, no tools, backend citation validation |
| Sensitive telemetry | Privacy breach | Content-free structured events, digested identifiers, redaction tests |
| Partial or replayed deletion | Deleted content remains searchable | Tombstone first, idempotent cleanup, ingestion replay guards, bounded retry |

## Registration and recovery limitation

The application allows direct email/password registration but does not yet verify ownership of that
email address. It also has no automated recovery email in Sprint 2. An administrator creates reset
tokens through a protected CLI and sends them through an accepted private channel after an external
identity check. This avoids an external-provider/regional dependency but means public launch remains
blocked on verified email, scalable anti-abuse controls, and an accepted recovery process.

## Residual risk

Owning authentication means this project owns patching, credential policy, brute-force defense,
session incident response, recovery, and security review. Argon2id and secure cookies reduce risk but
do not make a compromised browser or administrator machine trustworthy. MFA/WebAuthn, automated
verified email, backup/restore, load, and assisted accessibility exercises remain future gates.
