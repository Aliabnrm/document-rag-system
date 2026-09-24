from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from app.platform.observability import bind_observation


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID


def get_current_user(request: Request) -> CurrentUser:
    """Development identity boundary; replace with verified auth in a later sprint."""
    user = CurrentUser(id=request.app.state.settings.development_user_id)
    bind_observation(user_id=user.id)
    return user
