from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import List
from datetime import datetime
from datetime import datetime, date
from app.core.cache import RedisCache
from app.core.logger import logger
from app.models.itinerary.itinerary_model import Itinerary
from app.models.itinerary.activity import Activity
from app.models.user.user import User
from app.models.trips.trip_model import Trip
from app.models.trips.trip_member import TripMember
from app.schemas.itineraries.itinerary import ItineraryCreate, ItineraryResponse, ItineraryUpdate
from app.schemas.itineraries.activity import ActivityResponse
from datetime import datetime, date
class ItineraryService:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def create_itinerary_with_activities(
        self,
        db: AsyncSession,
        current_user: User,
        itinerary_data: ItineraryCreate
    ):
        # Get trip with selectinload to avoid lazy loading
        result = await db.execute(
            select(Trip)
            .where(Trip.id == itinerary_data.trip_id)
        )
        trip = result.scalar_one_or_none()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")
        
        # Check user is a trip member
        result = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == itinerary_data.trip_id,
                TripMember.user_id == current_user.id
            )
        )
        trip_member = result.scalar_one_or_none()
        if not trip_member:
            raise HTTPException(status_code=403, detail="You are not a member of this trip")

        # Create itinerary
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

        # Create empty activities collection without triggering lazy load
        itinerary._sa_instance_state.dict["activities"] = []
        
        # Add activities
        for act in itinerary_data.activities or []:
            activity = Activity(
                itinerary_id=itinerary.id,
                time=act.time,
                title=act.title,
                description=act.description,
                created_at=datetime.utcnow()
            )
            db.add(activity)
            # Just collect activities, we'll set the relationship after commit
            itinerary.activities.append(activity)

        await db.commit()
        # No need for selectinload since we have all activities in memory

        # Invalidate trip itineraries cache
        await self.cache.delete_pattern(f"itineraries:trip:{itinerary_data.trip_id}:*")

        # Convert to response model
        return ItineraryResponse.model_validate(itinerary.to_dict())
    
    async def get_itineraries_by_trip(
        self,
        db: AsyncSession,
        current_user: User,
        trip_id: int
    ) -> List[Itinerary]:
        # Check access
        result = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == trip_id,
                TripMember.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied to this trip")

        # --- Versioned cache integration ---
        version = await self.cache.get(f"itineraries_version:{trip_id}") or 1
        cache_key = self.cache.build_key("itineraries", "trip", trip_id)
        cached_itineraries = await self.cache.get(cache_key, version=version)

        if cached_itineraries:
            logger.info(f"Retrieved itineraries for trip {trip_id} from cache")
            # ... existing processing of cached_itineraries ...
            result_list = []
            for itin in cached_itineraries:
                # convert dates & activities as before
                if isinstance(itin.get('date'), str):
                    itin['date'] = datetime.strptime(itin['date'], "%Y-%m-%d").date()
                if isinstance(itin.get('created_at'), str):
                    itin['created_at'] = datetime.fromisoformat(itin['created_at'])

                activities = []
                for activity in itin.get('activities', []):
                    if isinstance(activity, dict):
                        activity_data = {**activity}
                        if isinstance(activity_data.get('time'), str):
                            try:
                                activity_data['time'] = datetime.strptime(activity_data['time'], "%H:%M:%S").time()
                            except ValueError:
                                pass
                        activities.append(ActivityResponse.model_validate(activity_data))
                itin_data = {**itin, 'activities': activities}
                result_list.append(ItineraryResponse.model_validate(itin_data))
            return result_list

        # --- Database fetch as before ---
        result = await db.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.activities))
            .where(Itinerary.trip_id == trip_id)
            .order_by(Itinerary.day_number)
        )
        itineraries = [itin.to_dict() for itin in result.scalars().all()]

        response_models = []
        for itin in itineraries:
            activities = []
            for activity in itin.get('activities', []):
                if isinstance(activity, dict):
                    activity_data = {**activity}
                    if isinstance(activity_data.get('time'), str):
                        try:
                            activity_data['time'] = datetime.strptime(activity_data['time'], "%H:%M:%S").time()
                        except ValueError:
                            pass
                    activities.append(ActivityResponse.model_validate(activity_data))
            itin_data = {**itin, 'activities': activities}
            if isinstance(itin_data.get('date'), str):
                itin_data['date'] = datetime.strptime(itin_data['date'], "%Y-%m-%d").date()
            if isinstance(itin_data.get('created_at'), str):
                itin_data['created_at'] = datetime.fromisoformat(itin_data['created_at'])
            response_models.append(ItineraryResponse.model_validate(itin_data))

        # --- Cache result using versioned key ---
        await self.cache.set(
            cache_key,
            [itin.model_dump() for itin in response_models],
            expire=900,
            version=version
        )

        return response_models


   

    async def update_itinerary(
        self,
        db: AsyncSession,
        current_user: User,
        itinerary_id: int,
        itinerary_update: ItineraryUpdate
    ):
        result = await db.execute(
            select(Itinerary)
            .options(
                selectinload(Itinerary.trip),
                selectinload(Itinerary.activities)
            )
            .where(Itinerary.id == itinerary_id)
        )
        itinerary = result.scalar_one_or_none()
        
        if not itinerary:
            raise HTTPException(status_code=404, detail="Itinerary not found")

        # Check access
        result = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == itinerary.trip_id,
                TripMember.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to update this itinerary")

         # Update itinerary fields
        update_data = itinerary_update.model_dump(exclude_unset=True)
        if update_data.get('date') and isinstance(update_data['date'], str):
            update_data['date'] = datetime.strptime(update_data['date'], "%Y-%m-%d").date()

        for field, value in update_data.items():
            setattr(itinerary, field, value)

        await db.commit()
        await db.refresh(itinerary)

        trip_id = itinerary.trip_id

        # --- Version bump for cache ---
        current_version = await self.cache.get(f"itineraries_version:{trip_id}") or 1
        new_version = current_version + 1
        await self.cache.set(f"itineraries_version:{trip_id}", new_version, expire=86400)

        # --- Save updated itinerary in cache with new version ---
        cache_key = self.cache.build_key("itineraries", "trip", trip_id)
        await self.cache.set(cache_key, [itinerary.to_dict()], version=new_version, expire=900)

        return ItineraryResponse.model_validate(itinerary.to_dict())
    
    async def delete_itinerary(
        self,
        db: AsyncSession,
        current_user: User,
        itinerary_id: int
    ):
        result = await db.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.activities))
            .where(Itinerary.id == itinerary_id)
        )
        itinerary = result.scalar_one_or_none()
        
        if not itinerary:
            raise HTTPException(status_code=404, detail="Itinerary not found")

        # Access check
        result = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == itinerary.trip_id,
                TripMember.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to delete this itinerary")

        trip_id = itinerary.trip_id

        # Delete activities
        for activity in itinerary.activities:
            await db.delete(activity)
        await db.delete(itinerary)
        await db.commit()

        # --- Version bump for cache ---
        current_version = await self.cache.get(f"itineraries_version:{trip_id}") or 1
        new_version = current_version + 1
        await self.cache.set(f"itineraries_version:{trip_id}", new_version, expire=86400)

        # --- Mark deleted in cache for instant effect ---
        cache_key = self.cache.build_key("itineraries", "trip", trip_id)
        await self.cache.set(cache_key, None, version=new_version, expire=900)

        return ItineraryResponse.model_validate(itinerary.to_dict())
