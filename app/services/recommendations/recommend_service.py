# services/recommendation_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from fastapi import HTTPException
from app.models import Trip
from app.schemas.recommendation.recommendation import RecommendationResponse
from app.services.recommendations.internal_query import get_services_for_trip
from app.services.recommendations.rule_engine import group_and_select_top_services
from app.core.logger import logger
from app.models.trips.trip_member_preference import TripMemberPreference
from collections import Counter
from app.models.service.recommendation_models import TripRecommendedService, TripServiceVote
from app.models.service.service_provider import Service,TripSelectedService
from sqlalchemy.orm import joinedload,selectinload
from app.schemas.recommendation.recommendation import TripRecommendedListResponse, TripRecommendedOption, RecommendedService

async def generate_recommendations_for_trip(
    session: AsyncSession,
    trip_id: int
) -> RecommendationResponse:
    # Step 1: Get trip
    trip = await session.get(Trip, trip_id)

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    logger.info(f"[Trip] ID: {trip.id}, Location: {trip.location}, Budget: {trip.budget}")

    # Step 1.5: Aggregate member preferences
    result = await session.execute(
        select(TripMemberPreference).where(TripMemberPreference.trip_id == trip_id)
    )
    prefs = result.scalars().all()
    if prefs:
        budgets = [p.budget for p in prefs if p.budget is not None]
        agg_budget = sum(budgets) / len(budgets) if budgets else trip.budget
        budget_min = agg_budget * 0.8
        budget_max = agg_budget * 1.2
        def most_common(lst):
            return Counter([x for x in lst if x]).most_common(1)[0][0] if lst else None
        accommodation_type = most_common([p.accommodation_type for p in prefs])
        food_preferences = most_common([p.food_preferences for p in prefs])
        activity_interests = most_common([p.activity_interests for p in prefs])
        pace = most_common([p.pace for p in prefs])
    else:
        agg_budget = trip.budget
        budget_min = agg_budget * 0.8
        budget_max = agg_budget * 1.2
        accommodation_type = None
        food_preferences = None
        activity_interests = None
        pace = None

    # Step 2: Fetch internal services based on aggregated prefs and budget range
    services = await get_services_for_trip(session, trip, agg_budget, accommodation_type, food_preferences, activity_interests, pace, budget_min, budget_max)

    # Step 3: Pass to rule engine for top N per type
    response = group_and_select_top_services(services)

    # Step 4: Persist top lists per category for voting
    # Map response back to services so we can store ids with rank
    type_to_services: dict[str, list[Service]] = {
        "hotels": [s for s in services if s.type.lower() == "hotel"],
        "buses": [s for s in services if s.type.lower() == "bus"],
        "rentals": [s for s in services if s.type.lower() == "rental"],
        "packages": [s for s in services if s.type.lower() == "package"],
    }

    # For each category, store up to 4 items with rank
    for category, rec_list in (
        ("hotels", response.hotels),
        ("buses", response.buses),
        ("rentals", response.rentals),
        ("packages", response.packages),
    ):
        for rank, item in enumerate(rec_list[:4], start=1):
            # upsert-like: check exists then insert if missing
            existing = await session.execute(
                select(TripRecommendedService).where(
                    TripRecommendedService.trip_id == trip_id,
                    TripRecommendedService.service_id == item.id,
                )
            )
            trs = existing.scalar_one_or_none()
            if trs:
                trs.service_type = item.type
                trs.rank = rank
            else:
                session.add(TripRecommendedService(
                    trip_id=trip_id,
                    service_id=item.id,
                    service_type=item.type,
                    rank=rank,
                ))
    await session.commit()

    logger.info(f"Generated {len(services)} internal services for trip {trip.id}")
    return response

async def cast_vote(session: AsyncSession, trip_id: int, user_id: int, service_type: str, service_id: int) -> None:
    # Ensure the option exists in recommended list for this trip
    exists = await session.execute(
        select(TripRecommendedService).where(
            TripRecommendedService.trip_id == trip_id,
            TripRecommendedService.service_type == service_type,
            TripRecommendedService.service_id == service_id,
        )
    )
    if not exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Service is not in recommended list for this trip")

    # Upsert vote per (trip,user,service_type)
    existing = await session.execute(
        select(TripServiceVote).where(
            TripServiceVote.trip_id == trip_id,
            TripServiceVote.user_id == user_id,
            TripServiceVote.service_type == service_type,
        )
    )
    vote = existing.scalar_one_or_none()
    if vote:
        vote.service_id = service_id
    else:
        session.add(TripServiceVote(
            trip_id=trip_id,
            user_id=user_id,
            service_type=service_type,
            service_id=service_id,
        ))
    await session.commit()

async def get_vote_counts(session: AsyncSession, trip_id: int, service_type: str) -> dict[int, int]:
    # Return vote counts per service_id for given category
    result = await session.execute(
        select(TripServiceVote.service_id).where(
            TripServiceVote.trip_id == trip_id,
            TripServiceVote.service_type == service_type,
        )
    )
    service_ids = [row[0] for row in result.all()]
    counts: dict[int, int] = {}
    for sid in service_ids:
        counts[sid] = counts.get(sid, 0) + 1
    return counts

async def confirm_selection(session: AsyncSession, trip_id: int, service_type: str, service_id: int, notes: str | None = None):
    # Store final selection using existing TripSelectedService model
    # Optional: you could store per-category; here we just insert another selected_service row
     # avoid circular import

    session.add(TripSelectedService(trip_id=trip_id, service_id=service_id, custom_notes=notes))
    await session.commit()

async def get_persisted_recommendations_with_votes(
    session: AsyncSession,
    trip_id: int,
    service_type: str
) -> TripRecommendedListResponse:
    # Fetch recommended entries for the trip and type, join Service for details
    rec_result = await session.execute(
        select(TripRecommendedService)
        .options(joinedload(TripRecommendedService.service).joinedload(Service.provider))
        .where(
            TripRecommendedService.trip_id == trip_id,
            TripRecommendedService.service_type == service_type,
        )
        .order_by(TripRecommendedService.rank.asc().nulls_last())
    )
    recs = rec_result.scalars().all()

    # Get vote counts
    vote_counts = await get_vote_counts(session, trip_id, service_type)

    options: list[TripRecommendedOption] = []
    for rec in recs:
        svc: Service = rec.service
        options.append(
            TripRecommendedOption(
                service_id=svc.id,
                rank=rec.rank,
                votes=vote_counts.get(svc.id, 0),
                service=RecommendedService(
                    id=svc.id,
                    title=svc.title,
                    type=svc.type,
                    price=svc.price,
                    rating=svc.rating,
                    provider_name=svc.provider.name if svc.provider else None,
                    location=svc.location,
                    is_available=svc.is_available,
                    features=svc.features,
                )
            )
        )

    return TripRecommendedListResponse(
        trip_id=trip_id,
        service_type=service_type,
        options=options
    )


async def get_selected_services(
    db: AsyncSession,
    trip_id: int
):
    result = await db.execute(
        select(TripSelectedService)
        .options(selectinload(TripSelectedService.service)
        .selectinload(Service.provider))
        .where(TripSelectedService.trip_id == trip_id)
    )
    return result.scalars().all()