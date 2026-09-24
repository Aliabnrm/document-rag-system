# Document Q&A engineering contract

This file is the repository-wide operating agreement for Codex and human contributors. Read it together with the closest nested `AGENTS.md`; instructions closer to the edited code specialize these rules.

## Product promise

Build a trustworthy bilingual Persian/English document Q&A product. A user uploads a document, asks in either language, receives an answer grounded in retrieved evidence, and can inspect every citation. When evidence is insufficient, the product says so plainly.

Optimize for correctness, clarity, maintainability, accessibility, and a strong learning trail. Do not optimize for feature count or architectural novelty.

## Current work

- Active plan: `docs/product/sprint-1.md`.
- Product scope: `docs/product/product-brief.md`.
- Architecture: `docs/architecture/system-overview.md` and accepted ADRs in `docs/architecture/decisions/`.
- Domain vocabulary: `docs/architecture/domain-model.md`.

Before changing a subsystem, read its nearest instructions and the directly relevant plan or ADR. When code and documentation disagree, investigate and reconcile them in the same change.

## Repository boundaries

```text
frontend/   Next.js application and bilingual design system
backend/    FastAPI modular monolith, workers, and AI orchestration
infra/      Reproducible local and deployment infrastructure
evals/      Versioned RAG evaluation data, runners, and reports
docs/       Product, architecture, decisions, runbooks, and learning notes
```

Keep `frontend/` and `backend/` at the repository root. Add a shared package only when at least two real consumers exist and the ownership boundary is clear.

## Delivery method

1. Restate the requested outcome and inspect the affected code, tests, docs, and working tree.
2. Trace the smallest end-to-end vertical slice before adding horizontal infrastructure.
3. Record material architectural choices as ADRs before or with implementation.
4. Implement behavior behind explicit boundaries; avoid speculative abstractions.
5. Verify the success path, failure paths, authorization scope, and bilingual UX.
6. Run proportionate quality checks and inspect the final diff.
7. Update product, architecture, API, runbook, and learning documentation affected by the change.
8. Explain the result to the user in Persian: what changed, why, request/data flow, concepts learned, tradeoffs, verification, and remaining limitations.

Make reasonable reversible decisions and record assumptions. Ask only when a missing choice changes product behavior, data safety, public cost, or architecture materially.

## Engineering principles

- Prefer a modular monolith with strong module boundaries. Introduce another service only after measured operational or ownership pressure.
- Apply separation of concerns, dependency inversion at external boundaries, and cohesive domain models. Do not create interfaces, repositories, or classes without a real substitution or testing need.
- Keep business rules independent from frameworks, databases, queues, storage SDKs, and model SDKs.
- Use explicit names from the domain vocabulary. Avoid `utils`, `helpers`, `manager`, and `service` as catch-all modules.
- Keep files focused and public APIs small. Remove dead code and stale documentation in the same change.
- Validate untrusted data at system boundaries and use typed internal representations after validation.
- Treat timestamps as timezone-aware UTC, identifiers as opaque UUIDs, and persisted state transitions as explicit.
- Never put secrets, credentials, private documents, model weights, generated builds, or local runtime data in Git.
- Preserve existing user changes. Do not perform destructive Git operations.

## AI and RAG invariants

- Document content is untrusted data, never an instruction source.
- Retrieval authorization and collection/document-version scope are applied before search.
- Preserve immutable source text and page metadata for citations; normalize a separate retrieval representation.
- Version extraction, normalization, chunking, embedding, retrieval, prompts, and models so an answer can be reproduced.
- Access embedding, reranking, and generation through application ports. Provider SDKs stay in infrastructure adapters.
- A generated citation may reference only evidence identifiers supplied by the backend, and the backend validates them before persistence or display.
- Insufficient evidence produces an explicit abstention. Never hide hallucination risk behind confident UI copy.
- Do not call a model, chunk strategy, or retrieval method “best” without a versioned evaluation and measured comparison.
- CI uses deterministic fake providers. Real-model evaluation is a separate, reproducible workflow.

## Documentation and learning contract

Documentation is part of the feature, not a follow-up task.

- Keep public repository documentation and code comments in clear English.
- Keep UI copy in both Persian and English through the localization system.
- For every sprint, maintain `docs/product/sprint-N.md` with goal, scope, user flow, risks, and Definition of Done.
- Add or update an ADR when a decision affects architecture, data ownership, security, infrastructure, or provider choice.
- Add learning notes for non-obvious backend and AI flows. Include a plain-language explanation, request/data flow, failure modes, tradeoffs, and glossary.
- At sprint completion, add an English engineering review and a Persian learning walkthrough under `docs/learning/`.
- Keep diagrams small and synchronized with the implementation.

## Quality gates

Run checks relevant to changed code. Before a sprint PR, run the complete suites:

```bash
cd backend && uv run ruff check . && uv run mypy src && uv run pytest
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
docker compose -f infra/compose.yaml config --quiet
git diff --check
```

Add tests for domain rules, state transitions, security boundaries, parsing, retrieval behavior, and public contracts. Prefer behavior tests over tests that repeat implementation. Model-dependent quality belongs in `evals/` with recorded model and pipeline versions.

Do not declare work complete while required checks fail. Report external blockers with the exact failing boundary and evidence.

## Git workflow

- Branch names follow `<type>/<sprint-or-area>-<short-outcome>`, for example `feat/sprint-1-rag-vertical-slice`.
- Use Conventional Commits with one coherent outcome per commit.
- Inspect staged content and ensure generated/private files are ignored before committing.
- Do not commit, push, open a pull request, merge, or rewrite history unless the user explicitly asks.

## Code Review Rules

- Flag any retrieval path that can search outside the authorized collection or document versions.
- Flag citations that are accepted directly from model text without backend validation.
- Flag synchronous extraction, embedding, or model inference on the API event loop.
- Flag schema changes without migrations and worker operations without idempotency behavior.
- Flag user-visible strings that bypass localization or layouts that fail in RTL.
- Flag arbitrary colors, spacing, or component variants that bypass design tokens.
- Flag logs that contain raw document text, user questions, credentials, or sensitive identifiers by default.
- Flag completion claims without tests, evaluation evidence, or synchronized documentation appropriate to the change.
