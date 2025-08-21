from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.services.service_analytics import TotalServicesCountResponse
from app.services.service.service_analytics import ( 
    get_total_services_created,get_recommended_services_analytics,get_selected_services_with_rank_analytics,
    get_services_count_by_type
    )
from app.dependencies.auth import get_current_user,require_role  # 👈 import the role checker
from app.models.user.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user.user import User,UserRole
from typing import List,Dict,Any

router = APIRouter(
    prefix="/providers",
    tags=["Service Analytics"],
)


@router.get("/services/count", response_model=TotalServicesCountResponse)
async def total_services_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.provider)),
):
    total = await get_total_services_created(db, current_user.id)
    return TotalServicesCountResponse(total_services=total)


@router.get("/recommended-services", response_model=List[Dict[str, Any]])
async def get_recommended_services_analytics_endpoint(
    current_user: User = Depends(require_role(UserRole.provider)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics data for recommended services for the current user's provider account.
    
    Returns a list of service types with their recommendation counts, 
    ordered by recommendation count (highest first).
    
    - **service_type**: The type of service
    - **recommendation_count**: Number of times this service type was recommended
    """
    try:
        analytics_data = await get_recommended_services_analytics(db, current_user.id)
        
        if not analytics_data:
            return []
            
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics data: {str(e)}"
        )

@router.get("/recommended-services/{user_id}", response_model=List[Dict[str, Any]])
async def get_recommended_services_analytics_by_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics data for recommended services for a specific user's provider account.
    (Admin or specific authorization required)
    
    - **user_id**: The ID of the user whose analytics to retrieve
    """
    # Add authorization check here if needed
    # For example: check if current_user is admin or has permission to view this data
    
    try:
        analytics_data = await get_recommended_services_analytics(db, user_id)
        
        if not analytics_data:
            return []
            
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics data for user {user_id}: {str(e)}"
        )
    



@router.get("/selected-services/by-type", response_model=List[Dict[str, Any]])
async def get_selected_services_by_type_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get selected services analytics categorized by service type.
    Shows count of selections and most common recommendation rank.
    
    Returns:
    - **service_type**: Type of service (hotel, bus, etc.)
    - **selected_count**: Number of times services of this type were selected
    - **most_common_rank**: The rank that appears most frequently when this service type was recommended
    """
    try:
        analytics_data = await get_selected_services_with_rank_analytics(
            db, current_user.id
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve selected services by type analytics: {str(e)}"
        )


@router.get("/services/count-by-type", response_model=List[Dict[str, Any]])
async def get_services_count_by_type_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of services by type for the current provider.
    Perfect for pie chart visualization in frontend.
    
    Returns:
    - **service_type**: Type of service (hotel, transportation, restaurant, etc.)
    - **count**: Number of services of this type
    """
    try:
        services_count = await get_services_count_by_type(
            db, current_user.id
        )
        
        if not services_count:
            return []
            
        return services_count
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services count by type: {str(e)}"
        )
