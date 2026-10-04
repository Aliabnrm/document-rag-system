from __future__ import annotations

from hashlib import sha256

import pytest
from pydantic import ValidationError

from app.core.settings import Settings
from app.modules.identity.domain import IdentityPolicyError, normalize_email, validate_password
from app.platform.security import Argon2PasswordHasher, SecureTokenService


def test_email_normalization_is_conservative() -> None:
    assert normalize_email("  Person+Beta@Example.COM ") == "person+beta@example.com"
    assert normalize_email("first.last@example.com") == "first.last@example.com"


@pytest.mark.parametrize("value", ["", "missing-at.example.com", "a@localhost"])
def test_invalid_email_is_rejected(value: str) -> None:
    with pytest.raises(IdentityPolicyError, match="invalid_email"):
        normalize_email(value)


def test_password_policy_allows_unicode_and_spaces() -> None:
    validate_password("عبارت عبور امن و طولانی")
    with pytest.raises(IdentityPolicyError, match="password_too_short"):
        validate_password("short")
    with pytest.raises(IdentityPolicyError, match="password_too_long"):
        validate_password("x" * 1025)


def test_argon2id_hash_verify_and_rehash_decision() -> None:
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost_kib=8192, parallelism=1)
    encoded = hasher.hash("correct horse battery staple")

    assert encoded.startswith("$argon2id$")
    assert hasher.verify(encoded, "correct horse battery staple") is True
    assert hasher.verify(encoded, "wrong password") is False
    assert hasher.needs_rehash(encoded) is False

    stronger = Argon2PasswordHasher(time_cost=2, memory_cost_kib=8192, parallelism=1)
    assert stronger.needs_rehash(encoded) is True
    stronger.verify_unknown("any supplied password")


def test_secure_tokens_have_256_bits_and_only_digest_is_persistable() -> None:
    service = SecureTokenService()
    token = service.generate()

    assert len(token.raw) >= 43
    assert token.digest == sha256(token.raw.encode()).hexdigest()
    assert service.matches(token.raw, token.digest) is True
    assert service.matches(token.raw + "x", token.digest) is False


def test_secure_environments_reject_insecure_auth_cookie() -> None:
    with pytest.raises(ValidationError, match="secure authentication cookies"):
        Settings(app_env="production", auth_cookie_secure=False)
    settings = Settings(app_env="production", auth_cookie_secure=True)
    assert settings.session_cookie_name.startswith("__Host-")
