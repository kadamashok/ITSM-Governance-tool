from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.config import router as config_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(config_router, tags=["config"])
api_router.include_router(sync_router, tags=["sync"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(dashboard_router, tags=["dashboard"])
