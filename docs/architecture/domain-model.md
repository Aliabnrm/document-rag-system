# Initial domain vocabulary

| Entity | Purpose | Key invariant |
|---|---|---|
| User | Stable internal owner identity | Email is not an ownership key; disabled users cannot resolve sessions |
| PasswordCredential | Current Argon2id verifier | Hash is separate from public user projection |
| Session | Revocable browser authentication | Raw token is never stored; idle and absolute expiry both apply |
| PasswordResetToken | Operator-assisted recovery capability | Short-lived, digest-only, atomically single-use |
| Collection | Groups related documents | A query has an explicit collection scope |
| Document | Stable identity of an uploaded source | Replacing content creates a version |
| DocumentVersion | Immutable processing target | Answers cite a specific version |
| IngestionJob | Tracks asynchronous processing | Retrying is idempotent |
| Chunk | Page-aware retrievable passage | Retains source offsets and processing version |
| Conversation | Holds a scoped dialogue | Scope changes are explicit |
| Message | User question or assistant result | Generated answers preserve model/run metadata |
| Citation | Connects an answer claim to evidence | References an immutable chunk/document version |
| Feedback | Captures structured user judgment | Verified owner + exact assistant message/RAG run; one per answer |
| DeletionCleanupJob | Durable removal of source and derived evidence | One job per owner/resource; duplicate delivery is harmless |

These are product concepts rather than database-table instructions. Persistence design follows after lifecycle and invariants are validated in the first vertical slice.

## Sprint 1 lifecycle rules

`Document` is a stable identity and `DocumentVersion` is immutable source content plus a pipeline
version. Re-uploading changed bytes must create another version rather than mutating evidence that
an old answer cited.

```text
DocumentVersion: uploaded → queued → extracting → chunking → embedding → ready
                                               ↘ failure from every processing stage
failed → queued is allowed only through the explicit retry use case

IngestionJob: pending → running → succeeded
                         ↘ retry_scheduled → running
                         ↘ failed → retry_scheduled
```

Invalid transitions raise domain errors before infrastructure writes. Database constraints repeat
critical invariants—valid statuses, positive sizes/token counts, unique version numbers, unique
chunk ordinals, and page ranges—so a programming bug cannot silently create impossible state.

## Ownership path

```text
User → Collection → Document → DocumentVersion → Chunk
User → Conversation → Message → RagRun → Citation → Chunk
User → AnswerFeedback → assistant Message/RagRun
User → Session
```

Authorization predicates are applied inside dense and lexical SQL queries before candidates leave
PostgreSQL. Filtering after retrieval would leak existence and ranking signals across users.

## Sprint 2 identity and deletion invariants

```text
Session: active → revoked
                ↘ idle-expired (derived)
                ↘ absolute-expired (derived)

PasswordResetToken: active → consumed
                           ↘ revoked/expired

Collection/Document: live → tombstoned (one-way)

DeletionCleanupJob: pending → running → succeeded
                              ↘ failed → running
```

Registration applies IP/email rate limits and, in one transaction, atomically claims the normalized
email, creates the user and Argon2id credential, and creates a fresh session. Concurrent requests for
the same email cannot create duplicate users. Session/reset values have at least 256 random bits;
only SHA-256 digests are persisted. Passwords are
low-entropy human secrets and therefore use measured Argon2id with salt and memory cost.

Tombstoning is one-way product state. Old worker delivery cannot make a deleted version ready, and
retrieval predicates require live collection, live document, ready immutable version, and matching
owner before vector candidates leave PostgreSQL.
