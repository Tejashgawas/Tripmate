from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user.user import User
from app.models.expense.expense_models import ExpenseCategory, ExpenseStatus
from app.schemas.expense.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseSummary,
    ExpenseSplitCreate, ExpenseSplitResponse, ExpenseSplitUpdate,
    ExpenseSettlementCreate, ExpenseSettlementResponse, ExpenseSettlementUpdate,
    UserBalance, SettlementSummary, TripExpenseSummary, BulkExpenseSplit,
    BulkExpenseStatusUpdate, ExpenseExportRequest,ExpenseSettlementOut
)
from app.services.expense.expense_service import (
    create_expense, get_expense, get_trip_expenses, update_expense, delete_expense,
    update_expense_splits, mark_split_paid, calculate_user_balances,
    calculate_settlements_needed, create_settlement, confirm_settlement,
    get_trip_expense_summary, export_expense_report,get_from_user_settlement,get_to_user_pending_settlement
)
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.models.expense.expense_models import (
    Expense, ExpenseMember, ExpenseSplit, ExpenseSettlement,
    ExpenseCategory, ExpenseStatus
)

router = APIRouter(prefix="/expenses", tags=["Expense Management"])

# CRUD Operations
@router.post("/trips/{trip_id}", response_model=ExpenseResponse, status_code=201)
async def create_trip_expense(
    trip_id: int = Path(..., gt=0),
    expense_data: ExpenseCreate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense for a trip."""
    try:
        expense = await create_expense(session, trip_id, expense_data, current_user.id)
        return expense
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {str(e)}")

@router.get("/trips/{trip_id}", response_model=List[ExpenseResponse])
async def get_trip_expenses_list(
    trip_id: int = Path(..., gt=0),
    category: Optional[ExpenseCategory] = Query(None),
    status: Optional[ExpenseStatus] = Query(None),
    paid_by: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all expenses for a trip with optional filters."""
    try:
        expenses = await get_trip_expenses(session, trip_id, category, status, paid_by)
        return expenses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {str(e)}")

@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense_by_id(
    expense_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific expense by ID."""
    try:
        expense = await get_expense(session, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        return expense
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch expense: {str(e)}")

@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense_by_id(
    expense_id: int = Path(..., gt=0),
    update_data: ExpenseUpdate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an expense."""
    try:
        expense = await get_expense(session, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Only the person who paid or trip creator can update
        if expense.paid_by != current_user.id:
            # TODO: Add trip creator check
            raise HTTPException(status_code=403, detail="Only the payer can update this expense")
        
        updated_expense = await update_expense(session, expense_id, update_data)
        return updated_expense
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update expense: {str(e)}")

@router.delete("/{expense_id}", status_code=204)
async def delete_expense_by_id(
    expense_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an expense."""
    # 1. Fetch the expense ONCE
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # 2. Check permissions
    if expense.paid_by != current_user.id:
        # TODO: Add trip creator check
        raise HTTPException(status_code=403, detail="Only the payer can delete this expense")

    # 3. Pass the fetched OBJECT to the service function
    success = await delete_expense(session, expense)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete expense")

# Split Management
@router.put("/{expense_id}/splits", response_model=List[ExpenseSplitResponse])
async def update_expense_splits_route(
    expense_id: int = Path(..., gt=0),
    splits: List[ExpenseSplitCreate] = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update expense splits manually."""
    # 1. Fetch the expense ONCE
    expense = await get_expense(session, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # 2. Check permissions
    if expense.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can update expense splits")
    
    # 3. Pass the fetched OBJECT to the service function
    updated_splits = await update_expense_splits(session, expense, splits)

    final_splits_res = await session.execute(
        select(ExpenseSplit)
        .where(ExpenseSplit.expense_id == expense_id)
        .options(selectinload(ExpenseSplit.user))
    )
    
    # 5. Return the fully loaded objects for the response
    return final_splits_res.scalars().all()

@router.post("/{expense_id}/splits/{user_id}/pay", response_model=dict)
async def mark_split_as_paid(
    expense_id: int = Path(..., gt=0),
    user_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a user's split as paid."""
    try:
        # Only the user themselves can mark their split as paid
        if current_user.id != user_id:
            raise HTTPException(status_code=403, detail="You can only mark your own splits as paid")
        
        success = await mark_split_paid(session, expense_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Split not found")
        
        return {"message": "Split marked as paid successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark split as paid: {str(e)}")

# Balance and Settlement
@router.get("/trips/{trip_id}/balances", response_model=List[UserBalance])
async def get_trip_user_balances(
    trip_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get running balances for all users in a trip."""
    try:
        balances = await calculate_user_balances(session, trip_id)
        return balances
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate balances: {str(e)}")

@router.get("/trips/{trip_id}/settlements", response_model=List[SettlementSummary])
async def get_trip_settlements_needed(
    trip_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get optimal settlements needed to balance the trip."""
    try:
        settlements = await calculate_settlements_needed(session, trip_id)
        return settlements
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate settlements: {str(e)}")

@router.post("/trips/{trip_id}/settlements", response_model=ExpenseSettlementResponse, status_code=201)
async def create_expense_settlement(
    trip_id: int = Path(..., gt=0),
    settlement_data: ExpenseSettlementCreate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense settlement."""
    try:
        settlement = await create_settlement(session, trip_id, current_user.id, settlement_data)
        return settlement
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create settlement: {str(e)}")

@router.put("/settlements/{settlement_id}/confirm", response_model=dict)
async def confirm_expense_settlement(
    settlement_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a settlement by the recipient."""
    try:
        success = await confirm_settlement(session, settlement_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Settlement not found")
        
        return {"message": "Settlement confirmed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm settlement: {str(e)}")

# Summary and Analytics
@router.get("/trips/{trip_id}/summary", response_model=TripExpenseSummary)
async def get_trip_expense_summary_route(
    trip_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive expense summary for a trip."""
    try:
        summary = await get_trip_expense_summary(session, trip_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch expense summary: {str(e)}")

# Export functionality
@router.post("/trips/{trip_id}/export")
async def export_expense_report_route(
    trip_id: int = Path(..., gt=0),
    export_request: ExpenseExportRequest = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export expense report in various formats."""
    try:
        export_data = await export_expense_report(
            session=session,
            trip_id=trip_id,
            format=export_request.format,
            include_settlements=export_request.include_settlements,
            include_balances=export_request.include_balances,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            categories=export_request.categories
        )
        
        # For now, return JSON. In production, you'd generate actual files
        if export_request.format == "json":
            return export_data
        elif export_request.format == "csv":
            # TODO: Implement CSV generation
            return {"message": "CSV export not yet implemented", "data": export_data}
        elif export_request.format == "pdf":
            # TODO: Implement PDF generation
            return {"message": "PDF export not yet implemented", "data": export_data}
        else:
            return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export expense report: {str(e)}")

# # Bulk Operations
# @router.post("/trips/{trip_id}/bulk-status", response_model=dict)
# async def bulk_update_expense_status(
#     trip_id: int = Path(..., gt=0),
#     bulk_update: BulkExpenseStatusUpdate = ...,
#     session: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Bulk update expense statuses."""
#     try:
#         # TODO: Implement bulk status update
#         # This would require additional service functions
#         return {"message": "Bulk status update not yet implemented"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to bulk update expenses: {str(e)}")

# Additional utility endpoints
@router.get("/categories", response_model=List[str])
async def get_expense_categories():
    """Get all available expense categories."""
    return [category.value for category in ExpenseCategory]

@router.get("/statuses", response_model=List[str])
async def get_expense_statuses():
    """Get all available expense statuses."""
    return [status.value for status in ExpenseStatus]

@router.get("/currencies", response_model=List[str])
async def get_supported_currencies():
    """Get supported currencies."""
    return ["USD", "EUR", "GBP", "INR", "CAD", "AUD"]  # Add more as needed

# 1. Get all settlements created by current user
@router.get("/from/settlement", response_model=List[ExpenseSettlementOut])
async def fetch_user_created_settlements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settlements = await get_from_user_settlement(db, current_user.id)
    return settlements


# 2. Get only pending settlements where current user is receiver
@router.get("/to/pending", response_model=List[ExpenseSettlementOut])
async def fetch_user_pending_settlements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settlements = await get_to_user_pending_settlement(db, current_user.id)
    return settlements