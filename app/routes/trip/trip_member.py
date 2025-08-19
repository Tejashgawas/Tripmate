from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies.auth import get_current_user
from app.core.database import get_db
from app.schemas.trip.trip_member import TripMemberResponse,UserTripsResponse
from app.services.trips.trip_member_service import get_trip_members,remove_member,get_user_trips_with_membership
from app.models.user.user import User

router = APIRouter(prefix="/trip-member",tags=["Trip Member"])

@router.get("/trip/{trip_id}",response_model=TripMemberResponse)
async def list_trip_members(
    trip_id:int,
    db:AsyncSession= Depends(get_db),
    current_user :User=Depends(get_current_user)
    ):
    return await get_trip_members(db,trip_id)

@router.delete("/{member_id}")
async def delete_trip_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # In future, add permission checks (only owner/co-host can remove others)
    await remove_member(db, member_id,current_user)
    return {"detail": "Member removed"}


@router.get("/users/{user_id}/trips", response_model=UserTripsResponse)
async def list_user_trips(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # enforce: a user can only see their own trips (or allow admins if you want)
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    return await get_user_trips_with_membership(db, user_id)