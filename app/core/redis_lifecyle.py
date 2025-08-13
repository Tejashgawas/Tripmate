# app/core/redis_lifecycle.py
import redis.asyncio as redis
from app.core.config import settings
from app.core.cache import RedisCache
from typing import AsyncGenerator, Optional

_redis_client: Optional[redis.Redis] = None
_cache_instance: Optional[RedisCache] = None


async def init_redis_client() -> redis.Redis:
    """Initialize and return a Redis client (for startup)."""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await _redis_client.ping()
        except redis.ConnectionError:
            raise Exception("Could not connect to Redis server") from None
    
    return _redis_client


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency injection for Redis client."""
    client = await init_redis_client()
    try:
        yield client
    finally:
        pass  # Don't close the global client


async def get_cache() -> AsyncGenerator[RedisCache, None]:
    """FastAPI dependency injection for RedisCache."""
    global _cache_instance
    
    if _cache_instance is None:
        client = await init_redis_client()
        _cache_instance = RedisCache(client)
    
    yield _cache_instance


async def close_redis():
    """Close the Redis connection on application shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
