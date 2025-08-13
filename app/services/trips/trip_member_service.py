from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException,status
from datetime import datetime
from sqlalchemy.orm import selectinload
from app.models.trips.trip_member import TripMember
from app.schemas.trip.trip_member import TripMemberCreate,TripMemberResponse,TripMemberOut
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