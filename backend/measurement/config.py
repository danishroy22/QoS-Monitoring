"""Load measurement parameters from measurement_config.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("measurement_config.json")


@lru_cache(maxsize=1)
def load_measurement_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or "full" not in payload:
        raise ValueError("measurement_config.json must contain a 'full' profile")
    return payload


def reload_measurement_config() -> None:
    load_measurement_config.cache_clear()


def load_version() -> str:
    return str(load_measurement_config().get("version") or "2.0")


def profile(quick: bool = False) -> dict[str, Any]:
    cfg = load_measurement_config()
    block = cfg.get("quick") if quick else cfg.get("full")
    return dict(block or cfg["full"])


def public_methodology() -> dict[str, Any]:
    """Safe snapshot for GET /speedtest/config (no secrets)."""
    cfg = load_measurement_config()
    return {
        "version": cfg.get("version"),
        "throughput_mode": cfg.get("throughput_mode"),
        "note": cfg.get("note"),
        "full": cfg.get("full"),
        "quick": cfg.get("quick"),
        "rationale": cfg.get("rationale"),
        "formulas": {
            "download_mbps": "mean(bytes_per_pass * 8 / 1e6 / pass_elapsed_s)",
            "upload_mbps": "uploaded_bytes * 8 / 1e6 / elapsed_s",
            "throughput_mbps": "bytes * 8 / 1e6 / duration_s",
            "packet_loss_pct": "packets_lost / packets_sent * 100",
            "latency_avg_ms": "mean(successful_rtt_samples)",
            "jitter_ms": "population standard deviation of successful RTT samples (existing QoS input)",
        },
        "protocols": {
            "download": "HTTPS GET (chunked) against the configured measurement backend",
            "upload": "HTTPS POST (application/octet-stream)",
            "latency": "ICMP echo via OS ping; TCP connect fallback if ICMP yields no RTTs",
            "dns": "OS getaddrinfo",
            "http": "HTTPS GET with optional DNS/TCP/TLS split timings",
        },
        "server_selection": "See docs/server-selection-methodology.md",
    }


def throughput_mbps(bytes_transferred: int, duration_s: float) -> float:
    return (max(0, int(bytes_transferred)) * 8 / 1_000_000.0) / max(float(duration_s), 0.001)


def packet_loss_pct(sent: int, received: int) -> float:
    sent = max(int(sent), 0)
    received = max(int(received), 0)
    lost = max(sent - received, 0)
    if sent <= 0:
        return 100.0 if received <= 0 else 0.0
    return (lost / sent) * 100.0


def rtt_stats(samples: list[float], *, sent: int, received: int) -> dict[str, Any]:
    """Summarise latency samples. Jitter uses population stdev (QoS engine input)."""
    import statistics

    lost = max(sent - received, 0)
    if not samples:
        return {
            "ping_ms": None,
            "ping_min_ms": None,
            "ping_max_ms": None,
            "ping_median_ms": None,
            "jitter_ms": None,
            "packet_loss_pct": packet_loss_pct(sent, received),
            "packets_sent": sent,
            "packets_received": received,
            "packets_lost": lost,
            "samples": [],
        }
    ordered = sorted(samples)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    jitter = statistics.pstdev(samples) if len(samples) > 1 else 0.0
    return {
        "ping_ms": round(statistics.mean(samples), 2),
        "ping_min_ms": round(min(samples), 2),
        "ping_max_ms": round(max(samples), 2),
        "ping_median_ms": round(median, 2),
        "jitter_ms": round(jitter, 2),
        "packet_loss_pct": round(packet_loss_pct(sent, received), 2),
        "packets_sent": sent,
        "packets_received": received,
        "packets_lost": lost,
        "samples": [round(x, 2) for x in samples],
    }
