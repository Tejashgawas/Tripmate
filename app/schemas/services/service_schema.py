from pydantic import BaseModel, Field,EmailStr
from typing import Optional, List,Any,Literal
from datetime import datetime


#Service Provider Schemas
class ServiceProviderBase(BaseModel):
    name: str
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    location: Optional[str]
    description: Optional[str]

class ServiceProviderCreate(ServiceProviderBase):
    pass

class ServiceProviderResponse(ServiceProviderBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

#Service Schemas

class ServiceBase(BaseModel):
    type: str  # hotel, lodge, rental, bus, etc.
    title: str
    description: Optional[str]
    location: Optional[str]
    price: Optional[float]
    rating: Optional[float] = None  # optional for services without ratings
    features: Optional[dict]  # flexible structure: JSON
    is_available: Optional[bool] = True

class ServiceCreate(ServiceBase):
    pass


class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ServiceUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    location: Optional[str] = None
    price: Optional[float] = None
    features: Optional[dict] = None
    is_available: Optional[bool] = None



# TripSelectedService Schemas

class TripSelectedServiceBase(BaseModel):
    service_id: int
    custom_notes: Optional[str]


class TripSelectedServiceCreate(TripSelectedServiceBase):
    pass


class TripSelectedServiceResponse(TripSelectedServiceBase):
    id: int
    selected_on: datetime
    service: ServiceResponse

    class Config:
        from_attributes = True



class ServiceFilterParams(BaseModel):
    type: Optional[Literal['hotel', 'lodge', 'rental', 'bus', 'activity', 'package']]
    location: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    is_available: Optional[bool] = True