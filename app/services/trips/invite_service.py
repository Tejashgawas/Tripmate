from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from app.models.trips.trip_model import Trip
from app.models.user.user import User
from app.models.trips.trip_invite import TripInvite,InviteStatus
from app.schemas.trip.invite import TripInviteAccept,TripInviteCreate,TripInviteResponse
from fastapi import HTTPException,status
from app.models.trips.trip_member import TripMember
from app.services.trips.email_invite import generate_invite_link,send_invite_email
from datetime import datetime
import secrets
import string

from app.services.trips.trip_member_service import add_member
from app.schemas.trip.trip_member import TripMemberCreate

def generate_invite_code(length: int = 10) -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


async def create_trip_invite(
        db : AsyncSession,
        invite_data:TripInviteCreate,
        current_user : User
        
) -> TripInviteResponse:
    
    #validate the trip exists and user is the owner
    print(invite_data.dict()) 
    result = await db.execute(
        select(Trip).where(
            and_(
                Trip.id == invite_data.trip_id,
                Trip.creator_id == current_user.id
            )
        )
    )

    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or not authorized")
    
    #check for duplicate invite
    existing_invite = await db.execute(
        select(TripInvite).where(
            and_(
                TripInvite.trip_id == invite_data.trip_id,
                TripInvite.invitee_email == invite_data.invitee_email,
                TripInvite.status == InviteStatus.pending  # Only block pending
            )
        )
    )

    if existing_invite.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invite already sent to this email")
    Invite_code = generate_invite_code()
     # 3. Create invite
    new_invite = TripInvite(
        trip_id=invite_data.trip_id,
        inviter_id=current_user.id,
        invitee_email=invite_data.invitee_email,
        invite_code = Invite_code,
        status="pending",
       
    )

    db.add(new_invite)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create invite")

    invite_link = generate_invite_link(Invite_code)
    send_invite_email(invitee_email=invite_data.invitee_email, invite_link=invite_link, trip_name=trip.title)

    return TripInviteResponse(
        id=new_invite.id,
        trip_id=new_invite.trip_id,
        inviter_id=new_invite.inviter_id,
        invitee_email=new_invite.invitee_email,
        status=new_invite.status,
        invite_code=Invite_code,
        trip_code=trip.trip_code or ""
        
    )
    


async def accept_trip_invite(
        db: AsyncSession,
        invite_code: str,
        current_user:User
) -> str:
    #fetch the invite

    result = await db.execute(
        select(TripInvite).where(
            and_(
                TripInvite.invite_code == invite_code,
                TripInvite.status == InviteStatus.pending,


            )
        )

    )

    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")
    
    if invite.invitee_email != current_user.email:
        raise  HTTPException(status_code=403, detail="This invite is not for your email")
    
     # 3. Mark as accepted
    invite.status = InviteStatus.accepted
    invite.accepted_at = datetime.utcnow()

   # ✅ Add user to trip members using service
    trip_member_data = TripMemberCreate(
        trip_id=invite.trip_id,
        user_id=current_user.id,
        role="member"  # default role
    )

    await add_member(db, trip_member_data)
    await db.commit()

    return "Invite accepted successfully."
   

async def get_user_trip_invites(
    db: AsyncSession,
    current_user: User
) -> list[TripInviteResponse]:
    result = await db.execute(
        select(TripInvite)
        .options(joinedload(TripInvite.trip),
                 joinedload(TripInvite.inviter)
                 )
        .where(TripInvite.invitee_email == current_user.email)
    )

    invites = result.scalars().all()
    return [
        TripInviteResponse(
            id=invite.id,
            trip_id=invite.trip_id,
            inviter_id=invite.inviter_id,
            invitee_email=invite.invitee_email,
            status=invite.status,
            invite_code=invite.invite_code,
            trip_code=invite.trip.trip_code if invite.trip else None,
            trip_title=invite.trip.title if invite.trip else None,
            inviter_username=invite.inviter.username if invite.inviter else None
        )
        for invite in invites
    ]

async def get_user_sent_invites(
    db: AsyncSession,
    current_user: User
) -> list[TripInviteResponse]:
    result = await db.execute(
        select(TripInvite)
        .options(joinedload(TripInvite.trip),
                 joinedload(TripInvite.inviter)
                 )
        .join(Trip, TripInvite.trip_id == Trip.id)
        .where(TripInvite.inviter_id == current_user.id)  # <- change here
    )

    invites = result.scalars().all()
    return [
        TripInviteResponse(
            id=invite.id,
            trip_id=invite.trip_id,
            inviter_id=invite.inviter_id,
            invitee_email=invite.invitee_email,
            status=invite.status,
            invite_code=invite.invite_code,
            trip_code=invite.trip.trip_code if invite.trip else None,
            trip_title=invite.trip.title if invite.trip else None,
            inviter_username=invite.inviter.username if invite.inviter else None
        )
        for invite in invites
    ]

async def decline_trip_invite(
    db: AsyncSession,
    invite_code: str,
    current_user: User
) -> str:
    result = await db.execute(
        select(TripInvite).where(
            and_(
                TripInvite.invite_code == invite_code,
                TripInvite.status == InviteStatus.pending
            )
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")

    if invite.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="This invite is not for your email")

    invite.status = InviteStatus.declined
    invite.declined_at = datetime.utcnow()

    await db.commit()
    return "Invite declined successfully."
