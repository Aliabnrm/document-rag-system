# Account administration CLI

Run commands from `backend/` with the same environment and database as the API. Commands call
application use cases; they never issue ad-hoc SQL.

```bash
uv run python -m app.entrypoints.cli create-password-reset --email user@example.com --expires-in 30m
uv run python -m app.entrypoints.cli disable-user --email user@example.com --yes
uv run python -m app.entrypoints.cli enable-user --email user@example.com --yes
uv run python -m app.entrypoints.cli revoke-user-sessions --email user@example.com --yes
uv run python -m app.entrypoints.cli retry-deletion-cleanup --id <cleanup-job-uuid> --yes
```

Reset secrets are printed exactly once. Never paste them into tickets, shell history, logs,
analytics, or source control. Send them through an approved private recovery channel after verifying
the account owner. Destructive account/session commands require interactive confirmation unless an operator
explicitly supplies `--yes` in controlled automation.

Automatic deletion cleanup stops after 10 claimed attempts. After repairing PostgreSQL or object
storage, an operator may reset only a failed cleanup with `retry-deletion-cleanup`; the periodic
reconciler dispatches it. This command never clears the resource tombstone.

If the CLI reports no matching account, verify identity out-of-band. Do not disclose account
existence through a public recovery endpoint.
