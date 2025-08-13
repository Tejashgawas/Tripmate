from sqlalchemy import Column, Integer, String, ForeignKey, Float, UniqueConstraint
from app.core.database import Base

class TripMemberPreference(Base):
    __tablename__ = "trip_member_preferences"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    budget = Column(Float, nullable=True)
    accommodation_type = Column(String, nullable=True)
    food_preferences = Column(String, nullable=True)
    activity_interests = Column(String, nullable=True)
    pace = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint('trip_id', 'user_id', name='_trip_user_uc'),)
