from pydantic import BaseModel,EmailStr
from typing import Optional
from datetime import datetime

# 📨 When a user sends an invite
class TripInviteCreate(BaseModel):
    trip_id:int
    invitee_email: EmailStr


# 🧾 What we return to the inviter or admin
class TripInviteResponse(BaseModel):
    id: int
    trip_id: int
    inviter_id: int
    invitee_email: EmailStr
    status: str
    invite_code : str
    trip_code : str

    class Config:
        from_attributes = True


# ✅ For accepting the invite (optional but future-proof)
class TripInviteAccept(BaseModel):
    invite_code: str