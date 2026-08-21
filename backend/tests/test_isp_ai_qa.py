"""Phase 10 — grounded ISP AI Q&A."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.isp_ai_qa import (
    EXAMPLE_QUESTIONS,
    _detect_intent,
    answer_isp_question,
    build_isp_facts,
)


def test_detect_intent_examples():
    intent, _ = _detect_intent("Which ISP has the best average latency?")
    assert intent == "best_latency"
    intent, _ = _detect_intent("Which ISP has the best package fulfilment?")
    assert intent == "best_fulfilment"
    intent, _ = _detect_intent("Which regions experience the greatest degradation?")
    assert intent == "region_degradation"
    intent, isp = _detect_intent("When does Emtel experience its worst performance?")
    assert intent == "isp_worst_time"
    assert isp == "Emtel"
    intent, _ = _detect_intent("How has Mauritius broadband performance changed?")
    assert intent == "mauritius_trend"
    intent, _ = _detect_intent("Which packages consistently underperform?")
    assert intent == "underperforming_packages"


def test_answer_best_latency_from_facts(db_session):
    db_session.add_all(
        [
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 10, tzinfo=timezone.utc),
                download_mbps=90,
                upload_mbps=30,
                ping_ms=12,
                jitter_ms=2,
                packet_loss_pct=0,
                overall_score=92,
                isp_name="Emtel Ltd",
                internet_package="Fibre 100",
                advertised_download_mbps=100,
                advertised_upload_mbps=40,
                download_fulfilment_pct=90,
                upload_fulfilment_pct=75,
                server_label="Emtel · Ebene",
                detected_region="Ebene",
                hour_utc=10,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 11, tzinfo=timezone.utc),
                download_mbps=200,
                upload_mbps=40,
                ping_ms=35,
                jitter_ms=8,
                packet_loss_pct=1,
                overall_score=70,
                isp_name="Rogers",
                internet_package="Fibre 200",
                advertised_download_mbps=200,
                advertised_upload_mbps=50,
                download_fulfilment_pct=100,
                upload_fulfilment_pct=80,
                server_label="Rogers · Rose-Hill",
                detected_region="Rose Hill",
                hour_utc=11,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
        ]
    )
    db_session.commit()

    facts = build_isp_facts(db_session, days=30)
    assert facts["best_latency_isp"]["isp"] == "Emtel"
    assert facts["best_latency_isp"]["avg_ping_ms"] == 12

    result = answer_isp_question(
        db_session, question=EXAMPLE_QUESTIONS[0], days=30
    )
    assert result.intent == "best_latency"
    assert "Emtel" in result.answer
    assert "12" in result.answer
    assert result.model_provider == "offline-playbook"
    assert any(c.source == "isp_analytics" for c in result.citations)

    fulfil = answer_isp_question(
        db_session, question="Which ISP has the best package fulfilment?", days=30
    )
    assert fulfil.intent == "best_fulfilment"
    assert "Rogers" in fulfil.answer or "Emtel" in fulfil.answer
