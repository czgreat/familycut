from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_exercises import router as exercises_router
from app.api.routes_measurements import router as measurements_router
from app.api.routes_media import router as media_router
from app.api.routes_members import router as members_router
from app.api.routes_nutrition import router as nutrition_router
from app.api.routes_reports import router as reports_router
from app.api.routes_settings import router as settings_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(exercises_router)
api_router.include_router(members_router)
api_router.include_router(measurements_router)
api_router.include_router(nutrition_router)
api_router.include_router(media_router)
api_router.include_router(reports_router)
api_router.include_router(settings_router)
