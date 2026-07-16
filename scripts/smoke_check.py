"""Quick end-to-end smoke check against a running backend."""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def get(path: str):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.load(resp)


def main() -> int:
    health = get("/health")
    print("HEALTH:", health)

    latest = get("/api/metrics/latest")
    print("LATEST:")
    for row in latest:
        print(
            f"  {row['node_code']}: {row['scenario_label']} "
            f"health={row['health_status']} "
            f"lat={row['latency_ms']}ms loss={row['packet_loss_pct']}%"
        )

    history = get("/api/metrics/history?node_code=DSL-SHJ-001&metric=latency_ms")
    print("HISTORY DSL-SHJ-001 latency points:", len(history["points"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
