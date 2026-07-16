"""Command-line interface for the broadband QoS simulator.

Purpose
-------
Provide a single entry point to:
- generate historical labelled datasets (CSV) for ML training
- run a live tick loop that prints or POSTs measurements
- force a specific degradation scenario for demos and testing

Placement
---------
``backend/simulator/cli.py`` — run via::

    python -m backend.simulator.cli --mode batch --samples 100
    python -m backend.simulator.cli --mode live --ticks 20 --interval 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .generator import QoSSimulator
from .models import ScenarioType
from .publishers import ApiPublisher, CsvPublisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Broadband QoS Network Simulator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=("batch", "live"),
        default="batch",
        help="batch = historical CSV dataset; live = periodic tick loop",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=120,
        help="Samples per node in batch mode",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=0,
        help="Number of live ticks (0 = run until interrupted)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Seconds between live ticks / batch sample spacing",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible datasets",
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.08,
        help="Probability of starting a degradation when currently normal",
    )
    parser.add_argument(
        "--force-scenario",
        choices=[s.value for s in ScenarioType],
        default=None,
        help="Force every sample into one scenario (useful for demos)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/simulator",
        help="Directory for CSV measurement and event exports",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="FastAPI base URL for live publishing",
    )
    parser.add_argument(
        "--publish-api",
        action="store_true",
        help="POST each measurement to /api/measurements",
    )
    parser.add_argument(
        "--dry-run-api",
        action="store_true",
        help="Simulate API publishing without network calls",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print each tick as JSON to stdout",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser


def run_batch(args: argparse.Namespace) -> int:
    force = ScenarioType(args.force_scenario) if args.force_scenario else None
    simulator = QoSSimulator(
        seed=args.seed,
        force_scenario=force,
        anomaly_rate=args.anomaly_rate,
        interval_seconds=args.interval,
    )
    # Deterministic historical window so seeded runs are fully reproducible.
    start_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    measurements = simulator.generate_batch(args.samples, start_time=start_time)
    publisher = CsvPublisher(args.output_dir)
    measurements_path = publisher.write_measurements(measurements)
    events_path = publisher.write_events(simulator.events)

    labels: dict[str, int] = {}
    for sample in measurements:
        labels[sample.scenario_label] = labels.get(sample.scenario_label, 0) + 1

    print(f"Generated {len(measurements)} measurements across {len(simulator.nodes)} nodes")
    print(f"Scenario distribution: {labels}")
    print(f"Ground-truth events: {len(simulator.events)}")
    print(f"Measurements CSV: {measurements_path}")
    print(f"Events CSV: {events_path}")
    return 0


def run_live(args: argparse.Namespace) -> int:
    force = ScenarioType(args.force_scenario) if args.force_scenario else None
    simulator = QoSSimulator(
        seed=args.seed,
        force_scenario=force,
        anomaly_rate=args.anomaly_rate,
        interval_seconds=args.interval,
    )
    csv_publisher = CsvPublisher(args.output_dir)
    api_publisher = None
    if args.publish_api or args.dry_run_api:
        api_publisher = ApiPublisher(
            args.api_url,
            dry_run=args.dry_run_api or not args.publish_api,
        )

    max_ticks = args.ticks if args.ticks > 0 else None
    tick_count = 0
    print(
        f"Starting live simulation "
        f"(interval={args.interval}s, nodes={len(simulator.nodes)}, "
        f"max_ticks={max_ticks or 'infinite'})"
    )

    try:
        for batch in simulator.stream(max_ticks=max_ticks):
            tick_count += 1
            csv_publisher.append_measurements(batch)

            if api_publisher is not None:
                api_publisher.publish_many(batch)

            if args.print_json:
                print(json.dumps([m.to_dict() for m in batch], indent=2))
            else:
                stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
                summary = ", ".join(
                    f"{m.node_code}:{m.scenario_label}"
                    f"(lat={m.latency_ms}ms, loss={m.packet_loss_pct}%)"
                    for m in batch
                )
                print(f"[{stamp}] tick={tick_count} | {summary}")

            if max_ticks is None or tick_count < max_ticks:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")
    finally:
        simulator.engine.close_all(datetime.now(timezone.utc))
        csv_publisher.write_events(simulator.events)
        if api_publisher is not None:
            print(
                f"API publish summary: "
                f"ok={api_publisher.success_count}, "
                f"failed={api_publisher.failure_count}"
            )
        print(f"Live measurements appended to {csv_publisher.measurements_path}")
        print(f"Events written to {csv_publisher.events_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Resolve relative output paths from repository root when possible.
    output = Path(args.output_dir)
    if not output.is_absolute():
        # Prefer project root (two levels above this file: backend/simulator).
        project_root = Path(__file__).resolve().parents[2]
        args.output_dir = str(project_root / output)

    if args.mode == "batch":
        return run_batch(args)
    return run_live(args)


if __name__ == "__main__":
    sys.exit(main())
