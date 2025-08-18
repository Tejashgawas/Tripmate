from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Enum, UniqueConstraint, Index, Float, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class ExpenseCategory(str, enum.Enum):
    accommodation = "accommodation"
    transportation = "transportation"
    food = "food"
    activities = "activities"
    shopping = "shopping"
    emergency = "emergency"
    other = "other"

class ExpenseStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    settled = "settled"

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
    Integer,
    ForeignKey("trips.id", ondelete="SET NULL"),
    nullable=True
    )
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)  # Total amount of the expense
    currency = Column(String(3), default="USD", nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False, default=ExpenseCategory.other)
    status = Column(Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.pending)
    expense_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    receipt_url = Column(String, nullable=True)  # URL to receipt image/document
    is_split_equally = Column(Boolean, default=True)  # Whether to split equally among all members

    # Relationships
    trip = relationship("Trip", backref="expenses",passive_deletes=True)
    payer = relationship("User", foreign_keys=[paid_by])
    members = relationship("ExpenseMember", back_populates="expense", cascade="all, delete")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete")

    __table_args__ = (
        Index("ix_expenses_trip_id", "trip_id"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_status", "status"),
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_paid_by", "paid_by"),
    )
    @property
    def payer_name(self):
        return self.payer.username if self.payer else None

class ExpenseMember(Base):
    __tablename__ = "expense_members"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_included = Column(Boolean, default=True)  # Whether this member is included in the expense
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    expense = relationship("Expense", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_member"),
        Index("ix_expense_members_expense_id", "expense_id"),
        Index("ix_expense_members_user_id", "user_id"),
    )
    @property
    def user_name(self):
        return self.user.username if self.user else None

class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)  # Amount this user owes for this expense
    is_paid = Column(Boolean, default=False)  # Whether this user has paid their share
    paid_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_split_user"),
        Index("ix_expense_splits_expense_id", "expense_id"),
        Index("ix_expense_splits_user_id", "user_id"),
        Index("ix_expense_splits_is_paid", "is_paid"),
    )
    @property
    def user_name(self):
        return self.user.username if self.user else None

class ExpenseSettlement(Base):
    __tablename__ = "expense_settlements"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
    Integer,
    ForeignKey("trips.id", ondelete="SET NULL"),
    nullable=True
    )
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)  # Amount being settled
    currency = Column(String(3), default="USD", nullable=False)
    settlement_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False)  # Whether the recipient has confirmed the settlement

    # Relationships
    trip = relationship("Trip", backref="expense_settlements",passive_deletes=True)
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])

    __table_args__ = (
        Index("ix_expense_settlements_trip_id", "trip_id"),
        Index("ix_expense_settlements_from_user", "from_user_id"),
        Index("ix_expense_settlements_to_user", "to_user_id"),
        Index("ix_expense_settlements_settlement_date", "settlement_date"),
    )

    @property
    def from_user_name(self):
        return self.from_user.username if self.from_user else None

    @property
    def to_user_name(self):
        return self.to_user.username if self.to_user else None
