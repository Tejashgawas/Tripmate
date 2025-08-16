from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import api_router
from app.core.redis_lifecyle import init_redis_client, close_redis
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    openapi_url=f"/openapi.json"
)

# # Set all CORS enabled origins
# if settings.BACKEND_CORS_ORIGINS:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^(http:\/\/localhost(:\d{1,5})?|http:\/\/127\.0\.0\.1(:\d{1,5})?"
        r"|https:\/\/preview-tripmate-[a-z0-9]+\.vusercontent\.net)$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# required for Authlib OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY,  # reuse your JWT secret
    same_site="lax",
    https_only=settings.COOKIE_SECURE
)


# Include all API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to TripMate API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    await init_redis_client()

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()
