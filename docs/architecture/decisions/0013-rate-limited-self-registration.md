# ADR 0013: Rate-limited self-registration

- Status: Accepted
- Date: 2026-09-26
- Supersedes: ADR 0008 registration gate and ADR 0012 invitation lifecycle

## Context

Invitation-bound registration created an operator-only onboarding step and confused users who
expected to create their own account. The product owner explicitly removed invitation tokens from
the user journey and project runtime. Direct registration increases abuse and duplicate-request risk,
especially before verified email or a managed identity provider exists.

## Decision

Allow a user to register with email, password, and an optional display name. Keep application-owned
Argon2id credentials, opaque sessions, exact-Origin browser protection, and the existing ownership
UUID. Apply Redis limits independently to the client IP and normalized email before password hashing.
Claim the normalized email with a PostgreSQL `ON CONFLICT DO NOTHING` insert so concurrent requests
cannot create two users. Create the credential and initial session in the same transaction.

Remove invitation application contracts, persistence model, CLI commands, API field, frontend input,
and active database table. Preserve the already-applied migration history and add a forward migration
that drops the obsolete table.

## Alternatives considered

- Keep an optional invitation field: rejected because it preserves two onboarding paths and stale
  operational complexity.
- OAuth/OIDC or managed Auth: still outside the requested product direction.
- Registration without server limits: rejected because Argon2 work and stored resources are abuse
  targets.
- CAPTCHA immediately: deferred because it adds an external/regional dependency and accessibility
  cost; revisit with measured abuse.

## Consequences

Onboarding no longer needs an administrator or secret token. Duplicate registration is race-safe and
account creation has bounded request pressure. The application does not verify ownership of an email
address yet, so it must not claim that email is verified and public launch remains blocked on an
accepted verification, recovery, and anti-automation plan. Password-reset tokens remain an
administrator-issued private recovery mechanism for this sprint.
