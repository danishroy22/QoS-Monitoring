"""ORM models for the broadband QoS monitoring platform."""

from app.models.network import (
    AiRecommendation,
    AnomalyResult,
    NetworkEvent,
    NetworkNode,
    QoSMeasurement,
)
from app.models.speedtest import SpeedTestResult

__all__ = [
    "AiRecommendation",
    "AnomalyResult",
    "NetworkEvent",
    "NetworkNode",
    "QoSMeasurement",
    "SpeedTestResult",
]
