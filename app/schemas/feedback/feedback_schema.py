from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FeedbackBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    rating: float = Field(..., ge=1, le=5)
    category: str = Field(..., 
                        description="Category of feedback (UI/UX, Services, Trip Planning, etc.)")

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    category: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|reviewed|addressed)$")

class UserResponse(BaseModel):
    username: str
    email: str

    class Config:
        from_attributes = True

class FeedbackResponse(FeedbackBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse]   # 👈 nested user

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    total: int
    feedbacks: list[FeedbackResponse]

    class Config:
        from_attributes = True
