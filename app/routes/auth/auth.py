from fastapi import APIRouter,Depends,Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user.user import UserCreate,UserLogin,UserOut,ChooseRoleRequest,UserRole
from app.services.auth import auth as auth_service
from app.core.database import get_db
from app.models.user.user import User
from app.dependencies.auth import get_current_user,require_role
from fastapi import HTTPException, status, Response, Request
from app.core.config import settings
from typing import Optional
from app.core.redis_lifecyle import get_redis_client
from app.utils.Oauth.googleauth import oauth
import uuid
from app.utils.Oauth.googleauth import generate_nonce
from app.core.cache import RedisCache
from app.core.redis_lifecyle import get_cache
from fastapi.responses import RedirectResponse
router = APIRouter(prefix="/auth",tags=["Auth"])

@router.post("/register",response_model=UserOut)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
    response: Response = None
):
    new_user = await auth_service.register_user(user, db)
    return JSONResponse(
        status_code=201,
        content={
            **UserOut.from_orm(new_user).dict()
        }
    )

@router.post("/login")
async def login_route(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    # Remove response parameter from service call
    tokens = await auth_service.login_user(
        user_data.email, 
        user_data.password, 
        db, 
        redis_client
    )
    return tokens  # Return tokens directly


@router.post("/refresh")
async def refresh_token_route(
    request: Request, 
    response: Response,
    redis_client = Depends(get_redis_client)
):
    # Get refresh token from request body instead of cookie
    body = await request.json()
    refresh_token = body.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Call service logic (modified to return tokens instead of setting cookies)
    tokens = await auth_service.refresh_access_token(refresh_token, redis_client)
    return tokens

@router.post("/logout")
async def logout(
    response: Response,
    refresh_cookie: Optional[str] = Cookie(None),
    all_sessions: Optional[bool] = False
    
):
    result = await auth_service.logout_user(refresh_cookie, all_sessions)
   # Clear refresh cookie
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN,  # must match login
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,  # must match login
        samesite="none"                 # must match login
    )

    # Optional: clear access token as well
    response.delete_cookie(
        key="access_token",
        domain=settings.COOKIE_DOMAIN,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="none"
    )

    return result

@router.get("/health/redis")
async def redis_health_check(
    client = Depends(get_redis_client)
):
    try:
        pong = await client.ping()
        await client.close()
        if pong:
            return {"redis": "healthy"}
        else:
            return {"redis": "unhealthy"}
    except Exception as e:
        return {"redis": "unhealthy", "error": str(e)}
    

@router.get("/google/login")
async def google_login(request: Request,redis_client = Depends(get_redis_client) ):
    nonce = generate_nonce()
    request.session["nonce"] = nonce
    await redis_client.setex(f"google_nonce:{nonce}", 600, "valid")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri, nonce=nonce)

@router.get("/google/callback")
async def google_callback(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
    cache = Depends(get_cache)
):
    user_data = await auth_service.handle_google_callback(request, db, cache, redis_client)
    
    # Return tokens in URL instead of cookies
    redirect_response = RedirectResponse(
        # f"https://tripmate-v1.vercel.app/login?"
        f"http://localhost:3000//login?"
        f"new_user={user_data['is_new_user']}&"
        f"access_token={user_data['access_token']}&"
        f"refresh_token={user_data['refresh_token']}"
    )
    
    return redirect_response


@router.post("/choose-role")
async def choose_role(
    role: ChooseRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    print(f"Current user role: {current_user.role}, Requested role: {UserRole(role.role)}")
    if current_user.role == UserRole(role.role):
        return {"message": "Role already set", "role": current_user.role}
    
    try:
        updated_user = await auth_service.update_user_role(current_user, role, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Role updated", "role": updated_user.role}



