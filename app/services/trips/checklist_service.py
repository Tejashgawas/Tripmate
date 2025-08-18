from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime

from app.models.trips.checklist_models import TripChecklist, ChecklistAssignment, ChecklistCompletion
from app.models.user.user import User
from app.schemas.trip.checklist import (
    ChecklistCreate, ChecklistUpdate, AssignmentCreate, CompletionCreate,
    ChecklistResponse, ChecklistSummary, ChecklistProgress
)

# CRUD Operations
async def create_checklist_item(
    session: AsyncSession,
    trip_id: int,
    checklist_data: ChecklistCreate,
    created_by: int
) -> TripChecklist:
    """Create a new checklist item for a trip."""
    new_item = TripChecklist(
        trip_id=trip_id,
        created_by=created_by,
        **checklist_data.dict()
    )
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return new_item

async def get_checklist_item(
    session: AsyncSession,
    task_id: int
) -> Optional[TripChecklist]:
    """Get a single checklist item by ID."""
    result = await session.execute(
        select(TripChecklist)
        .options(
            joinedload(TripChecklist.assignments).joinedload(ChecklistAssignment.assigned_user),
            joinedload(TripChecklist.assignments).joinedload(ChecklistAssignment.assigner),
            joinedload(TripChecklist.completions).joinedload(ChecklistCompletion.user),
            joinedload(TripChecklist.creator)
        )
        .where(TripChecklist.id == task_id)
    )
    return result.unique().scalar_one_or_none()

async def get_trip_checklist(
    session: AsyncSession,
    trip_id: int,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    completed: Optional[bool] = None
) -> List[TripChecklist]:
    """Get all checklist items for a trip with optional filters."""
    query = select(TripChecklist).options(
        joinedload(TripChecklist.assignments).joinedload(ChecklistAssignment.assigned_user),
        joinedload(TripChecklist.assignments).joinedload(ChecklistAssignment.assigner),
        joinedload(TripChecklist.completions).joinedload(ChecklistCompletion.user),
        joinedload(TripChecklist.creator)
    ).where(TripChecklist.trip_id == trip_id)
    
    if category:
        query = query.where(TripChecklist.category == category)
    if priority:
        query = query.where(TripChecklist.priority == priority)
    if completed is not None:
        query = query.where(TripChecklist.is_completed == completed)
    
    query = query.order_by(TripChecklist.priority.desc(), TripChecklist.due_date.asc().nulls_last())
    
    result = await session.execute(query)
    return result.unique().scalars().all()

async def update_checklist_item(
    session: AsyncSession,
    task_id: int,
    update_data: ChecklistUpdate
) -> Optional[TripChecklist]:
    """Update a checklist item."""
    item = await get_checklist_item(session, task_id)
    if not item:
        return None
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(item)
    return item

async def delete_checklist_item(
    session: AsyncSession,
    task_id: int
) -> bool:
    """Delete a checklist item."""
    item = await get_checklist_item(session, task_id)
    if not item:
        return False
    
    await session.delete(item)
    await session.commit()
    return True

# Assignment Operations
async def assign_task_to_member(
    session: AsyncSession,
    task_id: int,
    assignment_data: AssignmentCreate,
    assigned_by: int
) -> ChecklistAssignment:
    """Assign a task to a member."""
    # Check if task exists
    task = await get_checklist_item(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if already assigned to this user
    existing = await session.execute(
        select(ChecklistAssignment).where(
            and_(
                ChecklistAssignment.task_id == task_id,
                ChecklistAssignment.assigned_to == assignment_data.assigned_to
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Task already assigned to this user")
    
    # Create assignment
    assignment = ChecklistAssignment(
        task_id=task_id,
        assigned_to=assignment_data.assigned_to,
        assigned_by=assigned_by,
        notes=assignment_data.notes
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment

async def remove_task_assignment(
    session: AsyncSession,
    task_id: int,
    assigned_to: int
) -> bool:
    """Remove a task assignment."""
    result = await session.execute(
        select(ChecklistAssignment).where(
            and_(
                ChecklistAssignment.task_id == task_id,
                ChecklistAssignment.assigned_to == assigned_to
            )
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return False
    
    await session.delete(assignment)
    await session.commit()
    return True

# Completion Operations
async def mark_task_complete(
    session: AsyncSession,
    task_id: int,
    completion_data: CompletionCreate,
    completed_by: int
) -> ChecklistCompletion:
    """Mark a task as complete."""
    # Check if task exists
    task = await get_checklist_item(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if already completed by this user
    existing = await session.execute(
        select(ChecklistCompletion).where(
            and_(
                ChecklistCompletion.task_id == task_id,
                ChecklistCompletion.completed_by == completed_by
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Task already completed by this user")
    
    # Create completion record
    completion = ChecklistCompletion(
        task_id=task_id,
        completed_by=completed_by,
        notes=completion_data.notes
    )
    session.add(completion)
    
    # Update task completion status if all assigned members have completed
    assignments = await session.execute(
        select(ChecklistAssignment).where(ChecklistAssignment.task_id == task_id)
    )
    assignments = assignments.scalars().all()
    
    if assignments:
        # Check if all assigned members have completed
        completed_count = await session.execute(
            select(func.count(ChecklistCompletion.id)).where(
                ChecklistCompletion.task_id == task_id
            )
        )
        completed_count = completed_count.scalar()
        
        if completed_count + 1 >= len(assignments):
            task.is_completed = True
    else:
        task.is_completed = True

    
    await session.commit()
    await session.refresh(completion)
    return completion

async def mark_task_incomplete(
    session: AsyncSession,
    task_id: int,
    completed_by: int
) -> bool:
    """Mark a task as incomplete (remove completion record)."""
    result = await session.execute(
        select(ChecklistCompletion).where(
            and_(
                ChecklistCompletion.task_id == task_id,
                ChecklistCompletion.completed_by == completed_by
            )
        )
    )
    completion = result.scalar_one_or_none()
    if not completion:
        return False
    
    await session.delete(completion)
    
    # Update task completion status
    task = await get_checklist_item(session, task_id)
    if task:
        task.is_completed = False
    
    await session.commit()
    return True

# Progress Tracking
async def get_checklist_progress(
    session: AsyncSession,
    trip_id: int
) -> ChecklistProgress:
    """Get overall progress statistics for a trip's checklist."""
    # Total tasks
    total_result = await session.execute(
        select(func.count(TripChecklist.id)).where(TripChecklist.trip_id == trip_id)
    )
    total_tasks = total_result.scalar()
    
    # Completed tasks
    completed_result = await session.execute(
        select(func.count(TripChecklist.id)).where(
            and_(
                TripChecklist.trip_id == trip_id,
                TripChecklist.is_completed == True
            )
        )
    )
    completed_tasks = completed_result.scalar()
    
    pending_tasks = total_tasks - completed_tasks
    completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Tasks by category
    category_result = await session.execute(
        select(
            TripChecklist.category,
            TripChecklist.is_completed,
            func.count(TripChecklist.id)
        ).where(TripChecklist.trip_id == trip_id)
        .group_by(TripChecklist.category, TripChecklist.is_completed)
    )
    
    tasks_by_category = {}
    for row in category_result:
        cat, completed, count = row
        if cat not in tasks_by_category:
            tasks_by_category[cat] = {"completed": 0, "pending": 0}
        if completed:
            tasks_by_category[cat]["completed"] = count
        else:
            tasks_by_category[cat]["pending"] = count
    
    # Tasks by priority
    priority_result = await session.execute(
        select(
            TripChecklist.priority,
            TripChecklist.is_completed,
            func.count(TripChecklist.id)
        ).where(TripChecklist.trip_id == trip_id)
        .group_by(TripChecklist.priority, TripChecklist.is_completed)
    )
    
    tasks_by_priority = {}
    for row in priority_result:
        prio, completed, count = row
        if prio not in tasks_by_priority:
            tasks_by_priority[prio] = {"completed": 0, "pending": 0}
        if completed:
            tasks_by_priority[prio]["completed"] = count
        else:
            tasks_by_priority[prio]["pending"] = count
    
    return ChecklistProgress(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        completion_percentage=round(completion_percentage, 2),
        tasks_by_category=tasks_by_category,
        tasks_by_priority=tasks_by_priority
    )
