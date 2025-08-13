from typing import List,Dict,Any
from fastapi import HTTPException,status,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.itineraries.itinerary import ItineraryDayPreview,ItineraryPreviewResponse,ActivityCreate,ItineraryCreate
from app.schemas.trip.trip_member import TripRole
from app.models.trips.trip_member import TripMember
from app.models.trips.trip_model import Trip
from app.services.itineraries.itinerary import create_itinerary_with_activites
from app.core.logger import logger
from sqlalchemy import select
from app.models.user.user import User
from datetime import timedelta
from app.utils.normalize import normalize_to_dict
from app.utils.ai_itinerary import build_prompt, parse_ai_response
from app.core.llm_client import get_ai_completion
from datetime import date
from app.core.redis_lifecyle import get_cache
from app.services.trips.trip_service import TripService


async def validate_user_membership(
        trip_id:int,user_id:User,db:AsyncSession
):
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == user_id.id
        )
    )

    member = result.scalars().first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not a member of this trip"
        )

# --- PLAN USING AI ---

async def plan_itinerary_ai(
    db: AsyncSession,
    trip_id: int,
    user_id: User,
    ai_generated_data: List[ItineraryCreate]  # assume already generated via OpenAI etc.
):
    await validate_user_membership(trip_id, user_id, db)

    if not ai_generated_data:
        raise HTTPException(status_code=400, detail="No itinerary data received from AI")
    
    for raw_plan in ai_generated_data:
        day_plan = normalize_to_dict(raw_plan)
        itinerary_data = ItineraryCreate(
            trip_id=trip_id,
            day_number=day_plan.get("day_number"),
            title=day_plan.get("title"),
            description=day_plan.get("description"),
            date=day_plan.get("date"),
            activities=day_plan.get("activities", [])
        )
        await create_itinerary_with_activites(db=db, itinerary_data=itinerary_data, current_user=user_id)

    logger.info(f"AI itinerary planned for trip_id={trip_id} by user_id={user_id}")

# --- PLAN USING SERVICE PROVIDER PACKAGE ---
async def plan_itinerary_from_provider(
    db: AsyncSession,
    trip_id: int,
    user_id: User,
    provider_package_data: List[Dict[str, Any]]  # same format as AI itinerary
):
    await validate_user_membership(trip_id, user_id, db)

    if not provider_package_data:
        raise HTTPException(status_code=400, detail="Provider package is empty")

    for raw_plan in provider_package_data:
        day_plan = normalize_to_dict(raw_plan)
        itinerary_data = ItineraryCreate(
            trip_id=trip_id,
            day_number=day_plan.get("day_number"),
            title=day_plan.get("title"),
            description=day_plan.get("description"),
            date=day_plan.get("date"),
            activities=day_plan.get("activities", [])
        )
        await create_itinerary_with_activites(db=db, itinerary_data=itinerary_data, current_user=user_id)

    logger.info(f"Provider itinerary planned for trip_id={trip_id} by user_id={user_id}")

async def get_single_cache():
    # This is a hypothetical way to get a single item from an async generator
    async for cache_item in get_cache():
        return cache_item
    return None

async def generate_ai_itinerary_preview(
    trip_id: int,
    location: str,
    days: int,
    start_date: date,
    db: AsyncSession,
    user: User
) -> List[ItineraryDayPreview]:
    # Ensure user is a member of the trip
    await validate_user_membership(trip_id, user, db)

    # Get cache instance
    cache = await get_single_cache()

    # Create trip service instance with cache
    trip_service = TripService(cache)

    # Get trip details
    trip = await trip_service.get_trip_by_id(db=db, user_id=user.id, trip_id=trip_id)
    if not trip:
        raise ValueError("Trip not found")
    print(trip)



    prompt = build_prompt(location, days, start_date)
    ai_response = get_ai_completion(prompt)

    preview = parse_ai_response(ai_response, start_date)

    return preview