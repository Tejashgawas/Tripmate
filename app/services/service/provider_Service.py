from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.service.service_provider import Service
from app.schemas.services.service_schema import ServiceCreate, ServiceUpdate
from app.models.user.user import User

from app.services.auth.provider_profile import ProviderProfileService

class ServiceProviderService:

    # @staticmethod
    # async def get_provider(user: User, db: AsyncSession) -> ServiceProvider:
    #     """Fetch the provider profile for the logged-in provider"""
    #     result = await db.execute(
    #         select(ServiceProvider).where(ServiceProvider.user_id == user.id)
    #     )
    #     provider = result.scalar_one_or_none()
    #     if not provider:
    #         raise HTTPException(status_code=404, detail="Provider profile not found")
    #     return provider

    @staticmethod
    async def create_service(
        provider: User,
        data: ServiceCreate,
        db: AsyncSession
    )-> Service:
        
        provider = await ProviderProfileService.get_by_user(provider, db)

        
        new_service = Service(
            provider_id=provider.id,
            title=data.title,
            description=data.description,
            type=data.type,
            location=data.location,
            price=data.price,
            features=data.features,
            is_available=data.is_available
        )

        db.add(new_service)
        await db.commit()
        await db.refresh(new_service)
        return new_service
    
    @staticmethod
    async def list_my_services(user: User, db: AsyncSession) -> list[Service]:
        provider = await ProviderProfileService.get_by_user(user, db)
        result = await db.execute(
            select(Service).where(Service.provider_id == provider.id)
        )
        services = result.scalars().all()
        print("Services from service layer:", services)
        return services

    @staticmethod
    async def update_service(user: User, service_id: int, data: ServiceUpdate, db: AsyncSession) -> Service:
        provider = await ProviderProfileService.get_by_user(user, db)
        result = await db.execute(
            select(Service).where(Service.id == service_id, Service.provider_id == provider.id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        update_fields = data.dict(exclude_unset=True)
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided to update.")

        for key, value in update_fields.items():
            setattr(service, key, value)

        await db.commit()
        await db.refresh(service)
        return service


    @staticmethod
    async def delete_service(user: User, service_id: int, db: AsyncSession):
        provider = await ProviderProfileService.get_by_user(user, db)
        result = await db.execute(
            select(Service).where(Service.id == service_id, Service.provider_id == provider.id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        await db.delete(service)
        await db.commit()
        return {"message": "Service deleted successfully"}
    






