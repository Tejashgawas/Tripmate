from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user.user import UserRole
from app.core.database import get_db
from app.dependencies.auth import require_role
from app.schemas.admin.admin_analytics import AdminAnalyticsResponse, NewUsersCountResponse,DailyUserRegistrationsResponse,DailyUserRegistration
from app.services.admin.admin_analytics import AdminAnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])

@router.get("/", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(db: AsyncSession = Depends(get_db),current_user = Depends(require_role(UserRole.admin))):
    analytics = await AdminAnalyticsService.get_admin_analytics(db)
    return analytics

@router.get("/new-users", response_model=NewUsersCountResponse)
async def new_users_count(days: int = 7, db: AsyncSession = Depends(get_db)):
    total = await AdminAnalyticsService.get_new_users_count(db, days)
    return NewUsersCountResponse(days=days, total=total)


@router.get("/daily-registrations", response_model=DailyUserRegistrationsResponse)
async def daily_registrations(days: int = 7, db: AsyncSession = Depends(get_db)):
    rows = await AdminAnalyticsService.get_daily_user_registrations(db, days)
    registrations = [DailyUserRegistration(date=row.date, count=row.count) for row in rows]
    return DailyUserRegistrationsResponse(days=days, registrations=registrations)