# refactored expense_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_,delete,update
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
    expense_to_delete: Expense  # Accept the object itself
) -> bool:
    """Delete an expense object."""
    try:
        # No need to fetch or check for existence here,
        # as that's already done in the route handler.
        await session.delete(expense_to_delete)
        await session.commit()
        return True
    except Exception:
        # It's good practice to rollback on failure
        await session.rollback()
        return False

# ----------------------
# Split Management
# ----------------------
from sqlalchemy.orm import selectinload
from sqlalchemy import select

async def update_expense_splits(
    session: AsyncSession,
    expense: Expense,
    splits: List[ExpenseSplitCreate]
) -> List[ExpenseSplit]:
    """Update expense splits manually."""
    total_split = sum((s.amount for s in splits), Decimal('0.00'))
    if total_split != expense.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Split amounts must equal expense amount. Expected: {expense.amount}, Got: {total_split}"
        )

    # Delete existing splits
    await session.execute(
        delete(ExpenseSplit).where(ExpenseSplit.expense_id == expense.id)
    )
    

    # Create new splits
    new_splits = []
    for split_data in splits:
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=split_data.user_id,
            amount=split_data.amount,
            notes=split_data.notes,
            is_paid=(split_data.user_id == expense.paid_by)
        )
        session.add(split)
        new_splits.append(split)

    expense.is_split_equally = False
    await session.flush()
    await session.commit()

    # --- FIX ---
    # Return the list of newly created split objects.
    return new_splits


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

    # Check if all splits for this expense are now paid
    total_splits_res = await session.execute(
        select(func.count(ExpenseSplit.id)).where(ExpenseSplit.expense_id == expense_id)
    )
    total_splits_count = total_splits_res.scalar_one()

    paid_splits_res = await session.execute(
        select(func.count(ExpenseSplit.id)).where(
            ExpenseSplit.expense_id == expense_id,
            ExpenseSplit.is_paid == True
        )
    )
    paid_splits_count = paid_splits_res.scalar_one()

    # If all splits are paid, update the parent expense status to 'approved'
    if total_splits_count > 0 and total_splits_count == paid_splits_count:
        expense_res = await session.execute(select(Expense).where(Expense.id == expense_id))
        parent_expense = expense_res.scalar_one_or_none()
        if parent_expense:
            # --- CHANGE IS HERE ---
            parent_expense.status = ExpenseStatus.approved



    await session.commit()
    return True


# ----------------------
# Balance Calculations
# ----------------------
async def calculate_user_balances(
    session: AsyncSession,
    trip_id: int
) -> List[UserBalance]:
    """Calculate running balances for all users in a trip, 
    considering owed, already paid, and remaining balances."""

    # Get all trip members with user details
    tm_res = await session.execute(
        select(TripMember).where(TripMember.trip_id == trip_id).options(selectinload(TripMember.user))
    )
    trip_members = tm_res.scalars().all()

    balances = []

    for member in trip_members:
        user_id = member.user_id

        # 1. Total paid by this user (as creator of expenses)
        paid_result = await session.execute(
            select(func.sum(Expense.amount)).where(
                and_(
                    Expense.trip_id == trip_id,
                    Expense.paid_by == user_id
                )
            )
        )
        total_paid = paid_result.scalar() or Decimal('0.00')

        # 2. Total owed by this user (all splits assigned)
        owed_result = await session.execute(
            select(func.sum(ExpenseSplit.amount)).join(Expense).where(
                and_(
                    Expense.trip_id == trip_id,
                    ExpenseSplit.user_id == user_id
                )
            )
        )
        total_owed = owed_result.scalar() or Decimal('0.00')

        # 3. Already paid from owed (splits marked is_paid=True)
        already_paid_result = await session.execute(
            select(func.sum(ExpenseSplit.amount)).join(Expense).where(
                and_(
                    Expense.trip_id == trip_id,
                    ExpenseSplit.user_id == user_id,
                    ExpenseSplit.is_paid == True
                )
            )
        )
        already_paid_owed = already_paid_result.scalar() or Decimal('0.00')

        # 4. Remaining owed
        remaining_owed = total_owed - already_paid_owed

        # 5. Net balance (what this user is effectively at after considering splits)
        net_balance = total_paid - remaining_owed

        balance = UserBalance(
            user_id=user_id,
            user_name=member.user.username if member.user else None,
            user_email=member.user.email if member.user else None,
            total_paid=total_paid,
            total_owed=total_owed,
            already_paid_owed=already_paid_owed,
            remaining_owed=remaining_owed,
            net_balance=net_balance
        )
        balances.append(balance)

    return balances

from sqlalchemy.orm import aliased
async def calculate_settlements_needed(
    session: AsyncSession,
    trip_id: int
) -> List[SettlementSummary]:
    """
    Calculate settlements directly from unpaid splits (who owes whom).
    Excludes self-pay and ignores already paid splits.
    """

    debtor = aliased(User)
    creditor = aliased(User)

    q = (
    select(
        ExpenseSplit.user_id.label("debtor_id"),
        debtor.username.label("debtor_name"),
        Expense.paid_by.label("creditor_id"),
        creditor.username.label("creditor_name"),
        func.sum(ExpenseSplit.amount).label("total_owed")
    )
    .join(Expense, Expense.id == ExpenseSplit.expense_id)
    .join(debtor, debtor.id == ExpenseSplit.user_id)
    .join(creditor, creditor.id == Expense.paid_by)
    .where(
        Expense.trip_id == trip_id,
        ExpenseSplit.user_id != Expense.paid_by,
        ExpenseSplit.is_paid == False
    )
    .group_by(ExpenseSplit.user_id, debtor.username, Expense.paid_by, creditor.username)
)

    results = await session.execute(q)
    rows = results.fetchall()

    settlements: List[SettlementSummary] = []

    # Step 2: Apply settlement rule (-30% optimization if you want partial payment)
    for row in rows:
        debtor_id = row.debtor_id
        creditor_id = row.creditor_id
        total_owed = float(row.total_owed)

        # Example: allow debtor to pay 70% of amount instead of 100%
        settlement_amount = round(total_owed * 0.7, 2)

        settlements.append(
            SettlementSummary(
                from_user_id=debtor_id,
                from_user_name=row.debtor_name,  # replace with lookup if needed
                to_user_id=creditor_id,
                to_user_name=row.creditor_name,
                amount=settlement_amount,
                currency="INR"
            )
        )

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

    
    # Re-fetch with relationships eagerly loaded
    result = await session.execute(
        select(ExpenseSettlement)
        .options(
            selectinload(ExpenseSettlement.from_user),
            selectinload(ExpenseSettlement.to_user)
        )
        .where(ExpenseSettlement.id == settlement.id)
    )
    return result.scalar_one()


async def get_from_user_settlement(
    session: AsyncSession,
    user_id: int
):
    result = await session.execute(
        select(ExpenseSettlement)
        .options(
            selectinload(ExpenseSettlement.from_user),
            selectinload(ExpenseSettlement.to_user)
        )
        .where(ExpenseSettlement.from_user_id == user_id)
    )

    return result.scalars().all()

async def get_to_user_pending_settlement(
    session: AsyncSession,
    user_id: int
):
    result = await session.execute(
        select(ExpenseSettlement)
        .options(
            selectinload(ExpenseSettlement.from_user),
            selectinload(ExpenseSettlement.to_user)
        )
        .where(ExpenseSettlement.to_user_id == user_id,
                ExpenseSettlement.is_confirmed == False)
    )

    return result.scalars().all()






async def confirm_settlement(
    session: AsyncSession,
    settlement_id: int,
    confirmed_by: int
) -> bool:
    """Confirm a settlement by the recipient and update splits + expense status."""

    # 1. Fetch settlement
    result = await session.execute(
        select(ExpenseSettlement).where(ExpenseSettlement.id == settlement_id)
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        return False

    # 2. Ensure only recipient can confirm
    if settlement.to_user_id != confirmed_by:
        raise HTTPException(
            status_code=403,
            detail="Only the recipient can confirm this settlement"
        )

    # 3. Mark settlement confirmed
    settlement.is_confirmed = True

    # 4. Update related expense splits as paid
    await session.execute(
        update(ExpenseSplit)
        .where(
            ExpenseSplit.user_id == settlement.from_user_id,
            ExpenseSplit.expense_id.in_(
                select(Expense.id).where(
                    Expense.paid_by == settlement.to_user_id,
                    Expense.trip_id == settlement.trip_id
                )
            ),
            ExpenseSplit.is_paid == False
        )
        .values(is_paid=True)
    )

    # 5. For each expense, check if all splits are paid → then mark expense as settled
    result = await session.execute(
        select(Expense.id).where(
            Expense.trip_id == settlement.trip_id
        )
    )
    expense_ids = [row[0] for row in result.fetchall()]

    for expense_id in expense_ids:
        split_result = await session.execute(
            select(ExpenseSplit.is_paid).where(
                ExpenseSplit.expense_id == expense_id
            )
        )
        all_paid = all([row[0] for row in split_result.fetchall()])
        if all_paid:
            await session.execute(
                update(Expense)
                .where(Expense.id == expense_id)
                .values(status=ExpenseStatus.settled)
            )

    # 6. Commit all updates
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

    # Confirmed settlements (actual money moved)
    settled_result = await session.execute(
        select(func.sum(ExpenseSettlement.amount)).where(
            and_(
                ExpenseSettlement.trip_id == trip_id,
                ExpenseSettlement.is_confirmed == True
            )
        )
    )
    total_settled = settled_result.scalar() or Decimal("0.00")
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
    format: str = "json",
    include_settlements: bool = True,
    include_balances: bool = True,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    categories: Optional[List[ExpenseCategory]] = None
) -> Dict:
    """Export a detailed expense report for a trip."""

    # --- Base Expense Query ---
    query = (
        select(Expense)
        .options(
            selectinload(Expense.members).selectinload(ExpenseMember.user),
            selectinload(Expense.splits).selectinload(ExpenseSplit.user),
            selectinload(Expense.payer),
        )
        .where(Expense.trip_id == trip_id)
    )

    if date_from:
        query = query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
    if categories:
        query = query.where(Expense.category.in_(categories))

    result = await session.execute(query)
    expenses = result.unique().scalars().all()

    # --- Build Expense Data ---
    expense_list = []
    for e in expenses:
        expense_list.append({
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "amount": float(e.amount),
            "currency": e.currency,
            "category": e.category.value,
            "status": e.status.value,
            "expense_date": e.expense_date.isoformat(),
            "paid_by": e.payer_name or f"User {e.paid_by}",
            "members": [
                m.user_name or f"User {m.user_id}"
                for m in e.members if m.is_included
            ],
            "splits": [
                {
                    "user_id": s.user_id,
                    "user_name": s.user_name or f"User {s.user_id}",
                    "amount": float(s.amount),
                    "is_paid": s.is_paid,
                }
                for s in e.splits
            ]
        })

    # --- Summary (reuse your summary function) ---
    summary = await get_trip_expense_summary(session, trip_id)

    # --- Balances ---
    balances = []
    if include_balances:
        balances = [
            {
                "user_id": b.user_id,
                "user_name": b.user_name,
                "total_paid": float(b.total_paid),
                "total_owed": float(b.total_owed),
                "net_balance": float(b.net_balance),
            }
            for b in summary.user_balances
        ]

    # --- Settlements ---
    settlements = []
    if include_settlements:
        settlements = [
            {
                "from_user_id": s.from_user_id,
                "from_user_name": s.from_user_name or f"User {s.from_user_id}",
                "to_user_id": s.to_user_id,
                "to_user_name": s.to_user_name or f"User {s.to_user_id}",
                "amount": float(s.amount),
                "currency": s.currency,
                "is_confirmed": getattr(s, "is_confirmed", None)
            }
            for s in summary.settlements_needed
        ]

    # --- Final Export ---
    export_data = {
        "metadata": {
            "trip_id": trip_id,
            "export_date": datetime.utcnow().isoformat(),
            "currency": summary.currency,
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "categories": [c.value for c in categories] if categories else None,
            },
        },
        "summary": {
            "total_expenses": float(summary.total_expenses),
            "total_settled": float(summary.total_settled),
            "total_pending": float(summary.total_pending),
            "by_category": summary.expenses_by_category,
            "by_status": summary.expenses_by_status,
        },
        "expenses": expense_list,
        "user_balances": balances,
        "settlements_needed": settlements,
    }

    return export_data
