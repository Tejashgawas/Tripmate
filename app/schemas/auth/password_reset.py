from pydantic import BaseModel, EmailStr, Field, validator
from app.core.config import settings

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)

    @validator("new_password")
    def strong_enough(cls, v: str):
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        return v

class MessageResponse(BaseModel):
    message: str

class ResetTokenResponse(BaseModel):
    reset_token: str