from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.trips.trip_member_preference import TripMemberPreference
from app.schemas.trip.trip_member_preference import TripMemberPreferenceCreate
from typing import List

async def set_member_preference(trip_id: int, user_id: int, preference_data: TripMemberPreferenceCreate, db: AsyncSession) -> TripMemberPreference:
    # Check if preference exists
    result = await db.execute(
        select(TripMemberPreference).where(
            TripMemberPreference.trip_id == trip_id,
            TripMemberPreference.user_id == user_id,
        )
    )
    pref = result.scalar_one_or_none()

    if pref:
        # Update existing
        for field, value in preference_data.dict(exclude_unset=True).items():
            setattr(pref, field, value)
    else:
        # Create new
        pref = TripMemberPreference(trip_id=trip_id, user_id=user_id, **preference_data.dict())
        db.add(pref)

    await db.commit()
    await db.refresh(pref)
    return pref

async def get_trip_preferences(trip_id: int, db: AsyncSession) -> List[TripMemberPreference]:
    result = await db.execute(
        select(TripMemberPreference).where(TripMemberPreference.trip_id == trip_id)
    )
    return result.scalars().all()
