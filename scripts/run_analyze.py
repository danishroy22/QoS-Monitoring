"""Call POST /api/analyze against a running backend."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def main() -> int:
    node = sys.argv[1] if len(sys.argv) > 1 else "BNG-DXB-001"
    payload = json.dumps(
        {"node_code": node, "include_recent_history": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/analyze",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.load(resp)
    except urllib.error.URLError as exc:
        print("API_UNAVAILABLE", exc)
        return 1

    print("node:", body.get("node_code"))
    print("provider:", body.get("model_provider"))
    print("severity:", body.get("severity"))
    print("summary:", body.get("summary"))
    print("causes:")
    for item in body.get("likely_causes", []):
        print(" -", item)
    print("actions:")
    for item in body.get("recommended_actions", []):
        print(" -", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
