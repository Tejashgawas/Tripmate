from fastapi import Depends,HTTPException,status,Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt,JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user.user import User
from app.core.database import get_db
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

async def get_current_user(
          request: Request,
          token: str = Depends(oauth2_scheme),
          db:AsyncSession=Depends(get_db)
          ):
     # Try cookie first if header token is missing
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials"
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=ALGORITHM
        )

        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
        print("pass jwt")
    except JWTError:
        raise credentials_exception
    print("enter db")
    stmt = select(User).filter(User.id == user_id)
    result = await db.scalar(stmt)
    if result is None:
        raise credentials_exception
    print(f"exit db and user {result}")
    return result

def require_role(role:str):
    async def role_checker(user:User = Depends(get_current_user)):
        print(f"User Role in Token: {user.role}")
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"only user with {role} role can access this route"
            )
        return user
    return role_checker
