# Local development runbook

This runbook expands the [README quick start](../../README.md). Commands use a POSIX shell. Run the
clone command from the directory where you want the checkout; subsequent commands assume a terminal
at the repository root unless another directory is shown. The local profile is
intended for one developer or reviewer, not a public deployment.

## Prerequisites and ports

- Docker with Compose, Python 3.13+, `uv`, Node.js 24+, pnpm 11+, and Ollama.
- Network access for Docker images, Python/Node dependencies, the pinned multilingual embedding
  snapshot, and the Qwen 3 weight download on first setup.
- Enough free disk and memory for the stack. The evaluated `qwen3:1.7b` weight was 1.36 GB and its
  loaded footprint was 1.89 GB on an Apple M2 with 8 GB unified memory. Other hosts may differ.

| Local port | Process | Purpose |
|---|---|---|
| `3000` | Next.js | Persian/English web UI |
| `8000` | FastAPI | API and development OpenAPI docs |
| `11434` | Ollama | Local answer generator |
| `55432` | PostgreSQL + pgvector | Product data and vector search |
| `56379` | Redis | Celery broker and rate/concurrency limits |
| `59000` / `59001` | MinIO | Object API / development console |

Check for port conflicts before startup. Docker Compose starts only PostgreSQL, Redis, and MinIO;
the API, Celery worker with local beat scheduler, frontend, and Ollama run on the host. Docker uses
named volumes so ordinary restarts preserve the local database, Redis state, and source files.

## Prepare a clean checkout

Clone the default branch and start the local dependencies:

```bash
git clone https://github.com/Aliabnrm/document-rag-system.git
cd document-rag-system
cp .env.example .env
docker compose -f infra/compose.yaml up -d --wait
(cd backend && uv sync --locked --dev --extra models && uv run --extra models alembic upgrade head)
(cd frontend && pnpm install --frozen-lockfile)
```

The example credentials in `.env.example` and `infra/compose.yaml` are local-only. The API creates
the `documents` bucket at startup. Do not commit `.env`, model weights, or local documents.

## Select the real-model demonstration profile

The default deterministic providers exercise the workflow for CI and contract tests; they do not
establish natural-language answer quality. To show the real local model path, uncomment these lines
in the copied `.env` before the first upload:

```dotenv
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_SOURCE_REPO=qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q
EMBEDDING_REVISION=faf4aa4225822f3bc6376869cb1164e8e3feedd0
ANSWER_PROVIDER=ollama
ANSWER_MODEL=qwen3:1.7b
ANSWER_MAX_OUTPUT_TOKENS=384
OLLAMA_BASE_URL=http://localhost:11434
```

Start the Ollama desktop app or run `ollama serve` in a separate terminal, then:

```bash
ollama pull qwen3:1.7b
ollama list
curl http://localhost:11434/api/tags
```

The worker downloads the embedding snapshot at the exact `EMBEDDING_REVISION` on first use and
caches it outside the repository. This first ingestion can take longer. `ollama pull` resolves a
tag that may change over time; compare its local digest with the one in
[the evaluation report](../evaluation/sprint-2.md) before claiming that a rerun reproduces the
recorded measurements. Qwen 3 is the leading automated candidate, not an accepted beta default;
independent human review remains open. The real-model profile is a local demonstration and quality
experiment, not a public release configuration.

The ingestion worker and API must use the same embedding configuration. Changing the embedding
model after indexing requires a new document version or re-ingestion; do not silently mix old
document vectors with new query vectors. `uv run --extra models` keeps FastEmbed installed in both
processes when `uv` synchronizes the environment.

## Start processes

Open three terminals at the repository root and keep them running:

```bash
# Terminal 1: API
cd backend
uv run --extra models uvicorn app.main:app --reload
```

```bash
# Terminal 2: worker and local dispatch-recovery scheduler
cd backend
uv run --extra models celery -A app.entrypoints.worker.celery_app worker --beat --pool=solo --loglevel=INFO
```

```bash
# Terminal 3: frontend
cd frontend
pnpm dev
```

Run only one local Celery beat scheduler against this checkout. The worker processes extraction,
normalization, chunking, embedding, and deletion; beat repairs persisted jobs if dispatch to Redis
was interrupted.

## Verify and try one question

From another repository-root terminal:

```bash
docker compose -f infra/compose.yaml ps
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:11434/api/tags
```

`/health` checks the API process. `/ready` checks PostgreSQL, Redis, and the MinIO bucket; it does
not check the Celery worker or Ollama. A successful `/ready` response is therefore only the first
check. Open `http://localhost:3000/en` or `/fa`, register an account, create a collection, upload
`evals/fixtures/sprint-2-en-product.pdf`, and wait for `ready`. Ask “What is Northstar's internal
registration code?” and inspect the answer and page citation. The controlled fixture states
`NSL-4826` on page 1, but a model answer can still fail or abstain; inspect the cited evidence
instead of treating a plausible answer as proof of quality.

The MinIO console is at `http://localhost:59001` with the development credentials in Compose.
Development API docs are at `http://localhost:8000/docs`.

## Diagnose and stop

- `/ready` fails: inspect `docker compose -f infra/compose.yaml ps` and API logs; check the local
  ports and the copied `.env` values. The API must start after the database migration.
- Upload remains queued or fails: inspect the Celery terminal and
  [worker runbook](ingestion-worker.md). The first FastEmbed snapshot download needs network access.
- Question fails while `/ready` passes: check `ollama list`, `curl http://localhost:11434/api/tags`,
  `ANSWER_PROVIDER`, `ANSWER_MODEL`, and the API terminal. `/ready` does not probe the generator.
- Browser requests fail: check that the UI uses `http://localhost:3000` and the API uses
  `http://localhost:8000`; CORS and local authentication cookies expect those origins. See the
  [environment reference](../reference/environment.md).

Stop the API, worker, frontend, and `ollama serve` foreground processes with Ctrl-C, then run:

```bash
docker compose -f infra/compose.yaml down
```

Omit `-v` to preserve local data. Deleting volumes is destructive and is not a normal
troubleshooting step.
