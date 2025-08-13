from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
import uuid
from app.core.redis_lifecyle import get_redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _now_ts() -> int:
    """Return current UTC timestamp as int."""
    return int(datetime.utcnow().timestamp())

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire,"jti": jti,"type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def refresh_token(user_id: int,redis_client) -> str:
    """Generate refresh token, store in Redis, and enforce refresh limits."""

    jwt_id = str(uuid.uuid4())
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

    payload = {
        "sub": str(user_id),
        "jti": jwt_id,
        "exp": datetime.utcnow() + timedelta(seconds=ttl_seconds),
        "type": "refresh"
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    await store_refresh_redis(redis_client, jwt_id, user_id, ttl_seconds)
    await enforce_refresh_limit(redis_client, user_id, ttl_seconds)

    return token

async def store_refresh_redis(redis_client, jwt_id: str, user_id: int, ttl_seconds: int, meta: dict = None):
    """Store a refresh token in Redis with TTL and track in sorted set."""
    key = f"refresh:{user_id}:{jwt_id}"
    value = {"created_at": str(_now_ts())}
    if meta:
        value.update(meta)

    await redis_client.hset(key, mapping=value)
    await redis_client.expire(key, ttl_seconds)

    zkey = f"refreshs:{user_id}"
    await redis_client.zadd(zkey, {jwt_id: _now_ts()})
    await redis_client.expire(zkey, ttl_seconds)

async def enforce_refresh_limit(redis_client, user_id: int, ttl_seconds: int):
    """Limit the number of active refresh tokens for a user."""
    zkey = f"refreshs:{user_id}"
    max_allowed = settings.MAX_CONCURRENT_REFRESHES

    count = await redis_client.zcard(zkey)
    if count <= max_allowed:
        return

    to_remove = await redis_client.zrange(zkey, 0, count - max_allowed - 1)
    for jwt_id in to_remove:
        await redis_client.delete(f"refresh:{user_id}:{jwt_id}")
        await redis_client.zrem(zkey, jwt_id)

async def revoke_refresh_token(user_id: str, jti: str):
    redis_client = await get_redis_client()
    key = f"refresh:{user_id}:{jti}"
    zkey = f"refreshs:{user_id}"
    await redis_client.delete(key)
    await redis_client.zrem(zkey, jti)

async def revoke_all_refresh_tokens(user_id: str):
    redis_client = await get_redis_client()
    zkey = f"refreshs:{user_id}"
    jtis = await redis_client.zrange(zkey, 0, -1)
    for jti in jtis:
        await redis_client.delete(f"refresh:{user_id}:{jti}")
    await redis_client.delete(zkey)

async def is_refresh_token_valid(user_id: str, jti: str) -> bool:
    redis_client = await get_redis_client()
    key = f"refresh:{user_id}:{jti}"
    exists = await redis_client.exists(key)
    return bool(exists)
