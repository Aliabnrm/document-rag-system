# Sprint 0 — Engineering foundation

## Goal

Create a shared product and architecture contract, then prove that the bilingual frontend can communicate with a versioned backend API.

## Deliverables

- Root-level `frontend/` and `backend/` applications.
- Persian and English landing states with RTL/LTR support.
- Versioned backend API and health endpoint.
- Typed frontend boundary for the health response.
- Local PostgreSQL, Redis, and object-storage services.
- Initial product brief, system architecture, domain vocabulary, and ADRs.
- Automated backend test plus frontend lint/type/test commands.

## Definition of done

- `/fa` and `/en` render with the correct direction and content.
- The UI reports whether the backend is reachable.
- `GET /api/v1/health` returns a documented response.
- Backend tests, linting, and type checks pass.
- Frontend linting, type checks, and tests pass.
- A new contributor can start the project using the README.

## Learning goals

- Understand the difference between a deployable application and a domain module.
- Trace one request from the browser through HTTP routing and an application service.
- Understand why background processing is necessary for document ingestion.
- See how ADRs keep architecture decisions synchronized with code.

## Next sprint

Build the first vertical RAG slice using one known Persian document and one known English document: upload, extract, chunk, embed, retrieve, generate, and cite. Its quality will be measured against a small hand-authored evaluation set before UI breadth is expanded.
