from sqlalchemy import Integer,Column,String,ForeignKey,Enum,DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class InviteStatus(enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"

class TripInvite(Base):
    __tablename__ = "trip_invites"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"))
    inviter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    invitee_email = Column(String, index=True)
    invite_code = Column(String, unique=True, index=True)
    status = Column(Enum(InviteStatus), default=InviteStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)

    trip = relationship("Trip", back_populates="invites")
    inviter = relationship("User", back_populates="sent_invites")