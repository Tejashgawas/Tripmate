from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user.user import User,UserRole
from app.schemas.user.user import UserCreate,ChooseRoleRequest
from app.core.security import hash_password,verify_password,create_access_token
from fastapi import HTTPException,status
from app.core.security import refresh_token,store_refresh_redis,enforce_refresh_limit,is_refresh_token_valid,revoke_refresh_token,revoke_all_refresh_tokens
from app.core.config import settings
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request, Cookie
from jose import jwt, JWTError
from typing import Optional
from app.core.redis_lifecyle import get_redis_client
from app.utils.Oauth.googleauth import oauth
from fastapi.responses import RedirectResponse
from sqlalchemy import update

async def register_user(user_data:UserCreate,db:AsyncSession):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar():
        raise HTTPException(status_code=400,detail="Email already registered")
    
    if user_data.role == "admin":
        raise HTTPException(status_code=403, detail="Not allowed to register as admin")

    if not user_data.password:
        raise HTTPException(status_code=400, detail="Password is required for registration")

    new_user = User(
        email = user_data.email,
        username = user_data.username,
        hashed_password = hash_password(user_data.password),
        role=user_data.role,
        auth_type = "local"
        )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
    response: Response,
    redis_client
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=401,detail="user not registered.")

    if user.auth_type != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registered with different auth method"
        )
    if not user.hashed_password:
        raise HTTPException(400, "User has no password set")

    if not user or not verify_password(password,user.hashed_password):
        raise HTTPException(status_code=401,detail="Invalid credentials")
    
    token = create_access_token(data={"sub":str(user.id)})

    user_id = str(user.id)
    refreshtoken = await refresh_token(user_id,redis_client)
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
       # Cookie: Access token
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="none",
        domain=settings.COOKIE_DOMAIN,
        path="/"
        )
    
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refreshtoken,
        httponly=True,
        max_age=max_age,
        secure=settings.COOKIE_SECURE,
        samesite="none",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


    return {"role": user.role}


async def refresh_access_token(response: Response,refresh_token: str,redis_client) -> str:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    
    # Verify refresh token is still in Redis (not revoked)
    stored_jti = await redis_client.hget(f"user:{user_id}", "refresh_jti")
    if stored_jti != jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked"
        )
    
    # Generate new access token
    new_access_token = create_access_token({"sub": user_id})
    # Update access_token cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="none",
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )
    return {"message": "Access token refreshed"}


async def logout_user(
    refresh_token: Optional[str],
    all_sessions: bool = False
) -> dict:
    if not refresh_token:
        return {"ok": True}

    try:
        payload = jwt.decode(
            refresh_token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return {"ok": True}

    user_id = str(payload.get("sub"))
    jti = payload.get("jti")

    if not user_id:
        return {"ok": True}

    if all_sessions:
        await revoke_all_refresh_tokens(user_id)
    else:
        if jti:
            await revoke_refresh_token(user_id, jti)

    return {"ok": True,"message":"logout successfull"}


async def handle_google_callback(request, db: AsyncSession, redis_client):
    nonce = request.session.get("nonce")

    if not nonce:
        raise HTTPException(status_code=400, detail="Nonce not found in session")
    
    token = await oauth.google.authorize_access_token(request)

    if not token:
        raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google")

 


    user_info = await oauth.google.parse_id_token(token=token,nonce=nonce)

    

    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid Google user info")
    
    email = user_info.get("email")
    username = user_info.get("name", email.split("@")[0])
    
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google user info")
    
    result = await db.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()
    is_new_user = False

    if not user:
        user = User(
            email=email,
            username=username,
            hashed_password=None,  # No password for OAuth users
            role ="general",
            auth_type="google"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    else:
        if user and  user.auth_type != "google":
            request.session.pop("nonce", None)  
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User registered with different auth method")
        
    
    
    # Generate access token
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = await refresh_token(user.id, redis_client)


    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "user": user,
        "is_new_user": is_new_user

    }


async def update_user_role(user:User, role: ChooseRoleRequest, db: AsyncSession):
    
    if role.role not in UserRole._value2member_map_:
        raise ValueError(f"Invalid role: {role.role}")
    
    if UserRole(role.role) == UserRole.admin:
        raise ValueError("Cannot change role to admin via this endpoint")


    if user.role != role.role:
        await db.execute(
        update(User).where(User.id == user.id).values(role=role.role)
        )
        await db.commit()
        await db.refresh(user)

    return user


