"""AI analysis endpoints (Phase 6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import AiRecommendation
from app.schemas.qos import AnalyzeRequest, AnalyzeResponse, RecommendationResponse
from app.services import ai_service
from app.services.ai_service import AnalysisError

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


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Generate a natural-language QoS explanation and corrective actions.

    Uses an OpenAI-compatible LLM when ``QOS_OPENAI_API_KEY`` is set; otherwise
    falls back to the deterministic telecom playbook generator.
    """
    try:
        result = ai_service.analyze_incident(
            db,
            anomaly_id=payload.anomaly_id,
            node_code=payload.node_code,
            include_recent_history=payload.include_recent_history,
        )
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return AnalyzeResponse(
        recommendation_id=result.recommendation_id,
        anomaly_id=result.anomaly_id,
        node_code=result.node_code,
        summary=result.summary,
        likely_causes=result.likely_causes,
        recommended_actions=result.recommended_actions,
        severity=result.severity,
        model_provider=result.model_provider,
        created_at=result.created_at,
    )
