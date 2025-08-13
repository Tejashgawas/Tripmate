from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from app.core.database import get_db
from app.core.redis_lifecyle import get_cache
from app.schemas.itineraries.itinerary import (
    ItineraryCreate, ItineraryResponse, ItineraryUpdate,
    ItineraryPreviewResponse, ItineraryDayPreview
)
from app.models.user.user import User
from app.services.itineraries.itinerary_service import ItineraryService
from app.dependencies.auth import get_current_user
from app.services.itineraries.planner_service import(
    plan_itinerary_ai,
    plan_itinerary_from_provider,
    generate_ai_itinerary_preview
)
from app.core.logger import logger
from datetime import date
from app.schemas.itineraries.itinerary import AIPreviewRequest
from app.utils.structure_ai import structure_itinerary_data
from fastapi import Path


router = APIRouter(prefix="/itinerary", tags=["itinerary"])


async def get_itinerary_service(
    cache=Depends(get_cache)
) -> ItineraryService:
    return ItineraryService(cache)

@router.post("/", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    itinerary_data: ItineraryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    itinerary_service: ItineraryService = Depends(get_itinerary_service)
):
    return await itinerary_service.create_itinerary_with_activities(
        db=db,
        current_user=current_user,
        itinerary_data=itinerary_data
    )

# 🔹 Get all itineraries by trip
@router.get("/trip/{trip_id}", response_model=List[ItineraryResponse])
async def get_itineraries(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    itinerary_service: ItineraryService = Depends(get_itinerary_service)
):
    return await itinerary_service.get_itineraries_by_trip(
        db=db,
        current_user=current_user,
        trip_id=trip_id
    )

# 🔹 Update itinerary
@router.put("/{itinerary_id}", response_model=ItineraryResponse)
async def update_itinerary_route(
    itinerary_id: int,
    itinerary_update: ItineraryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    itinerary_service: ItineraryService = Depends(get_itinerary_service)
):
    return await itinerary_service.update_itinerary(
        db=db,
        current_user=current_user,
        itinerary_id=itinerary_id,
        itinerary_update=itinerary_update
    )

# 🔹 Delete itinerary
@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary_route(
    itinerary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    itinerary_service: ItineraryService = Depends(get_itinerary_service)
):
    await itinerary_service.delete_itinerary(
        db=db,
        current_user=current_user,
        itinerary_id=itinerary_id
    )
    return "deleted successfully"

@router.post("/ai-preview/{trip_id}", response_model=ItineraryPreviewResponse)
async def ai_itinerary_preview(
    ai_preview_data: AIPreviewRequest,
    trip_id: int = Path(..., description="ID of the trip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
   
):
    try:
        preview = await generate_ai_itinerary_preview(
            trip_id=trip_id,
            location=ai_preview_data.location,
            days=ai_preview_data.days,
            start_date =ai_preview_data.start_date,
            db=db,
            user=current_user
        )
        return ItineraryPreviewResponse(preview=preview)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/plan/ai-confirm/{trip_id}", status_code=201)
async def confirm_ai_plan(
    trip_id: int,
    ai_generated_data: List[ItineraryDayPreview],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    structured_data = structure_itinerary_data(ai_generated_data, trip_id)
    try:
        await plan_itinerary_ai(
            db=db,
            trip_id=trip_id,
            user_id=current_user,
            ai_generated_data=structured_data,
        )
        return {"message": "AI itinerary confirmed and saved"}
    except Exception as e:
        logger.error(f"🔥 Error while confirming AI plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to save itinerary")


# 🧑‍💼 PLAN VIA PROVIDER PACKAGE
@router.post("/plan/provider/{trip_id}", status_code=201)
async def plan_itinerary_provider_route(
    trip_id: int,
    provider_package_data: List[ItineraryCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await plan_itinerary_from_provider(
            db=db,
            trip_id=trip_id,
            user_id=current_user,
            provider_package_data=provider_package_data,
        )
        return {"message": "Itinerary planned via provider", "data": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"🔥 Error while confirming AI plan: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")