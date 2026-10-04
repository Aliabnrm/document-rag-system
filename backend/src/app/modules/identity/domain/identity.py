from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class IdentityPolicyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_email(value: str) -> str:
    """Normalize only whitespace and case; never apply provider-specific aliases."""
    normalized = value.strip().casefold()
    if not normalized or len(normalized) > 320 or normalized.count("@") != 1:
        raise IdentityPolicyError("invalid_email")
    local, domain = normalized.split("@", maxsplit=1)
    if not local or not domain or "." not in domain:
        raise IdentityPolicyError("invalid_email")
    return normalized


def validate_password(value: str) -> None:
    """Password policy: length-first, Unicode-friendly, no composition rules."""
    if len(value) < 12:
        raise IdentityPolicyError("password_too_short")
    if len(value) > 1024:
        raise IdentityPolicyError("password_too_long")
    if value.casefold().strip() in {
        "password1234",
        "123456789012",
        "qwerty123456",
        "رمزعبور۱۲۳۴۵۶",
    }:
        raise IdentityPolicyError("password_too_common")
