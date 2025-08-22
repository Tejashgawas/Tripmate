from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import List,Optional

load_dotenv()  # ✅ This makes sure your updated .env is loaded

class Settings(BaseSettings):
    DATABASE_URL:str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20

    # ✅ Add these:
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    FRONTEND_BASE_URL: str

    OPENROUTER_API_KEY: str
    BASE_URL: str

    # Redis settings
    REDIS_URL: str 
    REFRESH_COOKIE_NAME: str 
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Default to 7 days

    # Cookie settings
    COOKIE_SECURE: bool = True  # set True in prod (HTTPS)
    COOKIE_DOMAIN: str = "tripmate-v1.vercel.app" # Optional, can be set to None

    MAX_CONCURRENT_REFRESHES: int = 3  # Default to 3

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    AUTH_SECRET: str

    BOOKING_COM_API_KEY: str
    BOOKING_COM_API_HOST: str
    BOOKING_COM_BASE_URL: str

    PROJECT_NAME: str = "TripMate API"
    PROJECT_VERSION: str = "1.0.0" 
    PROJECT_DESCRIPTION: str = "A comprehensive trip management API"
    # BACKEND_CORS_ORIGINS: List[str] = [
    #     "http://localhost:3000",
    #     "http://127.0.0.1:3000",
    #     "http://localhost:8080", 
    #     "http://127.0.0.1:8080"
    # ]

    PASSWORD_MIN_LENGTH: int = 8
    OTP_TTL_SECONDS: int = 300
    RESET_TOKEN_TTL_SECONDS: int = 900
    APP_NAME: str = "TripMate"
    


    class Config:
        env_file = ".env"
    
    
    
settings = Settings()

