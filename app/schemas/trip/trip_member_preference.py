from pydantic import BaseModel
from typing import Optional

class TripMemberPreferenceCreate(BaseModel):
    budget: Optional[float]
    accommodation_type: Optional[str]
    food_preferences: Optional[str]
    activity_interests: Optional[str]
    pace: Optional[str]

class TripMemberPreferenceOut(BaseModel):
    id: int
    trip_id: int
    user_id: int
    budget: Optional[float]
    accommodation_type: Optional[str]
    food_preferences: Optional[str]
    activity_interests: Optional[str]
    pace: Optional[str]

    class Config:
        from_attributes = True
