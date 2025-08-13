from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, DateTime, func
from app.core.database import Base
from sqlalchemy.orm import relationship
import enum
import uuid

class TripTypeEnum(str,enum.Enum):
    leisure = "leisure"
    adventure = "adventure"
    workation = "workation"
    pilgrimage = "pilgrimage"
    cultural = "cultural"
    other = "other"

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    location = Column(String, nullable=False)
    budget = Column(Integer, nullable=False)
    trip_type = Column(Enum(TripTypeEnum), nullable=False)

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator = relationship("User", back_populates="created_trips")

    trip_code = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4())[:8])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    invites = relationship("TripInvite", back_populates="trip", cascade="all, delete")
    
    members = relationship("TripMember", back_populates="trip", cascade="all, delete")
    itineraries = relationship("Itinerary", back_populates="trip")
    
    def to_dict(self):
        """Convert Trip instance to dictionary for caching"""
        return {
            "id": self.id,
            "title": self.title,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "location": self.location,
            "budget": self.budget,
            "trip_type": self.trip_type.value,
            "creator_id": self.creator_id,
            "trip_code": self.trip_code,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }