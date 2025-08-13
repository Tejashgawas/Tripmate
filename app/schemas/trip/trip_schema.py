from pydantic import BaseModel,Field
from typing import Literal,Optional
from datetime import date

class TripBase(BaseModel):
    title : str
    start_date : date
    end_date: date
    location: str
    budget: int
    trip_type: Literal["leisure", "adventure", "workation", "pilgrimage", "cultural", "other"]

class TripCreate(TripBase):
    pass

class TripResponse(TripBase):
    id: int
    trip_code: str
    creator_id: int

    class Config:
        from_attributes = True

class TripUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    trip_type: Optional[str] = None