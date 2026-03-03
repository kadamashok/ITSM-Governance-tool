from app.schemas.health import HealthResponse
from app.utils.config import get_settings


def get_health_status() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
