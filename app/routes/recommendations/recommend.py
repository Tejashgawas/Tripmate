# routes/recommendation.py

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.recommendation.recommendation import RecommendationResponse, VoteRequest, VoteSummaryResponse, VoteCount, TripSelectionRequest, TripRecommendedListResponse,TripSelectedServiceOut
from app.services.recommendations.recommend_service import generate_recommendations_for_trip, cast_vote, get_vote_counts, confirm_selection, get_persisted_recommendations_with_votes,get_selected_services
from app.dependencies.auth import get_current_user
from app.models.user.user import User

router = APIRouter(prefix="/recommendations", tags=["Trip Recommendations"])


@router.get("/trips/{trip_id}", response_model=RecommendationResponse)
async def get_recommendations_for_trip(
    trip_id: int = Path(..., gt=0, description="Trip ID to fetch recommendations for"),
    session: AsyncSession = Depends(get_db)
):
    return await generate_recommendations_for_trip(session, trip_id)

@router.get("/trips/{trip_id}/persisted", response_model=TripRecommendedListResponse)
async def get_persisted_recommendations(
    trip_id: int,
    service_type: str = Query(...),
    session: AsyncSession = Depends(get_db)
):
    return await get_persisted_recommendations_with_votes(session, trip_id, service_type)

@router.post("/trips/{trip_id}/vote")
async def vote_for_service(
    trip_id: int,
    payload: VoteRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await cast_vote(session, trip_id, current_user.id, payload.service_type, payload.service_id)
    return {"status": "ok"}

@router.get("/trips/{trip_id}/votes", response_model=VoteSummaryResponse)
async def get_votes(
    trip_id: int,
    service_type: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    counts = await get_vote_counts(session, trip_id, service_type)
    return VoteSummaryResponse(
        service_type=service_type,
        counts=[VoteCount(service_id=sid, votes=v) for sid, v in counts.items()]
    )

@router.post("/trips/{trip_id}/confirm")
async def confirm_trip_service(
    trip_id: int,
    payload: TripSelectionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await confirm_selection(session, trip_id, payload.service_type, payload.service_id, payload.notes)
    return {"status": "confirmed"}

@router.get("/{trip_id}/services/selected", response_model=List[TripSelectedServiceOut])
async def fetch_selected_services(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # (optional) check if current_user is part of trip before showing services
    services = await get_selected_services(db, trip_id)
    return services