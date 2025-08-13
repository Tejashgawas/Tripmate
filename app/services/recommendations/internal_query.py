from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Service, ServiceProvider, Trip
from typing import List
from app.core.logger import logger
import json

async def get_services_for_trip(
    session: AsyncSession,
    trip: Trip,
    budget: float = None,
    accommodation_type: str = None,
    food_preferences: str = None,
    activity_interests: str = None,
    pace: str = None,
    budget_min: float = None,
    budget_max: float = None
) -> List[Service]:
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    # Use aggregated budget if provided, else trip.budget
    effective_budget = budget if budget is not None else trip.budget
    if effective_budget <= 0:
        raise HTTPException(status_code=400, detail="Trip budget must be greater than zero.")

    try:
        filters = [
            Service.location.ilike(f"%{trip.location}%"),
            Service.is_available == True
        ]
        # Use budget range if provided
        if budget_min is not None and budget_max is not None:
            filters.append(Service.price >= budget_min)
            filters.append(Service.price <= budget_max)
        else:
            filters.append(Service.price <= effective_budget * 1.1)
        if accommodation_type:
            filters.append(Service.type.ilike(f"%{accommodation_type}%"))
        # You can add more filters for food_preferences, activity_interests, pace if your Service model supports them

        stmt = (
            select(Service)
            .options(joinedload(Service.provider))
            .join(ServiceProvider)
            .where(*filters)
            .order_by(Service.price.asc())
        )

        result = await session.execute(stmt)
        services = result.scalars().all()

        if services:
            logger.info(f"🔍 [Internal Query] Found {len(services)} services matching trip filters:")
        else:
            logger.warning("⚠️ [Internal Query] No services matched the filters for this trip.")

        return services

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching services: {str(e)}")