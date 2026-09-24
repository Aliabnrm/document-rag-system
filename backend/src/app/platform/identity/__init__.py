"""Current-user boundary used until production authentication is introduced."""

from app.platform.identity.current_user import CurrentUser, get_current_user

__all__ = ["CurrentUser", "get_current_user"]
