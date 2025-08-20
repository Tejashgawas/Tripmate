from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


class ProviderOut(BaseModel):
    id: int
    name: str
    contact_phone: Optional[str]

    class Config:
        from_attributes = True

class RecommendedService(BaseModel):
    id: int
    title: str
    type: str
    price: Optional[float]
    rating: Optional[float]
    provider: ProviderOut
    location: Optional[str]
    is_available: Optional[bool]
    features: Optional[Any]

    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    hotels: List[RecommendedService] = []
    buses: List[RecommendedService] = []
    rentals: List[RecommendedService] = []
    packages: List[RecommendedService] = []

    class Config:
        from_attributes = True

class VoteRequest(BaseModel):
    service_type: str
    service_id: int

class VoteCount(BaseModel):
    service_id: int
    votes: int

class VoteSummaryResponse(BaseModel):
    service_type: str
    counts: List[VoteCount]

class TripSelectionRequest(BaseModel):
    service_type: str
    service_id: int
    notes: Optional[str] = None

class TripSelectionResponse(BaseModel):
    trip_id: int
    service_type: str
    service_id: int
    selected_on: datetime
    notes: Optional[str] = None

class TripRecommendedOption(BaseModel):
    service_id: int
    rank: Optional[int] = None
    votes: int
    service: RecommendedService

class TripRecommendedListResponse(BaseModel):
    trip_id: int
    service_type: str
    options: List[TripRecommendedOption]




class TripSelectedServiceOut(BaseModel):
    id: int
    trip_id: int
    service_id: int
    selected_on: datetime
    custom_notes: Optional[str]
    service: RecommendedService   # nested service details

    class Config:
        from_attributes = True

