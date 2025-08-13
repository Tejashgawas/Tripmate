from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from datetime import time as dt_time


class ActivityCreate(BaseModel):
    time:Optional[dt_time]=None
    title : str
    description: Optional[str] = None

class ActivityPreview(BaseModel):
    time: Optional[dt_time] = None
    title: str
    description: Optional[str] = None


class ActivityResponse(ActivityCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True