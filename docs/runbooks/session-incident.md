# Session and account incident runbook

## Suspected stolen session

1. Verify the report through an accepted private support channel.
2. Revoke all sessions with the Auth CLI.
3. If credential compromise is possible, create a short-lived reset token and deliver it privately.
4. Review privacy-safe events by request/user UUID and time; never request the raw cookie.
5. Rotate infrastructure credentials only when evidence shows infrastructure compromise.

Revocation is immediate because every request resolves the opaque token digest against PostgreSQL.
There is no self-validating JWT that survives database revocation.

## Credential stuffing or brute force

Login uses per-source-and-normalized-identifier Redis windows, a dummy Argon2 verification for
unknown accounts, generic errors, and `Retry-After`. Check Redis/API health and aggregate counts;
do not log complete email addresses or raw IPs. Tightening limits is a configuration change that
must include accessibility and false-positive review.

## Redis unavailable

Login and generation admission fail closed with a safe `503`; existing session validation remains
database-backed. Do not bypass the limiter for a public service. Restore Redis, check readiness, and
then retry.
