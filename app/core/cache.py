import json
from typing import Any, Optional
import redis.asyncio as redis
from datetime import timedelta

# class RedisCache:
    # def __init__(self, redis_client: redis.Redis):
    #     self.redis = redis_client

    # async def get(self, key: str) -> Optional[Any]:
    #     """Get value from cache"""
    #     data = await self.redis.get(key)
    #     if data:
    #         return json.loads(data)
    #     return None

    # async def set(self, key: str, value: Any, expire: int = 3600) -> None:
    #     """Set value in cache with expiration in seconds (default 1 hour)"""
    #     await self.redis.set(
    #         key,
    #         json.dumps(value, default=str),
    #         ex=expire
    #     )

    # async def delete(self, key: str) -> None:
    #     """Delete value from cache"""
    #     await self.redis.delete(key)

    # async def delete_pattern(self, pattern: str) -> None:
    #     """Delete all keys matching pattern safely and efficiently"""
    #     cursor = b"0"
    #     while cursor:
    #         cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
    #         if keys:
    #             # Delete in batches to avoid large command overhead
    #             await self.redis.delete(*keys)
    #         if cursor == b'0':
    #             break

    # @staticmethod
    # def build_key(*args) -> str:
    #     """Build cache key from arguments"""
    #     return ":".join(str(arg) for arg in args)
    
class RedisCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, key: str, version: int = None) -> Optional[Any]:
        """Get value from cache, optionally using version"""
        if version is not None:
            key = f"{key}:v{version}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, expire: int = 3600, version: int = None) -> None:
        """Set value in cache with optional version"""
        if version is not None:
            key = f"{key}:v{version}"
        await self.redis.set(
            key,
            json.dumps(value, default=str),
            ex=expire
        )

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern safely and efficiently"""
        cursor = b"0"
        while cursor:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == b'0':
                break
