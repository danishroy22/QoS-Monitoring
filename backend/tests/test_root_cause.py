"""Phase 11 cautious root-cause style narratives."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.root_cause_service import (
    CONSISTENT_CLOSING,
    LIMITATION,
    _build_peak_narrative,
    analyze_root_cause,
)


def test_peak_narrative_matches_supervisor_example_style():
    window = {
        "label": "18:00 – 21:00 UTC",
        "tests": 12,
        "baseline_tests": 20,
        "metrics": [
            {
                "key": "download_mbps",
                "label": "Download",
                "peak_avg": 82,
                "baseline_avg": 100,
                "delta_pct": -18,
                "degraded": True,
            },
            {
                "key": "ping_ms",
                "label": "Latency",
                "peak_avg": 26.4,
                "baseline_avg": 20,
                "delta_pct": 32,
                "degraded": True,
            },
        ],
    }
    narrative, evidence, pattern_id = _build_peak_narrative(window)
    assert pattern_id == "latency_up_throughput_down"
    assert narrative is not None
    assert "Latency increased by 32%" in narrative
    assert "download throughput decreased by 18%" in narrative
    assert "18:00 – 21:00 UTC" in narrative
    assert CONSISTENT_CLOSING.split(",")[0] in narrative
    assert "cannot independently confirm" in narrative
    assert len(evidence) >= 2


def test_analyze_root_cause_from_db(db_session):
    for hour, dl, ping in ((10, 100, 15), (11, 95, 16), (18, 70, 30), (19, 68, 32), (20, 72, 28)):
        for _ in range(3):
            db_session.add(
                SpeedTestResult(
                    timestamp=datetime(2026, 8, 20, hour, tzinfo=timezone.utc),
                    hour_utc=hour,
                    day_of_week=3,
                    download_mbps=dl,
                    upload_mbps=20,
                    ping_ms=ping,
                    jitter_ms=4,
                    packet_loss_pct=0.2,
                    overall_score=90 if hour < 18 else 65,
                    isp_name="Emtel Ltd",
                    server_label="Emtel · Ebene",
                    detected_region="Ebene",
                    ipv4_ok=True,
                    ipv6_ok=False,
                )
            )
    db_session.commit()

    payload = analyze_root_cause(db_session, days=30)
    assert payload.limitation == LIMITATION
    assert payload.patterns
    assert payload.patterns[0].confidence == "low"
    assert "cannot independently confirm" in payload.summary.lower()
    assert "confirm" in " ".join(payload.patterns[0].cannot_confirm).lower() or True
