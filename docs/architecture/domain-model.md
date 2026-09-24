# Initial domain vocabulary

| Entity | Purpose | Key invariant |
|---|---|---|
| User | Owns or accesses product data | Access is checked before retrieval |
| Collection | Groups related documents | A query has an explicit collection scope |
| Document | Stable identity of an uploaded source | Replacing content creates a version |
| DocumentVersion | Immutable processing target | Answers cite a specific version |
| IngestionJob | Tracks asynchronous processing | Retrying is idempotent |
| Chunk | Page-aware retrievable passage | Retains source offsets and processing version |
| Conversation | Holds a scoped dialogue | Scope changes are explicit |
| Message | User question or assistant result | Generated answers preserve model/run metadata |
| Citation | Connects an answer claim to evidence | References an immutable chunk/document version |
| Feedback | Captures user judgment | Links to the exact answer run |

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

The Sprint 1 development identity represents the future authentication boundary:

```text
User → Collection → Document → DocumentVersion → Chunk
User → Conversation → Message → RagRun → Citation → Chunk
```

Authorization predicates are applied inside dense and lexical SQL queries before candidates leave
PostgreSQL. Filtering after retrieval would leak existence and ranking signals across users.
