from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import List

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
