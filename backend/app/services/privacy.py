"""Privacy helpers for traceable measurement context (Phase 3).

Raw public IPs are optional. Aggregation and cross-run correlation should use
``client_hash`` (HMAC-SHA256) so the dissertation can avoid unnecessary PII.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


def anonymize_client_id(public_ip: str | None, *, salt: str) -> str | None:
    """Return a stable, non-reversible client identifier from a public IP."""
    value = (public_ip or "").strip()
    if not value:
        return None
    digest = hmac.new(
        (salt or "smartqos").encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:32]


def time_buckets(ts: datetime | None) -> dict[str, int | str | None]:
    """UTC calendar buckets used for aggregation by date / day / hour."""
    if ts is None:
        return {"test_date": None, "day_of_week": None, "hour_utc": None}
    aware = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    utc = aware.astimezone(timezone.utc)
    return {
        "test_date": utc.date().isoformat(),
        "day_of_week": int(utc.weekday()),  # Monday=0 … Sunday=6
        "hour_utc": int(utc.hour),
    }
