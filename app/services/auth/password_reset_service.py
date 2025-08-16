import secrets
import string
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_lifecyle import get_cache
from app.core.cache import RedisCache
from app.core.security import hash_password
from app.models.user.user import User  # adjust import if your model path differs
from app.services.email_service import send_email_text

# Redis key helpers

def _otp_key(email: str) -> str:
    return f"reset_otp:{email.lower()}"

def _tries_key(email: str) -> str:
    return f"reset_otp_tries:{email.lower()}"

def _token_key(token: str) -> str:
    return f"reset_token:{token}"

# Configs
OTP_TTL = settings.OTP_TTL_SECONDS
RESET_TOKEN_TTL = settings.RESET_TOKEN_TTL_SECONDS
MAX_TRIES = 5

# Utils

def _generate_otp(length: int = 6) -> str:
    digits = string.digits
    return ''.join(secrets.choice(digits) for _ in range(length))

def _generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

async def _find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    q = await db.execute(select(User).where(User.email == email))
    return q.scalar_one_or_none()

async def request_password_reset(db: AsyncSession, cache: RedisCache, email: str) -> None:
    user = await _find_user_by_email(db, email)
    if not user:
        return

    otp = _generate_otp()
    await cache.set(_otp_key(email), otp, expire=OTP_TTL)
    await cache.set(_tries_key(email), 0, expire=OTP_TTL)

    subject = f"{settings.APP_NAME} Password Reset Code"
    body = (
        f"Hi {user.username},\n\n"
        f"Your OTP is: {otp}\nExpires in {OTP_TTL // 60} minutes."
    )
    send_email_text(to_email=email, subject=subject, body=body)

async def verify_otp_issue_token(cache: RedisCache, email: str, otp: str) -> str:
    stored = await cache.get(_otp_key(email))
    if not stored:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    tries = int(await cache.get(_tries_key(email)) or 0)
    if otp != stored:
        tries += 1
        await cache.set(_tries_key(email), tries, expire=OTP_TTL)
        if tries >= MAX_TRIES:
            await cache.delete(_otp_key(email))
            await cache.delete(_tries_key(email))
            raise HTTPException(status_code=429, detail="Too many incorrect attempts")
        raise HTTPException(status_code=400, detail="Invalid OTP")

    await cache.delete(_otp_key(email))
    await cache.delete(_tries_key(email))

    token = _generate_reset_token()
    await cache.set(_token_key(token), email.lower(), expire=RESET_TOKEN_TTL)
    return token

async def reset_password_with_token(db: AsyncSession, cache: RedisCache, token: str, new_password: str) -> None:
    email = await cache.get(_token_key(token))
    if not email:
        raise HTTPException(status_code=400, detail="Token invalid or expired")

    user = await _find_user_by_email(db, email)
    if not user:
        await cache.delete(_token_key(token))
        raise HTTPException(status_code=400, detail="Token invalid or expired")

    user.hashed_password = hash_password(new_password)
    await db.commit()

    await cache.delete(_token_key(token))