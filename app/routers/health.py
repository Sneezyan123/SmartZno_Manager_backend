from fastapi import APIRouter, Depends

from app import db
from app.config import Settings, get_settings
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        db="memory" if db.using_memory() else "mongo",
        tz=settings.tz,
    )
