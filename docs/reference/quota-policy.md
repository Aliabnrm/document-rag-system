# Beta quota policy

Quotas protect a free local/beta deployment from accidental and abusive load. Enforcement
is server-side; frontend messages are only recovery guidance.

| Resource | Default | Behavior |
|---|---:|---|
| Upload size | 50 MiB/file | Stream stops with safe `413`/validation error |
| Live documents | 100/user | `429 document_quota_exceeded`; deleted tombstones do not count |
| Questions | 200/user/day | `429 question_quota_exceeded` + `Retry-After` |
| Concurrent generations | 1/user | Redis lease; `429 generation_concurrency_exceeded` |
| Active sessions | 5/user | Oldest active session is revoked on new issuance |
| Login attempts | 8/15 minutes | Reduced source+email key; generic `429` |

The concurrency lease has a timeout longer than provider timeout, so process death eventually
recovers capacity. Redis failure fails closed rather than admitting unbounded work. These defaults
are hypotheses; change them only after observing beta latency, accessibility, and capacity.
