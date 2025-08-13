from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user,require_role
from app.core.database import get_db

from app.models.user.user import User,UserRole
from app.schemas.user.user import UserUpdate,UserOut, ProviderProfileCreate, ProviderProfileResponse
from app.services.auth.provider_profile import ProviderProfileService

from app.services.auth.profile_service import ProfileService

router = APIRouter(prefix="/me", tags=["Profile"])


@router.get("/", response_model=UserOut)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await ProfileService.get_user_by_id(current_user.id, db)


@router.put("/", response_model=UserOut)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await ProfileService.update_user_profile(current_user.id, data, db)


@router.post("/provider-profile", response_model=ProviderProfileResponse)
async def setup_profile(
    data: ProviderProfileCreate,
    user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    
    return await ProviderProfileService.create_or_update(user, data, db)

@router.get("/get-provider", response_model=ProviderProfileResponse)
async def get_my_provider_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.provider))
):
    return await ProviderProfileService.get_by_user(user, db)
