from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Request, Response
from app.core.config import settings
import secrets

def generate_nonce(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)