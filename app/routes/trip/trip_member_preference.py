from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.trip.trip_member_preference import TripMemberPreferenceCreate, TripMemberPreferenceOut
from app.services.trips.trip_member_preference_service import set_member_preference, get_trip_preferences
from app.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user.user import User

router = APIRouter(prefix="/trip-member-preference", tags=["Trip Member Preference"])

@router.post("/trips/{trip_id}/preferences", response_model=TripMemberPreferenceOut)
async def set_preference(trip_id: int, preference: TripMemberPreferenceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await set_member_preference(trip_id, current_user.id, preference, db)

@router.get("/trips/{trip_id}/preferences", response_model=List[TripMemberPreferenceOut])
async def get_preferences(trip_id: int, db: AsyncSession = Depends(get_db)):
    return await get_trip_preferences(trip_id, db)

__all__ = ["router"]
