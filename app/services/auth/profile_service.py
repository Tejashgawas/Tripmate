from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user.user import User
from app.schemas.user.user import UserOut, UserUpdate
from fastapi import HTTPException, status
from sqlalchemy.future import select
from app.core.security import hash_password

class ProfileService:
    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    async def update_user_profile(user_id: int, update_data: UserUpdate, db: AsyncSession) -> User:
        user = await ProfileService.get_user_by_id(user_id, db)

        update_fields = update_data.dict(exclude_unset=True)
       
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update.")

        if 'password' in update_fields:
            update_fields['hashed_password'] = hash_password(update_fields.pop('password'))


        for key, value in update_fields.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user
