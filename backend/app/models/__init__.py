"""ORM models for the broadband QoS monitoring platform."""

from app.models.network import (
    AiRecommendation,
    AnomalyResult,
    NetworkEvent,
    NetworkNode,
    QoSMeasurement,
)
from app.models.speedtest import SpeedTestResult
from app.models.monitoring import MonitoringState

__all__ = [
    "AiRecommendation",
    "AnomalyResult",
    "NetworkEvent",
    "NetworkNode",
    "QoSMeasurement",
    "SpeedTestResult",
    "MonitoringState",
]
