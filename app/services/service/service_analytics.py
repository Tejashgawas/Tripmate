from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.service.service_provider import Service,ServiceProvider
from app.models.user.user import User
from sqlalchemy.orm import aliased
from app.models.service.recommendation_models import TripRecommendedService
from app.models.service.service_provider import ServiceProvider,Service,TripSelectedService


async def get_total_services_created(
    db: AsyncSession,
    user_id: int
) -> int:
    # Step 1: find provider_id for this user
    result = await db.execute(
        select(ServiceProvider.id).where(ServiceProvider.user_id == user_id)
    )
    provider_id = result.scalar_one_or_none()
    if not provider_id:
        return 0  # user is not a provider or hasn’t set up profile

    # Step 2: count services tied to this provider
    result = await db.execute(
        select(func.count(Service.id)).where(Service.provider_id == provider_id)
    )
    return result.scalar() or 0

async def get_recommended_services_analytics(db: AsyncSession, user_id: int):
    # Step 1: get provider_id for the user
    provider_subq = (
        select(ServiceProvider.id)
        .where(ServiceProvider.user_id == user_id)
        .scalar_subquery()
    )

    # Step 2 + 3 + 4: join services → recommended_services and filter by provider_id
    result = await db.execute(
        select(
            TripRecommendedService.service_type,
            func.count(TripRecommendedService.id).label("recommendation_count")
        )
        .join(Service, Service.id == TripRecommendedService.service_id)
        .where(Service.provider_id == provider_subq)  # only provider's services
        .group_by(TripRecommendedService.service_type)
        .order_by(func.count(TripRecommendedService.id).desc())
    )

    # Convert to dicts
    return [
        {
            "service_type": row.service_type,
            "recommendation_count": row.recommendation_count
        }
        for row in result.all()
    ]

async def get_selected_services_with_rank_analytics(
    db: AsyncSession, 
    user_id: int
):
    """
    Get analytics for selected services categorized by service type,
    with count of selections and most common recommendation rank.
    
    Args:
        db: Database session
        user_id: User ID of the provider
    
    Returns:
        List of dictionaries containing service type analytics with rank data
    """
    # Step 1: Get provider_id for the user
    provider_subq = (
        select(ServiceProvider.id)
        .where(ServiceProvider.user_id == user_id)
        .scalar_subquery()
    )

    # Step 2: Get selected services with their recommendation ranks
    # We need to find the most common rank for each service type
    rank_analysis_cte = (
        select(
            Service.type.label("service_type"),
            TripRecommendedService.rank,
            func.count().label("rank_frequency")
        )
        .select_from(TripSelectedService)
        .join(Service, Service.id == TripSelectedService.service_id)
        .join(
            TripRecommendedService, 
            (TripRecommendedService.service_id == TripSelectedService.service_id) &
            (TripRecommendedService.trip_id == TripSelectedService.trip_id)
        )
        .where(Service.provider_id == provider_subq)
        .where(TripRecommendedService.rank.is_not(None))  # Only services with ranks
        .group_by(Service.type, TripRecommendedService.rank)
    ).cte("rank_analysis")

    # Step 3: Find the most common rank for each service type
    most_common_rank_subq = (
        select(
            rank_analysis_cte.c.service_type,
            rank_analysis_cte.c.rank,
            func.row_number().over(
                partition_by=rank_analysis_cte.c.service_type,
                order_by=rank_analysis_cte.c.rank_frequency.desc()
            ).label("rn")
        )
        .select_from(rank_analysis_cte)
    ).cte("most_common_rank")

    # Step 4: Get the main analytics with most common rank
    result = await db.execute(
        select(
            Service.type.label("service_type"),
            func.count(TripSelectedService.id).label("selected_count"),
            most_common_rank_subq.c.rank.label("most_common_rank")
        )
        .select_from(TripSelectedService)
        .join(Service, Service.id == TripSelectedService.service_id)
        .outerjoin(
            most_common_rank_subq,
            (most_common_rank_subq.c.service_type == Service.type) &
            (most_common_rank_subq.c.rn == 1)
        )
        .where(Service.provider_id == provider_subq)
        .group_by(Service.type, most_common_rank_subq.c.rank)
        .order_by(func.count(TripSelectedService.id).desc())
    )

    return [
        {
            "service_type": row.service_type,
            "selected_count": row.selected_count,
            "most_common_rank": row.most_common_rank
        }
        for row in result.all()
    ]

async def get_services_count_by_type(
    db: AsyncSession, 
    user_id: int
):
    """
    Get count of services by type for the provider.
    Used for pie chart visualization.
    
    Args:
        db: Database session
        user_id: User ID of the provider
    
    Returns:
        List of dictionaries containing service type and count
    """
    # Step 1: Get provider_id for the user
    provider_subq = (
        select(ServiceProvider.id)
        .where(ServiceProvider.user_id == user_id)
        .scalar_subquery()
    )

    # Step 2: Count services by type
    result = await db.execute(
        select(
            Service.type.label("service_type"),
            func.count(Service.id).label("count")
        )
        .where(Service.provider_id == provider_subq)
        .where(Service.is_available == True)  # Only count available services
        .group_by(Service.type)
        .order_by(func.count(Service.id).desc())
    )

    return [
        {
            "service_type": row.service_type,
            "count": row.count
        }
        for row in result.all()
    ]
