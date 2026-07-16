"""Trigger anomaly detection on a running backend and print results."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def main() -> int:
    req = urllib.request.Request(
        f"{BASE}/api/anomalies/run?limit=500&only_unscored=false",
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print("RUN", resp.status, resp.read().decode())
        with urllib.request.urlopen(f"{BASE}/api/anomalies?active_only=true&limit=10") as resp:
            data = json.load(resp)
        print("ANOMALIES", len(data))
        for row in data[:8]:
            print(
                f"  {row['node_code']} {row['severity']} "
                f"{row['suspected_issue']} score={row['anomaly_score']:.4f}"
            )
    except urllib.error.URLError as exc:
        print("API_UNAVAILABLE", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
