# Infrastructure engineering rules

These rules specialize the repository contract for `infra/` and deployment-related files.

## Reproducibility and ownership

- Local setup must be deterministic from a clean checkout and documented in the root README.
- Pin images and actions to reviewed stable versions; avoid mutable `latest` tags in production-bound definitions.
- Keep state in named volumes and declare health checks for required services.
- Store configuration in environment variables with safe development examples. Never commit real credentials or production endpoints.
- Prefer one understandable local stack over premature Kubernetes or multiple environment frameworks.

## Service boundaries

- PostgreSQL is the source of truth and initial vector/lexical store.
- Redis carries ephemeral queue/runtime data, not authoritative product state.
- S3-compatible storage holds immutable original files; the database holds ownership and metadata.
- API and worker are separate processes from the same backend codebase.
- AI runtimes are replaceable providers and must not be coupled to storage or network topology.

## Reliability and security

- Define liveness, readiness, resource limits, restart behavior, graceful shutdown, and dependency startup behavior explicitly.
- Use least-privilege credentials and separate development defaults from production configuration.
- Do not publish unnecessary ports or place private services on public networks.
- Backups require a documented restore procedure; a backup without a tested restore is incomplete.
- Infrastructure changes must include rollback considerations and preserve existing local data unless deletion is explicitly requested.

## Verification and documentation

Validate Compose changes with:

```bash
docker compose -f infra/compose.yaml config --quiet
```

When adding a service, document why it exists, ownership, ports, persisted data, health signal, required variables, failure effect, and how to inspect it. Update architecture diagrams and operational runbooks in the same change.
