# ADR 0008: Application-owned invitation and password authentication

- Status: Superseded by ADR 0013
- Date: 2026-09-26

## Context

The private beta needs real users but explicitly does not use OAuth, OIDC, social login, or an
external identity provider. Public registration and email recovery would add delivery, abuse,
privacy, and regional dependencies before external usage is understood.

## Decision

Use invitation-bound email/password accounts. Keep `users.id` as the stable ownership UUID and a
unique normalized email only as a login identifier. Store password credentials separately and hash
passwords with Argon2id through a maintained library using measured parameters. An administrator CLI
creates one-time invitation and reset tokens; no public signup or automated email is included.

Do not implement cryptographic algorithms. Use operating-system CSPRNGs, standard SHA-256 only for
high-entropy token digests, and constant-time comparisons where applicable.

## Alternatives considered

- OAuth/OIDC or managed Auth: explicitly rejected for this product direction.
- Custom password hashing: rejected as unsafe and unnecessary.
- Public registration immediately: rejected until abuse, verification, recovery, and email delivery
  are accepted product and operations decisions.
- API keys as user login: poor browser recovery, rotation, and session UX.

## Consequences

Credential security, recovery, rate limiting, session incidents, and library patching become this
application's responsibility. The private beta can operate without an identity or email provider,
but operators must securely deliver invitation/reset tokens and verify recovery requests.
