"""Tests for QoS Analysis Engine and Internet Quality schemas."""

from __future__ import annotations

import unittest

from measurement.qos_analysis import analyze_qos, rating_from_score


class QosAnalysisTests(unittest.TestCase):
    def test_excellent_connection(self) -> None:
        report = analyze_qos(
            {
                "download_mbps": 250,
                "upload_mbps": 60,
                "ping_ms": 12,
                "jitter_ms": 2,
                "packet_loss_pct": 0,
                "dns_lookup_ms": 15,
                "http_response_ms": 120,
            }
        )
        self.assertGreaterEqual(report.overall_score, 90)
        self.assertEqual(report.overall_rating, "Excellent")

    def test_poor_packet_loss_drags_score(self) -> None:
        report = analyze_qos(
            {
                "download_mbps": 100,
                "upload_mbps": 20,
                "ping_ms": 30,
                "jitter_ms": 8,
                "packet_loss_pct": 8,
                "dns_lookup_ms": 40,
                "http_response_ms": 200,
            }
        )
        loss = next(m for m in report.metrics if m.name == "Packet Loss")
        self.assertEqual(loss.rating, "Critical")
        self.assertLess(report.overall_score, 90)

    def test_rating_bands(self) -> None:
        self.assertEqual(rating_from_score(95), "Excellent")
        self.assertEqual(rating_from_score(80), "Good")
        self.assertEqual(rating_from_score(65), "Fair")
        self.assertEqual(rating_from_score(45), "Poor")
        self.assertEqual(rating_from_score(10), "Critical")


if __name__ == "__main__":
    unittest.main()
