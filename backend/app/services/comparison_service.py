"""Fair ISP comparison (Phase 6).

Compares ISPs with avg / median / min / max / stdev and n=, filtered by package,
region, and time so different tiers or geographies are not mixed unfairly.

Does NOT rank ISPs by raw download speed alone — primary ordering uses QoS
score (then sample size). Raw throughput remains visible as context only.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import default_profile, normalize_isp, region_from_label
from app.services.map_service import resolve_district
from measurement.qos_analysis import rating_from_score

CompareMode = Literal["isp_vs_isp", "isp_vs_benchmark", "isp_vs_ideal"]

METRIC_DEFS = (
    ("download_mbps", "Download", "Mbps", True),
    ("upload_mbps", "Upload", "Mbps", True),
    ("ping_ms", "Ping", "ms", False),
    ("jitter_ms", "Jitter", "ms", False),
    ("packet_loss_pct", "Packet Loss", "%", False),
    ("dns_lookup_ms", "DNS", "ms", False),
    ("http_response_ms", "HTTP", "ms", False),
    ("overall_score", "QoS Score", "/100", True),
    ("fulfilment_pct", "Package Fulfilment", "%", True),
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


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


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _stats(values: Iterable[float | int | None]) -> dict[str, Any]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return {
            "count": 0,
            "avg": None,
            "median": None,
            "min": None,
            "max": None,
            "stdev": None,
        }
    stdev = statistics.pstdev(nums) if len(nums) > 1 else 0.0
    return {
        "count": len(nums),
        "avg": _round(statistics.mean(nums)),
        "median": _round(statistics.median(nums)),
        "min": _round(min(nums)),
        "max": _round(max(nums)),
        "stdev": _round(stdev),
    }


def _fulfilment_value(row: SpeedTestResult) -> float | None:
    vals = [
        v
        for v in (row.download_fulfilment_pct, row.upload_fulfilment_pct)
        if v is not None
    ]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _metric_samples(rows: list[SpeedTestResult], key: str) -> list[float | None]:
    if key == "fulfilment_pct":
        return [_fulfilment_value(r) for r in rows]
    return [getattr(r, key, None) for r in rows]


def _filter_rows(
    rows: list[SpeedTestResult],
    *,
    package: str | None,
    region: str | None,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
    hour_from: int | None,
    hour_to: int | None,
    isps: list[str] | None,
) -> list[SpeedTestResult]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start is None and days:
        start = _utcnow() - timedelta(days=days)
    if end is not None and end.hour == 0 and end.minute == 0 and len((date_to or "").strip()) == 10:
        end = end + timedelta(days=1) - timedelta(microseconds=1)

    package_key = (package or "").strip().lower() or None
    region_key = (region or "").strip().lower() or None
    isp_set = {normalize_isp(x) for x in (isps or []) if x} or None

    out: list[SpeedTestResult] = []
    for row in rows:
        ts = _aware(row.timestamp)
        if start and (ts is None or ts < start):
            continue
        if end and (ts is None or ts > end):
            continue
        if package_key and (row.internet_package or "").strip().lower() != package_key:
            continue
        if region_key:
            district = resolve_district(row).lower()
            locality = (region_from_label(row.server_label) or "").lower()
            if region_key not in district and region_key not in locality:
                continue
        if isp_set and normalize_isp(row.isp_name) not in isp_set:
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
            elif not (hour >= h_from or hour <= h_to):
                continue
        out.append(row)
    return out


def _ideal_target(key: str, profile) -> float | None:
    mapping = {
        "download_mbps": profile.download_mbps,
        "upload_mbps": profile.upload_mbps,
        "ping_ms": profile.ping_ms,
        "jitter_ms": profile.jitter_ms,
        "packet_loss_pct": profile.packet_loss_pct,
        "overall_score": float(profile.overall_score),
        "fulfilment_pct": 100.0,
        "dns_lookup_ms": 50.0,
        "http_response_ms": 300.0,
    }
    return mapping.get(key)


def _vs_target(actual: float | None, target: float | None, higher_is_better: bool) -> dict[str, Any]:
    if actual is None or target is None:
        return {"target": target, "gap": None, "meets_target": None, "delta_pct": None}
    gap = round(actual - target, 2)
    meets = actual >= target if higher_is_better else actual <= target
    if target == 0:
        delta_pct = None
    elif higher_is_better:
        delta_pct = round((actual / target) * 100.0, 1)
    else:
        # Lower is better: 100% means matching target; >100 worse
        delta_pct = round((target / max(actual, 0.001)) * 100.0, 1)
    return {
        "target": target,
        "gap": gap,
        "meets_target": meets,
        "delta_pct": delta_pct,
    }


def compare_isps(
    db: Session,
    *,
    mode: CompareMode = "isp_vs_isp",
    isp_a: str | None = None,
    isp_b: str | None = None,
    package: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int | None = 90,
    hour_from: int | None = None,
    hour_to: int | None = None,
) -> dict[str, Any]:
    mode_key = (mode or "isp_vs_isp").strip().lower()
    if mode_key not in {"isp_vs_isp", "isp_vs_benchmark", "isp_vs_ideal"}:
        raise ValueError(
            "mode must be isp_vs_isp, isp_vs_benchmark, or isp_vs_ideal"
        )

    all_rows = list(db.scalars(select(SpeedTestResult).order_by(SpeedTestResult.timestamp.asc())))
    option_rows = _filter_rows(
        all_rows,
        package=None,
        region=None,
        date_from=date_from,
        date_to=date_to,
        days=days,
        hour_from=None,
        hour_to=None,
        isps=None,
    )

    selected: list[str] | None = None
    if mode_key == "isp_vs_isp" and (isp_a or isp_b):
        selected = [x for x in (isp_a, isp_b) if x]

    rows = _filter_rows(
        all_rows,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=None if (date_from or date_to) else days,
        hour_from=hour_from,
        hour_to=hour_to,
        isps=selected,
    )

    grouped: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        grouped[normalize_isp(row.isp_name)].append(row)

    profile = default_profile()
    include_targets = mode_key in {"isp_vs_benchmark", "isp_vs_ideal"}

    isp_rows: list[dict[str, Any]] = []
    for isp, items in grouped.items():
        metrics = []
        for key, label, unit, higher in METRIC_DEFS:
            samples = _metric_samples(items, key)
            block = _stats(samples)
            entry: dict[str, Any] = {
                "key": key,
                "label": label,
                "unit": unit,
                "higher_is_better": higher,
                **block,
            }
            if include_targets:
                target = _ideal_target(key, profile)
                entry.update(_vs_target(block["avg"], target, higher))
            metrics.append(entry)

        qos_avg = next((m["avg"] for m in metrics if m["key"] == "overall_score"), None)
        fulfilment_avg = next((m["avg"] for m in metrics if m["key"] == "fulfilment_pct"), None)
        isp_rows.append(
            {
                "isp": isp,
                "tests": len(items),
                "qos_score": qos_avg,
                "qos_rating": rating_from_score(int(round(qos_avg))) if qos_avg is not None else None,
                "fulfilment_pct": fulfilment_avg,
                "metrics": metrics,
            }
        )

    # Fair ordering: QoS first, then n=, never raw download Mbps.
    isp_rows.sort(key=lambda r: (-(r["qos_score"] if r["qos_score"] is not None else -1), -r["tests"], r["isp"]))

    pairwise = None
    if mode_key == "isp_vs_isp" and isp_a and isp_b:
        left = next((r for r in isp_rows if r["isp"] == normalize_isp(isp_a)), None)
        right = next((r for r in isp_rows if r["isp"] == normalize_isp(isp_b)), None)
        if left and right:
            deltas = []
            for m_a, m_b in zip(left["metrics"], right["metrics"]):
                avg_a, avg_b = m_a["avg"], m_b["avg"]
                if avg_a is None or avg_b is None:
                    delta = None
                    better = None
                else:
                    delta = round(avg_a - avg_b, 2)
                    if m_a["higher_is_better"]:
                        better = left["isp"] if avg_a > avg_b else (right["isp"] if avg_b > avg_a else "tie")
                    else:
                        better = left["isp"] if avg_a < avg_b else (right["isp"] if avg_b < avg_a else "tie")
                deltas.append(
                    {
                        "key": m_a["key"],
                        "label": m_a["label"],
                        "unit": m_a["unit"],
                        "isp_a_avg": avg_a,
                        "isp_b_avg": avg_b,
                        "delta": delta,
                        "better": better,
                    }
                )
            pairwise = {
                "isp_a": left["isp"],
                "isp_b": right["isp"],
                "deltas": deltas,
                "note": "Delta is A − B. ‘Better’ respects whether higher or lower values are desirable.",
            }

    return {
        "mode": mode_key,
        "profile": profile.model_dump() if include_targets else None,
        "isps": isp_rows,
        "pairwise": pairwise,
        "filters": {
            "isp_a": isp_a,
            "isp_b": isp_b,
            "package": package,
            "region": region,
            "date_from": date_from,
            "date_to": date_to,
            "days": days,
            "hour_from": hour_from,
            "hour_to": hour_to,
        },
        "available_isps": sorted({normalize_isp(r.isp_name) for r in option_rows if r.isp_name}),
        "available_packages": sorted(
            {(r.internet_package or "").strip() for r in option_rows if r.internet_package}
        ),
        "available_regions": sorted({resolve_district(r) for r in option_rows}),
        "total_tests": len(rows),
        "ranking_note": (
            "ISPs are ordered by mean QoS score (then sample size), not raw download speed. "
            "Filter by package and region before comparing throughput."
        ),
        "generated_at": _utcnow().isoformat().replace("+00:00", "Z"),
    }
