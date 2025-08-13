from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.trips.checklist_models import TaskPriority, TaskCategory

# Base schemas
class ChecklistBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: TaskCategory = TaskCategory.other
    priority: TaskPriority = TaskPriority.medium
    due_date: Optional[datetime] = None

class ChecklistCreate(ChecklistBase):
    pass

class ChecklistUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[TaskCategory] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None

# Assignment schemas
class AssignmentCreate(BaseModel):
    assigned_to: int
    notes: Optional[str] = None

class AssignmentResponse(BaseModel):
    id: int
    task_id: int
    assigned_to: int
    assigned_by: int
    assigned_at: datetime
    notes: Optional[str] = None
    assigned_user_name: Optional[str] = None
    assigner_name: Optional[str] = None

    class Config:
        from_attributes = True

# Completion schemas
class CompletionCreate(BaseModel):
    notes: Optional[str] = None

class CompletionResponse(BaseModel):
    id: int
    task_id: int
    completed_by: int
    completed_at: datetime
    notes: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

# Response schemas
class ChecklistResponse(BaseModel):
    id: int
    trip_id: int
    title: str
    description: Optional[str]
    category: TaskCategory
    priority: TaskPriority
    due_date: Optional[datetime]
    is_completed: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None
    assignments: List[AssignmentResponse] = []
    completions: List[CompletionResponse] = []

    class Config:
        from_attributes = True

class ChecklistSummary(BaseModel):
    id: int
    title: str
    category: TaskCategory
    priority: TaskPriority
    due_date: Optional[datetime]
    is_completed: bool
    assigned_count: int
    completed_count: int

    class Config:
        from_attributes = True

# Progress tracking
class ChecklistProgress(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    completion_percentage: float
    tasks_by_category: dict[str, dict[str, int]]
    tasks_by_priority: dict[str, dict[str, int]]

# Bulk operations
class BulkAssignmentCreate(BaseModel):
    task_ids: List[int]
    assigned_to: int
    notes: Optional[str] = None

class BulkCompletionCreate(BaseModel):
    task_ids: List[int]
    notes: Optional[str] = None
