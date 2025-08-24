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
from app.core.cache import RedisCache
from sqlalchemy.exc import IntegrityError



async def register_user(user_data:UserCreate,db:AsyncSession):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar():
        raise HTTPException(status_code=400,detail="Email already registered")
    
    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar():
        raise HTTPException(status_code=400, detail="Username already taken")

    
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
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        # Fallback in case of race condition between the two queries above
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email or username already exists")

    return new_user


async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
    redis_client
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not registered.")

    if user.auth_type != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registered with different auth method"
        )
    
    if not user.hashed_password:
        raise HTTPException(400, "User has no password set")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = await refresh_token(str(user.id), redis_client)

    # Return tokens instead of setting cookies
    return {
        "access_token": token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "role": user.role
    }


async def refresh_access_token(refresh_token: str, redis_client) -> dict:
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
    exists = await redis_client.exists(f"refresh:{user_id}:{jti}")
    if not exists:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    
    # Generate new access token
    new_access_token = create_access_token({"sub": user_id})
    
    # Return tokens instead of setting cookies
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,  # Keep same refresh token
        "token_type": "bearer"
    }

async def logout_user(
    refresh_token: Optional[str],
    all_sessions: bool = False
) -> dict:
    # Same logic, just doesn't need to clear cookies
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

    return {"ok": True, "message": "Logout successful"}


async def handle_google_callback(request, db: AsyncSession, cache: RedisCache, redis_client):
    token = await oauth.google.authorize_access_token(request)
    print("Token response:", token)
    nonce = request.session.get("nonce")
    print(f"nonce inside handle:{nonce}")

    if not token:
        raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google")

    # Parse ID token (contains user info + nonce)
    claims = await oauth.google.parse_id_token(token, nonce=nonce)
    print("Token response:", token.keys())
    received_nonce = claims.get("nonce")

    if not received_nonce:
        raise HTTPException(status_code=400, detail="Nonce missing from token")

    # Validate nonce from Redis
    stored_nonce = await redis_client.get(f"google_nonce:{received_nonce}")
    if not stored_nonce:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    # Once used, delete nonce to prevent replay attacks
    await redis_client.delete(f"google_nonce:{received_nonce}")

    email = claims.get("email")
    username = claims.get("name", email.split("@")[0])

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google user info")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    is_new_user = False

    if not user:
        user = User(
            email=email,
            username=username,
            hashed_password=None,
            role="general",
            auth_type="google"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    else:
        if user.auth_type != "google":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User registered with different auth method")

    # Generate tokens
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


