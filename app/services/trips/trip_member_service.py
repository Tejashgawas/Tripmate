from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException,status
from datetime import datetime
from sqlalchemy.orm import selectinload
from app.models.trips.trip_member import TripMember
from app.schemas.trip.trip_member import TripMemberCreate,TripMemberResponse,TripMemberOut,UserTrip,UserTripsResponse,GetTrip,CreatorInfo
from app.models.user.user import User
from app.models.trips.trip_model import Trip
from sqlalchemy.orm import selectinload



async def is_user_already_member(db:AsyncSession,trip_id:int,user_id:int):
    result = await db.execute(select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == user_id
    ))

    return result.scalar_one_or_none() is not None

async def add_member(db:AsyncSession,member_data:TripMemberCreate)->TripMember:
    if await (is_user_already_member(db,member_data.trip_id,member_data.user_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this trip"

        )

    new_member = TripMember(
        trip_id = member_data.trip_id,
        user_id = member_data.user_id,
        role = member_data.role,
        joined_at = datetime.utcnow()
    )

    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return new_member


async def get_trip_members(db: AsyncSession, trip_id: int):
    result = await db.execute(
        select(TripMember).where(TripMember.trip_id == trip_id)
        .options(selectinload(TripMember.user)) 
    )
    
    members = result.scalars().all()
    test = [TripMemberOut.model_validate(m) for m in members]
    print(test)
    return TripMemberResponse(
    members=[TripMemberOut.model_validate(member) for member in members]
    )


async def remove_member(db: AsyncSession, member_id: int,current_user:User):
    result = await db.execute(
        select(TripMember).where(TripMember.id == member_id).options(selectinload(TripMember.trip))
    )
    member = result.scalar_one_or_none()
    trip = member.trip 

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
     # 3. Authorization check
    if member.user_id != current_user.id and trip.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to remove this member")


    await db.delete(member)
    await db.commit()


async def get_user_trips_with_membership(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(
            Trip,
            TripMember.role,
            TripMember.joined_at,
            User.id.label("creator_id"),
            User.username.label("creator_username")
        )
        .select_from(TripMember)
        .join(Trip, Trip.id == TripMember.trip_id)
        .join(User, User.id == Trip.creator_id)
        .where(TripMember.user_id == user_id)
    )

    rows = result.all()
    if not rows:
        raise HTTPException(status_code=404, detail="No trips found for this user")

    return UserTripsResponse(
        trips=[
            UserTrip(
                trip=GetTrip(
                    id=row.Trip.id,
                    title=row.Trip.title,
                    start_date=row.Trip.start_date,
                    end_date=row.Trip.end_date,
                    location=row.Trip.location,
                    budget=row.Trip.budget,
                    trip_type=row.Trip.trip_type,
                    trip_code=row.Trip.trip_code,
                    created_at=row.Trip.created_at,
                    creator=CreatorInfo(
                        id=row.creator_id,
                        username=row.creator_username
                    )
                ),
                role=row.role,
                joined_at=row.joined_at
            )
            for row in rows
        ]
    )
