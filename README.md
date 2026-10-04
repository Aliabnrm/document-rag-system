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

## Local development

Prerequisites: Node.js 24+, pnpm 11+, Python 3.13+, uv, and Docker.

```bash
cp .env.example .env
docker compose -f infra/compose.yaml up -d --wait

cd backend
uv sync --locked --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# In another terminal: worker plus the local dispatch-recovery scheduler
cd backend
uv run celery -A app.entrypoints.worker.celery_app worker --beat --pool=solo --loglevel=INFO

# In another terminal
cd ../frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000/fa` for Persian or `http://localhost:3000/en` for English. The API documentation is at `http://localhost:8000/docs`.

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
cd backend && uv run ruff check . && uv run mypy src && uv run pytest
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
docker compose -f infra/compose.yaml config --quiet
git diff --check
```

Architecture decisions are recorded as ADRs under `docs/architecture/decisions` so implementation and documentation evolve together.
