from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user,require_role
from app.schemas.feedback.feedback_schema import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackListResponse,
    adminFeedbackListResponse
)
from app.services.feedback.feedback_service import (
    create_feedback,
    get_feedback,
    get_user_feedbacks,
    get_all_feedbacks,
    update_feedback,
    delete_feedback
)
from app.models.user.user import User,UserRole
from typing import Optional

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"]
)

@router.post("", response_model=FeedbackResponse)
async def create_new_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create a new feedback"""
    return await create_feedback(session, current_user.id, feedback_data)

@router.get("/my-feedbacks", response_model=FeedbackListResponse)
async def list_user_feedbacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all feedbacks for the current user"""
    feedbacks, total = await get_user_feedbacks(session, current_user.id, skip, limit)
    return FeedbackListResponse(total=total, feedbacks=feedbacks)

@router.get("/all", response_model=adminFeedbackListResponse)
async def list_all_feedbacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(pending|reviewed|addressed)$"),
    current_user: User = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db)
):
    # """Get all feedbacks (admin only)"""
    # if not current_user:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only administrators can view all feedbacks"
    #     )
    feedbacks, total = await get_all_feedbacks(session, skip, limit, status)
    return FeedbackListResponse(total=total, feedbacks=feedbacks)

@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_single_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get a specific feedback"""
    feedback = await get_feedback(session, feedback_id)
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this feedback"
        )
    return feedback

@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def update_existing_feedback(
    feedback_id: int,
    feedback_data: FeedbackUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update a feedback"""
    feedback = await get_feedback(session, feedback_id)
    if feedback.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this feedback"
        )
    return await update_feedback(session, feedback_id, feedback_data)

@router.delete("/{feedback_id}")
async def delete_existing_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Delete a feedback"""
    feedback = await get_feedback(session, feedback_id)
    if feedback.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this feedback"
        )
    await delete_feedback(session, feedback_id)
    return {"message": "Feedback deleted successfully"}
