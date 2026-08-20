"""Mauritius geographic QoS map aggregations (Phase 5).

Builds a GeoJSON FeatureCollection of districts with filtered metric averages
and documented colour-scale thresholds for the administrator map.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import normalize_isp, region_from_label
from measurement.qos_analysis import rating_from_score

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "measurement" / "mauritius_districts.geojson"

MAP_METRICS = (
    "download",
    "upload",
    "latency",
    "jitter",
    "packet_loss",
    "qos",
    "fulfilment",
)

# Continuous colour stops: Excellent → Critical (higher-is-better metrics).
# Hex colours chosen for sequential readability (teal→amber→rose), not rainbow.
COLOUR_STOPS = (
    ("Excellent", "#059669", 90),
    ("Good", "#10b981", 75),
    ("Fair", "#f59e0b", 60),
    ("Poor", "#f97316", 40),
    ("Critical", "#e11d48", 0),
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


@lru_cache(maxsize=1)
def load_district_geojson() -> dict[str, Any]:
    with GEOJSON_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("type") != "FeatureCollection":
        raise ValueError("mauritius_districts.geojson must be a FeatureCollection")
    return payload


def district_catalog() -> list[dict[str, Any]]:
    features = load_district_geojson().get("features") or []
    out = []
    for feature in features:
        props = feature.get("properties") or {}
        out.append(
            {
                "id": props.get("id"),
                "name": props.get("name"),
                "aliases": list(props.get("aliases") or []),
            }
        )
    return out


def resolve_district(row: SpeedTestResult) -> str:
    """Map a measurement to a Mauritius district name."""
    candidates = [
        getattr(row, "detected_region", None),
        getattr(row, "detected_city", None),
        getattr(row, "server_location", None),
        region_from_label(getattr(row, "server_label", None)),
    ]
    blob = " ".join(str(c).lower() for c in candidates if c)
    for district in district_catalog():
        aliases = [a.lower() for a in district["aliases"]]
        name = str(district["name"]).lower()
        if name in blob or any(alias in blob for alias in aliases):
            return str(district["name"])
    # Fall back to locality label so unknown points still appear in tables.
    return region_from_label(getattr(row, "server_label", None)) or "Unknown"


def _metric_value(row: SpeedTestResult, metric: str) -> float | None:
    if metric == "download":
        return row.download_mbps
    if metric == "upload":
        return row.upload_mbps
    if metric == "latency":
        return row.ping_ms
    if metric == "jitter":
        return row.jitter_ms
    if metric == "packet_loss":
        return row.packet_loss_pct
    if metric == "qos":
        return float(row.overall_score) if row.overall_score is not None else None
    if metric == "fulfilment":
        vals = [
            v
            for v in (row.download_fulfilment_pct, row.upload_fulfilment_pct)
            if v is not None
        ]
        return _mean(vals)
    return None


def _higher_is_better(metric: str) -> bool:
    return metric in {"download", "upload", "qos", "fulfilment"}


def _score_0_100(value: float | None, metric: str) -> float | None:
    """Normalise a metric into 0–100 for colouring (100 = best)."""
    if value is None:
        return None
    if metric == "qos":
        return max(0.0, min(100.0, float(value)))
    if metric == "fulfilment":
        # 100% of advertised = Excellent band; >100 still excellent.
        return max(0.0, min(100.0, float(value)))
    if metric == "download":
        # Align loosely with qos_analysis download bands.
        if value >= 200:
            return 100.0
        if value >= 100:
            return 90.0
        if value >= 50:
            return 80.0
        if value >= 25:
            return 65.0
        if value >= 10:
            return 45.0
        return 25.0
    if metric == "upload":
        if value >= 50:
            return 100.0
        if value >= 20:
            return 90.0
        if value >= 10:
            return 75.0
        if value >= 5:
            return 60.0
        if value >= 2:
            return 40.0
        return 20.0
    if metric == "latency":
        if value <= 20:
            return 100.0
        if value <= 40:
            return 90.0
        if value <= 60:
            return 75.0
        if value <= 100:
            return 60.0
        if value <= 150:
            return 40.0
        return 20.0
    if metric == "jitter":
        if value <= 5:
            return 100.0
        if value <= 10:
            return 85.0
        if value <= 20:
            return 70.0
        if value <= 40:
            return 50.0
        return 25.0
    if metric == "packet_loss":
        if value <= 0.1:
            return 100.0
        if value <= 1:
            return 80.0
        if value <= 2:
            return 60.0
        if value <= 5:
            return 35.0
        return 10.0
    return None


def colour_for_score(score: float | None) -> str | None:
    if score is None:
        return None
    for _label, colour, threshold in COLOUR_STOPS:
        if score >= threshold:
            return colour
    return COLOUR_STOPS[-1][1]


def legend_for_metric(metric: str) -> dict[str, Any]:
    higher = _higher_is_better(metric)
    bands = []
    for label, colour, threshold in COLOUR_STOPS:
        bands.append(
            {
                "rating": label,
                "colour": colour,
                "min_score": threshold,
                "meaning": (
                    f"Normalised score ≥ {threshold}"
                    if higher or metric in {"qos", "fulfilment"}
                    else f"Normalised quality score ≥ {threshold}"
                ),
            }
        )
    return {
        "metric": metric,
        "higher_is_better": higher,
        "bands": bands,
        "note": (
            "Colours use a documented Excellent→Critical scale. "
            "Raw averages are shown in tooltips; colour uses the same "
            "quality bands as the SmartQoS rating engine where applicable."
        ),
    }


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _filter_rows(
    rows: list[SpeedTestResult],
    *,
    isp: str | None,
    package: str | None,
    region: str | None,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
    day_of_week: int | None,
    hour_from: int | None,
    hour_to: int | None,
) -> list[SpeedTestResult]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start is None and days:
        start = _utcnow() - timedelta(days=days)
    if end is not None and end.hour == 0 and end.minute == 0 and len((date_to or "").strip()) == 10:
        end = end + timedelta(days=1) - timedelta(microseconds=1)

    isp_key = normalize_isp(isp) if isp else None
    package_key = (package or "").strip().lower() or None
    region_key = (region or "").strip().lower() or None

    filtered: list[SpeedTestResult] = []
    for row in rows:
        ts = _aware(row.timestamp)
        if start and (ts is None or ts < start):
            continue
        if end and (ts is None or ts > end):
            continue
        if isp_key and normalize_isp(row.isp_name) != isp_key:
            continue
        if package_key:
            name = (row.internet_package or "").strip().lower()
            if name != package_key:
                continue
        if region_key:
            district = resolve_district(row).lower()
            locality = (region_from_label(row.server_label) or "").lower()
            if region_key not in district and region_key not in locality:
                continue
        if day_of_week is not None:
            dow = row.day_of_week if row.day_of_week is not None else (ts.weekday() if ts else None)
            if dow != day_of_week:
                continue
        if hour_from is not None or hour_to is not None:
            hour = row.hour_utc if row.hour_utc is not None else (ts.hour if ts else None)
            if hour is None:
                continue
            h_from = 0 if hour_from is None else int(hour_from)
            h_to = 23 if hour_to is None else int(hour_to)
            if h_from <= h_to:
                if not (h_from <= hour <= h_to):
                    continue
            else:
                # Overnight window e.g. 22–6
                if not (hour >= h_from or hour <= h_to):
                    continue
        filtered.append(row)
    return filtered


def build_qos_map(
    db: Session,
    *,
    metric: str = "qos",
    isp: str | None = None,
    package: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int | None = 30,
    day_of_week: int | None = None,
    hour_from: int | None = None,
    hour_to: int | None = None,
) -> dict[str, Any]:
    metric_key = (metric or "qos").strip().lower()
    if metric_key not in MAP_METRICS:
        raise ValueError(
            f"Unsupported map metric '{metric}'. Use one of: {', '.join(MAP_METRICS)}"
        )

    stmt = select(SpeedTestResult).order_by(SpeedTestResult.timestamp.asc())
    all_rows = list(db.scalars(stmt))
    # Options should stay stable while a filter is applied (use date window only).
    option_rows = _filter_rows(
        all_rows,
        isp=None,
        package=None,
        region=None,
        date_from=date_from,
        date_to=date_to,
        days=days,
        day_of_week=None,
        hour_from=None,
        hour_to=None,
    )
    rows = _filter_rows(
        all_rows,
        isp=isp,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=days,
        day_of_week=day_of_week,
        hour_from=hour_from,
        hour_to=hour_to,
    )

    by_district: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        by_district[resolve_district(row)].append(row)

    geo = load_district_geojson()
    features: list[dict[str, Any]] = []
    for feature in geo.get("features") or []:
        props = dict(feature.get("properties") or {})
        name = props.get("name") or "Unknown"
        items = by_district.get(name, [])
        avg_download = _mean(r.download_mbps for r in items)
        avg_upload = _mean(r.upload_mbps for r in items)
        avg_ping = _mean(r.ping_ms for r in items)
        avg_jitter = _mean(r.jitter_ms for r in items)
        avg_loss = _mean(r.packet_loss_pct for r in items)
        avg_qos = _mean(r.overall_score for r in items)
        avg_fulfilment = _mean(
            v
            for r in items
            for v in (r.download_fulfilment_pct, r.upload_fulfilment_pct)
            if v is not None
        )
        metric_avg = {
            "download": avg_download,
            "upload": avg_upload,
            "latency": avg_ping,
            "jitter": avg_jitter,
            "packet_loss": avg_loss,
            "qos": avg_qos,
            "fulfilment": avg_fulfilment,
        }[metric_key]
        score = _score_0_100(metric_avg, metric_key)
        colour = colour_for_score(score)
        rating = rating_from_score(int(round(score))) if score is not None else None
        features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    **props,
                    "tests": len(items),
                    "avg_download_mbps": avg_download,
                    "avg_upload_mbps": avg_upload,
                    "avg_ping_ms": avg_ping,
                    "avg_jitter_ms": avg_jitter,
                    "avg_packet_loss_pct": avg_loss,
                    "avg_qos_score": avg_qos,
                    "avg_fulfilment_pct": avg_fulfilment,
                    "metric": metric_key,
                    "metric_value": metric_avg,
                    "colour_score": score,
                    "colour": colour,
                    "rating": rating,
                },
            }
        )

    # Include unknown districts that have data but no polygon.
    known = {f["properties"]["name"] for f in features}
    for name, items in by_district.items():
        if name in known or name == "Unknown":
            continue
        # Skip — only polygon districts are painted; unknown counted in meta.

    isps = sorted({normalize_isp(r.isp_name) for r in option_rows if r.isp_name})
    packages = sorted(
        {(r.internet_package or "").strip() for r in option_rows if r.internet_package}
    )
    regions = sorted({resolve_district(r) for r in option_rows})

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "metric": metric_key,
            "total_tests": len(rows),
            "districts_with_data": sum(
                1 for f in features if (f["properties"] or {}).get("tests")
            ),
            "filters": {
                "isp": isp,
                "package": package,
                "region": region,
                "date_from": date_from,
                "date_to": date_to,
                "days": days,
                "day_of_week": day_of_week,
                "hour_from": hour_from,
                "hour_to": hour_to,
            },
            "available_isps": isps,
            "available_packages": packages,
            "available_regions": regions,
            "generated_at": _utcnow().isoformat().replace("+00:00", "Z"),
        },
        "legend": legend_for_metric(metric_key),
        "metrics": list(MAP_METRICS),
    }
