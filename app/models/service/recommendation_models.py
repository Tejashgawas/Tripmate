from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class TripRecommendedService(Base):
    __tablename__ = "trip_recommended_services"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String, nullable=False)
    rank = Column(Integer, nullable=True)  # 1..N order in the list
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", backref="recommended_services")
    service = relationship("Service")

    __table_args__ = (
        UniqueConstraint("trip_id", "service_id", name="uq_trip_recommended_service"),
        Index("ix_trip_recommended_trip_id", "trip_id"),
        Index("ix_trip_recommended_service_type", "service_type"),
    )

class TripServiceVote(Base):
    __tablename__ = "trip_service_votes"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", backref="service_votes")
    user = relationship("User")
    service = relationship("Service")

    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", "service_type", name="uq_trip_user_service_type_vote"),
        Index("ix_trip_votes_trip_id", "trip_id"),
        Index("ix_trip_votes_service_type", "service_type"),
    )
