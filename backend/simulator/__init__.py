"""Broadband QoS network simulator package.

Generates synthetic ISP-style measurements for normal operation and
degradation scenarios used by the monitoring backend and ML pipeline.
"""

from .generator import QoSSimulator
from .models import NetworkEvent, NetworkNode, QoSMeasurement

__all__ = [
    "NetworkEvent",
    "NetworkNode",
    "QoSMeasurement",
    "QoSSimulator",
]
