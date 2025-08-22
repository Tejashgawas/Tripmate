from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user.user import UserRole
from app.core.database import get_db
from app.dependencies.auth import require_role
from app.schemas.admin.admin_analytics import AdminAnalyticsResponse
from app.services.admin.admin_analytics import AdminAnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])

@router.get("/", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(db: AsyncSession = Depends(get_db),current_user = Depends(require_role(UserRole.admin))):
    analytics = await AdminAnalyticsService.get_admin_analytics(db)
    return analytics
