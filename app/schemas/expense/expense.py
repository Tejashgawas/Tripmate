from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from app.models.expense.expense_models import ExpenseCategory, ExpenseStatus

# Base schemas
class ExpenseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    category: ExpenseCategory = ExpenseCategory.other
    expense_date: datetime = Field(default_factory=datetime.utcnow)
    receipt_url: Optional[str] = None
    is_split_equally: bool = True

class ExpenseCreate(ExpenseBase):
    member_ids: List[int] = Field(..., min_items=1)  # List of user IDs to split the expense with

class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    category: Optional[ExpenseCategory] = None
    expense_date: Optional[datetime] = None
    receipt_url: Optional[str] = None
    is_split_equally: Optional[bool] = None
    status: Optional[ExpenseStatus] = None

# Member schemas
class ExpenseMemberCreate(BaseModel):
    user_id: int
    is_included: bool = True

class ExpenseMemberResponse(BaseModel):
    id: int
    expense_id: int
    user_id: int
    is_included: bool
    created_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True

# Split schemas
class ExpenseSplitCreate(BaseModel):
    user_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    notes: Optional[str] = None

class ExpenseSplitUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    notes: Optional[str] = None
    is_paid: Optional[bool] = None

class ExpenseSplitResponse(BaseModel):
    id: int
    expense_id: int
    user_id: int
    amount: Decimal
    is_paid: bool
    paid_at: Optional[datetime]
    notes: Optional[str]
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True

# Settlement schemas
class ExpenseSettlementCreate(BaseModel):
    to_user_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    notes: Optional[str] = None

class ExpenseSettlementUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    notes: Optional[str] = None
    is_confirmed: Optional[bool] = None

class ExpenseSettlementResponse(BaseModel):
    id: int
    trip_id: int
    from_user_id: int
    to_user_id: int
    amount: Decimal
    currency: str
    settlement_date: datetime
    notes: Optional[str]
    is_confirmed: bool
    from_user_name: Optional[str] = None
    to_user_name: Optional[str] = None

    class Config:
        from_attributes = True

# Response schemas
class ExpenseResponse(BaseModel):
    id: int
    trip_id: int
    title: str
    description: Optional[str]
    amount: Decimal
    currency: str
    category: ExpenseCategory
    status: ExpenseStatus
    expense_date: datetime
    paid_by: int
    created_at: datetime
    updated_at: datetime
    receipt_url: Optional[str]
    is_split_equally: bool
    payer_name: Optional[str] = None
    payer_email: Optional[str] = None
    members: List[ExpenseMemberResponse] = []
    splits: List[ExpenseSplitResponse] = []

    class Config:
        from_attributes = True

class ExpenseSummary(BaseModel):
    id: int
    title: str
    amount: Decimal
    currency: str
    category: ExpenseCategory
    status: ExpenseStatus
    expense_date: datetime
    paid_by: int
    payer_name: Optional[str] = None
    member_count: int
    total_owed: Decimal
    total_paid: Decimal

    class Config:
        from_attributes = True

# Balance and settlement schemas
class UserBalance(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    total_paid: Decimal
    total_owed: Decimal
    net_balance: Decimal  # Positive means they are owed money, negative means they owe money

class SettlementSummary(BaseModel):
    from_user_id: int
    from_user_name: Optional[str] = None
    to_user_id: int
    to_user_name: Optional[str] = None
    amount: Decimal
    currency: str

class TripExpenseSummary(BaseModel):
    trip_id: int
    total_expenses: Decimal
    total_settled: Decimal
    total_pending: Decimal
    currency: str
    user_balances: List[UserBalance]
    settlements_needed: List[SettlementSummary]
    expenses_by_category: Dict[str, Decimal]
    expenses_by_status: Dict[str, Decimal]

# Bulk operations
class BulkExpenseSplit(BaseModel):
    expense_id: int
    splits: List[ExpenseSplitCreate]

class BulkExpenseStatusUpdate(BaseModel):
    expense_ids: List[int]
    status: ExpenseStatus

# Export schemas
class ExpenseExportRequest(BaseModel):
    trip_id: int
    format: str = Field(default="csv", pattern="^(csv|json|pdf)$")
    include_settlements: bool = True
    include_balances: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    categories: Optional[List[ExpenseCategory]] = None
