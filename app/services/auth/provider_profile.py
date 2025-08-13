from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user.user import User
from app.schemas.user.user import UserOut, UserUpdate
from fastapi import HTTPException, status
from sqlalchemy.future import select
from app.models.service.service_provider import ServiceProvider
from app.schemas.user.user import ProviderProfileCreate


class ProviderProfileService:

    @staticmethod
    async def create_or_update(user: User, data: ProviderProfileCreate, db: AsyncSession) -> ServiceProvider:
        result = await db.execute(
            select(ServiceProvider).where(ServiceProvider.user_id == user.id)
        )
        provider = result.scalar_one_or_none()

        if provider:
            for key, value in data.dict(exclude_unset=True).items():
                setattr(provider, key, value)
        else:
            provider = ServiceProvider(user_id=user.id, **data.dict())
            db.add(provider)

        await db.commit()
        await db.refresh(provider)
        return provider

    @staticmethod
    async def get_by_user(user: User, db: AsyncSession) -> ServiceProvider:
        result = await db.execute(
            select(ServiceProvider).where(ServiceProvider.user_id == user.id)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            raise HTTPException(status_code=404, detail="Provider profile not found")

        return provider
