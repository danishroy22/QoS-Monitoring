"""Output publishers for CSV files and the FastAPI ingestion endpoint."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import NetworkEvent, QoSMeasurement

logger = logging.getLogger(__name__)

MEASUREMENT_FIELDS = [
    "node_code",
    "timestamp",
    "latency_ms",
    "jitter_ms",
    "packet_loss_pct",
    "throughput_mbps",
    "bandwidth_utilisation_pct",
    "signal_quality",
    "availability_pct",
    "scenario_label",
]

EVENT_FIELDS = [
    "event_id",
    "node_code",
    "event_type",
    "severity",
    "start_time",
    "end_time",
    "description",
]


class CsvPublisher:
    """Write QoS measurements and events to CSV for offline analysis."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.measurements_path = self.output_dir / "qos_measurements.csv"
        self.events_path = self.output_dir / "network_events.csv"

    def write_measurements(self, measurements: Iterable[QoSMeasurement]) -> Path:
        rows = [m.to_csv_row() for m in measurements]
        with self.measurements_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MEASUREMENT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Wrote %s measurements to %s", len(rows), self.measurements_path)
        return self.measurements_path

    def append_measurements(self, measurements: Iterable[QoSMeasurement]) -> Path:
        rows = [m.to_csv_row() for m in measurements]
        write_header = not self.measurements_path.exists()
        with self.measurements_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MEASUREMENT_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
        return self.measurements_path

    def write_events(self, events: Iterable[NetworkEvent]) -> Path:
        rows = [e.to_dict() for e in events]
        with self.events_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Wrote %s events to %s", len(rows), self.events_path)
        return self.events_path


class ApiPublisher:
    """POST measurements to the FastAPI ``/api/measurements`` endpoint.

    Phase 3 will implement the backend. Until then, this publisher can run
    in dry-run mode or report connection errors without crashing the simulator.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        timeout_seconds: float = 5.0,
        dry_run: bool = False,
    ) -> None:
        self.endpoint = base_url.rstrip("/") + "/api/measurements"
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run
        self.success_count = 0
        self.failure_count = 0

    def publish(self, measurement: QoSMeasurement) -> bool:
        payload = measurement.to_dict()
        if self.dry_run:
            logger.debug("Dry-run publish: %s", payload)
            self.success_count += 1
            return True

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if 200 <= response.status < 300:
                    self.success_count += 1
                    return True
                self.failure_count += 1
                logger.warning("API publish failed with status %s", response.status)
                return False
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            self.failure_count += 1
            logger.warning("API publish error: %s", exc)
            return False

    def publish_many(self, measurements: Iterable[QoSMeasurement]) -> tuple[int, int]:
        for measurement in measurements:
            self.publish(measurement)
        return self.success_count, self.failure_count
