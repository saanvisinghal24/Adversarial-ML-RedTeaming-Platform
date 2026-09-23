from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])

API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse, summary="Liveness + DB connectivity")
def health(db: DbSession) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:  # noqa: BLE001 — health must report, not raise
        database = "down"
    return HealthResponse(
        status="ok" if database == "up" else "degraded",
        environment=settings.ENVIRONMENT,
        database=database,
        version=API_VERSION,
    )
