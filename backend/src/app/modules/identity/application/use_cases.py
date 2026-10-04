from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.modules.identity.domain import (
    IdentityPolicyError,
    UserStatus,
    normalize_email,
    validate_password,
)
from app.platform.errors import ApplicationError, FieldError


class GeneratedToken(Protocol):
    @property
    def raw(self) -> str: ...

    @property
    def digest(self) -> str: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...
    def verify_unknown(self, password: str) -> None: ...
    def needs_rehash(self, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    def generate(self) -> GeneratedToken: ...
    def digest(self, raw: str) -> str: ...


@dataclass(frozen=True, slots=True)
class LoginRecord:
    user_id: UUID
    email: str
    display_name: str | None
    status: str
    password_hash: str


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    email: str
    display_name: str | None


@dataclass(frozen=True, slots=True)
class CurrentSession:
    id: UUID
    user: AuthenticatedUser
    idle_expires_at: datetime
    absolute_expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedSession:
    current: CurrentSession
    session_token: str
    csrf_token: str


class IdentityRepository(Protocol):
    async def create_user(
        self,
        *,
        email: str,
        email_normalized: str,
        display_name: str | None,
        password_hash: str,
        now: datetime,
    ) -> AuthenticatedUser | None: ...
    async def create_session(
        self,
        *,
        user: AuthenticatedUser,
        token_digest: str,
        csrf_token_digest: str,
        now: datetime,
        idle_expires_at: datetime,
        absolute_expires_at: datetime,
        max_active_sessions: int,
    ) -> CurrentSession: ...
    async def get_login_record(self, email_normalized: str) -> LoginRecord | None: ...
    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, now: datetime
    ) -> None: ...
    async def resolve_session(
        self, token_digest: str, now: datetime, idle_ttl: timedelta
    ) -> CurrentSession | None: ...
    async def revoke_session(self, session_id: UUID, now: datetime) -> None: ...
    async def revoke_all_sessions(self, user_id: UUID, now: datetime) -> None: ...
    async def revoke_other_sessions(
        self, *, user_id: UUID, current_session_id: UUID, now: datetime
    ) -> None: ...
    async def create_password_reset(
        self, *, email_normalized: str, token_digest: str, expires_at: datetime
    ) -> UUID | None: ...
    async def consume_password_reset(
        self, *, token_digest: str, password_hash: str, now: datetime
    ) -> AuthenticatedUser | None: ...
    async def set_user_status(
        self, *, email_normalized: str, status: UserStatus, now: datetime
    ) -> UUID | None: ...
    async def revoke_user_sessions(self, *, email_normalized: str, now: datetime) -> bool: ...


class RateLimiter(Protocol):
    async def hit(self, *, scope: str, identifier: str, limit: int, window_seconds: int) -> int: ...


@dataclass(frozen=True, slots=True)
class RegisterCommand:
    email: str
    password: str
    display_name: str | None
    rate_identifier: str


class Register:
    def __init__(
        self,
        repository: IdentityRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        rate_limiter: RateLimiter,
        *,
        idle_ttl: timedelta,
        absolute_ttl: timedelta,
        limit: int,
        window_seconds: int,
        max_active_sessions: int,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer
        self._rate_limiter = rate_limiter
        self._idle_ttl = idle_ttl
        self._absolute_ttl = absolute_ttl
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_active_sessions = max_active_sessions

    async def execute(self, command: RegisterCommand) -> IssuedSession:
        now = datetime.now(UTC)
        email_normalized = _normalized_email(command.email)
        await _enforce_rate_limit(
            self._rate_limiter,
            scope="registration-ip",
            identifier=command.rate_identifier,
            limit=self._limit,
            window_seconds=self._window_seconds,
        )
        await _enforce_rate_limit(
            self._rate_limiter,
            scope="registration-email",
            identifier=email_normalized,
            limit=self._limit,
            window_seconds=self._window_seconds,
        )
        _valid_password(command.password)
        password_hash = self._password_hasher.hash(command.password)
        user = await self._repository.create_user(
            email=command.email.strip(),
            email_normalized=email_normalized,
            display_name=_display_name(command.display_name),
            password_hash=password_hash,
            now=now,
        )
        if user is None:
            raise _auth_error("registration_unavailable", 409)
        return await _issue_session(
            repository=self._repository,
            token_issuer=self._token_issuer,
            user=user,
            now=now,
            idle_ttl=self._idle_ttl,
            absolute_ttl=self._absolute_ttl,
            max_active_sessions=self._max_active_sessions,
        )


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
    rate_identifier: str


class Login:
    def __init__(
        self,
        repository: IdentityRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        rate_limiter: RateLimiter,
        *,
        idle_ttl: timedelta,
        absolute_ttl: timedelta,
        limit: int,
        window_seconds: int,
        max_active_sessions: int,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer
        self._rate_limiter = rate_limiter
        self._idle_ttl = idle_ttl
        self._absolute_ttl = absolute_ttl
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_active_sessions = max_active_sessions

    async def execute(self, command: LoginCommand) -> IssuedSession:
        try:
            email_normalized = normalize_email(command.email)
        except IdentityPolicyError:
            email_normalized = "invalid@invalid.local"
        attempts = await self._rate_limiter.hit(
            scope="login",
            identifier=f"{command.rate_identifier}:{email_normalized}",
            limit=self._limit,
            window_seconds=self._window_seconds,
        )
        if attempts > self._limit:
            raise ApplicationError(
                code="rate_limited",
                message_key="errors.rate_limited",
                status_code=429,
                context={"retry_after": self._window_seconds},
            )
        record = await self._repository.get_login_record(email_normalized)
        if record is None:
            self._password_hasher.verify_unknown(command.password)
            raise _auth_error("invalid_credentials", 401)
        if not self._password_hasher.verify(record.password_hash, command.password):
            raise _auth_error("invalid_credentials", 401)
        if record.status != UserStatus.ACTIVE:
            raise _auth_error("invalid_credentials", 401)
        now = datetime.now(UTC)
        if self._password_hasher.needs_rehash(record.password_hash):
            await self._repository.update_password_hash(
                user_id=record.user_id,
                password_hash=self._password_hasher.hash(command.password),
                now=now,
            )
        return await _issue_session(
            repository=self._repository,
            token_issuer=self._token_issuer,
            user=AuthenticatedUser(record.user_id, record.email, record.display_name),
            now=now,
            idle_ttl=self._idle_ttl,
            absolute_ttl=self._absolute_ttl,
            max_active_sessions=self._max_active_sessions,
        )


class ResolveSession:
    def __init__(
        self,
        repository: IdentityRepository,
        token_issuer: TokenIssuer,
        *,
        idle_ttl: timedelta,
    ) -> None:
        self._repository = repository
        self._token_issuer = token_issuer
        self._idle_ttl = idle_ttl

    async def execute(self, raw_token: str) -> CurrentSession:
        current = await self._repository.resolve_session(
            self._token_issuer.digest(raw_token), datetime.now(UTC), self._idle_ttl
        )
        if current is None:
            raise _auth_error("authentication_required", 401)
        return current


class LogoutAll:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> None:
        await self._repository.revoke_all_sessions(user_id, datetime.now(UTC))


class ChangePassword:
    def __init__(self, repository: IdentityRepository, password_hasher: PasswordHasher) -> None:
        self._repository = repository
        self._password_hasher = password_hasher

    async def execute(
        self,
        *,
        current: CurrentSession,
        current_password: str,
        new_password: str,
    ) -> None:
        _valid_password(new_password)
        record = await self._repository.get_login_record(current.user.email.casefold())
        if record is None or not self._password_hasher.verify(
            record.password_hash, current_password
        ):
            raise _auth_error("invalid_credentials", 401)
        now = datetime.now(UTC)
        await self._repository.update_password_hash(
            user_id=current.user.id,
            password_hash=self._password_hasher.hash(new_password),
            now=now,
        )
        await self._repository.revoke_other_sessions(
            user_id=current.user.id,
            current_session_id=current.id,
            now=now,
        )


class ResetPassword:
    def __init__(
        self,
        repository: IdentityRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    async def execute(self, *, raw_token: str, new_password: str) -> AuthenticatedUser:
        _valid_password(new_password)
        user = await self._repository.consume_password_reset(
            token_digest=self._token_issuer.digest(raw_token),
            password_hash=self._password_hasher.hash(new_password),
            now=datetime.now(UTC),
        )
        if user is None:
            raise _auth_error("invalid_password_reset", 400)
        return user


class CreatePasswordReset:
    def __init__(self, repository: IdentityRepository, token_issuer: TokenIssuer) -> None:
        self._repository = repository
        self._token_issuer = token_issuer

    async def execute(self, *, email: str, expires_in: timedelta) -> tuple[UUID, str] | None:
        token = self._token_issuer.generate()
        reset_id = await self._repository.create_password_reset(
            email_normalized=_normalized_email(email),
            token_digest=token.digest,
            expires_at=datetime.now(UTC) + expires_in,
        )
        return (reset_id, token.raw) if reset_id is not None else None


class SetUserStatus:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    async def execute(self, *, email: str, status: UserStatus) -> bool:
        user_id = await self._repository.set_user_status(
            email_normalized=_normalized_email(email),
            status=status,
            now=datetime.now(UTC),
        )
        return user_id is not None


class RevokeUserSessions:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    async def execute(self, email: str) -> bool:
        return await self._repository.revoke_user_sessions(
            email_normalized=_normalized_email(email), now=datetime.now(UTC)
        )


async def _issue_session(
    *,
    repository: IdentityRepository,
    token_issuer: TokenIssuer,
    user: AuthenticatedUser,
    now: datetime,
    idle_ttl: timedelta,
    absolute_ttl: timedelta,
    max_active_sessions: int,
) -> IssuedSession:
    session_token = token_issuer.generate()
    csrf_token = token_issuer.generate()
    current = await repository.create_session(
        user=user,
        token_digest=session_token.digest,
        csrf_token_digest=csrf_token.digest,
        now=now,
        idle_expires_at=now + idle_ttl,
        absolute_expires_at=now + absolute_ttl,
        max_active_sessions=max_active_sessions,
    )
    return IssuedSession(current, session_token.raw, csrf_token.raw)


def _normalized_email(value: str) -> str:
    try:
        return normalize_email(value)
    except IdentityPolicyError as error:
        raise ApplicationError(
            code=error.code,
            message_key=f"errors.{error.code}",
            status_code=422,
            field_errors=(FieldError("email", error.code),),
        ) from error


def _valid_password(value: str) -> None:
    try:
        validate_password(value)
    except IdentityPolicyError as error:
        raise ApplicationError(
            code=error.code,
            message_key=f"errors.{error.code}",
            status_code=422,
            field_errors=(FieldError("password", error.code),),
        ) from error


def _display_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) > 120:
        raise ApplicationError(
            code="display_name_too_long",
            message_key="errors.display_name_too_long",
            status_code=422,
            field_errors=(FieldError("display_name", "too_long"),),
        )
    return normalized or None


def _auth_error(code: str, status_code: int) -> ApplicationError:
    return ApplicationError(code=code, message_key=f"errors.{code}", status_code=status_code)


async def _enforce_rate_limit(
    limiter: RateLimiter,
    *,
    scope: str,
    identifier: str,
    limit: int,
    window_seconds: int,
) -> None:
    attempts = await limiter.hit(
        scope=scope,
        identifier=identifier,
        limit=limit,
        window_seconds=window_seconds,
    )
    if attempts > limit:
        raise ApplicationError(
            code="rate_limited",
            message_key="errors.rate_limited",
            status_code=429,
            context={"retry_after": window_seconds},
        )
