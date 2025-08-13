from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user.user import User
from app.services.trips.checklist_service import (
    create_checklist_item, get_checklist_item, get_trip_checklist,
    update_checklist_item, delete_checklist_item, assign_task_to_member,
    remove_task_assignment, mark_task_complete, mark_task_incomplete,
    get_checklist_progress
)
from app.schemas.trip.checklist import (
    ChecklistCreate, ChecklistUpdate, ChecklistResponse, ChecklistSummary,
    AssignmentCreate, CompletionCreate, ChecklistProgress
)

router = APIRouter(prefix="/trips", tags=["Trip Checklist"])

# CRUD Operations
@router.post("/{trip_id}/checklist", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
async def create_checklist_task(
    trip_id: int = Path(..., gt=0),
    checklist_data: ChecklistCreate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new checklist item for a trip."""
    try:
        item = await create_checklist_item(session, trip_id, checklist_data, current_user.id)
        # Fetch the created item with all relationships
        return await get_checklist_item(session, item.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checklist item: {str(e)}")

@router.get("/{trip_id}/checklist", response_model=List[ChecklistResponse])
async def get_trip_checklist_items(
    trip_id: int = Path(..., gt=0),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all checklist items for a trip with optional filters."""
    try:
        items = await get_trip_checklist(session, trip_id, category, priority, completed)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch checklist items: {str(e)}")

# Progress Tracking
@router.get("/{trip_id}/checklist/progress", response_model=ChecklistProgress)
async def get_trip_checklist_progress(
    trip_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall progress statistics for a trip's checklist."""
    try:
        progress = await get_checklist_progress(session, trip_id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress: {str(e)}")

# Summary endpoint
@router.get("/{trip_id}/checklist/summary", response_model=List[ChecklistSummary])
async def get_checklist_summary(
    trip_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary of all checklist items for a trip."""
    try:
        items = await get_trip_checklist(session, trip_id)
        summaries = []
        for item in items:
            summaries.append(ChecklistSummary(
                id=item.id,
                title=item.title,
                category=item.category,
                priority=item.priority,
                due_date=item.due_date,
                is_completed=item.is_completed,
                assigned_count=len(item.assignments),
                completed_count=len(item.completions)
            ))
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch checklist summary: {str(e)}")

@router.get("/{trip_id}/checklist/{task_id}", response_model=ChecklistResponse)
async def get_checklist_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific checklist item by ID."""
    try:
        item = await get_checklist_item(session, task_id)
        if not item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch checklist item: {str(e)}")

@router.put("/{trip_id}/checklist/{task_id}", response_model=ChecklistResponse)
async def update_checklist_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    update_data: ChecklistUpdate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a checklist item."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        # Only creator can update
        if existing_item.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only the creator can update this task")
        
        updated_item = await update_checklist_item(session, task_id, update_data)
        if not updated_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        
        return await get_checklist_item(session, task_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update checklist item: {str(e)}")

@router.delete("/{trip_id}/checklist/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checklist_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a checklist item."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        # Only creator can delete
        if existing_item.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only the creator can delete this task")
        
        success = await delete_checklist_item(session, task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Checklist item not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete checklist item: {str(e)}")

# Assignment Operations
@router.post("/{trip_id}/checklist/{task_id}/assign", response_model=dict)
async def assign_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    assignment_data: AssignmentCreate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a task to a member."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        assignment = await assign_task_to_member(session, task_id, assignment_data, current_user.id)
        return {"message": "Task assigned successfully", "assignment_id": assignment.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")

@router.delete("/{trip_id}/checklist/{task_id}/assign/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_assignment(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    user_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a task assignment."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        # Only creator or assigned user can remove assignment
        if existing_item.created_by != current_user.id and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to remove this assignment")
        
        success = await remove_task_assignment(session, task_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Assignment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove assignment: {str(e)}")

# Completion Operations
@router.post("/{trip_id}/checklist/{task_id}/complete", response_model=dict)
async def complete_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    completion_data: CompletionCreate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a task as complete."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        completion = await mark_task_complete(session, task_id, completion_data, current_user.id)
        return {"message": "Task marked as complete", "completion_id": completion.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark task complete: {str(e)}")

@router.delete("/{trip_id}/checklist/{task_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def uncomplete_task(
    trip_id: int = Path(..., gt=0),
    task_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a task as incomplete."""
    try:
        # Check if item exists and belongs to trip
        existing_item = await get_checklist_item(session, task_id)
        if not existing_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if existing_item.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="Task does not belong to this trip")
        
        success = await mark_task_incomplete(session, task_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Completion record not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark task incomplete: {str(e)}")
