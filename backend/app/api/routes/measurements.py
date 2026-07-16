"""Measurement ingestion endpoint used by the simulator."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.qos import MeasurementCreate, MeasurementCreateResponse
from app.services import measurement_service
from app.services.measurement_service import NodeNotFoundError

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.post(
    "",
    response_model=MeasurementCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
) -> MeasurementCreateResponse:
    """Store a single QoS measurement."""
    try:
        measurement = measurement_service.create_measurement(db, payload)
    except NodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return MeasurementCreateResponse(measurement_id=measurement.id, stored=True)
