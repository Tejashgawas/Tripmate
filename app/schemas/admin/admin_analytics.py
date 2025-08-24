from pydantic import BaseModel
from datetime import date
from typing import List

class AdminAnalyticsResponse(BaseModel):
    total_active_users: int
    total_service_providers: int
    total_services: int
    total_trips: int


class UserMiniResponse(BaseModel):
    username: str
    email: str

    class Config:
        from_attributes = True

class NewUsersCountResponse(BaseModel):
    days: int
    total: int

class DailyUserRegistration(BaseModel):
    date: date
    count: int
    users: List[UserMiniResponse] 

class DailyUserRegistrationsResponse(BaseModel):
    days: int
    registrations: List[DailyUserRegistration]