# Document Q&A

A bilingual Persian/English document question-answering product. Users upload documents, ask questions in either language, and receive grounded answers with inspectable citations.

The repository is intentionally organized around two deployable applications at its root:

```text
frontend/   Next.js user interface
backend/    FastAPI API, domain modules, and AI workflow
docs/       Product, architecture, decisions, and learning notes
infra/      Local and production infrastructure definitions
evals/      RAG evaluation datasets and experiments (added with the first RAG slice)
```

## Current milestone

Sprint 2 turns the completed RAG vertical slice into a trusted beta foundation: measured
real-model quality, application-owned email/password authentication, two-user isolation,
resumable conversations, safe deletion, feedback, and quotas. Authentication uses Argon2id and
revocable opaque sessions without OAuth/OIDC or an external identity provider. See
[docs/product/sprint-2.md](docs/product/sprint-2.md).

Repository-wide and subsystem-specific Codex instructions live in layered `AGENTS.md` files. See [docs/engineering/README.md](docs/engineering/README.md).

## Run the full local stack

This walkthrough uses a POSIX shell. Run the clone command from the directory where you want the
checkout; subsequent commands start at the repository root unless a terminal is named. Install
Docker with Compose, Python 3.13+, `uv`, Node.js
24+, pnpm 11+, and Ollama. Allow local model downloads and enough disk and memory for the services;
the measured Qwen 3 model alone occupied 1.89 GB when loaded on an 8 GB Apple M2.

```bash
git clone https://github.com/Aliabnrm/document-rag-system.git
cd document-rag-system
cp .env.example .env
docker compose -f infra/compose.yaml up -d --wait
(cd backend && uv sync --locked --dev --extra models && uv run --extra models alembic upgrade head)
(cd frontend && pnpm install --frozen-lockfile)
```

Docker starts PostgreSQL/pgvector, Redis, and MinIO. The API creates its `documents` bucket in
MinIO at startup. In the copied `.env`, uncomment the real-model profile and set
`ANSWER_MODEL=qwen3:1.7b` (the example already has the required values). Do this **before the first
upload** so the worker and API use the same embedding model for indexed documents and questions.
Start the Ollama desktop app, or run `ollama serve` in a separate terminal, then pull the model:

```bash
ollama pull qwen3:1.7b
ollama list
```

The multilingual embedding weights are fetched at their pinned revision on first use and cached
outside Git. Open three more terminals at the repository root and keep them running:

```bash
# Terminal 1: API
cd backend
uv run --extra models uvicorn app.main:app --reload
```

```bash
# Terminal 2: Celery worker and local dispatch-recovery scheduler
cd backend
uv run --extra models celery -A app.entrypoints.worker.celery_app worker --beat --pool=solo --loglevel=INFO
```

```bash
# Terminal 3: bilingual web application
cd frontend
pnpm dev
```

Check `curl http://localhost:8000/api/v1/ready`, then open
`http://localhost:3000/fa` or `http://localhost:3000/en`. Register an account, create a collection,
upload `evals/fixtures/sprint-2-en-product.pdf`, wait for the document to become ready, and ask
“What is Northstar's internal registration code?” Inspect the answer and its page citation. The
development API documentation is at `http://localhost:8000/docs`; the MinIO console is at
`http://localhost:59001` with the development credentials in `infra/compose.yaml`.

The deterministic providers remain the reproducible CI/default profile. Qwen 3 is a measured local
demonstration candidate, **not an approved beta default**: automated results exist, but independent
human review is pending. See the [evaluation](docs/evaluation/sprint-2.md) and the
[local development runbook](docs/runbooks/local-development.md) for health checks, failure diagnosis,
and shutdown. This setup is for a local demonstration; do not expose its example credentials or
HTTP development configuration to the internet.

Detailed setup, operational recovery, configuration, API events, and evaluation live in:

- [Local development runbook](docs/runbooks/local-development.md)
- [Ingestion worker runbook](docs/runbooks/ingestion-worker.md)
- [Environment reference](docs/reference/environment.md)
- [Sprint 1 API guide](docs/api/sprint-1-api.md)
- [Sprint 2 Auth/product API guide](docs/api/sprint-2-api.md)
- [Account administration CLI](docs/runbooks/auth-cli.md)
- [Session incident runbook](docs/runbooks/session-incident.md)
- [Deletion and retention runbook](docs/runbooks/deletion-retention.md)
- [Quota policy](docs/reference/quota-policy.md)
- [Sprint 1 evaluation](docs/evaluation/sprint-1.md)
- [Sprint 2 generator evaluation](docs/evaluation/sprint-2.md)
- [Persian backend/AI walkthrough](docs/learning/sprint-1-rag-walkthrough-fa.md)
- [Persian Sprint 2 trust/auth walkthrough](docs/learning/sprint-2-trusted-foundation-fa.md)
- [Frontend architecture](docs/engineering/frontend-architecture.md)

## Quality checks

```bash
(cd backend && uv run ruff check . && uv run mypy src && uv run pytest)
(cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build)
docker compose -f infra/compose.yaml config --quiet
git diff --check
```

Architecture decisions are recorded as ADRs under `docs/architecture/decisions` so implementation and documentation evolve together.
