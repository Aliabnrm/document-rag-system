from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecureToken:
    raw: str
    digest: str


class SecureTokenService:
    """Generate 256-bit opaque tokens and persistable SHA-256 digests."""

    def generate(self) -> SecureToken:
        raw = secrets.token_urlsafe(32)
        return SecureToken(raw=raw, digest=self.digest(raw))

    def digest(self, raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def matches(self, raw: str, expected_digest: str) -> bool:
        return secrets.compare_digest(self.digest(raw), expected_digest)
