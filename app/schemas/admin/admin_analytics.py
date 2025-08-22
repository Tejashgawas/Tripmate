from pydantic import BaseModel

class AdminAnalyticsResponse(BaseModel):
    total_active_users: int
    total_service_providers: int
    total_services: int
    total_trips: int
