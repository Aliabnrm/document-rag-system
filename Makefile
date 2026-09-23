.PHONY: infra-up infra-down backend-dev backend-check frontend-dev frontend-check

infra-up:
	docker compose -f infra/compose.yaml up -d

infra-down:
	docker compose -f infra/compose.yaml down

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload

backend-check:
	cd backend && uv run ruff check . && uv run mypy src && uv run pytest

frontend-dev:
	cd frontend && pnpm dev

frontend-check:
	cd frontend && pnpm lint && pnpm typecheck && pnpm test
