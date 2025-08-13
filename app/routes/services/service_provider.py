from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import require_role
from app.models.user.user import User,UserRole
from app.schemas.services.service_schema import ServiceCreate, ServiceUpdate, ServiceResponse
from app.services.service.provider_Service import ServiceProviderService


router = APIRouter(prefix="/me/services", tags=["Provider Services"])

@router.post("", response_model=ServiceResponse)
async def create_service(
    data: ServiceCreate,
    user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    return await ServiceProviderService.create_service(user, data, db)


@router.get("/list", response_model=list[ServiceResponse])
async def list_my_services(
    user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    services = await ServiceProviderService.list_my_services(user, db)
    return services  # ✅ Let FastAPI + Pydantic handle conversion


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    return await ServiceProviderService.update_service(user, service_id, data, db)


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    return await ServiceProviderService.delete_service(user, service_id, db)