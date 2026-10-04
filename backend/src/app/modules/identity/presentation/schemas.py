from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.identity.application.use_cases import CurrentSession


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class CompletePasswordResetRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=1, max_length=1024)


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    idle_expires_at: datetime
    absolute_expires_at: datetime

    @classmethod
    def from_session(cls, current: CurrentSession) -> "CurrentUserResponse":
        return cls(
            id=current.user.id,
            email=current.user.email,
            display_name=current.user.display_name,
            idle_expires_at=current.idle_expires_at,
            absolute_expires_at=current.absolute_expires_at,
        )
