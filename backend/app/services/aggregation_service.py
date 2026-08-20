"""Traceable measurement aggregations (Phase 3).

Supports grouping by ISP, package, region, date, day of week, hour, server,
and metric. Works against SQLite (local) and Supabase Postgres (dissertation).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import normalize_isp, region_from_label

AGGREGATION_DIMENSIONS = (
    "isp",
    "package",
    "region",
    "date",
    "day_of_week",
    "hour",
    "server",
    "metric",
)

METRIC_FIELDS = (
    ("download_mbps", "download_mbps"),
    ("upload_mbps", "upload_mbps"),
    ("ping_ms", "ping_ms"),
    ("jitter_ms", "jitter_ms"),
    ("packet_loss_pct", "packet_loss_pct"),
    ("dns_lookup_ms", "dns_lookup_ms"),
    ("http_response_ms", "http_response_ms"),
    ("overall_score", "overall_score"),
)

DAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _mean(values: Iterable[float | int | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def _bucket_key(row: SpeedTestResult, dimension: str) -> str:
    if dimension == "isp":
        return normalize_isp(row.isp_name)
    if dimension == "package":
        return (row.internet_package or "Unknown").strip() or "Unknown"
    if dimension == "region":
        return (
            (row.detected_region or "").strip()
            or region_from_label(row.server_label)
            or "Unknown"
        )
    if dimension == "date":
        if row.test_date:
            return str(row.test_date)
        ts = _aware(row.timestamp)
        return ts.date().isoformat() if ts else "Unknown"
    if dimension == "day_of_week":
        dow = row.day_of_week
        if dow is None:
            ts = _aware(row.timestamp)
            dow = ts.weekday() if ts else None
        if dow is None:
            return "Unknown"
        return DAY_NAMES[int(dow) % 7]
    if dimension == "hour":
        hour = row.hour_utc
        if hour is None:
            ts = _aware(row.timestamp)
            hour = ts.hour if ts else None
        if hour is None:
            return "Unknown"
        return f"{int(hour):02d}:00"
    if dimension == "server":
        return row.server_id or row.server_label or "Unknown"
    return "Unknown"


def _metric_summary(rows: list[SpeedTestResult]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "avg_download_mbps": _mean(r.download_mbps for r in rows),
        "avg_upload_mbps": _mean(r.upload_mbps for r in rows),
        "avg_ping_ms": _mean(r.ping_ms for r in rows),
        "avg_jitter_ms": _mean(r.jitter_ms for r in rows),
        "avg_packet_loss_pct": _mean(r.packet_loss_pct for r in rows),
        "avg_dns_lookup_ms": _mean(r.dns_lookup_ms for r in rows),
        "avg_http_response_ms": _mean(r.http_response_ms for r in rows),
        "avg_overall_score": _mean(r.overall_score for r in rows),
    }


def aggregate_measurements(
    db: Session,
    *,
    by: str = "isp",
    days: int | None = 30,
    metric: str | None = None,
) -> dict[str, Any]:
    """Group ``speed_tests`` by a documented dimension."""
    dimension = (by or "isp").strip().lower()
    if dimension not in AGGREGATION_DIMENSIONS:
        raise ValueError(
            f"Unsupported aggregation dimension '{by}'. "
            f"Use one of: {', '.join(AGGREGATION_DIMENSIONS)}"
        )

    stmt = select(SpeedTestResult).order_by(SpeedTestResult.timestamp.asc())
    if days:
        cutoff = _utcnow() - timedelta(days=days)
        stmt = stmt.where(SpeedTestResult.timestamp >= cutoff)
    rows = list(db.scalars(stmt))

    if dimension == "metric":
        chosen = (metric or "download_mbps").strip()
        allowed = {src for src, _ in METRIC_FIELDS}
        if chosen not in allowed:
            raise ValueError(
                f"Unsupported metric '{chosen}'. Use one of: {', '.join(sorted(allowed))}"
            )
        attr = chosen
        buckets = []
        values = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
        buckets.append(
            {
                "key": chosen,
                "label": chosen,
                "count": len(values),
                "avg": _mean(values),
                "min": round(min(values), 2) if values else None,
                "max": round(max(values), 2) if values else None,
            }
        )
        return {
            "dimension": "metric",
            "days": days,
            "metric": chosen,
            "total_rows": len(rows),
            "bucket_count": len(buckets),
            "buckets": buckets,
            "note": "Metric aggregation summarises one column across the filtered window.",
        }

    grouped: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        grouped[_bucket_key(row, dimension)].append(row)

    buckets = []
    for key in sorted(grouped.keys()):
        summary = _metric_summary(grouped[key])
        sample = grouped[key][0]
        buckets.append(
            {
                "key": key,
                "label": key,
                "server_operator": getattr(sample, "server_operator", None)
                if dimension == "server"
                else None,
                "server_location": getattr(sample, "server_location", None)
                if dimension == "server"
                else None,
                **summary,
            }
        )

    return {
        "dimension": dimension,
        "days": days,
        "total_rows": len(rows),
        "bucket_count": len(buckets),
        "buckets": buckets,
        "backend": "sqlalchemy",
        "note": (
            "Aggregations are computed from speed_tests. On Supabase the same "
            "dimensions are also available as SQL views (see database/supabase)."
        ),
    }
