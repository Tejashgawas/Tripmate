import json
from typing import Any, Optional
import redis.asyncio as redis
from datetime import timedelta

class RedisCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> None:
        """Set value in cache with expiration in seconds (default 1 hour)"""
        await self.redis.set(
            key,
            json.dumps(value, default=str),
            ex=expire
        )

    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    @staticmethod
    def build_key(*args) -> str:
        """Build cache key from arguments"""
        return ":".join(str(arg) for arg in args)
