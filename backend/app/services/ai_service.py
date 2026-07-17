"""Generative AI analysis service for broadband QoS incidents."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.models.network import AiRecommendation, AnomalyResult, NetworkNode, QoSMeasurement
from app.services.ai_fallback import generate_fallback_analysis
from app.services.ai_llm import LLMError, call_chat_completion
from app.services.ai_prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.health_rules import classify_health
from backend.ml.classifier import classify_severity, classify_suspected_issue
from backend.ml.features import MODEL_NAME

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    recommendation_id: int
    anomaly_id: int
    node_code: str
    summary: str
    likely_causes: list[str]
    recommended_actions: list[str]
    severity: str
    model_provider: str
    created_at: datetime


class AnalysisError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _join_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _split_lines(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if cleaned:
            rows.append(cleaned)
    return rows


def _measurement_context(
    measurement: QoSMeasurement,
    node: NetworkNode,
    anomaly: AnomalyResult,
    history: list[QoSMeasurement],
) -> dict:
    recent = []
    for sample in history[-8:]:
        recent.append(
            f"{sample.timestamp.isoformat()} lat={sample.latency_ms}ms "
            f"loss={sample.packet_loss_pct}% util={sample.bandwidth_utilisation_pct}% "
            f"thru={sample.throughput_mbps}Mbps avail={sample.availability_pct}%"
        )
    return {
        "node_code": node.node_code,
        "region": node.region,
        "access_technology": node.access_technology,
        "service_tier_mbps": node.service_tier_mbps,
        "suspected_issue": anomaly.suspected_issue or "performance_degradation",
        "anomaly_score": anomaly.anomaly_score,
        "severity_hint": anomaly.severity,
        "timestamp": measurement.timestamp.isoformat(),
        "latency_ms": measurement.latency_ms,
        "jitter_ms": measurement.jitter_ms,
        "packet_loss_pct": measurement.packet_loss_pct,
        "throughput_mbps": measurement.throughput_mbps,
        "bandwidth_utilisation_pct": measurement.bandwidth_utilisation_pct,
        "signal_quality": measurement.signal_quality,
        "availability_pct": measurement.availability_pct,
        "scenario_label": measurement.scenario_label,
        "recent_history": recent,
    }


def _resolve_anomaly(
    db: Session,
    *,
    anomaly_id: int | None,
    node_code: str | None,
) -> tuple[AnomalyResult, QoSMeasurement, NetworkNode]:
    if anomaly_id is not None:
        anomaly = db.scalar(
            select(AnomalyResult)
            .options(
                joinedload(AnomalyResult.measurement).joinedload(QoSMeasurement.node),
                joinedload(AnomalyResult.recommendation),
            )
            .where(AnomalyResult.id == anomaly_id)
        )
        if anomaly is None:
            raise AnalysisError(f"Anomaly id {anomaly_id} not found", status_code=404)
        measurement = anomaly.measurement
        node = measurement.node
        return anomaly, measurement, node

    if not node_code:
        raise AnalysisError("Provide anomaly_id or node_code")

    node = db.scalar(select(NetworkNode).where(NetworkNode.node_code == node_code))
    if node is None:
        raise AnalysisError(f"Unknown node_code: {node_code}", status_code=404)

    # Prefer the latest flagged anomaly for the node.
    anomaly = db.scalar(
        select(AnomalyResult)
        .join(QoSMeasurement, AnomalyResult.measurement_id == QoSMeasurement.id)
        .options(
            joinedload(AnomalyResult.measurement).joinedload(QoSMeasurement.node),
            joinedload(AnomalyResult.recommendation),
        )
        .where(QoSMeasurement.node_id == node.id, AnomalyResult.is_anomaly.is_(True))
        .order_by(AnomalyResult.created_at.desc())
        .limit(1)
    )
    if anomaly is not None:
        return anomaly, anomaly.measurement, node

    # Otherwise synthesise an anomaly from the latest measurement so analysis
    # can still be persisted against the schema.
    measurement = db.scalar(
        select(QoSMeasurement)
        .where(QoSMeasurement.node_id == node.id)
        .order_by(QoSMeasurement.timestamp.desc())
        .limit(1)
    )
    if measurement is None:
        raise AnalysisError(
            f"No measurements available for node {node_code}",
            status_code=404,
        )

    row = {
        "latency_ms": measurement.latency_ms,
        "jitter_ms": measurement.jitter_ms,
        "packet_loss_pct": measurement.packet_loss_pct,
        "throughput_mbps": measurement.throughput_mbps,
        "bandwidth_utilisation_pct": measurement.bandwidth_utilisation_pct,
        "availability_pct": measurement.availability_pct,
        "service_tier_mbps": node.service_tier_mbps,
        "signal_quality": measurement.signal_quality,
    }
    health = classify_health(
        latency_ms=row["latency_ms"],
        jitter_ms=row["jitter_ms"],
        packet_loss_pct=row["packet_loss_pct"],
        bandwidth_utilisation_pct=row["bandwidth_utilisation_pct"],
        availability_pct=row["availability_pct"],
    )
    suspected = classify_suspected_issue(row)
    severity = classify_severity(anomaly_score=0.0, row=row)
    anomaly = AnomalyResult(
        measurement_id=measurement.id,
        model_name=f"{MODEL_NAME}+ai-context",
        anomaly_score=0.0,
        is_anomaly=health != "healthy",
        severity=severity if health != "healthy" else "low",
        suspected_issue=suspected if health != "healthy" else "performance_degradation",
    )
    db.add(anomaly)
    db.flush()
    return anomaly, measurement, node


def _generate(context: dict, settings: Settings) -> dict:
    if settings.ai_enabled:
        try:
            result = call_chat_completion(
                settings=settings,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(context),
            )
            logger.info("AI analysis produced by %s", result.get("model_provider"))
            return result
        except LLMError as exc:
            logger.warning("LLM failed, using offline fallback: %s", exc)
    return generate_fallback_analysis(context)


def analyze_incident(
    db: Session,
    *,
    anomaly_id: int | None = None,
    node_code: str | None = None,
    include_recent_history: bool = True,
    settings: Settings | None = None,
) -> AnalysisResult:
    """Generate and persist an AI explanation for an anomaly or node."""
    settings = settings or get_settings()
    anomaly, measurement, node = _resolve_anomaly(
        db, anomaly_id=anomaly_id, node_code=node_code
    )

    history: list[QoSMeasurement] = []
    if include_recent_history:
        history = list(
            db.scalars(
                select(QoSMeasurement)
                .where(QoSMeasurement.node_id == node.id)
                .order_by(QoSMeasurement.timestamp.desc())
                .limit(12)
            )
        )
        history.reverse()

    context = _measurement_context(measurement, node, anomaly, history)
    generated = _generate(context, settings)

    # Replace any previous recommendation for this anomaly.
    if anomaly.recommendation is not None:
        db.delete(anomaly.recommendation)
        db.flush()

    recommendation = AiRecommendation(
        anomaly_id=anomaly.id,
        summary=str(generated["summary"]).strip(),
        likely_causes=_join_lines([str(x) for x in generated["likely_causes"]]),
        recommended_actions=_join_lines(
            [str(x) for x in generated["recommended_actions"]]
        ),
        model_provider=str(generated.get("model_provider", "unknown")),
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return AnalysisResult(
        recommendation_id=recommendation.id,
        anomaly_id=anomaly.id,
        node_code=node.node_code,
        summary=recommendation.summary,
        likely_causes=_split_lines(recommendation.likely_causes),
        recommended_actions=_split_lines(recommendation.recommended_actions),
        severity=str(generated.get("severity", anomaly.severity)),
        model_provider=recommendation.model_provider,
        created_at=recommendation.created_at,
    )
