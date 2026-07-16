"""AI analysis endpoints.

GET /recommendations reads persisted AI output. POST /analyze is implemented in
Phase 6 (Generative AI integration); until then it returns HTTP 501.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import AiRecommendation
from app.schemas.qos import RecommendationResponse

router = APIRouter(tags=["ai"])


@router.get("/recommendations", response_model=list[RecommendationResponse])
def list_recommendations(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[RecommendationResponse]:
    stmt = (
        select(AiRecommendation)
        .order_by(AiRecommendation.created_at.desc())
        .limit(limit)
    )
    return [RecommendationResponse.model_validate(row) for row in db.scalars(stmt)]


@router.post("/analyze")
def analyze() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Generative AI analysis is implemented in Phase 6."},
    )
