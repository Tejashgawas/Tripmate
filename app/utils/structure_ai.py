from typing import Any, Dict, List, Optional
from datetime import datetime,time as dt_time
from app.schemas.itineraries.itinerary import ItineraryCreate,ItineraryDayPreview
from app.schemas.itineraries.activity import ActivityCreate
from app.core.logger import logger

def structure_itinerary_data(raw_data: List[ItineraryDayPreview], trip_id: int) -> List[ItineraryCreate]:
    structured = []

    for day in raw_data:
        activities = []
        for act in day.activities or []:
            activity = ActivityCreate(
                time=act.time,
                title=act.title.strip(),
                description=act.description.strip() if act.description else None
            )
            activities.append(activity)

        itinerary = ItineraryCreate(
            trip_id=trip_id,
            day_number=day.day_number,
            title=day.title,
            description=day.description,
            date=day.date,
            activities=activities
        )
        structured.append(itinerary)

    return structured