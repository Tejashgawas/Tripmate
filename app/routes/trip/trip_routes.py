from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.trip.trip_schema import TripCreate, TripUpdate, TripResponse
from app.models.user.user import User
from app.core.database import get_db
from app.core.redis_lifecyle import get_cache
from app.dependencies.auth import get_current_user, require_role
from app.services.trips.trip_service import TripService

router = APIRouter(prefix="/trips", tags=['Trips'])

async def get_trip_service(
    cache=Depends(get_cache)
) -> TripService:
    return TripService(cache)

@router.post("/create-trip", response_model=TripResponse)
async def create_trip_route(
    trip: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.create_trip(db, trip, current_user.id)

@router.get("/view-trips", response_model=list[TripResponse])
async def get_my_trips(
    skip: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.get_user_trip(session, current_user.id, skip, limit)

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.get_trip_by_id(session, current_user.id, trip_id)

@router.get("/trip-code/{trip_code}", response_model=TripResponse)
async def get_trip_by_code_route(
    trip_code: str,
    session: AsyncSession = Depends(get_db),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.get_trip_by_code(session, trip_code)

@router.put("/update-trip/{trip_id}", response_model=TripResponse)
async def update_trip_route(
    trip_id: int,
    trip_update: TripUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.update_trip(session, trip_id, trip_update, current_user.id)

@router.delete("/delete-trip/{trip_id}")
async def delete_trip_route(
    trip_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service)
):
    return await trip_service.delete_trip(session, trip_id, current_user.id)
