from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class TaskCategory(str, enum.Enum):
    packing = "packing"
    documents = "documents"
    activities = "activities"
    accommodation = "accommodation"
    transportation = "transportation"
    food = "food"
    other = "other"

class TripChecklist(Base):
    __tablename__ = "trip_checklist"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(TaskCategory), nullable=False, default=TaskCategory.other)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.medium)
    due_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trip = relationship("Trip", backref="checklist_items")
    creator = relationship("User", foreign_keys=[created_by])
    assignments = relationship("ChecklistAssignment", back_populates="task", cascade="all, delete")
    completions = relationship("ChecklistCompletion", back_populates="task", cascade="all, delete")

    __table_args__ = (
        Index("ix_trip_checklist_trip_id", "trip_id"),
        Index("ix_trip_checklist_category", "category"),
        Index("ix_trip_checklist_priority", "priority"),
        Index("ix_trip_checklist_due_date", "due_date"),
    )
    @property
    def creator_name(self):
        return self.creator.username if self.creator else None

class ChecklistAssignment(Base):
    __tablename__ = "checklist_assignments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("trip_checklist.id", ondelete="CASCADE"))
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    assigned_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    task = relationship("TripChecklist", back_populates="assignments")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("task_id", "assigned_to", name="uq_task_assigned_user"),
        Index("ix_checklist_assignments_task_id", "task_id"),
        Index("ix_checklist_assignments_assigned_to", "assigned_to"),
    )
    @property
    def assigned_user_name(self):
        return self.assigned_user.username if self.assigned_user else None

    @property
    def assigner_name(self):
        return self.assigner.username if self.assigner else None

class ChecklistCompletion(Base):
    __tablename__ = "checklist_completions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("trip_checklist.id", ondelete="CASCADE"))
    completed_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    completed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    task = relationship("TripChecklist", back_populates="completions")
    user = relationship("User", foreign_keys=[completed_by])

    __table_args__ = (
        UniqueConstraint("task_id", "completed_by", name="uq_task_completion_user"),
        Index("ix_checklist_completions_task_id", "task_id"),
        Index("ix_checklist_completions_completed_by", "completed_by"),
    )

    @property
    def user_name(self):
        return self.user.username if self.user else None
