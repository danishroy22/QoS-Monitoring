"""Smoke-test the Internet Quality API with a quick speedtest."""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def main() -> int:
    req = urllib.request.Request(
        f"{BASE}/speedtest",
        data=json.dumps({"quick": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.load(resp)

    result = body["result"]
    health = body["health"]
    print("SCORE", health["overall_score"], health["overall_rating"])
    print(
        "DOWN",
        result["download_mbps"],
        "UP",
        result["upload_mbps"],
        "PING",
        result["ping_ms"],
        "LOSS",
        result["packet_loss_pct"],
    )
    print("ISP", result["isp_name"], result["public_ip"])
    print("DNS", result["dns_lookup_ms"], "HTTP", result["http_response_ms"])
    print("IP4/IP6", result["ipv4_ok"], result["ipv6_ok"])
    print("ERRORS", body.get("errors"))

    with urllib.request.urlopen(f"{BASE}/recommendation", timeout=30) as resp:
        rec = json.load(resp)
    print("AI", rec["analysis"][:220])
    print("REASONS", rec["possible_reasons"][:2])
    print("ACTIONS", rec["recommended_actions"][:2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
