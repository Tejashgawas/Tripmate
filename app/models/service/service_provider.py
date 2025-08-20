from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, ForeignKey,
    DateTime, JSON, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ServiceProvider(Base):
    __tablename__ = "service_providers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    contact_email = Column(String)
    contact_phone = Column(String)
    location = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    services = relationship("Service", back_populates="provider", cascade="all, delete")
    user = relationship("User", back_populates="service_provider")

    __table_args__ = (
        Index("ix_provider_name", "name"),
    )


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id", ondelete="CASCADE"))
    type = Column(String, nullable=False)  # hotel, lodge, bus, etc.
    title = Column(String, nullable=False)
    description = Column(Text)
    location = Column(String)
    rating = Column(Float, nullable=True)
    price = Column(Float)
    features = Column(JSON, nullable=True)  # flexible structure (room_types, amenities, vehicle info)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("ServiceProvider", back_populates="services")

    __table_args__ = (
        Index("ix_service_type", "type"),
        Index("ix_service_location", "location"),
    )
    @property
    def provider_name(self):
        return self.provider.name if self.provider else None


class TripSelectedService(Base):
    __tablename__ = "trip_selected_services"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    selected_on = Column(DateTime, default=datetime.utcnow)
    custom_notes = Column(Text)

    trip = relationship("Trip", backref="selected_services")
    service = relationship("Service")

    __table_args__ = (
        Index("ix_trip_selected_trip_id", "trip_id"),
        Index("ix_trip_selected_service_id", "service_id"),
    )
