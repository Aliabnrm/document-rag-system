# Local development runbook

## Prerequisites

- Docker Desktop
- Python 3.13 and `uv`
- Node.js 24 and pnpm 11
- Optional: Ollama for real open-weight generation evaluation

## Start from a clean checkout

```bash
cp .env.example .env
docker compose -f infra/compose.yaml up -d --wait

cd backend
uv sync --locked --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

In a second terminal, run the worker and the local recovery scheduler:

```bash
cd backend
uv run celery -A app.entrypoints.worker.celery_app worker --beat --pool=solo --loglevel=INFO
```

In a third terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open `/fa` or `/en` on `http://localhost:3000`. API documentation is at
`http://localhost:8000/docs` in development.

## Verify health

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
docker compose -f infra/compose.yaml ps
```

Liveness means the API process responds. Readiness means PostgreSQL, Redis, and MinIO can serve the
request path. Do not configure a platform to restart the process solely because readiness is red.

## Real local model profile

CI and ordinary local setup use deterministic providers. For measured real-provider work:

```bash
cd backend
uv sync --locked --dev --extra models
ollama pull qwen2.5:1.5b
```

Then set the commented model variables in `.env`. Weights stay in user caches and must never be
copied into the repository.

## Stop and inspect

Stop foreground API, worker, and frontend processes with Ctrl-C, then:

```bash
docker compose -f infra/compose.yaml down
```

Omit `-v` to preserve local database/object data. Deleting volumes is destructive and is never a
normal troubleshooting step.
