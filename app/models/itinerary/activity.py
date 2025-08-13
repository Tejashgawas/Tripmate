# app/models/activity.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id", ondelete="CASCADE"))
    time = Column(Time, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to itinerary
    itinerary = relationship("Itinerary", back_populates="activities")

    def to_dict(self):
        """Convert Activity instance to dictionary for caching"""
        return {
            "id": self.id,
            "itinerary_id": self.itinerary_id,
            "time": self.time.strftime("%H:%M:%S") if self.time else None,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
