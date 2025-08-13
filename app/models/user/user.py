from sqlalchemy import Column,String,Boolean,Integer,DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
import enum

class UserRole(enum.Enum):
    general = "general"
    provider = "provider"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,index=True)
    email = Column(String,unique=True,index=True,nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.general) # general, provider, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    auth_type = Column(String, default="local")  
    
    created_trips = relationship("Trip", back_populates="creator")

    sent_invites = relationship("TripInvite", back_populates="inviter")

    trips = relationship("TripMember", back_populates="user", cascade="all, delete")

    service_provider = relationship("ServiceProvider", back_populates="user", uselist=False)
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete")
