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

router = APIRouter(prefix="/auth",tags=["Auth"])

@router.post("/register",response_model=UserOut)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
    response: Response = None
):
    new_user = await auth_service.register_user(user, db)
    # Generate access token and refresh token as in login
    from app.core.security import create_access_token, refresh_token, settings
    access_token = create_access_token({"sub": str(new_user.id)})
    refreshtoken = await refresh_token(str(new_user.id), redis_client)
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

   

    if response is not None:
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=refreshtoken,
            httponly=True,
            max_age=max_age,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            domain=settings.COOKIE_DOMAIN,
            path="/",
        )
    return JSONResponse(
        status_code=201,
        content={
            **UserOut.from_orm(new_user).dict()
        }
    )

@router.post("/login")
async def login(
    user: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    return await auth_service.login_user(user.email, user.password, db, response, redis_client)

@router.post("/refresh")
async def refresh_token_route(request: Request, response: Response,redis_client = Depends(get_redis_client)):
    # Read refresh token from HTTP-only cookie
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Call service logic
    new_access_return = await auth_service.refresh_access_token(refresh_token,redis_client)
    return new_access_return


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
        domain=settings.COOKIE_DOMAIN,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
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
async def google_login(
    request: Request
):  # Store nonce in session for later validation
    nonce = generate_nonce()
    request.session["nonce"] = nonce
    print("Nonce generated and stored in session:", nonce)
    redirect_uri = request.url_for('google_callback')
    print("Redirect URI for Google OAuth:", redirect_uri)
    # Redirect to Google's OAuth 2.0 server
    return await oauth.google.authorize_redirect(request, redirect_uri,nonce=nonce)

@router.get("/google/callback")
async def google_callback(
        response: Response,
        request: Request,
        db: AsyncSession = Depends(get_db),
        redis_client = Depends(get_redis_client),
        
    ):

    user_data = await auth_service.handle_google_callback(request, db, redis_client)
    #set access token
    response.set_cookie(
        key="access_token",
        value=user_data["access_token"],
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/"
        )
    # Set refresh cookie on response from returned refresh token
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=user_data["refresh_token"],
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    return {"message":"login through google successful","ok":True,"new_user":user_data["is_new_user"]}


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



