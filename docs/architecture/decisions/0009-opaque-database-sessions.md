# ADR 0009: Revocable opaque database sessions

- Status: Accepted
- Date: 2026-09-26

## Context

The first-party browser application needs logout, logout-all, password-reset revocation, disabled
user enforcement, idle expiry, and incident response. Stateless JWTs would require a second
revocation mechanism and expose bearer-token storage choices without a current scaling need.

## Decision

Issue at least 256 bits of random session entropy and place the raw token only in an HttpOnly cookie.
Store its SHA-256 digest in PostgreSQL with user ownership, idle/absolute expiry, last-seen,
revocation, and server-side CSRF material. Resolve every protected request through an active,
unexpired session and active user. Throttle last-seen writes.

Secure environments use a `__Host-` cookie with `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, and
no Domain attribute. Local HTTP development uses an explicit separate cookie profile. Unsafe
requests also require an allowed Origin and a valid CSRF header.

## Alternatives considered

- Browser JWT in local storage: rejected because XSS exposes a long-lived bearer token and immediate
  revocation is awkward.
- Signed cookie containing user identity: rejected because logout-all and server-side session state
  still require a revocation store.
- Redis-only sessions: rejected because session ownership/revocation is authoritative product state;
  Redis remains suitable for ephemeral rate-limit counters.

## Consequences

Authentication adds one indexed database lookup per protected request and requires expired-session
cleanup. In return, revocation and security policy are explicit, testable, and independent of
frontend JavaScript storage.
