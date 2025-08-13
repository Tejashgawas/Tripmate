from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.feedback.feedback_model import Feedback
from app.schemas.feedback.feedback_schema import FeedbackCreate, FeedbackUpdate
from typing import Optional

async def create_feedback(
    session: AsyncSession,
    user_id: int,
    feedback_data: FeedbackCreate
) -> Feedback:
    feedback = Feedback(
        user_id=user_id,
        **feedback_data.model_dump()
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback

async def get_feedback(
    session: AsyncSession,
    feedback_id: int
) -> Optional[Feedback]:
    feedback = await session.get(Feedback, feedback_id, options=[joinedload(Feedback.user)])
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

async def get_user_feedbacks(
    session: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 10
) -> tuple[list[Feedback], int]:
    # Get total count
    count_query = select(func.count()).select_from(Feedback).where(Feedback.user_id == user_id)
    total = await session.scalar(count_query)

    # Get feedbacks with pagination
    query = (
        select(Feedback)
        .where(Feedback.user_id == user_id)
        .options(joinedload(Feedback.user))
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    feedbacks = result.scalars().all()
    
    return feedbacks, total

async def get_all_feedbacks(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None
) -> tuple[list[Feedback], int]:
    # Base query
    base_query = select(Feedback).options(joinedload(Feedback.user))
    count_query = select(func.count()).select_from(Feedback)
    
    # Add status filter if provided
    if status:
        base_query = base_query.where(Feedback.status == status)
        count_query = count_query.where(Feedback.status == status)

    # Get total count
    total = await session.scalar(count_query)

    # Get feedbacks with pagination
    query = (
        base_query
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    feedbacks = result.scalars().all()
    
    return feedbacks, total

async def update_feedback(
    session: AsyncSession,
    feedback_id: int,
    feedback_data: FeedbackUpdate
) -> Feedback:
    feedback = await session.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    update_data = feedback_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feedback, field, value)
    
    await session.commit()
    await session.refresh(feedback)
    return feedback

async def delete_feedback(
    session: AsyncSession,
    feedback_id: int
) -> None:
    feedback = await session.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    await session.delete(feedback)
    await session.commit()
