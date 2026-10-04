# Environment reference

Copy `.env.example` to `.env`. Development defaults are intentionally local and are not production
credentials.

| Variable | Default/required behavior | Owner |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000`; browser-visible API | Frontend |
| `APP_ENV` | `development`; disables API docs in production | API/worker |
| `APP_LOG_LEVEL` | `INFO`; structured JSON application logs | API/worker |
| `APP_CORS_ORIGINS` | JSON list of allowed browser origins | API |
| `DATABASE_URL` | Async PostgreSQL URL; local host port `55432` | API/worker |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | Bounded SQL connection pool | API/worker |
| `REDIS_URL` | Celery broker/result transport; local port `56379` | API/worker |
| `S3_ENDPOINT_URL` | S3-compatible endpoint; local MinIO port `59000` | API/worker |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Required S3 credentials; never commit real values | API/worker |
| `S3_BUCKET` / `S3_REGION` | Immutable-source bucket and region | API/worker |
| `MAX_UPLOAD_BYTES` | `52428800` (50 MiB) | API |
| `PIPELINE_VERSION` | `ingestion-v1`; persisted with versions/chunks | Worker |
| `CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS` | `220` / `40`; evaluation hypotheses | Worker |
| `EMBEDDING_PROVIDER` | `deterministic` or `fastembed`; deterministic by default | API/worker |
| `EMBEDDING_MODEL` | Logical FastEmbed model identifier | API/worker |
| `EMBEDDING_SOURCE_REPO` | Exact ONNX source repository | API/worker |
| `EMBEDDING_REVISION` | Required 40-character source commit for FastEmbed | API/worker |
| `EMBEDDING_DIMENSIONS` | `384`; must match database vector dimension | API/worker |
| `ANSWER_PROVIDER` | `deterministic` or `ollama`; deterministic by default | API |
| `ANSWER_MODEL` | Ollama tag such as `qwen2.5:1.5b` | API |
| `ANSWER_MAX_OUTPUT_TOKENS` | `384`; hard bound against runaway generation | API |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | API |
| `RETRIEVAL_DENSE_K` / `RETRIEVAL_LEXICAL_K` | Candidate depths, both `12` | API |
| `RETRIEVAL_FINAL_K` | Fused candidate depth, `6` | API |
| `CONTEXT_TOKEN_BUDGET` | `1800` tokens | API |
| `REQUEST_TIMEOUT_SECONDS` | Provider request timeout, `60` | API |
| `AUTH_COOKIE_SECURE` | `false` locally; must be `true` in staging/production | API |
| `AUTH_SESSION_IDLE_MINUTES` / `AUTH_SESSION_ABSOLUTE_HOURS` | `60` / `168`; both must remain valid | API |
| `AUTH_ARGON2_TIME_COST` / `AUTH_ARGON2_MEMORY_COST_KIB` / `AUTH_ARGON2_PARALLELISM` | Measured defaults `3` / `65536` / `2` | API/CLI |
| `AUTH_LOGIN_ATTEMPT_LIMIT` / `AUTH_LOGIN_WINDOW_SECONDS` | `8` attempts per `900` seconds | API |
| `AUTH_REGISTRATION_ATTEMPT_LIMIT` / `AUTH_REGISTRATION_WINDOW_SECONDS` | `5` attempts per IP and email per `3600` seconds | API |
| `AUTH_MAX_ACTIVE_SESSIONS` | `5`; oldest active sessions are revoked when exceeded | API |
| `QUOTA_DOCUMENTS_PER_USER` | `100` live documents across owned collections | API |
| `QUOTA_QUESTIONS_PER_DAY` | `200` question attempts per authenticated user/day | API |
| `QUOTA_CONCURRENT_GENERATIONS_PER_USER` | `1`; Redis lease with bounded TTL | API |

Changing embedding dimension is a schema event, not a casual environment tweak. Add a migration,
version the pipeline, re-index affected versions, and compare evaluation results.

`APP_CORS_ORIGINS` is an exact JSON allow-list. Wildcards are invalid for credentialed browser
requests. Local HTTP uses `docqa_*_dev` cookies; secure environments use `__Host-` cookies with
`Secure`, `HttpOnly` for the session, `SameSite=Lax`, `Path=/`, and no `Domain` attribute. The
application refuses staging/production startup when secure cookies are disabled.
