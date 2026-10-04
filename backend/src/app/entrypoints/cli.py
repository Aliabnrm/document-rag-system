from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
from uuid import UUID

from app.core.settings import get_settings
from app.modules.data_lifecycle.infrastructure import SqlAlchemyCleanupRepository
from app.modules.identity.application import (
    CreatePasswordReset,
    RevokeUserSessions,
    SetUserStatus,
)
from app.modules.identity.domain import UserStatus
from app.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from app.platform.database.session import Database
from app.platform.security import SecureTokenService


def main() -> None:
    asyncio.run(run(parse_arguments()))


async def run(arguments: argparse.Namespace) -> None:
    database = Database(get_settings())
    tokens = SecureTokenService()
    try:
        async with database.session_factory() as session, session.begin():
            repository = SqlAlchemyIdentityRepository(session)
            if arguments.command == "create-password-reset":
                created = await CreatePasswordReset(repository, tokens).execute(
                    email=arguments.email,
                    expires_in=parse_duration(arguments.expires_in),
                )
                if created is None:
                    raise SystemExit("No matching account")
                reset_id, raw_token = created
                print(f"Password reset ID: {reset_id}")
                print("Secret reset token (shown once; do not log or store it):")
                print(raw_token)
            elif arguments.command in {"disable-user", "enable-user"}:
                status = (
                    UserStatus.DISABLED
                    if arguments.command == "disable-user"
                    else UserStatus.ACTIVE
                )
                confirm(arguments, f"set this user to {status}")
                changed = await SetUserStatus(repository).execute(
                    email=arguments.email, status=status
                )
                print("User updated" if changed else "No matching account")
            elif arguments.command == "revoke-user-sessions":
                confirm(arguments, "revoke every session for this user")
                changed = await RevokeUserSessions(repository).execute(arguments.email)
                print("Sessions revoked" if changed else "No matching account")
            elif arguments.command == "retry-deletion-cleanup":
                confirm(arguments, "reset automatic retries for this failed deletion cleanup")
                changed = await SqlAlchemyCleanupRepository(session).reschedule_failed(
                    UUID(arguments.id)
                )
                print("Cleanup rescheduled" if changed else "Cleanup is absent or not failed")
    finally:
        await database.dispose()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Document Q&A account administration")
    commands = parser.add_subparsers(dest="command", required=True)
    reset = commands.add_parser("create-password-reset")
    reset.add_argument("--email", required=True)
    reset.add_argument("--expires-in", default="30m")
    for name in ("disable-user", "enable-user", "revoke-user-sessions"):
        command = commands.add_parser(name)
        command.add_argument("--email", required=True)
        command.add_argument("--yes", action="store_true")
    retry_cleanup = commands.add_parser("retry-deletion-cleanup")
    retry_cleanup.add_argument("--id", required=True)
    retry_cleanup.add_argument("--yes", action="store_true")
    return parser.parse_args()


def parse_duration(value: str) -> timedelta:
    if len(value) < 2 or value[-1] not in {"m", "h", "d"}:
        raise SystemExit("Duration must use m, h, or d, for example 30m or 48h")
    try:
        amount = int(value[:-1])
    except ValueError as error:
        raise SystemExit("Duration amount must be an integer") from error
    if amount <= 0:
        raise SystemExit("Duration must be positive")
    return {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }[value[-1]]


def confirm(arguments: argparse.Namespace, action: str) -> None:
    if arguments.yes:
        return
    answer = input(f"Confirm: {action}? Type 'yes': ")
    if answer != "yes":
        raise SystemExit("Cancelled")


if __name__ == "__main__":
    main()
