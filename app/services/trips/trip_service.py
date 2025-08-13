from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException, status
from uuid import uuid4
from app.core.logger import logger
from app.core.cache import RedisCache
from app.models.trips.trip_model import Trip
from app.models.trips.trip_member import TripMember
from app.schemas.trip.trip_member import TripRole
from app.schemas.trip.trip_schema import TripCreate, TripResponse, TripUpdate
from typing import Optional, List
from sqlalchemy.orm import selectinload

class TripService:
    def __init__(self, cache: RedisCache):
        self.cache = cache
        
    async def _invalidate_trip_caches(self, trip_id: int, user_id: Optional[int] = None, trip_code: Optional[str] = None):
        """Invalidate all caches related to a trip"""
        patterns = [f"trips:id:{trip_id}"]
        if user_id:
            patterns.append(f"trips:user:{user_id}:*")
        if trip_code:
            patterns.append(f"trips:code:{trip_code}")
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
        
    async def create_trip(self, db: AsyncSession, trip_data: TripCreate, user_id: int) -> Trip:
        trip_code = str(uuid4()).split("-")[0]
        new_trip = Trip(**trip_data.dict(), creator_id=user_id, trip_code=trip_code)
        db.add(new_trip)
        await db.flush()

        new_member = TripMember(
            user_id=user_id,
            trip_id=new_trip.id,
            role=TripRole.OWNER
        )
        db.add(new_member)

        await db.commit()
        await db.refresh(new_trip)
        
        # Invalidate user's trips cache
        await self._invalidate_trip_caches(new_trip.id, user_id, trip_code)
        
        logger.info(f"Trip created by user {user_id} with trip_code {trip_code}")
        return new_trip

    async def get_user_trip(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> List[Trip]:
        # Try to get from cache
        cache_key = self.cache.build_key("trips", "user", user_id, skip, limit)
        cached_trips = await self.cache.get(cache_key)
        
        if cached_trips:
            logger.info(f"Retrieved {len(cached_trips)} trips for user {user_id} from cache")
            return [Trip(**trip) for trip in cached_trips]

        # Get from database
        result = await db.execute(
            select(Trip)
            .options(selectinload(Trip.members))
            .where(Trip.creator_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        trips = result.scalars().all()

        # Cache for 30 minutes
        await self.cache.set(
            cache_key,
            [trip.to_dict() for trip in trips],
            expire=1800
        )
        
        logger.info(f"Retrieved {len(trips)} trips for user {user_id} from database")
        return trips
    
    async def get_trip_by_id(self, db: AsyncSession, user_id: int, trip_id: int) -> Trip:
        # Try to get from cache
        cache_key = self.cache.build_key("trips", "id", trip_id)
        cached_trip = await self.cache.get(cache_key)
        
        if cached_trip:
            trip = Trip(**cached_trip)
            if trip.creator_id != user_id:
                logger.warning(f"Unauthorized access attempt: ID {trip_id} for user {user_id}")
                raise HTTPException(status_code=404, detail="Trip not Found")
            logger.info(f"Trip ID {trip_id} retrieved from cache")
            return trip

        # Get from database
        result = await db.execute(
            select(Trip)
            .options(selectinload(Trip.members))
            .where(Trip.creator_id == user_id, Trip.id == trip_id)
        )
        trip = result.scalar_one_or_none()

        if not trip:
            logger.warning(f"Trip not found: ID {trip_id} for user {user_id}")
            raise HTTPException(status_code=404, detail="Trip not Found")

        # Cache for 30 minutes
        await self.cache.set(
            cache_key,
            trip.to_dict(),
            expire=1800
        )
        
        logger.info(f"Trip ID {trip_id} retrieved from database")
        return trip

    async def get_trip_by_code(self, db: AsyncSession, trip_code: str) -> Trip:
        # Try to get from cache
        cache_key = self.cache.build_key("trips", "code", trip_code)
        cached_trip = await self.cache.get(cache_key)
        
        if cached_trip:
            logger.info(f"Trip with code {trip_code} retrieved from cache")
            return Trip(**cached_trip)

        # Get from database
        result = await db.execute(
            select(Trip)
            .options(selectinload(Trip.members))
            .where(Trip.trip_code == trip_code)
        )
        trip = result.scalar_one_or_none()

        if not trip:
            logger.warning(f"Trip with code {trip_code} not found")
            raise HTTPException(status_code=404, detail="Trip with code not found")

        # Cache for 30 minutes
        await self.cache.set(
            cache_key,
            trip.to_dict(),
            expire=1800
        )
        
        logger.info(f"Trip retrieved by code {trip_code} from database")
        return trip

    async def update_trip(self, db: AsyncSession, trip_id: int, trip_data: TripUpdate, user_id: int) -> Trip:
        result = await db.execute(
            select(Trip)
            .options(selectinload(Trip.members))
            .where(Trip.id == trip_id, Trip.creator_id == user_id)
        )
        trip = result.scalar_one_or_none()

        if not trip:
            logger.warning(f"Unauthorized update attempt or trip not found: ID {trip_id}, user {user_id}")
            raise HTTPException(status_code=404, detail="Trip not found or unauthorized")

        # Update trip
        update_data = trip_data.dict(exclude_unset=True)

        # Parse dates from strings
        if update_data.get("start_date"):
            update_data["start_date"] = datetime.strptime(update_data["start_date"], "%Y-%m-%d").date()
        if update_data.get("end_date"):
            update_data["end_date"] = datetime.strptime(update_data["end_date"], "%Y-%m-%d").date()

        for key, value in update_data.items():
            setattr(trip, key, value)

        await db.commit()
        await db.refresh(trip)
        
        # Invalidate all related caches
        await self._invalidate_trip_caches(trip_id, user_id, trip.trip_code)
        
        logger.info(f"Trip ID {trip_id} updated by user {user_id}")
        return trip

    async def delete_trip(self, db: AsyncSession, trip_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Trip).where(Trip.id == trip_id, Trip.creator_id == user_id)
        )
        trip = result.scalar_one_or_none()

        if not trip:
            logger.warning(f"Unauthorized delete attempt or trip not found: ID {trip_id}, user {user_id}")
            raise HTTPException(status_code=404, detail="Trip not found or unauthorized")

        trip_code = trip.trip_code
        await db.delete(trip)
        await db.commit()

        # Invalidate all related caches
        await self._invalidate_trip_caches(trip_id, user_id, trip_code)
        
        logger.info(f"Trip ID {trip_id} deleted by user {user_id}")
        return {"msg": "Trip deleted successfully"}
