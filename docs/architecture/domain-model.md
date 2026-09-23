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
