from fastapi import APIRouter, Depends,Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.trip.invite import TripInviteCreate, TripInviteAccept, TripInviteResponse
from app.services.trips.invite_service import create_trip_invite, accept_trip_invite,get_user_trip_invites,decline_trip_invite
from app.dependencies.auth import get_current_user
from app.models.user.user import User
from app.core.database import get_db

router = APIRouter(prefix="/trip-invite", tags=["Trip Invites"])

@router.post("/", response_model=TripInviteResponse)
async def send_trip_invite(
    invite_data: TripInviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await create_trip_invite(db, invite_data, current_user)

@router.post("/accept-invite")
async def accept_invite(
    payload: TripInviteAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await accept_trip_invite(db, invite_code=payload.invite_code, current_user=current_user)

@router.get("/accept-invite")
async def accept_invite_get(
    invite_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await accept_trip_invite(db, invite_code=invite_code, current_user=current_user)

@router.get("/view-invites", response_model=list[TripInviteResponse])
async def view_user_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_trip_invites(db, current_user)

@router.post("/trip/invite/decline")
async def decline_invite_post(
    payload: TripInviteAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await decline_trip_invite(db, payload.invite_code, current_user)

@router.get("/trip/invite/decline")
async def decline_invite(
    invite_code:  str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await decline_trip_invite(db, invite_code, current_user)
