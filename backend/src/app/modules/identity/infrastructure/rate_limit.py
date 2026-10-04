from __future__ import annotations

import hashlib
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.platform.errors import ApplicationError


class RedisRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(
        self,
        *,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        reduced_identifier = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        key = f"rate:{scope}:{reduced_identifier}"
        try:
            value = await self._redis.incr(key)
            if value == 1:
                await self._redis.expire(key, window_seconds)
            return int(value)
        except RedisError as error:
            raise ApplicationError(
                code="authentication_temporarily_unavailable",
                message_key="errors.authentication_temporarily_unavailable",
                status_code=503,
            ) from error


class RedisConcurrencyLimiter:
    """A bounded distributed lease; TTL recovers capacity after process death."""

    _ACQUIRE_SCRIPT = """
local value = redis.call('INCR', KEYS[1])
if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
if value > tonumber(ARGV[1]) then
  redis.call('DECR', KEYS[1])
  return 0
end
return 1
"""
    _RELEASE_SCRIPT = """
local value = tonumber(redis.call('GET', KEYS[1]) or '0')
if value <= 1 then
  redis.call('DEL', KEYS[1])
  return 0
end
return redis.call('DECR', KEYS[1])
"""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(scope: str, identifier: str) -> str:
        reduced_identifier = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        return f"concurrency:{scope}:{reduced_identifier}"

    async def try_acquire(
        self,
        *,
        scope: str,
        identifier: str,
        limit: int,
        lease_seconds: int,
    ) -> bool:
        try:
            result = await cast(
                Awaitable[object],
                self._redis.eval(
                    self._ACQUIRE_SCRIPT,
                    1,
                    self._key(scope, identifier),
                    str(limit),
                    str(lease_seconds),
                ),
            )
            return bool(result)
        except RedisError as error:
            raise ApplicationError(
                code="generation_temporarily_unavailable",
                message_key="errors.generation_temporarily_unavailable",
                status_code=503,
            ) from error

    async def release(self, *, scope: str, identifier: str) -> None:
        try:
            await cast(
                Awaitable[object],
                self._redis.eval(
                    self._RELEASE_SCRIPT,
                    1,
                    self._key(scope, identifier),
                ),
            )
        except RedisError:
            # The bounded TTL is the recovery path when release cannot reach Redis.
            return
