"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.qos import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    database = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - report any DB failure as a status
        database = "unavailable"
    return HealthResponse(status="ok", service=settings.app_name, database=database)
