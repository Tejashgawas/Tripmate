# ...existing imports and code...
# app/routes/__init__.py
from fastapi import APIRouter
from app.routes.auth import auth, profile
from app.routes.trip import trip_routes, trip_member, invitation, trip_member_preference, checklist
from app.routes.itineraries import itinerary_routes
from app.routes.recommendations import recommend
from app.routes.services import service_provider

from app.routes.expense import expense


api_router = APIRouter()


# Auth routes
api_router.include_router(auth.router)
api_router.include_router(profile.router)

# Alias /users for /users/me endpoints
from fastapi import APIRouter, Depends
from app.routes.auth import profile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user.user import User
from app.services.auth.profile_service import ProfileService
from app.dependencies.auth import get_current_user

users_router = APIRouter()
users_router.include_router(profile.router, prefix="/users", tags=["Profile"])
from app.schemas.user.user import UserUpdate, UserOut
# Add /users/me without trailing slash
@users_router.get("/users/me", response_model=UserOut, include_in_schema=False)
async def get_my_profile_no_slash(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
	return await ProfileService.get_user_by_id(current_user.id, db)
# Add PATCH /users/me for test compatibility
@users_router.patch("/users/me", response_model=UserOut, include_in_schema=False)
async def patch_my_profile(data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
	return await ProfileService.update_user_profile(current_user.id, data, db)
# Add DELETE /users/me for test compatibility
@users_router.delete("/users/me", response_model=UserOut, include_in_schema=False)
async def delete_my_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
	from app.models.user.user import User as UserModel
	user_obj = await db.get(UserModel, current_user.id)
	if user_obj is None:
		from fastapi import HTTPException
		raise HTTPException(status_code=404, detail="User not found")
	await db.delete(user_obj)
	await db.commit()
	return current_user
api_router.include_router(users_router)

# Trip routes
api_router.include_router(trip_routes.router)
api_router.include_router(trip_member.router)
api_router.include_router(invitation.router)
api_router.include_router(trip_member_preference.router)
api_router.include_router(checklist.router)

# Itinerary routes
api_router.include_router(itinerary_routes.router)

# Recommendation routes
api_router.include_router(recommend.router)


# Service provider routes
api_router.include_router(service_provider.router)

# Alias /service-provider for test compatibility
service_provider_alias = APIRouter()
service_provider_alias.include_router(service_provider.router, prefix="/service-provider", tags=["Provider Services"])
from app.schemas.services.service_schema import ServiceCreate, ServiceResponse
from app.dependencies.auth import require_role
from app.models.user.user import User, UserRole
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.service.provider_Service import ServiceProviderService
from fastapi import Body
# Add POST /service-provider endpoint (calls the real handler)
@service_provider_alias.post("/service-provider", response_model=ServiceResponse, include_in_schema=False)
async def create_service_provider(
	data: ServiceCreate = Body(...),
	user: User = Depends(require_role(UserRole.provider)),
	db: AsyncSession = Depends(get_db)
):
	return await ServiceProviderService.create_service(user, data, db)
api_router.include_router(service_provider_alias)


# Expense routes
api_router.include_router(expense.router)

# Feedback routes
from app.routes.feedback import feedback_routes
api_router.include_router(feedback_routes.router)
