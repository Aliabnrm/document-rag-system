# Sprint 2 API guide

The canonical contract remains `/openapi.json`. Every product route is under `/api/v1`, requires
an opaque session cookie except registration/login/reset completion, and returns the shared safe
error envelope documented in the Sprint 1 guide.

## Browser security contract

The session token is a secret `HttpOnly` cookie and is never available to JavaScript. Registration
and login also set a readable, session-bound CSRF cookie. Every unsafe browser request sends the
exact allowed `Origin` and copies that CSRF value to `X-CSRF-Token`. The API checks Origin and token
before route execution. CORS uses exact configured origins with credentials; no wildcard is used.

Registration, login, and reset completion are pre-authentication endpoints. A browser Origin must
still match exactly, but a stale/revoked session cookie does not require a session-bound CSRF token;
otherwise an expired session could deadlock its own recovery. Non-browser clients may omit Origin.

## Authentication

| Method and path | Purpose | Success |
|---|---|---|
| `POST /auth/registrations` | Create an email/password account and initial session | `201` |
| `POST /auth/sessions` | Email/password login with generic failures | `200` |
| `GET /auth/me` | Safe user and session expiry projection | `200` |
| `DELETE /auth/session` | Idempotently revoke current session | `204` |
| `DELETE /auth/sessions` | Revoke all user sessions | `204` |
| `POST /auth/password-changes` | Verify old password, replace hash, revoke other sessions | `204` |
| `POST /auth/password-resets/complete` | Consume admin-issued token and revoke all sessions | `204` |

Registration example:

```http
POST /api/v1/auth/registrations
Content-Type: application/json

{"email":"user@example.com","password":"a long passphrase","display_name":"Ava"}
```

Unknown email, wrong password, and disabled user all return the same `invalid_credentials` public
error. Session and reset tokens are shown to a caller only as raw values; the database holds SHA-256
digests. Passwords use Argon2id, never ordinary SHA-256. Registration is limited by client IP and
normalized email; duplicate email creation returns the safe `registration_unavailable` code.

## Owned navigation and history

- `GET /collections?page_size=20&cursor=…` lists only the current user's live collections.
- `GET /collections/{id}` returns safe `404` for a foreign/deleted collection.
- `GET /collections/{id}/conversations?page_size=20&cursor=…` is newest-first cursor pagination.
- `GET /conversations/{id}/messages?page_size=50&after_position=…` returns exact persisted messages
  and citations in position order; reopening never regenerates an answer.

## Feedback and deletion

`POST /messages/{assistant_message_id}/feedback` accepts one rating per user/answer with a
structured reason and optional comment. Ownership is resolved through message → conversation before
write. Feedback is product evidence, not automatic training data.

`DELETE /collections/{collection_id}/documents/{document_id}` and
`DELETE /collections/{collection_id}` are idempotent. They commit an authorization-checked
tombstone and durable cleanup job before returning `204`. Reads, ingestion completion, dense
search, and lexical search exclude the tombstone immediately. The worker asynchronously removes
source objects, citations, chunks, collection conversations, and user-controlled tombstone
metadata in dependency-safe order. Broker dispatch failure does not roll back the tombstone; the
periodic reconciler redispatches persisted cleanup work. Infrastructure backup expiry remains a
separate deployment policy.

## Quotas

Registration/login attempts, upload bytes, live-document count, active sessions, daily questions, and concurrent
generation are backend-enforced. `429` includes a stable code and `Retry-After` when meaningful.
Redis stores reduced/digested limiter identifiers, not raw email/token values.
