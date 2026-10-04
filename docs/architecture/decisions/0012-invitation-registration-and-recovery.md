# ADR 0012: CLI-issued invitations and private-beta recovery

- Status: Superseded in part by ADR 0013; reset-token recovery remains accepted
- Date: 2026-09-26

## Context

Sprint 2 needs controlled external testers without public registration or an automated email
provider. Invitation and recovery tokens are credentials and cannot be stored or logged in raw form.

## Decision

Provide administrator CLI use cases to create/revoke email-bound invitations and create short-lived
password-reset tokens. Generate at least 256 bits of entropy, show the raw token exactly once, and
persist only its SHA-256 digest. Invitations and reset tokens are expiring, revocable, and consumed
atomically under row locking. Registration creates the user, credential, consumed invitation, and
initial session in one transaction. Reset changes the Argon2id hash and revokes all existing sessions.

## Alternatives considered

- Automated email links: deferred until delivery cost, privacy, abuse, and regional accessibility
  are accepted.
- Reusable invite codes: rejected because leakage cannot be contained per user.
- Operator-written SQL: rejected because it bypasses domain rules, auditing, and token safety.

## Consequences

Private-beta onboarding has an operator step and recovery requires identity verification outside the
application. The same application use cases can later be called by an accepted email adapter without
changing token or account invariants.
