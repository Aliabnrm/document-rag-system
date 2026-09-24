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
| `DEVELOPMENT_USER_ID` | Fixed UUID for the pre-auth boundary | API |
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
| `OLLAMA_BASE_URL` | `http://localhost:11434` | API |
| `RETRIEVAL_DENSE_K` / `RETRIEVAL_LEXICAL_K` | Candidate depths, both `12` | API |
| `RETRIEVAL_FINAL_K` | Fused candidate depth, `6` | API |
| `CONTEXT_TOKEN_BUDGET` | `1800` tokens | API |
| `REQUEST_TIMEOUT_SECONDS` | Provider request timeout, `60` | API |

Changing embedding dimension is a schema event, not a casual environment tweak. Add a migration,
version the pipeline, re-index affected versions, and compare evaluation results.
