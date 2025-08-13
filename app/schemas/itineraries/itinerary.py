from pydantic import BaseModel
from datetime import date as dt, datetime
from typing import Optional, List
from datetime import date
from app.schemas.itineraries.activity import ActivityCreate, ActivityResponse,ActivityPreview

class ItineraryCreate(BaseModel):
    trip_id: Optional[int] = None 
    day_number: int
    title: str
    description: Optional[str] = None
    date: Optional[dt] = None
    activities: Optional[List[ActivityCreate]] = []

class ItineraryUpdate(BaseModel):
    title: Optional[str]=None
    description: Optional[str]=None
    date: Optional[dt]=None

class ItineraryDayPreview(BaseModel):
    day_number: int
    title: str
    description: Optional[str] = None
    date: Optional[dt] = None
    activities: Optional[List[ActivityPreview]] = []

class ItineraryPreviewResponse(BaseModel):
    preview: List[ItineraryDayPreview]


class ConfirmAIPlanRequest(BaseModel):
    itinerary: List[ItineraryCreate]

class ItineraryResponse(ItineraryCreate):
    id: int
    created_at: datetime
    activities: List[ActivityResponse] = []

    class Config:
        from_attributes = True

class AIPreviewRequest(BaseModel):
    location: str
    days: int
    start_date: date