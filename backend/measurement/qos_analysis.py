"""QoS Analysis Engine — network health scoring and classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MetricScore:
    name: str
    value: float | None
    unit: str
    score: int
    rating: str


@dataclass(frozen=True)
class HealthReport:
    overall_score: int
    overall_rating: str
    metrics: list[MetricScore]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "overall_rating": self.overall_rating,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "score": m.score,
                    "rating": m.rating,
                }
                for m in self.metrics
            ],
        }


def rating_from_score(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Poor"
    return "Critical"


def _score_ping(ms: float | None) -> int:
    if ms is None:
        return 0
    if ms <= 20:
        return 100
    if ms <= 40:
        return 90
    if ms <= 60:
        return 75
    if ms <= 100:
        return 60
    if ms <= 150:
        return 40
    return 20


def _score_jitter(ms: float | None) -> int:
    if ms is None:
        return 0
    if ms <= 5:
        return 100
    if ms <= 10:
        return 85
    if ms <= 20:
        return 70
    if ms <= 40:
        return 50
    return 25


def _score_loss(pct: float | None) -> int:
    if pct is None:
        return 0
    if pct <= 0.1:
        return 100
    if pct <= 1:
        return 80
    if pct <= 2:
        return 60
    if pct <= 5:
        return 35
    return 10


def _score_download(mbps: float | None) -> int:
    if mbps is None:
        return 0
    if mbps >= 200:
        return 100
    if mbps >= 100:
        return 90
    if mbps >= 50:
        return 80
    if mbps >= 25:
        return 65
    if mbps >= 10:
        return 45
    return 25


def _score_upload(mbps: float | None) -> int:
    if mbps is None:
        return 0
    if mbps >= 50:
        return 100
    if mbps >= 20:
        return 90
    if mbps >= 10:
        return 75
    if mbps >= 5:
        return 60
    if mbps >= 2:
        return 40
    return 20


def _score_dns(ms: float | None) -> int:
    if ms is None:
        return 0
    if ms <= 20:
        return 100
    if ms <= 50:
        return 85
    if ms <= 100:
        return 70
    if ms <= 200:
        return 50
    return 25


def _score_http(ms: float | None) -> int:
    if ms is None:
        return 0
    if ms <= 150:
        return 100
    if ms <= 300:
        return 85
    if ms <= 600:
        return 70
    if ms <= 1200:
        return 50
    return 25


def analyze_qos(sample: dict[str, Any]) -> HealthReport:
    """Compute per-metric and overall network health scores."""
    metrics = [
        MetricScore("Download", sample.get("download_mbps"), "Mbps", _score_download(sample.get("download_mbps")), ""),
        MetricScore("Upload", sample.get("upload_mbps"), "Mbps", _score_upload(sample.get("upload_mbps")), ""),
        MetricScore("Ping", sample.get("ping_ms"), "ms", _score_ping(sample.get("ping_ms")), ""),
        MetricScore("Jitter", sample.get("jitter_ms"), "ms", _score_jitter(sample.get("jitter_ms")), ""),
        MetricScore("Packet Loss", sample.get("packet_loss_pct"), "%", _score_loss(sample.get("packet_loss_pct")), ""),
        MetricScore("DNS Lookup", sample.get("dns_lookup_ms"), "ms", _score_dns(sample.get("dns_lookup_ms")), ""),
        MetricScore("HTTP Response", sample.get("http_response_ms"), "ms", _score_http(sample.get("http_response_ms")), ""),
    ]
    rated = [
        MetricScore(m.name, m.value, m.unit, m.score, rating_from_score(m.score))
        for m in metrics
    ]

    # Weighted overall score emphasising user-visible quality.
    weights = {
        "Download": 0.25,
        "Upload": 0.15,
        "Ping": 0.20,
        "Jitter": 0.10,
        "Packet Loss": 0.15,
        "DNS Lookup": 0.05,
        "HTTP Response": 0.10,
    }
    overall = 0.0
    for metric in rated:
        overall += metric.score * weights.get(metric.name, 0.0)
    overall_score = int(round(overall))
    return HealthReport(
        overall_score=overall_score,
        overall_rating=rating_from_score(overall_score),
        metrics=rated,
    )
