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

Sprint 0 establishes the product contract, architecture boundaries, bilingual foundation, and an end-to-end health check between the UI and API. See [docs/product/sprint-0.md](docs/product/sprint-0.md).

## Local development

Prerequisites: Node.js 24+, pnpm 11+, Python 3.13+, uv, and Docker.

```bash
cp .env.example .env
docker compose -f infra/compose.yaml up -d

cd backend
uv sync --dev
uv run uvicorn app.main:app --reload

cd ../frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000/fa` for Persian or `http://localhost:3000/en` for English. The API documentation is at `http://localhost:8000/docs`.

## Quality checks

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy src
cd frontend && pnpm lint && pnpm typecheck && pnpm test
```

Architecture decisions are recorded as ADRs under `docs/architecture/decisions` so implementation and documentation evolve together.
