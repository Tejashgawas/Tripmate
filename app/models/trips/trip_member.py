from sqlalchemy import Column, Integer, ForeignKey, DateTime, String,Enum,UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum
from sqlalchemy import Enum as PgEnum
import sqlalchemy as sa

class TripRole(enum.Enum):
    MEMBER = "member"
    OWNER = "owner"
    COHOST ="cohost"
    

class TripMember(Base):
    __tablename__ = "trip_members"

    id = Column(Integer, primary_key=True, index=True)

    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    triprole_enum = sa.Enum(
        TripRole,
        name="triprole",
        values_callable=lambda obj: [e.value for e in obj]  # this ensures lowercase values
    )
    role = Column(triprole_enum, nullable=False)

    joined_at = Column(DateTime, default=datetime.utcnow)

    # To ensure no duplicate members in a trip
    __table_args__ = (
        UniqueConstraint('trip_id', 'user_id', name='uq_trip_user'),
    )

    # Relationships (optional for eager loading)
    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="trips")
