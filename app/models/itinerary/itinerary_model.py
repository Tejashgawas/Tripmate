from sqlalchemy import Column,Integer,String,ForeignKey,Date,DateTime,Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"))
    day_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=True)

    created_at= Column(DateTime,default=datetime.utcnow())

    activities = relationship("Activity",back_populates="itinerary",cascade="all,delete-orphan")
    trip = relationship("Trip", back_populates="itineraries")

    def to_dict(self):
        """Convert Itinerary instance to dictionary for caching"""
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "day_number": self.day_number,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activities": [activity.to_dict() for activity in self.activities] if self.activities else []
        }

