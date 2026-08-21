"""Peak-hour and congestion-pattern analysis (Phase 8).

Compares evening / busy-hour buckets against off-peak baselines. Wording is
deliberately cautious: measured degradation may be *consistent with* congestion
but cannot independently confirm root cause.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import normalize_isp, region_from_label

DISCLAIMER = (
    "Observed performance degradation may be consistent with a possible congestion "
    "pattern. These measurements alone cannot independently confirm congestion or "
    "any other underlying network cause."
)

INTERPRETATION = (
    "Performance degradation consistent with a possible congestion pattern."
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

METRIC_DEFS = (
    ("download_mbps", "Download", "Mbps", True),
    ("upload_mbps", "Upload", "Mbps", True),
    ("ping_ms", "Latency", "ms", False),
    ("jitter_ms", "Jitter", "ms", False),
    ("packet_loss_pct", "Packet Loss", "%", False),
    ("overall_score", "QoS Score", "/100", True),
)

MIN_HOUR_SAMPLES = 2
WINDOW_LENGTHS = (2, 3, 4)


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


def _mean(values: Iterable[float | int | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _hour_of(row: SpeedTestResult) -> int | None:
    if row.hour_utc is not None:
        return int(row.hour_utc) % 24
    ts = _aware(row.timestamp)
    return ts.hour if ts else None


def _dow_of(row: SpeedTestResult) -> int | None:
    if row.day_of_week is not None:
        return int(row.day_of_week) % 7
    ts = _aware(row.timestamp)
    return ts.weekday() if ts else None


def _region_of(row: SpeedTestResult) -> str:
    return (
        (row.detected_region or "").strip()
        or region_from_label(row.server_label)
        or "Unknown"
    )


def _package_of(row: SpeedTestResult) -> str:
    return (row.internet_package or "").strip() or "Unspecified"


def _load_rows(db: Session) -> list[SpeedTestResult]:
    return list(db.scalars(select(SpeedTestResult).order_by(SpeedTestResult.timestamp)).all())


def _filter_rows(
    rows: list[SpeedTestResult],
    *,
    isp: str | None,
    package: str | None,
    region: str | None,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
) -> list[SpeedTestResult]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if end and len((date_to or "").strip()) == 10:
        end = end + timedelta(days=1)
    if start is None and end is None and days:
        start = _utcnow() - timedelta(days=int(days))

    isp_key = normalize_isp(isp) if isp else None
    package_key = (package or "").strip().lower() or None
    region_key = (region or "").strip().lower() or None

    out: list[SpeedTestResult] = []
    for row in rows:
        ts = _aware(row.timestamp)
        if start and (ts is None or ts < start):
            continue
        if end and (ts is None or ts >= end):
            continue
        if isp_key and normalize_isp(row.isp_name) != isp_key:
            continue
        if package_key and _package_of(row).lower() != package_key:
            continue
        if region_key and _region_of(row).lower() != region_key:
            continue
        out.append(row)
    return out


def _metric_avgs(rows: list[SpeedTestResult]) -> dict[str, float | None]:
    return {key: _mean(getattr(r, key) for r in rows) for key, *_ in METRIC_DEFS}


def _delta_block(
    *,
    key: str,
    label: str,
    unit: str,
    higher_is_better: bool,
    peak_avg: float | None,
    baseline_avg: float | None,
) -> dict[str, Any]:
    delta_abs = None
    delta_pct = None
    degraded = None
    if peak_avg is not None and baseline_avg is not None:
        delta_abs = _round(peak_avg - baseline_avg)
        if abs(baseline_avg) > 1e-9:
            delta_pct = _round(((peak_avg - baseline_avg) / abs(baseline_avg)) * 100.0, 1)
        if higher_is_better:
            degraded = peak_avg < baseline_avg
        else:
            degraded = peak_avg > baseline_avg
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "higher_is_better": higher_is_better,
        "peak_avg": _round(peak_avg),
        "baseline_avg": _round(baseline_avg),
        "delta_pct": delta_pct,
        "delta_abs": delta_abs,
        "degraded": degraded,
    }


def _hour_buckets(rows: list[SpeedTestResult]) -> dict[int, list[SpeedTestResult]]:
    buckets: dict[int, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        hour = _hour_of(row)
        if hour is None:
            continue
        buckets[hour].append(row)
    return buckets


def _window_hours(start: int, length: int) -> list[int]:
    return [(start + offset) % 24 for offset in range(length)]


def _format_window(hours: list[int]) -> tuple[int, int, str]:
    hour_from = hours[0]
    hour_to = (hours[-1] + 1) % 24
    # Display as inclusive start → exclusive end (e.g. 18–21 covers 18,19,20).
    label = f"{hour_from:02d}:00 – {hour_to:02d}:00 UTC"
    return hour_from, hour_to, label


def _degradation_index(peak: dict[str, float | None], baseline: dict[str, float | None]) -> float:
    score = 0.0
    counted = 0
    for key, _label, _unit, higher_is_better in METRIC_DEFS:
        p = peak.get(key)
        b = baseline.get(key)
        if p is None or b is None or abs(b) < 1e-9:
            continue
        if higher_is_better:
            worseness = max(0.0, (b - p) / abs(b))
        else:
            worseness = max(0.0, (p - b) / abs(b))
        score += worseness
        counted += 1
    return score / counted if counted else 0.0


def _find_peak_window(
    hourly_avgs: dict[int, dict[str, float | None]],
    hourly_counts: dict[int, int],
) -> list[int] | None:
    eligible = [h for h, n in hourly_counts.items() if n >= MIN_HOUR_SAMPLES and h in hourly_avgs]
    if len(eligible) < 2:
        return None

    overall = {
        key: _mean(hourly_avgs[h].get(key) for h in eligible)
        for key, *_ in METRIC_DEFS
    }

    best_hours: list[int] | None = None
    best_score = -1.0
    best_length = 0
    for length in WINDOW_LENGTHS:
        for start in range(24):
            hours = _window_hours(start, length)
            if any(h not in eligible for h in hours):
                continue
            # Weighted mean across the window.
            peak_rows_proxy = {key: [] for key, *_ in METRIC_DEFS}  # type: ignore[var-annotated]
            for h in hours:
                for key, *_ in METRIC_DEFS:
                    val = hourly_avgs[h].get(key)
                    if val is not None:
                        peak_rows_proxy[key].append(val)
            peak = {key: _mean(vals) for key, vals in peak_rows_proxy.items()}
            score = _degradation_index(peak, overall)
            # Prefer stronger degradation; on near-ties prefer longer windows.
            if score > best_score + 1e-6 or (
                abs(score - best_score) <= 1e-6 and length > best_length
            ):
                best_score = score
                best_hours = hours
                best_length = length
    return best_hours


def _bucket_series(
    rows: list[SpeedTestResult],
    *,
    key_fn,
    label_fn,
    peak_hours: set[int] | None,
) -> list[dict[str, Any]]:
    groups: dict[Any, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        key = key_fn(row)
        if key is None:
            continue
        groups[key].append(row)

    series: list[dict[str, Any]] = []
    for key in sorted(groups.keys(), key=lambda k: (str(type(k)), k)):
        items = groups[key]
        avgs = _metric_avgs(items)
        peak_items = (
            [r for r in items if _hour_of(r) in peak_hours] if peak_hours is not None else []
        )
        off_items = (
            [r for r in items if _hour_of(r) not in peak_hours] if peak_hours is not None else items
        )
        peak_avgs = _metric_avgs(peak_items) if peak_items else {k: None for k, *_ in METRIC_DEFS}
        base_avgs = _metric_avgs(off_items) if off_items else avgs
        metrics = [
            _delta_block(
                key=mkey,
                label=label,
                unit=unit,
                higher_is_better=hib,
                peak_avg=peak_avgs.get(mkey),
                baseline_avg=base_avgs.get(mkey),
            )
            for mkey, label, unit, hib in METRIC_DEFS
        ]
        series.append(
            {
                "key": key,
                "label": label_fn(key),
                "tests": len(items),
                "peak_tests": len(peak_items),
                "baseline_tests": len(off_items),
                "degradation_score": _round(
                    _degradation_index(peak_avgs, base_avgs), 3
                ),
                "metrics": metrics,
                "averages": {k: _round(v) for k, v in avgs.items()},
            }
        )
    # Prefer higher degradation first when peak window known.
    series.sort(key=lambda row: (-(row["degradation_score"] or 0), -row["tests"]))
    return series


def analyze_peak_hours(
    db: Session,
    *,
    isp: str | None = None,
    package: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int | None = 90,
) -> dict[str, Any]:
    all_rows = _load_rows(db)
    available_isps = sorted({normalize_isp(r.isp_name) for r in all_rows})
    available_packages = sorted({_package_of(r) for r in all_rows if _package_of(r) != "Unspecified"})
    available_regions = sorted({_region_of(r) for r in all_rows if _region_of(r) != "Unknown"})

    rows = _filter_rows(
        all_rows,
        isp=isp,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=None if (date_from or date_to) else days,
    )

    buckets = _hour_buckets(rows)
    hourly_avgs: dict[int, dict[str, float | None]] = {}
    hourly_counts: dict[int, int] = {}
    hourly_series: list[dict[str, Any]] = []
    for hour in range(24):
        items = buckets.get(hour) or []
        hourly_counts[hour] = len(items)
        avgs = _metric_avgs(items) if items else {k: None for k, *_ in METRIC_DEFS}
        if items:
            hourly_avgs[hour] = avgs
        hourly_series.append(
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "tests": len(items),
                "averages": {k: _round(v) for k, v in avgs.items()},
                "in_peak_window": False,
            }
        )

    peak_hours = _find_peak_window(hourly_avgs, hourly_counts)
    peak_window = None
    if peak_hours:
        peak_set = set(peak_hours)
        for item in hourly_series:
            item["in_peak_window"] = item["hour"] in peak_set

        peak_rows = [r for r in rows if _hour_of(r) in peak_set]
        baseline_rows = [r for r in rows if _hour_of(r) not in peak_set]
        peak_avgs = _metric_avgs(peak_rows)
        baseline_avgs = _metric_avgs(baseline_rows) if baseline_rows else _metric_avgs(rows)
        hour_from, hour_to, label = _format_window(peak_hours)
        metrics = [
            _delta_block(
                key=mkey,
                label=mlabel,
                unit=unit,
                higher_is_better=hib,
                peak_avg=peak_avgs.get(mkey),
                baseline_avg=baseline_avgs.get(mkey),
            )
            for mkey, mlabel, unit, hib in METRIC_DEFS
        ]
        peak_window = {
            "hour_from": hour_from,
            "hour_to": hour_to,
            "hours": peak_hours,
            "label": label,
            "tests": len(peak_rows),
            "baseline_tests": len(baseline_rows),
            "degradation_score": _round(_degradation_index(peak_avgs, baseline_avgs), 3),
            "metrics": metrics,
        }

    peak_set_for_break = set(peak_hours) if peak_hours else None
    by_day = _bucket_series(
        rows,
        key_fn=_dow_of,
        label_fn=lambda d: DAY_NAMES[int(d)] if d is not None else "Unknown",
        peak_hours=peak_set_for_break,
    )
    by_isp = _bucket_series(
        rows,
        key_fn=lambda r: normalize_isp(r.isp_name),
        label_fn=lambda k: str(k),
        peak_hours=peak_set_for_break,
    )
    by_region = _bucket_series(
        rows,
        key_fn=_region_of,
        label_fn=lambda k: str(k),
        peak_hours=peak_set_for_break,
    )
    by_package = _bucket_series(
        rows,
        key_fn=_package_of,
        label_fn=lambda k: str(k),
        peak_hours=peak_set_for_break,
    )

    return {
        "disclaimer": DISCLAIMER,
        "interpretation": INTERPRETATION if peak_window else (
            "Insufficient hourly samples to identify a peak-degradation window."
        ),
        "peak_window": peak_window,
        "hourly": hourly_series,
        "by_day_of_week": by_day,
        "breakdowns": {
            "isp": by_isp,
            "region": by_region,
            "package": by_package,
        },
        "filters": {
            "isp": isp,
            "package": package,
            "region": region,
            "date_from": date_from,
            "date_to": date_to,
            "days": None if (date_from or date_to) else days,
        },
        "available_isps": available_isps,
        "available_packages": available_packages,
        "available_regions": available_regions,
        "total_tests": len(rows),
        "generated_at": _utcnow().isoformat(),
    }
