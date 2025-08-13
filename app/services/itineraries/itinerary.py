from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.itinerary.itinerary_model import Itinerary
from app.models.itinerary.activity import Activity
from app.schemas.itineraries.itinerary import ItineraryCreate,ItineraryResponse,ItineraryUpdate
from app.schemas.itineraries.activity import ActivityCreate,ActivityResponse
from app.models.user.user import User
from app.models.trips.trip_model import Trip
from app.models.trips.trip_member import TripMember
from datetime import datetime
from typing import List

from fastapi import HTTPException, status

# ✅ Create itinerary with nested activities
async def create_itinerary_with_activites(
        db: AsyncSession,current_user:User,itinerary_data : ItineraryCreate
):
    trip = await db.get(Trip,itinerary_data.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # ✅ Check user is a trip member
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == itinerary_data.trip_id,
            TripMember.user_id == current_user.id
        )
    )
    trip_member = result.scalar_one_or_none()
    if not trip_member:
        raise HTTPException(status_code=403, detail="You are not a member of this trip")

     # 🚀 Create itinerary
    itinerary = Itinerary(
        trip_id=itinerary_data.trip_id,
        day_number=itinerary_data.day_number,
        title=itinerary_data.title,
        description=itinerary_data.description,
        date=itinerary_data.date,
        created_at=datetime.utcnow()
    )

    db.add(itinerary)
    await db.flush()

    for act in itinerary_data.activities or []:
        activity = Activity(
            itinerary_id=itinerary.id,
            time=act.time,
            title=act.title,
            description=act.description,
            created_at=datetime.utcnow()
        )
        db.add(activity)
    
    await db.commit()
    await db.refresh(itinerary)

    return itinerary


async def get_itineraries_by_trip(
    db: AsyncSession, current_user: User, trip_id: int
) -> List[Itinerary]:
    # ✅ Check if user is a member of trip
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied to this trip")

    result = await db.execute(
        select(Itinerary)
        .options(selectinload(Itinerary.activities))
        .where(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.day_number)
    )
    return result.scalars().all()

async def update_itinerary(
    db: AsyncSession, current_user: User, itinerary_id: int,itinerary_update: ItineraryUpdate
):
    result = await db.execute(
        select(Itinerary)
        .options(selectinload(Itinerary.trip),
                 selectinload(Itinerary.activities))
        .where(Itinerary.id == itinerary_id)
    )
    itinerary = result.scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # ✅ Access check
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == itinerary.trip_id,
            TripMember.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not allowed to update this itinerary")

    for field, value in itinerary_update.dict(exclude_unset=True).items():
        setattr(itinerary, field, value)

    await db.commit()
    await db.refresh(itinerary)
    return itinerary

async def delete_itinerary(
    db: AsyncSession, current_user: User, itinerary_id: int
):
    result = await db.execute(
        select(Itinerary)
        .options(selectinload(Itinerary.activities))
        .where(Itinerary.id == itinerary_id)
    )
    itinerary = result.scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # ✅ Access check
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == itinerary.trip_id,
            TripMember.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to delete this itinerary")

    for activity in itinerary.activities:
        await db.delete(activity)

    await db.delete(itinerary)
    await db.commit()
    return itinerary
