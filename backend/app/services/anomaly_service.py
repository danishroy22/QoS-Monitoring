"""Run Isolation Forest detection over stored QoS measurements."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.network import AnomalyResult, NetworkNode, QoSMeasurement
from app.services.health_rules import CRITICAL, DEGRADED, classify_health
from backend.ml.classifier import classify_severity, classify_suspected_issue
from backend.ml.detector import AnomalyDetector
from backend.ml.features import MODEL_NAME

logger = logging.getLogger(__name__)


@dataclass
class DetectionRunSummary:
    processed_measurements: int
    anomalies_detected: int
    model_name: str
    skipped_existing: int = 0


@lru_cache(maxsize=1)
def get_detector() -> AnomalyDetector:
    """Load the trained model once per process."""
    return AnomalyDetector.load()


def clear_detector_cache() -> None:
    get_detector.cache_clear()


def _is_operational_anomaly(row: dict, forest_flag: bool) -> bool:
    """Hybrid decision: Isolation Forest or clear QoS threshold breach.

    Pure IF can miss mild high-latency / bandwidth-cap cases that are still
    operationally important. Threshold confirmation improves recall for the NOC
    while keeping the ML score as the primary evidence field.
    """
    if forest_flag:
        return True
    health = classify_health(
        latency_ms=row["latency_ms"],
        jitter_ms=row["jitter_ms"],
        packet_loss_pct=row["packet_loss_pct"],
        bandwidth_utilisation_pct=row["bandwidth_utilisation_pct"],
        availability_pct=row["availability_pct"],
    )
    return health in {DEGRADED, CRITICAL}


def run_detection(
    db: Session,
    *,
    limit: int = 500,
    only_unscored: bool = True,
) -> DetectionRunSummary:
    """Score recent measurements and persist anomaly rows."""
    detector = get_detector()

    stmt = (
        select(QoSMeasurement)
        .options(joinedload(QoSMeasurement.node), joinedload(QoSMeasurement.anomaly))
        .order_by(QoSMeasurement.timestamp.desc())
        .limit(limit)
    )
    measurements = list(db.scalars(stmt).unique())

    to_score: list[QoSMeasurement] = []
    skipped = 0
    for measurement in measurements:
        if only_unscored and measurement.anomaly is not None:
            skipped += 1
            continue
        to_score.append(measurement)

    if not to_score:
        return DetectionRunSummary(
            processed_measurements=0,
            anomalies_detected=0,
            model_name=MODEL_NAME,
            skipped_existing=skipped,
        )

    feature_rows = []
    for m in to_score:
        node: NetworkNode = m.node
        feature_rows.append(
            {
                "latency_ms": m.latency_ms,
                "jitter_ms": m.jitter_ms,
                "packet_loss_pct": m.packet_loss_pct,
                "throughput_mbps": m.throughput_mbps,
                "bandwidth_utilisation_pct": m.bandwidth_utilisation_pct,
                "signal_quality": m.signal_quality,
                "availability_pct": m.availability_pct,
                "service_tier_mbps": node.service_tier_mbps if node else 0.0,
                "scenario_label": m.scenario_label,
            }
        )

    predictions = detector.predict_many(feature_rows)
    anomalies = 0

    for measurement, row, pred in zip(to_score, feature_rows, predictions, strict=True):
        if measurement.anomaly is not None:
            db.delete(measurement.anomaly)
            db.flush()

        is_anomaly = _is_operational_anomaly(row, pred.is_anomaly)
        suspected = classify_suspected_issue(row) if is_anomaly else None
        severity = (
            classify_severity(anomaly_score=pred.anomaly_score, row=row)
            if is_anomaly
            else "low"
        )
        result = AnomalyResult(
            measurement_id=measurement.id,
            model_name=MODEL_NAME,
            anomaly_score=pred.anomaly_score,
            is_anomaly=is_anomaly,
            severity=severity,
            suspected_issue=suspected,
        )
        db.add(result)
        if is_anomaly:
            anomalies += 1

    db.commit()
    logger.info(
        "Detection run complete: processed=%s anomalies=%s skipped=%s",
        len(to_score),
        anomalies,
        skipped,
    )
    return DetectionRunSummary(
        processed_measurements=len(to_score),
        anomalies_detected=anomalies,
        model_name=MODEL_NAME,
        skipped_existing=skipped,
    )
