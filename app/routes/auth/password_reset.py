from app.core.redis_lifecyle import get_cache
from app.core.cache import RedisCache
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db # your existing DB dependency
from app.schemas.auth.password_reset import (
ForgotPasswordRequest, VerifyOtpRequest, ResetPasswordRequest,
MessageResponse, ResetTokenResponse,
)
from app.services.auth.password_reset_service import (
request_password_reset, verify_otp_issue_token,
reset_password_with_token,
)
router = APIRouter(prefix="/auth", tags=["auth-password-reset"])
  

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db), cache: RedisCache = Depends(get_cache)):
    await request_password_reset(db, cache, payload.email)
    return MessageResponse(message="If this email exists, an OTP has been sent.")

@router.post("/verify-otp", response_model=ResetTokenResponse)
async def verify_otp(payload: VerifyOtpRequest, cache: RedisCache = Depends(get_cache)):
    token = await verify_otp_issue_token(cache, payload.email, payload.otp)
    return ResetTokenResponse(reset_token=token)

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db), cache: RedisCache = Depends(get_cache)):
    await reset_password_with_token(db, cache, payload.reset_token, payload.new_password)
    return MessageResponse(message="Password reset successful. Please log in.")