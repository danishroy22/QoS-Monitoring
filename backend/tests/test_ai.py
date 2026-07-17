"""Tests for Phase 6 Generative AI analysis (offline fallback path)."""

from __future__ import annotations

import unittest

from app.services.ai_fallback import generate_fallback_analysis
from app.services.ai_prompts import SYSTEM_PROMPT, build_user_prompt


class FallbackAnalysisTests(unittest.TestCase):
    def test_congestion_playbook(self) -> None:
        result = generate_fallback_analysis(
            {
                "node_code": "BNG-DXB-001",
                "region": "Dubai North",
                "suspected_issue": "congestion",
                "latency_ms": 90,
                "packet_loss_pct": 1.8,
                "bandwidth_utilisation_pct": 93,
                "severity_hint": "high",
            }
        )
        self.assertIn("BNG-DXB-001", result["summary"])
        self.assertGreaterEqual(len(result["likely_causes"]), 2)
        self.assertGreaterEqual(len(result["recommended_actions"]), 2)
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["model_provider"], "offline-fallback-v1")

    def test_outage_severity(self) -> None:
        result = generate_fallback_analysis(
            {
                "node_code": "FWA-AUH-001",
                "region": "Abu Dhabi Suburban",
                "suspected_issue": "outage",
                "availability_pct": 12,
                "latency_ms": 400,
                "packet_loss_pct": 15,
            }
        )
        self.assertEqual(result["severity"], "critical")
        self.assertTrue(any("outage" in c.lower() or "failure" in c.lower() for c in result["likely_causes"]))


class PromptTests(unittest.TestCase):
    def test_user_prompt_includes_metrics(self) -> None:
        prompt = build_user_prompt(
            {
                "node_code": "DSL-SHJ-001",
                "region": "Sharjah Central",
                "access_technology": "DSL",
                "service_tier_mbps": 50,
                "suspected_issue": "packet_loss",
                "anomaly_score": -0.1,
                "severity_hint": "high",
                "timestamp": "2026-07-17T12:00:00Z",
                "latency_ms": 55,
                "jitter_ms": 18,
                "packet_loss_pct": 4.2,
                "throughput_mbps": 12,
                "bandwidth_utilisation_pct": 70,
                "signal_quality": 80,
                "availability_pct": 99,
                "scenario_label": "packet_loss",
                "recent_history": ["sample-1"],
            }
        )
        self.assertIn("DSL-SHJ-001", prompt)
        self.assertIn("packet_loss", prompt)
        self.assertIn(SYSTEM_PROMPT.split(".", 1)[0], SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
