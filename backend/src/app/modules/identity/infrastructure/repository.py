from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application import AuthenticatedUser, CurrentSession
from app.modules.identity.application.use_cases import LoginRecord
from app.modules.identity.domain import UserStatus
from app.modules.identity.infrastructure.models import (
    PasswordCredentialModel,
    PasswordResetTokenModel,
    SessionModel,
    UserModel,
)


class SqlAlchemyIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(
        self,
        *,
        email: str,
        email_normalized: str,
        display_name: str | None,
        password_hash: str,
        now: datetime,
    ) -> AuthenticatedUser | None:
        user_id = uuid4()
        created_id = await self._session.scalar(
            insert(UserModel)
            .values(
                id=user_id,
                email=email,
                email_normalized=email_normalized,
                display_name=display_name,
                status=UserStatus.ACTIVE,
            )
            .on_conflict_do_nothing(index_elements=[UserModel.email_normalized])
            .returning(UserModel.id)
        )
        if created_id is None:
            return None
        credential = PasswordCredentialModel(
            user_id=created_id,
            password_hash=password_hash,
            password_changed_at=now,
        )
        self._session.add(credential)
        await self._session.flush()
        return AuthenticatedUser(created_id, email, display_name)

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
    ) -> CurrentSession:
        # Serialize session issuance per user so concurrent logins cannot exceed the cap.
        await self._session.scalar(
            select(UserModel.id).where(UserModel.id == user.id).with_for_update()
        )
        model = SessionModel(
            id=uuid4(),
            user_id=user.id,
            token_digest=token_digest,
            csrf_token_digest=csrf_token_digest,
            last_seen_at=now,
            idle_expires_at=idle_expires_at,
            absolute_expires_at=absolute_expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        active_ids = (
            await self._session.scalars(
                select(SessionModel.id)
                .where(
                    SessionModel.user_id == user.id,
                    SessionModel.revoked_at.is_(None),
                    SessionModel.absolute_expires_at > now,
                )
                .order_by(SessionModel.created_at.desc(), SessionModel.id.desc())
            )
        ).all()
        expired_ids = active_ids[max_active_sessions:]
        if expired_ids:
            await self._session.execute(
                update(SessionModel).where(SessionModel.id.in_(expired_ids)).values(revoked_at=now)
            )
        return CurrentSession(
            id=model.id,
            user=user,
            idle_expires_at=idle_expires_at,
            absolute_expires_at=absolute_expires_at,
        )

    async def get_login_record(self, email_normalized: str) -> LoginRecord | None:
        row = (
            await self._session.execute(
                select(UserModel, PasswordCredentialModel)
                .join(PasswordCredentialModel, PasswordCredentialModel.user_id == UserModel.id)
                .where(UserModel.email_normalized == email_normalized)
            )
        ).one_or_none()
        if row is None:
            return None
        user, credential = row
        return LoginRecord(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            password_hash=credential.password_hash,
        )

    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, now: datetime
    ) -> None:
        await self._session.execute(
            update(PasswordCredentialModel)
            .where(PasswordCredentialModel.user_id == user_id)
            .values(password_hash=password_hash, password_changed_at=now, updated_at=now)
        )

    async def resolve_session(
        self, token_digest: str, now: datetime, idle_ttl: timedelta
    ) -> CurrentSession | None:
        row = (
            await self._session.execute(
                select(SessionModel, UserModel)
                .join(UserModel, UserModel.id == SessionModel.user_id)
                .where(
                    SessionModel.token_digest == token_digest,
                    SessionModel.revoked_at.is_(None),
                    SessionModel.idle_expires_at > now,
                    SessionModel.absolute_expires_at > now,
                    UserModel.status == UserStatus.ACTIVE,
                )
            )
        ).one_or_none()
        if row is None:
            return None
        session, user = row
        if session.last_seen_at <= now - timedelta(minutes=5):
            session.last_seen_at = now
            session.idle_expires_at = min(
                session.absolute_expires_at,
                now + idle_ttl,
            )
        return CurrentSession(
            id=session.id,
            user=AuthenticatedUser(user.id, user.email, user.display_name),
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
        )

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id, SessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_session_by_digest(self, token_digest: str, now: datetime) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(
                SessionModel.token_digest == token_digest,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def revoke_all_sessions(self, user_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_other_sessions(
        self, *, user_id: UUID, current_session_id: UUID, now: datetime
    ) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.id != current_session_id,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def create_password_reset(
        self, *, email_normalized: str, token_digest: str, expires_at: datetime
    ) -> UUID | None:
        user_id = await self._session.scalar(
            select(UserModel.id).where(UserModel.email_normalized == email_normalized)
        )
        if user_id is None:
            return None
        model = PasswordResetTokenModel(
            id=uuid4(),
            user_id=user_id,
            token_digest=token_digest,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def consume_password_reset(
        self, *, token_digest: str, password_hash: str, now: datetime
    ) -> AuthenticatedUser | None:
        row = (
            await self._session.execute(
                select(PasswordResetTokenModel, UserModel)
                .join(UserModel, UserModel.id == PasswordResetTokenModel.user_id)
                .where(PasswordResetTokenModel.token_digest == token_digest)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        reset, user = row
        if reset.consumed_at is not None or reset.revoked_at is not None or reset.expires_at <= now:
            return None
        await self.update_password_hash(user_id=user.id, password_hash=password_hash, now=now)
        await self.revoke_all_sessions(user.id, now)
        reset.consumed_at = now
        return AuthenticatedUser(user.id, user.email, user.display_name)

    async def set_user_status(
        self, *, email_normalized: str, status: UserStatus, now: datetime
    ) -> UUID | None:
        user_id = await self._session.scalar(
            select(UserModel.id).where(UserModel.email_normalized == email_normalized)
        )
        if user_id is None:
            return None
        await self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(status=status, updated_at=now)
        )
        if status == UserStatus.DISABLED:
            await self.revoke_all_sessions(user_id, now)
        return user_id

    async def revoke_user_sessions(self, *, email_normalized: str, now: datetime) -> bool:
        user_id = await self._session.scalar(
            select(UserModel.id).where(UserModel.email_normalized == email_normalized)
        )
        if user_id is None:
            return False
        await self.revoke_all_sessions(user_id, now)
        return True
