from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.user.user import User
from app.models.service.service_provider import ServiceProvider
from app.models.service.service_provider import Service
from app.models.trips.trip_model import Trip

class AdminAnalyticsService:
    @staticmethod
    async def get_admin_analytics(db: AsyncSession) -> dict:
        # Active users (active in last 30 days or is_active flag = True)
        active_threshold = datetime.utcnow() - timedelta(days=30)

        active_users_query = await db.execute(
            select(func.count()).select_from(User).where(
                User.is_active == True,
                User.created_at >= active_threshold  # using created_at since no last_login
            )
        )
        total_active_users = active_users_query.scalar() or 0

        # Total service providers
        providers_query = await db.execute(
            select(func.count()).select_from(ServiceProvider)
        )
        total_service_providers = providers_query.scalar() or 0

        # Total services
        services_query = await db.execute(
            select(func.count()).select_from(Service)
        )
        total_services = services_query.scalar() or 0

        # Total trips
        trips_query = await db.execute(
            select(func.count()).select_from(Trip)
        )
        total_trips = trips_query.scalar() or 0

        return {
            "total_active_users": total_active_users,
            "total_service_providers": total_service_providers,
            "total_services": total_services,
            "total_trips": total_trips
        }

    @staticmethod
    async def get_new_users_count(session: AsyncSession, days: int = 7) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(func.count()).select_from(User).where(User.created_at >= cutoff_date)
        return await session.scalar(query)

    @staticmethod
    async def get_daily_user_registrations_with_users(session: AsyncSession, days: int = 7):
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                func.date(User.created_at).label("date"),
                User.username,
                User.email
            )
            .where(User.created_at >= cutoff_date)
            .order_by(func.date(User.created_at))
        )

        result = await session.execute(query)
        rows = result.all()  # [(date, username, email), ...]

        # Group by date
        registrations = {}
        for row in rows:
            d, username, email = row
            if d not in registrations:
                registrations[d] = {"count": 0, "users": []}
            registrations[d]["count"] += 1
            registrations[d]["users"].append({"username": username, "email": email})

        return registrations