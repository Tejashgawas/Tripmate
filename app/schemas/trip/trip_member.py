from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import List
from app.models.trips.trip_model import TripTypeEnum
from datetime import date

# Enum for member roles
class TripRole(str, Enum):
    MEMBER = "member"
    OWNER = "owner"
    COHOST = "cohost"

# Shared base schema for creation
class TripMemberBase(BaseModel):
    trip_id: int
    user_id: int

# For creating a trip member
class TripMemberCreate(TripMemberBase):
    role: TripRole = TripRole.MEMBER

# ✅ Nested user schema for response
class TripMemberUser(BaseModel):
    id: int
    username: str
    email: str

    model_config = {
        "from_attributes": True
    }

# ✅ Full response schema for a trip member
class TripMemberOut(BaseModel):
    id: int
    trip_id: int
    user_id: int
    user: TripMemberUser
    role: TripRole
    joined_at: datetime

    model_config = {
        "from_attributes": True
    }

# ✅ Final response for multiple members
class TripMemberResponse(BaseModel):
    members: List[TripMemberOut]

    model_config = {
        "from_attributes": True
    }

class CreatorInfo(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class GetTrip(BaseModel):
    id: int
    title: str
    start_date: date
    end_date: date
    location: str
    budget: int
    trip_type: TripTypeEnum
    trip_code: str
    created_at: datetime

    creator: CreatorInfo   # 👈 embed creator info here

    model_config = {"from_attributes": True}


class UserTrip(BaseModel):
    trip: GetTrip
    role: TripRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class UserTripsResponse(BaseModel):
    trips: List[UserTrip]

    model_config = {"from_attributes": True}
