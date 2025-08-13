# refactored expense_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.models.expense.expense_models import (
    Expense, ExpenseMember, ExpenseSplit, ExpenseSettlement,
    ExpenseCategory, ExpenseStatus
)
from app.models.user.user import User
from app.models.trips.trip_member import TripMember
from app.schemas.expense.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseMemberCreate, ExpenseSplitCreate,
    ExpenseSettlementCreate, UserBalance, SettlementSummary, TripExpenseSummary
)


# ----------------------
# Helper: eager load expense with relationships
# ----------------------
async def _fetch_expense_with_relations(session: AsyncSession, expense_id: int) -> Optional[Expense]:
    q = (
        select(Expense)
        .options(
            selectinload(Expense.members).selectinload(ExpenseMember.user),
            selectinload(Expense.splits).selectinload(ExpenseSplit.user),
            selectinload(Expense.payer)
        )
        .where(Expense.id == expense_id)
    )
    res = await session.execute(q)
    return res.unique().scalar_one_or_none()


# ----------------------
# CRUD Operations
# ----------------------
async def create_expense(
    session: AsyncSession,
    trip_id: int,
    expense_data: ExpenseCreate,
    paid_by: int
) -> Expense:
    """Create a new expense and automatically split it among members."""
    # Create the main expense
    new_expense = Expense(
        trip_id=trip_id,
        paid_by=paid_by,
        title=expense_data.title,
        description=expense_data.description,
        amount=expense_data.amount,
        currency=expense_data.currency,
        category=expense_data.category,
        expense_date=expense_data.expense_date,
        receipt_url=expense_data.receipt_url,
        is_split_equally=expense_data.is_split_equally
    )
    session.add(new_expense)
    await session.commit()
    await session.refresh(new_expense)

    # Add members to the expense
    for user_id in expense_data.member_ids:
        member = ExpenseMember(
            expense_id=new_expense.id,
            user_id=user_id,
            is_included=True
        )
        session.add(member)

    # Create expense splits
    if expense_data.is_split_equally:
        # Split equally among all members
        count = len(expense_data.member_ids)
        if count == 0:
            raise HTTPException(status_code=400, detail="member_ids cannot be empty for equal split")

        split_amount = (expense_data.amount / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Handle rounding differences by adjusting the last split
        remaining = expense_data.amount - (split_amount * (count - 1))

        for i, user_id in enumerate(expense_data.member_ids):
            if i == count - 1:
                amount = remaining
            else:
                amount = split_amount

            split = ExpenseSplit(
                expense_id=new_expense.id,
                user_id=user_id,
                amount=amount,
                is_paid=(user_id == paid_by)
            )
            session.add(split)
    else:
        # For manual splits, create splits with 0 amount initially
        for user_id in expense_data.member_ids:
            split = ExpenseSplit(
                expense_id=new_expense.id,
                user_id=user_id,
                amount=Decimal('0.00'),
                is_paid=(user_id == paid_by)
            )
            session.add(split)

    await session.commit()

    # Re-fetch expense with relations preloaded to avoid lazy-loading during serialization
    expense_with_rel = await _fetch_expense_with_relations(session, new_expense.id)
    return expense_with_rel


async def get_expense(
    session: AsyncSession,
    expense_id: int
) -> Optional[Expense]:
    """Get a single expense by ID with all relationships."""
    return await _fetch_expense_with_relations(session, expense_id)


async def get_trip_expenses(
    session: AsyncSession,
    trip_id: int,
    category: Optional[ExpenseCategory] = None,
    status: Optional[ExpenseStatus] = None,
    paid_by: Optional[int] = None
) -> List[Expense]:
    """Get all expenses for a trip with optional filters."""
    query = select(Expense).options(
        selectinload(Expense.members).selectinload(ExpenseMember.user),
        selectinload(Expense.splits).selectinload(ExpenseSplit.user),
        selectinload(Expense.payer)
    ).where(Expense.trip_id == trip_id)

    if category:
        query = query.where(Expense.category == category)
    if status:
        query = query.where(Expense.status == status)
    if paid_by:
        query = query.where(Expense.paid_by == paid_by)

    query = query.order_by(Expense.expense_date.desc())

    result = await session.execute(query)
    return result.unique().scalars().all()


async def update_expense(
    session: AsyncSession,
    expense_id: int,
    update_data: ExpenseUpdate
) -> Optional[Expense]:
    """Update an expense."""
    expense = await _fetch_expense_with_relations(session, expense_id)
    if not expense:
        return None

    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(expense, field, value)

    expense.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(expense)

    # Return with relations preloaded
    return await _fetch_expense_with_relations(session, expense_id)


async def delete_expense(
    session: AsyncSession,
    expense_id: int
) -> bool:
    """Delete an expense."""
    expense = await get_expense(session, expense_id)
    if not expense:
        return False

    session.delete(expense)
    await session.commit()
    return True


# ----------------------
# Split Management
# ----------------------
async def update_expense_splits(
    session: AsyncSession,
    expense_id: int,
    splits: List[ExpenseSplitCreate]
) -> List[ExpenseSplit]:
    """Update expense splits manually."""
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    total_split = sum((s.amount for s in splits), Decimal('0.00'))
    if total_split != expense.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Split amounts must equal expense amount. Expected: {expense.amount}, Got: {total_split}"
        )

    # Delete existing splits (fetch them first)
    existing_splits_res = await session.execute(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
    )
    existing_splits = existing_splits_res.scalars().all()
    for split in existing_splits:
        session.delete(split)

    # Create new splits
    new_splits = []
    for split_data in splits:
        split = ExpenseSplit(
            expense_id=expense_id,
            user_id=split_data.user_id,
            amount=split_data.amount,
            notes=split_data.notes,
            is_paid=(split_data.user_id == expense.paid_by)
        )
        session.add(split)
        new_splits.append(split)

    expense.is_split_equally = False
    await session.commit()

    # Return fresh splits loaded from DB
    new_res = await session.execute(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id).options(selectinload(ExpenseSplit.user))
    )
    return new_res.scalars().all()


async def mark_split_paid(
    session: AsyncSession,
    expense_id: int,
    user_id: int
) -> bool:
    """Mark a user's split as paid."""
    result = await session.execute(
        select(ExpenseSplit).where(
            and_(
                ExpenseSplit.expense_id == expense_id,
                ExpenseSplit.user_id == user_id
            )
        )
    )
    split = result.scalar_one_or_none()
    if not split:
        return False

    split.is_paid = True
    split.paid_at = datetime.utcnow()
    await session.commit()
    return True


# ----------------------
# Balance Calculations
# ----------------------
async def calculate_user_balances(
    session: AsyncSession,
    trip_id: int
) -> List[UserBalance]:
    """Calculate running balances for all users in a trip."""
    # Get all trip members (with user relation)
    tm_res = await session.execute(select(TripMember).where(TripMember.trip_id == trip_id).options(selectinload(TripMember.user)))
    trip_members = tm_res.scalars().all()

    balances = []
    for member in trip_members:
        # Calculate total paid by this user
        paid_result = await session.execute(
            select(func.sum(Expense.amount)).where(
                and_(
                    Expense.trip_id == trip_id,
                    Expense.paid_by == member.user_id,
                    Expense.status.in_([ExpenseStatus.approved, ExpenseStatus.settled])
                )
            )
        )
        total_paid = paid_result.scalar() or Decimal('0.00')

        # Calculate total owed by this user
        owed_result = await session.execute(
            select(func.sum(ExpenseSplit.amount)).join(Expense).where(
                and_(
                    Expense.trip_id == trip_id,
                    ExpenseSplit.user_id == member.user_id,
                    Expense.status.in_([ExpenseStatus.approved, ExpenseStatus.settled])
                )
            )
        )
        total_owed = owed_result.scalar() or Decimal('0.00')

        net_balance = total_paid - total_owed

        balance = UserBalance(
            user_id=member.user_id,
            user_name=member.user.username if member.user else None,
            user_email=member.user.email if member.user else None,
            total_paid=total_paid,
            total_owed=total_owed,
            net_balance=net_balance
        )
        balances.append(balance)

    return balances


async def calculate_settlements_needed(
    session: AsyncSession,
    trip_id: int
) -> List[SettlementSummary]:
    """Calculate optimal settlements to minimize transactions."""
    balances = await calculate_user_balances(session, trip_id)

    debtors = [b for b in balances if b.net_balance < 0]
    creditors = [b for b in balances if b.net_balance > 0]

    settlements = []

    debtors.sort(key=lambda x: abs(x.net_balance))
    creditors.sort(key=lambda x: x.net_balance, reverse=True)

    for debtor in debtors:
        remaining_debt = abs(debtor.net_balance)

        for creditor in creditors:
            if remaining_debt <= 0 or creditor.net_balance <= 0:
                continue

            settlement_amount = min(remaining_debt, creditor.net_balance)

            settlement = SettlementSummary(
                from_user_id=debtor.user_id,
                from_user_name=debtor.user_name,
                to_user_id=creditor.user_id,
                to_user_name=creditor.user_name,
                amount=settlement_amount,
                currency="INR"
            )
            settlements.append(settlement)

            remaining_debt -= settlement_amount
            creditor.net_balance -= settlement_amount

            if remaining_debt <= 0:
                break

    return settlements


# ----------------------
# Settlement Management
# ----------------------
async def create_settlement(
    session: AsyncSession,
    trip_id: int,
    from_user_id: int,
    settlement_data: ExpenseSettlementCreate
) -> ExpenseSettlement:
    """Create a new expense settlement."""
    settlement = ExpenseSettlement(
        trip_id=trip_id,
        from_user_id=from_user_id,
        to_user_id=settlement_data.to_user_id,
        amount=settlement_data.amount,
        currency=settlement_data.currency,
        notes=settlement_data.notes
    )
    session.add(settlement)
    await session.commit()
    await session.refresh(settlement)
    return settlement


async def confirm_settlement(
    session: AsyncSession,
    settlement_id: int,
    confirmed_by: int
) -> bool:
    """Confirm a settlement by the recipient."""
    result = await session.execute(
        select(ExpenseSettlement).where(ExpenseSettlement.id == settlement_id)
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        return False

    if settlement.to_user_id != confirmed_by:
        raise HTTPException(status_code=403, detail="Only the recipient can confirm this settlement")

    settlement.is_confirmed = True
    await session.commit()
    return True


# ----------------------
# Summary and Analytics
# ----------------------
async def get_trip_expense_summary(
    session: AsyncSession,
    trip_id: int
) -> TripExpenseSummary:
    """Get comprehensive expense summary for a trip."""
    # Total expenses
    total_result = await session.execute(
        select(func.sum(Expense.amount)).where(
            and_(
                Expense.trip_id == trip_id,
                Expense.status.in_([ExpenseStatus.approved, ExpenseStatus.settled])
            )
        )
    )
    total_expenses = total_result.scalar() or Decimal('0.00')

    # Expenses by category
    category_result = await session.execute(
        select(
            Expense.category,
            func.sum(Expense.amount)
        ).where(
            and_(
                Expense.trip_id == trip_id,
                Expense.status.in_([ExpenseStatus.approved, ExpenseStatus.settled])
            )
        ).group_by(Expense.category)
    )

    expenses_by_category = {}
    for row in category_result:
        category, amount = row
        expenses_by_category[category] = amount

    # Expenses by status
    status_result = await session.execute(
        select(
            Expense.status,
            func.sum(Expense.amount)
        ).where(Expense.trip_id == trip_id)
        .group_by(Expense.status)
    )

    expenses_by_status = {}
    for row in status_result:
        status, amount = row
        expenses_by_status[status] = amount

    # Calculate balances and settlements
    user_balances = await calculate_user_balances(session, trip_id)
    settlements_needed = await calculate_settlements_needed(session, trip_id)

    total_settled = sum(b.net_balance for b in user_balances if b.net_balance > 0)
    total_pending = total_expenses - total_settled

    return TripExpenseSummary(
        trip_id=trip_id,
        total_expenses=total_expenses,
        total_settled=total_settled,
        total_pending=total_pending,
        currency="INR",
        user_balances=user_balances,
        settlements_needed=settlements_needed,
        expenses_by_category=expenses_by_category,
        expenses_by_status=expenses_by_status
    )


# ----------------------
# Export functionality
# ----------------------
async def export_expense_report(
    session: AsyncSession,
    trip_id: int,
    format: str = "csv",
    include_settlements: bool = True,
    include_balances: bool = True,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    categories: Optional[List[ExpenseCategory]] = None
) -> Dict:
    """Export expense report in various formats."""
    query = select(Expense).options(
        selectinload(Expense.members).selectinload(ExpenseMember.user),
        selectinload(Expense.splits).selectinload(ExpenseSplit.user),
        selectinload(Expense.payer)
    ).where(Expense.trip_id == trip_id)

    if date_from:
        query = query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
    if categories:
        query = query.where(Expense.category.in_(categories))

    result = await session.execute(query)
    expenses = result.unique().scalars().all()

    export_data = {
        "trip_id": trip_id,
        "export_date": datetime.utcnow(),
        "expenses": []
    }

    for expense in expenses:
        expense_data = {
            "id": expense.id,
            "title": expense.title,
            "description": expense.description,
            "amount": float(expense.amount),
            "currency": expense.currency,
            "category": expense.category,
            "status": expense.status,
            "expense_date": expense.expense_date.isoformat(),
            "paid_by": getattr(expense, "payer_name", None) or f"User {expense.paid_by}",
            "members": [f"User {m.user_id}" for m in expense.members if m.is_included],
            "splits": [
                {
                    "user_id": s.user_id,
                    "amount": float(s.amount),
                    "is_paid": s.is_paid
                }
                for s in expense.splits
            ]
        }
        export_data["expenses"].append(expense_data)

    if include_balances:
        balances = await calculate_user_balances(session, trip_id)
        export_data["user_balances"] = [
            {
                "user_id": b.user_id,
                "user_name": b.user_name,
                "total_paid": float(b.total_paid),
                "total_owed": float(b.total_owed),
                "net_balance": float(b.net_balance)
            }
            for b in balances
        ]

    if include_settlements:
        settlements = await calculate_settlements_needed(session, trip_id)
        export_data["settlements_needed"] = [
            {
                "from_user_id": s.from_user_id,
                "from_user_name": s.from_user_name,
                "to_user_id": s.to_user_id,
                "to_user_name": s.to_user_name,
                "amount": float(s.amount),
                "currency": s.currency
            }
            for s in settlements
        ]

    return export_data
